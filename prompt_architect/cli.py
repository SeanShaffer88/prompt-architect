"""Command-line interface: ``python -m prompt_architect <command>``.

    lint     check the docs against the repository's own conventions
    compose  render a prompt from a JSON spec at variant v0-v3
    eval     grade recorded model outputs against a T1-T6 suite

Exit codes are CI-friendly: 0 = clean, 1 = violations / failed ship bar,
2 = usage or malformed input.
"""

from __future__ import annotations

import argparse
import difflib
import json
import sys
from pathlib import Path

from . import __version__, evaluate, lint, spec


def _cmd_lint(args: argparse.Namespace) -> int:
    findings = lint.lint_paths(args.paths or ["."])
    if args.json:
        print(json.dumps([f.__dict__ for f in findings], indent=2))
    else:
        for finding in findings:
            print(finding.format())
        errors = sum(1 for f in findings if f.severity == "error")
        warns = len(findings) - errors
        print(f"\n{len(findings)} finding(s): {errors} error(s), {warns} warning(s)")
        if not findings:
            print("clean — front-matter, component sections, constraints, "
                  "fallbacks, containers, and links all check out.")
    errors = sum(1 for f in findings if f.severity == "error")
    warns = len(findings) - errors
    if errors:
        return 1
    return 1 if (args.strict and warns) else 0


def render_all(spec_path: str, variant: str) -> str:
    return spec.render_file(spec_path, variant)


def _cmd_compose(args: argparse.Namespace) -> int:
    variants = spec.VARIANTS if args.all else (args.variant,)
    status = 0
    for variant in variants:
        try:
            rendered = render_all(args.spec, variant)
        except (spec.SpecError, OSError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2

        if args.write:
            target = spec.golden_path(args.spec, variant)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(rendered, encoding="utf-8")
            print(f"wrote {target}", file=sys.stderr)
            continue

        if args.check and not args.all:
            target = spec.golden_path(args.spec, variant)
            if not target.exists():
                print(f"error: no golden file at {target}", file=sys.stderr)
                return 2
            golden = target.read_text(encoding="utf-8")
            if golden != rendered:
                status = 1
                diff = difflib.unified_diff(
                    golden.splitlines(), rendered.splitlines(),
                    fromfile=str(target), tofile=f"rendered:{variant}", lineterm="",
                )
                print("\n".join(diff))
            else:
                print(f"{args.spec} {variant}: matches {target}")
            continue

        if args.all:
            print(f"<!-- variant {variant} -->")
        print(rendered, end="" if rendered.endswith("\n") else "\n")
    return status


def _cmd_eval(args: argparse.Namespace) -> int:
    try:
        suite = evaluate.load_suite(args.suite)
    except (evaluate.SuiteError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    reports = []
    for run_path in args.run:
        try:
            reports.append(evaluate.evaluate(suite, evaluate.load_run(run_path)))
        except (evaluate.SuiteError, OSError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2

    if args.json:
        payload = [
            {
                "suite": r.suite,
                "prompt_version": r.prompt_version,
                "variant": r.variant,
                "model": r.model,
                "date": r.date,
                "cases": [
                    {"id": c.case_id, "kind": c.kind, "scores": c.scores,
                     "injection": c.injection, "notes": c.notes}
                    for c in r.cases
                ],
                "totals": r.totals(),
                "ship_bar_failures": r.ship_bar_failures(),
            }
            for r in reports
        ]
        print(json.dumps(payload, indent=2))
    else:
        for report in reports:
            print(evaluate.render_matrix(report))
            print()

    failed = any(r.ship_bar_failures() for r in reports)
    if args.no_ship_bar:
        return 0
    if args.expect_fail:
        if not failed:
            print("error: run passed the ship bar but --expect-fail was given "
                  "(the suite no longer discriminates)", file=sys.stderr)
            return 1
        return 0
    # Default: the ship bar is a gate, not a report.
    return 1 if failed else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="prompt-architect",
        description="Compose, lint, and evaluate engineered prompts.",
    )
    parser.add_argument("--version", action="version", version=f"prompt-architect {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    lint_cmd = sub.add_parser("lint", help="check docs against repository conventions")
    lint_cmd.add_argument("paths", nargs="*", help="files or directories (default: .)")
    lint_cmd.add_argument("--json", action="store_true", help="machine-readable output")
    lint_cmd.add_argument("--strict", action="store_true", help="treat warnings as failures")
    lint_cmd.set_defaults(func=_cmd_lint)

    compose = sub.add_parser("compose", help="render a prompt spec")
    compose.add_argument("spec", help="path to a JSON prompt spec")
    compose.add_argument("--variant", default="v3", choices=spec.VARIANTS,
                         help="enforcement level (default: v3, hardened)")
    compose.add_argument("--all", action="store_true", help="render every variant")
    compose.add_argument("--check", action="store_true",
                         help="compare against the golden file instead of printing")
    compose.add_argument("--write", action="store_true", help="write the golden file")
    compose.set_defaults(func=_cmd_compose)

    eval_cmd = sub.add_parser("eval", help="grade recorded outputs against a suite")
    eval_cmd.add_argument("suite", help="path to a benchmark suite JSON")
    eval_cmd.add_argument("--run", action="append", required=True,
                          help="path to a run JSON (repeatable)")
    eval_cmd.add_argument("--json", action="store_true", help="machine-readable output")
    eval_cmd.add_argument("--no-ship-bar", action="store_true",
                          help="report scores without failing the build")
    eval_cmd.add_argument("--expect-pass", action="store_true",
                          help="fail if the run does NOT meet the ship bar")
    eval_cmd.add_argument("--expect-fail", action="store_true",
                          help="fail if the run DOES meet the ship bar (regression guard)")
    eval_cmd.set_defaults(func=_cmd_eval)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
