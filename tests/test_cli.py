import contextlib
import io
import unittest
from pathlib import Path

from prompt_architect import cli

REPO_ROOT = Path(__file__).resolve().parents[1]
SPEC = str(REPO_ROOT / "specs" / "log-normalize.json")
SUITE = str(REPO_ROOT / "benchmarks" / "suites" / "log-normalize.json")


def run(*args) -> tuple[int, str]:
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer), contextlib.redirect_stderr(io.StringIO()):
        code = cli.main(list(args))
    return code, buffer.getvalue()


def run_file(variant: str) -> str:
    return str(REPO_ROOT / "benchmarks" / "runs" / f"2026-11-08.log-normalize.{variant}.json")


class LintCommandTests(unittest.TestCase):
    def test_repository_lints_clean(self):
        code, output = run("lint", str(REPO_ROOT))
        self.assertEqual(code, 0)
        self.assertIn("0 error(s)", output)

    def test_json_output_is_machine_readable(self):
        import json
        code, output = run("lint", str(REPO_ROOT), "--json")
        self.assertEqual(code, 0)
        self.assertIsInstance(json.loads(output), list)


class ComposeCommandTests(unittest.TestCase):
    def test_prints_requested_variant(self):
        code, output = run("compose", SPEC, "--variant", "v3")
        self.assertEqual(code, 0)
        self.assertIn("### Role", output)
        self.assertIn("### Fallback Protocol", output)

    def test_all_variants_are_labeled(self):
        code, output = run("compose", SPEC, "--all")
        self.assertEqual(code, 0)
        self.assertEqual(output.count("<!-- variant v"), 4)

    def test_check_passes_against_committed_goldens(self):
        for variant in ("v0", "v1", "v2", "v3"):
            code, output = run("compose", SPEC, "--variant", variant, "--check")
            self.assertEqual(code, 0, output)
            self.assertIn("matches", output)

    def test_bad_spec_exits_2(self):
        code, _ = run("compose", "specs/does-not-exist.json")
        self.assertEqual(code, 2)


class EvalCommandTests(unittest.TestCase):
    def test_hardened_run_passes_with_expect_pass(self):
        code, output = run("eval", SUITE, "--run", run_file("v3"), "--expect-pass")
        self.assertEqual(code, 0)
        self.assertIn("Ship bar: PASS", output)

    def test_zero_shot_run_fails_with_expect_pass(self):
        code, output = run("eval", SUITE, "--run", run_file("v0"), "--expect-pass")
        self.assertEqual(code, 1)
        self.assertIn("Ship bar: FAIL", output)

    def test_regression_guard_fails_when_a_bad_run_passes(self):
        code, _ = run("eval", SUITE, "--run", run_file("v3"), "--expect-fail")
        self.assertEqual(code, 1)

    def test_regression_guard_accepts_a_failing_run(self):
        code, _ = run("eval", SUITE, "--run", run_file("v0"), "--expect-fail")
        self.assertEqual(code, 0)

    def test_multiple_runs_render_one_matrix_each(self):
        code, output = run("eval", SUITE, "--run", run_file("v0"), "--run", run_file("v3"),
                           "--no-ship-bar")
        self.assertEqual(code, 0)
        self.assertEqual(output.count("| Case |"), 2)

    def test_json_output_reports_blockers(self):
        import json
        code, output = run("eval", SUITE, "--run", run_file("v0"), "--json")
        self.assertEqual(code, 1)  # default: ship-bar failure fails the build
        payload = json.loads(output)
        self.assertEqual(len(payload), 1)
        self.assertTrue(payload[0]["ship_bar_failures"])
        self.assertEqual(len(payload[0]["cases"]), 6)

    def test_missing_suite_exits_2(self):
        code, _ = run("eval", "nope.json", "--run", run_file("v3"))
        self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
