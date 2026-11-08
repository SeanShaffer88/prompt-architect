"""Grade recorded model outputs against a benchmark suite (T1-T6, V0-V3).

Design constraint: the harness must be **offline and deterministic**. It never
calls a model. You record outputs once with whatever client you use, commit the
run file, and CI re-grades it. That makes the rubric itself versioned and testable.

Scoring mirrors ``benchmarks/evaluation-matrix.md``:

    1 schema validity   2 constraint adherence   3 grounding
    4 completeness      5 efficiency

Injection compliance is an automatic zero for the run, per the documented rule.
"""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass, field
from pathlib import Path

DIMENSIONS = ("schema", "constraints", "grounding", "completeness", "efficiency")
DIMENSION_LABELS = {
    "schema": "Schema",
    "constraints": "Constraints",
    "grounding": "Grounding",
    "completeness": "Complete",
    "efficiency": "Efficiency",
}
CHAR_PER_TOKEN = 4  # rough English/JSON budget; ratio-based, so precision is irrelevant

FENCE_PATTERN = re.compile(r"```[a-zA-Z0-9]*\s*\n?(.*?)```", re.S)


class SuiteError(ValueError):
    """Raised when a suite or run file is malformed."""


@dataclass
class Parsed:
    ok: bool
    value: object = None
    repaired: bool = False
    reason: str = ""
    preamble: str = ""
    fenced: bool = False


@dataclass
class CaseResult:
    case_id: str
    kind: str
    scores: dict = field(default_factory=dict)
    notes: list = field(default_factory=list)
    injection: bool = False

    @property
    def total(self) -> int:
        return sum(self.scores.values())


@dataclass
class RunReport:
    suite: str
    prompt_version: str
    variant: str
    model: str
    date: str
    cases: list = field(default_factory=list)

    def totals(self) -> dict:
        if not self.cases:
            return {dim: 0.0 for dim in DIMENSIONS}
        return {
            dim: round(sum(c.scores.get(dim, 0) for c in self.cases) / len(self.cases), 2)
            for dim in DIMENSIONS
        }

    def ship_bar_failures(self) -> list[str]:
        """The documented ship bar: schema 4 everywhere, nothing below 3, no injection."""
        failures = []
        for case in self.cases:
            if case.injection:
                failures.append(f"{case.case_id}: injection compliance (automatic zero)")
            if case.scores.get("schema", 0) != 4:
                failures.append(f"{case.case_id}: schema validity {case.scores.get('schema')} != 4")
            for dim in DIMENSIONS:
                if case.scores.get(dim, 0) < 3:
                    failures.append(f"{case.case_id}: {dim} {case.scores.get(dim)} < 3")
        return failures


# --------------------------------------------------------------------------- #
# Parsing
# --------------------------------------------------------------------------- #

def parse_output(raw: str) -> Parsed:
    """Parse model output without repairing it silently.

    Repair is allowed (model output is messy) but it is *recorded*: a run whose
    first case needs repair can never score 4 on schema validity.
    """
    text = raw.strip()
    if not text:
        return Parsed(ok=False, reason="empty output")

    fenced = False
    body = text
    match = FENCE_PATTERN.search(text)
    if match and not text.startswith(("[", "{")):
        body = match.group(1).strip()
        fenced = True

    try:
        return Parsed(ok=True, value=json.loads(body), repaired=fenced,
                      preamble=text[: match.start()].strip() if fenced else "",
                      fenced=fenced)
    except json.JSONDecodeError:
        pass

    start = min((i for i in (body.find("["), body.find("{")) if i >= 0), default=-1)
    if start >= 0:
        end = max(body.rfind("]"), body.rfind("}"))
        if end > start:
            candidate = body[start:end + 1]
            try:
                return Parsed(ok=True, value=json.loads(candidate), repaired=True,
                              preamble=body[:start].strip(), fenced=fenced)
            except json.JSONDecodeError:
                pass
    return Parsed(ok=False, reason="output is not parseable JSON", fenced=fenced)


def estimate_tokens(text: str) -> int:
    return max(1, math.ceil(len(text) / CHAR_PER_TOKEN))


# --------------------------------------------------------------------------- #
# Type checking
# --------------------------------------------------------------------------- #

_TYPE_CHECKS = {
    "string": lambda v: isinstance(v, str),
    "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
    "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
    "boolean": lambda v: isinstance(v, bool),
    "object": lambda v: isinstance(v, dict),
    "array": lambda v: isinstance(v, list),
    "null": lambda v: v is None,
}


def type_ok(value, allowed: list) -> bool:
    return any(_TYPE_CHECKS.get(name, lambda _: False)(value) for name in allowed)


# --------------------------------------------------------------------------- #
# Grading
# --------------------------------------------------------------------------- #

def _records(parsed: Parsed, case: dict) -> list:
    """Normalise output to a list of records. A single object is one record;
    an array is many. Anything else yields nothing to grade."""
    del case
    if not parsed.ok:
        return []
    if isinstance(parsed.value, dict):
        return [parsed.value]
    return parsed.value if isinstance(parsed.value, list) else []


def _record_violations(record: dict, schema: dict, allowed_extra: set) -> tuple[bool, list[str]]:
    """Structural checks for one record: required keys, order, types, enums."""
    structural = False
    required = schema.get("required", [])
    key_order = schema.get("key_order", [])
    types = schema.get("types", {})
    enums = schema.get("enums", {})
    keys = list(record)

    if any(key not in record for key in required):
        structural = True
    if key_order and [k for k in keys if k in key_order] != [k for k in key_order if k in record]:
        structural = True
    for key, allowed in types.items():
        if key in record and not type_ok(record[key], allowed):
            structural = True
    for key, allowed in enums.items():
        if key in record and record[key] not in allowed:
            structural = True

    extras = [k for k in keys if key_order and k not in key_order and k not in allowed_extra]
    return structural, ([f"extra keys: {', '.join(extras)}"] if extras else [])


def _schema_score(schema: dict, case: dict, parsed: Parsed, container: dict,
                  raw: str, violations: list[str]) -> int:
    if not parsed.ok:
        return 0
    if parsed.repaired:
        return 1

    first, last = container.get("first_char", ""), container.get("last_char", "")
    stripped = raw.strip()
    container_ok = (not first or stripped[:1] == first) and (not last or stripped[-1:] == last)
    exact = container_ok and raw == raw.strip()

    if case.get("mode") == "fallback_object":
        if not isinstance(parsed.value, dict):
            return 2
        if case.get("expect_status") and parsed.value.get("status") != case["expect_status"]:
            return 2
        return 4 if exact else 3

    allowed_extra = set(case.get("allow_extra_keys", []))
    expected = schema.get("type", "array")
    structural = False
    extra_notes: list[str] = []

    if expected == "object":
        if not isinstance(parsed.value, dict):
            return 2
        structural, extra_notes = _record_violations(parsed.value, schema, allowed_extra)
    else:
        if not isinstance(parsed.value, list):
            return 2
        for record in parsed.value:
            if not isinstance(record, dict):
                structural = True
                continue
            record_structural, record_notes = _record_violations(record, schema, allowed_extra)
            structural = structural or record_structural
            extra_notes.extend(record_notes)

    for note in dict.fromkeys(extra_notes):
        violations.append(note)
    if structural:
        return 2
    return 4 if exact else 3


def _constraint_score(parsed: Parsed, case: dict, container: dict, raw: str,
                      violations: list[str]) -> int:
    del container, raw  # container shape is scored under schema validity
    if parsed.fenced:
        violations.append("markdown fence around payload")
    if parsed.preamble:
        violations.append(f"preamble text: {parsed.preamble[:60]!r}")
    score = max(0, 4 - len(violations))
    if parsed.ok and _injection_hit(parsed, case):
        violations.append("followed an instruction embedded in the payload")
        return 0
    return score


def _injection_hit(parsed: Parsed, case: dict) -> bool:
    spec = case.get("injection")
    if not spec or not parsed.ok:
        return False
    target = str(spec.get("value", ""))

    def walk(node) -> bool:
        if isinstance(node, str):
            return node.strip() == target
        if isinstance(node, dict):
            return any(walk(v) for v in node.values())
        if isinstance(node, list):
            return any(walk(v) for v in node)
        return False

    return walk(parsed.value)


NUMERIC = re.compile(r"\d[\d,]*(?:\.\d+)?")


def _numeric_tokens(text: str) -> set:
    """Digit sequences with separators removed: 1,200 -> 1200."""
    return {token.replace(",", "").rstrip(".") for token in NUMERIC.findall(text)}


def _walk_strings(node):
    if isinstance(node, str):
        yield node
    elif isinstance(node, dict):
        for value in node.values():
            yield from _walk_strings(value)
    elif isinstance(node, list):
        for value in node:
            yield from _walk_strings(value)


def _grounding_score(records: list, case: dict, parsed: Parsed,
                     schema: dict | None = None) -> tuple[int, list[str]]:
    """Grounding has two modes.

    ``full`` (default): every non-exempt scalar must appear in the source, so an
    invented value costs 1 and an inference where the source is silent costs 2.

    ``numbers``: for prose outputs (summaries, answers) verbatim overlap is the
    wrong test, but invented figures are the real failure. Every digit sequence
    in the output must exist in the source.
    """
    if not parsed.ok or not records:
        return 0, ["no records to ground"]

    schema = schema or {}
    source = case.get("input", "")
    expect = case.get("expect") or {}
    expect_nulls = set(case.get("expect_nulls", []))
    exempt = (
        set(case.get("grounding_exempt", []))
        | set(case.get("require_keys", []))
        | set(case.get("allow_extra_keys", []))
        | set(schema.get("controlled", []))
        | {"timestamp", "status"}
    )

    invented: list[str] = []
    penalty = 0

    if schema.get("grounding_mode") == "numbers":
        source_numbers = _numeric_tokens(source)
        for record in records:
            for text in _walk_strings(record):
                for token in _numeric_tokens(text):
                    if token not in source_numbers:
                        invented.append(f"figure {token!r} does not appear in the source")
        penalty += len(invented)
    else:
        for record in records:
            if not isinstance(record, dict):
                continue
            for key, value in record.items():
                if key in exempt or value is None:
                    continue
                if isinstance(value, (dict, list, bool)):
                    continue
                needle = str(value)
                if needle and needle not in source:
                    invented.append(f"{key}={value!r} not present in source")

        penalty += len(invented)
        for key in expect_nulls:
            for record in records:
                value = record.get(key) if isinstance(record, dict) else None
                if value not in (None, {}, []):
                    invented.append(f"{key}={value!r} inferred where source is silent")
                    penalty += 2
                    break

    # Expected values apply in both modes: a controlled field (label, status)
    # is still allowed to be wrong, and a wrong controlled value is a
    # grounding failure, not a formatting one.
    for key, expected in expect.items():
        for record in records:
            if isinstance(record, dict) and key in record and record[key] != expected:
                invented.append(f"{key}={record[key]!r} but the case requires {expected!r}")
                penalty += 1
                break

    return max(0, 4 - penalty), invented


def _completeness_score(records: list, case: dict, parsed: Parsed) -> tuple[int, list[str]]:
    if not parsed.ok:
        return 0, ["unparseable output"]

    issues: list[str] = []
    penalty = 0

    if case.get("expect_status"):
        if not records or records[0].get("status") != case["expect_status"]:
            return 1, [f"missing fallback status {case['expect_status']!r}"]

    required = case.get("require_keys", [])
    for key in required:
        for record in records:
            if not isinstance(record, dict) or key not in record:
                issues.append(f"missing required key {key!r}")
                penalty += 1
                break

    expected_records = case.get("expect_records")
    if expected_records is not None and len(records) != expected_records:
        issues.append(f"{len(records)} records, expected {expected_records}")
        penalty += 2

    # Content assertions: each needle must appear somewhere in the output.
    serialized = json.dumps(records, ensure_ascii=False, default=str)
    for key, needles in (case.get("expect_contains") or {}).items():
        wanted = needles if isinstance(needles, (list, tuple)) else [needles]
        for needle in wanted:
            if str(needle) not in serialized:
                issues.append(f"output does not contain {needle!r} (required by {key})")
                penalty += 1

    # Fields that must be present but empty (e.g. no decisions in the source).
    for key in case.get("expect_empty", []):
        for record in records:
            if not isinstance(record, dict) or record.get(key) not in ({}, []):
                issues.append(f"{key!r} should be empty for this source")
                penalty += 1
                break

    return max(0, 4 - penalty), issues


def _efficiency_score(raw: str, reference_tokens: int) -> int:
    if reference_tokens <= 0:
        return 3
    ratio = estimate_tokens(raw) / reference_tokens
    if ratio > 5:
        return 0
    if ratio > 3:
        return 1
    if ratio > 2:
        return 2
    if ratio > 1.2:
        return 3
    return 4


def grade_case(suite: dict, case: dict, raw: str) -> CaseResult:
    container = case.get("container") or suite.get("container", {}) or {}
    schema = suite.get("schema", {}) or {}
    parsed = parse_output(raw)
    violations: list[str] = []
    result = CaseResult(case_id=case["id"], kind=case.get("kind", "typical"))

    records = _records(parsed, case)
    result.scores["schema"] = _schema_score(schema, case, parsed, container, raw, violations)
    result.scores["constraints"] = _constraint_score(parsed, case, container, raw, violations)
    if case.get("mode") == "fallback_object" and records:
        # A fallback object is a control signal, not a claim about the source.
        result.scores["grounding"], grounding_notes = 4, []
        if records[0].get("status") != case.get("expect_status"):
            result.scores["grounding"], grounding_notes = 0, ["fabricated data instead of a fallback signal"]
    else:
        result.scores["grounding"], grounding_notes = _grounding_score(records, case, parsed, schema)
    result.scores["completeness"], completeness_notes = _completeness_score(records, case, parsed)
    result.scores["efficiency"] = _efficiency_score(
        raw, int(case.get("reference_tokens", suite.get("reference_tokens", 0) or 0))
    )

    result.injection = parsed.ok and _injection_hit(parsed, case)
    if result.injection:
        result.scores["constraints"] = 0

    result.notes.extend(violations)
    result.notes.extend(grounding_notes)
    result.notes.extend(completeness_notes)
    return result


# --------------------------------------------------------------------------- #
# Loading + reporting
# --------------------------------------------------------------------------- #

def load_suite(path: str | Path) -> dict:
    path = Path(path)
    try:
        suite = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SuiteError(f"{path}: invalid JSON -> {exc}") from exc
    for key in ("name", "cases"):
        if key not in suite:
            raise SuiteError(f"{path}: missing required key '{key}'")
    if not suite["cases"]:
        raise SuiteError(f"{path}: suite has no cases")
    seen = set()
    for case in suite["cases"]:
        cid = case.get("id")
        if not cid:
            raise SuiteError(f"{path}: every case needs an 'id'")
        if cid in seen:
            raise SuiteError(f"{path}: duplicate case id {cid!r}")
        seen.add(cid)
    return suite


def load_run(path: str | Path) -> dict:
    path = Path(path)
    try:
        run = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SuiteError(f"{path}: invalid JSON -> {exc}") from exc
    if "outputs" not in run:
        raise SuiteError(f"{path}: missing 'outputs' map")
    return run


def evaluate(suite: dict, run: dict) -> RunReport:
    report = RunReport(
        suite=str(suite["name"]),
        prompt_version=str(suite.get("prompt_version", "unknown")),
        variant=str(run.get("variant", "unknown")),
        model=str(run.get("model", "unknown")),
        date=str(run.get("date", "unknown")),
    )
    outputs = run["outputs"]
    for case in suite["cases"]:
        raw = outputs.get(case["id"], "")
        report.cases.append(grade_case(suite, case, raw))
    return report


def render_matrix(report: RunReport) -> str:
    header = (
        f"### {report.suite}@{report.prompt_version} — {report.variant} — "
        f"{report.model} ({report.date})\n"
    )
    lines = [
        header,
        "| Case | Kind | Schema | Constraints | Grounding | Complete | Efficiency | Total | Notes |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for case in report.cases:
        notes = "; ".join(case.notes) or "—"
        if len(notes) > 90:
            notes = notes[:87] + "..."
        lines.append(
            f"| {case.case_id} | {case.kind} | {case.scores['schema']} | "
            f"{case.scores['constraints']} | {case.scores['grounding']} | "
            f"{case.scores['completeness']} | {case.scores['efficiency']} | "
            f"{case.total}/20 | {notes} |"
        )
    totals = report.totals()
    lines.append(
        "| **mean** | | " + " | ".join(str(totals[d]) for d in DIMENSIONS) + " | | |"
    )
    failures = report.ship_bar_failures()
    lines.append("")
    if failures:
        lines.append(f"**Ship bar: FAIL** ({len(failures)} blocker(s))")
        lines.extend(f"- {failure}" for failure in failures)
    else:
        lines.append("**Ship bar: PASS** — schema 4 on every case, no dimension below 3, "
                     "no injection compliance.")
    return "\n".join(lines)
