import unittest
from pathlib import Path

from prompt_architect import evaluate

REPO_ROOT = Path(__file__).resolve().parents[1]
SUITE = REPO_ROOT / "benchmarks" / "suites" / "log-normalize.json"
RUNS = REPO_ROOT / "benchmarks" / "runs"


def run_path(variant: str) -> Path:
    return RUNS / f"2026-11-08.log-normalize.{variant}.json"


class ParseTests(unittest.TestCase):
    def test_plain_json_is_not_repaired(self):
        parsed = evaluate.parse_output('[{"a": 1}]')
        self.assertTrue(parsed.ok)
        self.assertFalse(parsed.repaired)
        self.assertEqual(parsed.preamble, "")

    def test_fenced_json_is_repaired_and_recorded(self):
        parsed = evaluate.parse_output('Here is the JSON:\n```json\n[{"a": 1}]\n```')
        self.assertTrue(parsed.ok)
        self.assertTrue(parsed.repaired)
        self.assertTrue(parsed.fenced)
        self.assertIn("Here is the JSON", parsed.preamble)

    def test_prose_then_json_is_repaired(self):
        parsed = evaluate.parse_output('Sure! [{"a": 1}]')
        self.assertTrue(parsed.ok)
        self.assertTrue(parsed.repaired)
        self.assertEqual(parsed.preamble, "Sure!")

    def test_empty_output_fails_without_crashing(self):
        self.assertFalse(evaluate.parse_output("").ok)

    def test_garbage_is_not_parseable(self):
        self.assertFalse(evaluate.parse_output("I cannot help with that.").ok)

    def test_token_estimate_is_ratio_based(self):
        self.assertEqual(evaluate.estimate_tokens(""), 1)
        self.assertEqual(evaluate.estimate_tokens("x" * 40), 10)


class GradingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.suite = evaluate.load_suite(SUITE)
        cls.v0 = evaluate.evaluate(cls.suite, evaluate.load_run(run_path("v0")))
        cls.v1 = evaluate.evaluate(cls.suite, evaluate.load_run(run_path("v1")))
        cls.v2 = evaluate.evaluate(cls.suite, evaluate.load_run(run_path("v2")))
        cls.v3 = evaluate.evaluate(cls.suite, evaluate.load_run(run_path("v3")))

    def by_id(self, report, case_id):
        return next(c for c in report.cases if c.case_id == case_id)

    def test_fixture_suite_has_the_six_case_spine(self):
        self.assertEqual([c["id"] for c in self.suite["cases"]],
                         ["T1", "T2", "T3", "T4", "T5", "T6"])

    def test_hardened_run_meets_the_ship_bar(self):
        self.assertEqual(self.v3.ship_bar_failures(), [])
        for case in self.v3.cases:
            self.assertEqual(case.scores["schema"], 4, case.case_id)

    def test_zero_shot_run_fails_the_ship_bar(self):
        self.assertTrue(self.v0.ship_bar_failures())

    def test_ladder_is_monotonic_in_total_score(self):
        totals = [sum(c.total for c in r.cases) for r in (self.v0, self.v1, self.v2, self.v3)]
        self.assertEqual(totals, sorted(totals))
        self.assertLess(totals[0], totals[-1])

    def test_injection_compliance_is_an_automatic_zero(self):
        case = self.by_id(self.v0, "T4")
        self.assertTrue(case.injection)
        self.assertEqual(case.scores["constraints"], 0)

    def test_hardened_run_resists_injection(self):
        case = self.by_id(self.v3, "T4")
        self.assertFalse(case.injection)
        self.assertEqual(case.scores["constraints"], 4)

    def test_fence_is_scored_under_schema_validity(self):
        case = self.by_id(self.v1, "T1")
        self.assertEqual(case.scores["schema"], 1)
        self.assertLess(case.scores["constraints"], 4)

    def test_missing_fallback_shape_fails_completeness(self):
        case = self.by_id(self.v2, "T2")
        self.assertLessEqual(case.scores["completeness"], 2)
        self.assertEqual(case.scores["grounding"], 0)

    def test_fallback_object_is_not_treated_as_a_factual_claim(self):
        self.assertEqual(self.by_id(self.v3, "T2").scores["grounding"], 4)

    def test_inferred_value_costs_more_than_an_unsupported_one(self):
        case = self.by_id(self.v0, "T5")  # level invented where the source is silent
        self.assertLess(case.scores["grounding"], 4)

    def test_matrix_renders_scores_and_verdict(self):
        text = evaluate.render_matrix(self.v3)
        self.assertIn("| T1 |", text)
        self.assertIn("Ship bar: PASS", text)
        self.assertIn("Ship bar: FAIL", evaluate.render_matrix(self.v0))

    def test_malformed_run_file_is_rejected(self):
        with self.assertRaises(evaluate.SuiteError):
            evaluate.load_run(SUITE)  # a suite is not a run: no 'outputs'


class EfficiencyTests(unittest.TestCase):
    def test_efficiency_anchors(self):
        self.assertEqual(evaluate._efficiency_score("x" * 40, 10), 4)    # 10 tok = 1.0x
        self.assertEqual(evaluate._efficiency_score("x" * 100, 10), 2)   # 25 tok = 2.5x
        self.assertEqual(evaluate._efficiency_score("x" * 400, 10), 0)   # 100 tok = 10x

    def test_type_checks(self):
        self.assertTrue(evaluate.type_ok(1, ["integer", "null"]))
        self.assertFalse(evaluate.type_ok(True, ["integer"]))
        self.assertFalse(evaluate.type_ok("1", ["integer"]))
        self.assertTrue(evaluate.type_ok(None, ["string", "null"]))


if __name__ == "__main__":
    unittest.main()
