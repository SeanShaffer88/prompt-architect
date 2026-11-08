"""Documentation linter for the Prompt Architect specification set.

The linter enforces the conventions this repository publishes: front-matter
shape, the 5-component section order, paired negative constraints, a fallback
protocol, a deterministic output container, and an acceptance checklist.

Every rule exists because its absence produced a real, observable failure mode
in a prompt. That is the same bar the docs hold prompt constraints to.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from . import frontmatter

VALID_TYPES = {"blueprint", "pattern", "benchmark", "guide", "reference"}
REQUIRED_META = ("name", "type", "version", "output_format")
SEMVER = re.compile(r"^\d+\.\d+\.\d+$")

# Blueprints must map onto the 5-component architecture (components 1-5).
BLUEPRINT_SECTIONS = (
    ("role", r"\brole\b"),
    ("context", r"\bcontext\b"),
    ("objective", r"\bobjective\b"),
    ("constraints", r"\bconstraints?\b"),
    ("output specification", r"\boutput\b.*\b(spec|specification)\b"),
)

NEGATIVE_PATTERN = re.compile(r"\bdo not\b|\bdon't\b|\bnever\b|\bforbid", re.I)
FALLBACK_PATTERN = re.compile(
    r"\bfallback\b|\bnull\b|\binsufficient\b|\bunconfirmed\b|\bunsatisfiable\b"
    r"|\bempty input\b|\bstatus\b",
    re.I,
)
DETERMINISM_PATTERN = re.compile(
    r"```|first character|raw json|no prose|no preamble|no fences|"
    r"markdown with these sections|exact|table",
    re.I,
)
LINK_PATTERN = re.compile(r"\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.*?)\s*$")

SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "dist", "build"}


@dataclass(frozen=True)
class Finding:
    rule: str
    severity: str  # "error" | "warn"
    path: str
    message: str

    def format(self) -> str:
        marker = "ERROR" if self.severity == "error" else "WARN "
        return f"{marker} {self.rule} {self.path}: {self.message}"


def _headings(body: str) -> list[tuple[int, str]]:
    found = []
    for line in body.splitlines():
        match = HEADING_PATTERN.match(line)
        if match:
            found.append((len(match.group(1)), match.group(2)))
    return found


def _has_section(body: str, pattern: str) -> bool:
    """True when a heading matches ``pattern`` (headings only, not prose)."""
    for _, title in _headings(body):
        if re.search(pattern, title, re.I):
            return True
    return False


def _section_text(body: str, pattern: str) -> str:
    """Body text of the first matching section, up to the next heading of the
    same or shallower level. Empty string when no section matches."""
    lines = body.splitlines()
    start = level = None
    for i, line in enumerate(lines):
        match = HEADING_PATTERN.match(line)
        if match and re.search(pattern, match.group(2), re.I):
            start, level = i + 1, len(match.group(1))
            break
    if start is None or level is None:
        return ""
    collected = []
    for line in lines[start:]:
        match = HEADING_PATTERN.match(line)
        if match and len(match.group(1)) <= level:
            break
        collected.append(line)
    return "\n".join(collected)


def lint_document(doc: frontmatter.Document) -> list[Finding]:
    findings: list[Finding] = []
    path = str(doc.path)
    meta, body = doc.meta, doc.body

    def add(rule: str, message: str, severity: str = "error") -> None:
        findings.append(Finding(rule, severity, path, message))

    in_spec_tree = any(
        part in {"blueprints", "patterns", "benchmarks"} for part in doc.path.parts
    )

    if not doc.has_front_matter:
        # Narrative files (README, run provenance notes) are not specs.
        if in_spec_tree and doc.path.name != "README.md":
            add("PA001", "missing YAML front-matter (name/type/version/... required)")
        return findings

    for key in REQUIRED_META:
        if not str(meta.get(key, "")).strip():
            add("PA001", f"front-matter is missing required key '{key}'")

    doc_type = str(meta.get("type", "")).strip()
    if doc_type and doc_type not in VALID_TYPES:
        add("PA002", f"type '{doc_type}' is not one of {sorted(VALID_TYPES)}")

    version = str(meta.get("version", "")).strip()
    if version and not SEMVER.match(version):
        add("PA003", f"version '{version}' is not semver (MAJOR.MINOR.PATCH)")

    if doc_type in {"blueprint", "pattern"} and not meta.get("inputs"):
        add("PA001", "front-matter 'inputs' is required for blueprints and patterns")

    # PA004 — blueprints must expose the 5-component architecture by name.
    if doc_type == "blueprint":
        for label, pattern in BLUEPRINT_SECTIONS:
            if not _has_section(body, pattern):
                add("PA004", f"blueprint is missing the '{label}' component section")

    # PA005 — every spec ends with a pass/fail bar.
    if not _has_section(body, r"acceptance checklist"):
        add("PA005", "no 'Acceptance Checklist' section; the spec has no pass/fail bar")

    # PA006 — negative constraints carry equal weight to positive ones.
    if not NEGATIVE_PATTERN.search(body):
        add("PA006", "no negative constraint found (DO NOT / never); "
                    "positive instructions without inverses are unenforceable")

    # PA007 — every prompt needs a deterministic story for the unknown.
    if not FALLBACK_PATTERN.search(body):
        add("PA007", "no fallback protocol, null policy, or insufficient-evidence "
                    "path; the model will invent a value instead")

    # PA008 — the output container must be pinned, not described.
    output_section = _section_text(body, r"\boutput\b.*\b(spec|specification)\b")
    if doc_type == "blueprint":
        if not output_section:
            add("PA008", "no output specification section to pin the container")
        elif not DETERMINISM_PATTERN.search(output_section):
            add("PA008", "output specification does not pin a container/format "
                        "(fence, first character, raw JSON, or section list)")

    # PA010 — front-matter drift: an input declared but never mentioned anywhere.
    # Warn only when *no* token of the snake_case name appears, so legitimate
    # phrasings ("target_model" documented as "Target Model") stay quiet.
    inputs = meta.get("inputs") or []
    if isinstance(inputs, list):
        for item in inputs:
            tokens = [t for t in str(item).split("_") if len(t) > 2]
            if tokens and not any(re.search(rf"\b{re.escape(t)}\b", body, re.I) for t in tokens):
                add("PA010", f"declared input '{item}' never appears in the body",
                    severity="warn")

    return findings


def lint_links(root: Path) -> list[Finding]:
    findings = []
    for path in _markdown_files(root):
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for target in LINK_PATTERN.findall(text):
            if target.startswith(("http://", "https://", "mailto:", "#")):
                continue
            resolved = (path.parent / target.split("#", 1)[0]).resolve()
            if not resolved.exists():
                rel = path.relative_to(root) if path.is_relative_to(root) else path
                findings.append(
                    Finding("PA009", "error", str(rel), f"broken relative link -> {target}")
                )
    return findings


def _markdown_files(root: Path):
    for path in sorted(root.rglob("*.md")):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        yield path


def lint_paths(paths: list[str] | None = None) -> list[Finding]:
    """Lint the given files/directories (default: repository root)."""
    targets = [Path(p) for p in (paths or ["."])]
    findings: list[Finding] = []
    for target in targets:
        if target.is_dir():
            for path in _markdown_files(target):
                findings.extend(lint_document(frontmatter.load(path)))
            findings.extend(lint_links(target))
        elif target.suffix == ".md":
            findings.extend(lint_document(frontmatter.load(target)))
            findings.extend(lint_links(target.parent))
    # De-duplicate: navigating several paths can revisit the same broken link.
    seen, unique = set(), []
    for finding in findings:
        key = (finding.rule, finding.path, finding.message)
        if key not in seen:
            seen.add(key)
            unique.append(finding)
    return unique
