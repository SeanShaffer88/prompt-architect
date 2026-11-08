"""Every suite and spec in the repository must satisfy the same contract:

* every spec renders at all four variants and matches its golden file,
* every suite's hardened run passes the ship bar,
* every suite's zero-shot run fails it (the suite still discriminates).
"""

import json
import unittest
from pathlib import Path

from prompt_architect import evaluate, spec

REPO_ROOT = Path(__file__).resolve().parents[1]
SPECS = sorted((REPO_ROOT / "specs").glob("*.json"))
SUITES = sorted((REPO_ROOT / "benchmarks" / "suites").glob("*.json"))


def run_path(suite: dict, variant: str) -> Path:
    return REPO_ROOT / "benchmarks" / "runs" / f"2026-11-08.{suite['name']}.{variant}.json"


class SpecLibraryTests(unittest.TestCase):
    def test_every_blueprint_has_a_spec(self):
        blueprints = {p.stem for p in (REPO_ROOT / "blueprints").glob("*.md")}
        specs = {p.stem for p in SPECS}
        # log-normalize is a worked example, not a blueprint.
        missing = blueprints - specs
        self.assertEqual(missing, set(), f"blueprints without a spec: {sorted(missing)}")

    def test_every_spec_renders_all_variants(self):
        for path in SPECS:
            with self.subTest(spec=path.name):
                loaded = spec.load(path)
                rendered = {v: spec.render(loaded, v) for v in spec.VARIANTS}
                self.assertTrue(rendered["v3"].startswith("### Role"))
                self.assertIn("### Fallback Protocol", rendered["v3"])
                self.assertNotIn("### Role", rendered["v0"])
                sizes = [len(rendered[v]) for v in spec.VARIANTS]
                self.assertEqual(sizes, sorted(sizes))

    def test_every_spec_matches_its_goldens(self):
        for path in SPECS:
            for variant in spec.VARIANTS:
                with self.subTest(spec=path.name, variant=variant):
                    golden = spec.golden_path(path, variant)
                    self.assertTrue(golden.exists(), f"missing golden: {golden}")
                    self.assertEqual(
                        spec.render(spec.load(path), variant),
                        golden.read_text(encoding="utf-8"),
                    )

    def test_spec_front_matter_is_indexable(self):
        for path in SPECS:
            with self.subTest(spec=path.name):
                data = json.loads(path.read_text(encoding="utf-8"))
                self.assertEqual(data["name"], path.stem)
                for key in ("version", "role", "objective", "output", "constraints"):
                    self.assertIn(key, data)


class SuiteGateTests(unittest.TestCase):
    def test_there_is_at_least_one_suite_per_gated_prompt(self):
        names = {json.loads(p.read_text())["name"] for p in SUITES}
        self.assertTrue({"log-normalize", "classification-routing", "summarization"} <= names)

    def test_hardened_runs_pass_the_ship_bar(self):
        for path in SUITES:
            suite = evaluate.load_suite(path)
            with self.subTest(suite=suite["name"]):
                report = evaluate.evaluate(suite, evaluate.load_run(run_path(suite, "v3")))
                self.assertEqual(report.ship_bar_failures(), [])

    def test_zero_shot_runs_fail_the_ship_bar(self):
        for path in SUITES:
            suite = evaluate.load_suite(path)
            with self.subTest(suite=suite["name"]):
                report = evaluate.evaluate(suite, evaluate.load_run(run_path(suite, "v0")))
                self.assertTrue(report.ship_bar_failures())

    def test_every_suite_declares_the_six_case_spine(self):
        for path in SUITES:
            suite = evaluate.load_suite(path)
            with self.subTest(suite=suite["name"]):
                self.assertEqual([c["id"] for c in suite["cases"]],
                                 ["T1", "T2", "T3", "T4", "T5", "T6"])

    def test_runs_match_their_suite_prompt_version(self):
        for path in SUITES:
            suite = evaluate.load_suite(path)
            for variant in ("v0", "v3"):
                with self.subTest(suite=suite["name"], variant=variant):
                    run = evaluate.load_run(run_path(suite, variant))
                    self.assertEqual(run["suite"], suite["name"])
                    self.assertEqual(run["prompt_version"], suite["prompt_version"])
                    self.assertEqual(set(run["outputs"]), {c["id"] for c in suite["cases"]})


if __name__ == "__main__":
    unittest.main()
