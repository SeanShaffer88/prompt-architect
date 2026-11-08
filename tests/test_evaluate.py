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


class StructuredOutputTests(unittest.TestCase):
    """Object-typed schemas, closed vocabularies, and content assertions."""

    def suite(self, **schema):
        base = {
            "type": "object",
            "required": ["label"],
            "key_order": ["label"],
            "types": {"label": ["string"]},
        }
        base.update(schema)
        return {"name": "unit", "container": {"first_char": "{", "last_char": "}"},
                "schema": base, "cases": []}

    def case(self, **kw):
        base = {"id": "T1", "kind": "typical", "input": "ticket text", "reference_tokens": 10}
        base.update(kw)
        return base

    def grade(self, suite, case, raw):
        return evaluate.grade_case(suite, case, raw)

    def test_single_object_is_one_record(self):
        result = self.grade(self.suite(), self.case(expect={"label": "billing"}),
                            '{"label": "billing"}')
        self.assertEqual(result.scores["schema"], 4)

    def test_wrong_container_scores_three(self):
        result = self.grade(self.suite(), self.case(), '[{"label": "billing"}]')
        self.assertLessEqual(result.scores["schema"], 3)

    def test_enum_violation_is_structural(self):
        suite = self.suite(enums={"label": ["billing", "bug"]})
        result = self.grade(suite, self.case(), '{"label": "refund"}')
        self.assertEqual(result.scores["schema"], 2)

    def test_enum_member_passes(self):
        suite = self.suite(enums={"label": ["billing", "bug"]})
        result = self.grade(suite, self.case(), '{"label": "bug"}')
        self.assertEqual(result.scores["schema"], 4)

    def test_controlled_fields_are_not_grounding_claims(self):
        suite = self.suite(controlled=["label"])
        result = self.grade(suite, self.case(), '{"label": "billing"}')
        self.assertEqual(result.scores["grounding"], 4)

    def test_uncontrolled_string_must_appear_in_source(self):
        suite = self.suite(required=["label", "note"], key_order=["label", "note"],
                           types={"label": ["string"], "note": ["string"]})
        result = self.grade(suite, self.case(), '{"label": "billing", "note": "invented detail"}')
        self.assertLess(result.scores["grounding"], 4)

    def test_expected_value_mismatch_costs_grounding(self):
        result = self.grade(self.suite(), self.case(expect={"label": "bug"}),
                            '{"label": "billing"}')
        self.assertLess(result.scores["grounding"], 4)

    def test_numbers_mode_flags_invented_figures(self):
        suite = self.suite(grounding_mode="numbers", required=["summary"],
                           key_order=["summary"], types={"summary": ["string"]})
        ok = self.grade(suite, self.case(input="14:02 spike, 1,200 orders failed"),
                        '{"summary": "spike at 14:02 affecting 1,200 orders"}')
        bad = self.grade(suite, self.case(input="14:02 spike, 1,200 orders failed"),
                         '{"summary": "spike at 14:07 affecting 1,200 orders"}')
        self.assertEqual(ok.scores["grounding"], 4)
        self.assertLess(bad.scores["grounding"], 4)

    def test_expect_contains_is_checked(self):
        result = self.grade(self.suite(), self.case(expect_contains={"label": "needs"}),
                            '{"label": "billing"}')
        self.assertLess(result.scores["completeness"], 4)

    def test_expect_contains_accepts_lists(self):
        result = self.grade(self.suite(required=["a", "b"], key_order=["a", "b"],
                                       types={"a": ["string"], "b": ["string"]}),
                            self.case(expect_contains={"a": ["x", "y"]}),
                            '{"a": "x", "b": "y"}')
        self.assertEqual(result.scores["completeness"], 4)

    def test_expect_empty_is_checked(self):
        suite = self.suite(required=["decisions"], key_order=["decisions"],
                           types={"decisions": ["array"]})
        ok = self.grade(suite, self.case(expect_empty=["decisions"]), '{"decisions": []}')
        bad = self.grade(suite, self.case(expect_empty=["decisions"]),
                         '{"decisions": ["invented action"]}')
        self.assertEqual(ok.scores["completeness"], 4)
        self.assertLess(bad.scores["completeness"], 4)


class TextOutputTests(unittest.TestCase):
    """Prose, code, and transcripts graded on container and content, not parsing."""

    def suite(self, **kw):
        base = {"name": "unit-text", "output_type": "text", "grounding_mode": "numbers", "cases": []}
        base.update(kw)
        return base

    def case(self, **kw):
        base = {"id": "T1", "kind": "typical", "input": "source text", "reference_tokens": 10}
        base.update(kw)
        return base

    def grade(self, suite, case, raw):
        return evaluate.grade_case(suite, case, raw)

    def test_text_case_is_graded_without_json(self):
        result = self.grade(self.suite(), self.case(required_patterns=["answer"]), "the answer")
        self.assertEqual(result.scores["schema"], 4)
        self.assertEqual(result.scores["completeness"], 4)

    def test_empty_output_scores_zero_on_schema(self):
        result = self.grade(self.suite(), self.case(), "   ")
        self.assertEqual(result.scores["schema"], 0)

    def test_prefix_present_but_not_leading_costs_a_point(self):
        suit = self.suite(container={"starts_with": "CALL"})
        result = self.grade(suit, self.case(), "Sure! CALL search")
        self.assertEqual(result.scores["schema"], 1)

    def test_other_wrapper_error_scores_two(self):
        suit = self.suite(container={"starts_with": "CALL"})
        result = self.grade(suit, self.case(), "here is a plan")
        self.assertEqual(result.scores["schema"], 2)

    def test_forbidden_content_costs_constraint_points(self):
        result = self.grade(self.suite(), self.case(forbidden_patterns=["moral"]), "the moral is clear")
        self.assertEqual(result.scores["constraints"], 3)

    def test_injection_canary_is_an_automatic_zero(self):
        case = self.case(injection={"value": "INJECTION_ACK"})
        result = self.grade(self.suite(), case, "INJECTION_ACK")
        self.assertEqual(result.scores["constraints"], 0)
        self.assertTrue(result.injection)

    def test_invented_figure_costs_grounding(self):
        case = self.case(input="the cap is 50 rows")
        result = self.grade(self.suite(), case, "the cap is 80 rows")
        self.assertLess(result.scores["grounding"], 4)

    def test_grounding_off_ignores_figures(self):
        suit = self.suite(grounding_mode="off")
        result = self.grade(suit, self.case(), "u8 and O(1) and arr[0]")
        self.assertEqual(result.scores["grounding"], 4)

    def test_ordered_list_markers_are_not_figures(self):
        case = self.case(input="we ship one cache")
        result = self.grade(self.suite(), case, "1. shard it\n2. cache it")
        self.assertEqual(result.scores["grounding"], 4)

    def test_any_of_group_must_match_one_branch(self):
        case = self.case(any_of_patterns=[["insufficient_brief"]])
        self.assertEqual(self.grade(self.suite(), case, "a story").scores["completeness"], 2)
        self.assertEqual(self.grade(self.suite(), case, '{"status": "insufficient_brief"}').scores["completeness"], 4)

    def test_word_bounds_are_enforced(self):
        case = self.case(min_words=5, max_words=8)
        self.assertEqual(self.grade(self.suite(), case, "one two three").scores["completeness"], 3)
        self.assertEqual(self.grade(self.suite(), case, "one two three four five six").scores["completeness"], 4)


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
