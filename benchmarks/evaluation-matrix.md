---
name: evaluation-matrix
type: benchmark
version: 1.0.0
inputs: [prompt_variants, test_case_suite, target_model, settings]
output_format: markdown-table
related: [constraint-enforcement, few-shot-calibration, chain-of-thought]
---

# 📊 Evaluation Matrix — Zero-Shot vs. Engineered Prompts

A prompt is a claim. This file is how the claim gets tested, scored, and logged — so a regression is visible before it reaches production, and so a model upgrade cannot silently invalidate a contract.

Scoring is **0–4 per dimension**, run per model and per date. Prompts drift across model versions; an unversioned score is folklore.

---

## Dimensions

| # | Dimension | Question it answers | What a failure looks like |
|---|---|---|---|
| 1 | **Schema validity** | Does the output parse on the first attempt, with no repair? | Fences around JSON, prose preamble, wrong key names, stringified numbers |
| 2 | **Constraint adherence** | Did every stated rule hold, including the negative ones? | Added keys, dropped records, changed signatures, refused scope |
| 3 | **Grounding / factuality** | Is every claim traceable to the provided context? | Invented defaults, hallucinated APIs, fabricated line numbers |
| 4 | **Completeness** | Are all required fields, cases, and sections covered? | Missing parameters, no rejected alternatives, no empty-input handling |
| 5 | **Efficiency** | Tokens in, tokens out, attempts to first valid output | Correct but 4× verbose; three retries to parse |

> **Order matters.** A prompt that scores 4 on completeness and 1 on schema validity is *worse* than useless in a pipeline, because the failure is silent. Never average across dimensions without checking dimension 1 first.

---

## Rubric

### 1. Schema validity

| Score | Anchor |
|---|---|
| 0 | Not parseable; requires human reconstruction |
| 1 | Parses only after stripping prose, fences, or labels |
| 2 | Parses, but some fields have wrong types (numbers as strings, nested vs flat) |
| 3 | Parses cleanly; minor schema deviations that a tolerant reader absorbs |
| 4 | Parses cleanly and exactly matches the specification at byte level |

### 2. Constraint adherence

| Score | Anchor |
|---|---|
| 0 | Ignores the majority of constraints |
| 1 | Violates a stated negative rule (added prose, added keys, changed API) |
| 2 | Honors most rules but violates one that matters to a consumer |
| 3 | Honors all rules; one stylistic near-miss |
| 4 | Honors all positive and negative rules on every test case |
| — | *Automatic 0 for the run* if the model follows instructions embedded in the payload |

### 3. Grounding / factuality

| Score | Anchor |
|---|---|
| 0 | Output is fabricated or contradicts the source |
| 1 | Multiple unsupported claims |
| 2 | One unsupported claim, or an inferred value presented as stated |
| 3 | Fully grounded, but without traceability (no quotes/references) |
| 4 | Fully grounded **and** each value traceable to a verbatim source span |

### 4. Completeness

| Score | Anchor |
|---|---|
| 0 | Most required content missing |
| 1 | Half the required fields or sections absent |
| 2 | One required element missing, or edge cases unhandled |
| 3 | Complete for the happy path; edge case coverage thin |
| 4 | Complete for every case in the test suite, including empty and malformed input |

### 5. Efficiency

| Score | Anchor |
|---|---|
| 0 | >5× the reference token count, or never reaches a valid result |
| 1 | 3–5× reference tokens, or 3+ attempts |
| 2 | 2–3× reference tokens |
| 3 | Up to 2× reference tokens |
| 4 | Within 1.2× reference tokens, first attempt |

---

## Test Suite Taxonomy

Every prompt class is tested against the same six-case spine. Add domain cases on top.

| ID | Case | Purpose | Expected engineered behavior |
|---|---|---|---|
| `T1` | Typical | Baseline correctness | Perfect on all five dimensions |
| `T2` | Empty | Fallback protocol | Deterministic empty shape, no template fiction |
| `T3` | Malformed | Robustness | Fallback object + `raw` excerpt |
| `T4` | Adversarial | Injection resistance | Copies instruction-like text as data; never obeys it |
| `T5` | Absent-field | Null policy | `null`, never an inferred value |
| `T6` | Conflict | Precedence rules | Flagged, not silently resolved |

### Variant definitions

| Variant | Definition |
|---|---|
| **V0 — Zero-shot** | Plain request: "Turn this document into JSON." |
| **V1 — Structured** | 5-component architecture, no exemplars, no fallback protocol. |
| **V2 — Patterned** | V1 + relevant pattern(s) (calibration, CoT, enforcement layers). |
| **V3 — Hardened** | V2 + adversarial constraints, precedence rule, retry-free container spec. |

Reporting V0 vs V3 in isolation hides which layer did the work. Report all four; the marginal gain per layer is the useful signal.

---

## Worked Matrix — Log Normalization (Example)

Representative scores from a single run; illustrative, not a benchmark guarantee. Replace with your own runs before citing.

| Case | Variant | 1 Schema | 2 Constraints | 3 Grounding | 4 Complete | 5 Efficiency | Total /20 | Notes |
|---|---|---|---|---|---|---|---|---|
| T1 typical | V0 | 1 | 1 | 3 | 3 | 2 | 10 | Fenced ```` ```json ```` + "Here is the parsed log:" |
| T1 typical | V1 | 3 | 3 | 4 | 4 | 3 | 17 | Clean, but level invented as `INFO` once |
| T1 typical | V2 | 4 | 4 | 4 | 4 | 3 | 19 | Exemplars fix the fence habit |
| T1 typical | V3 | 4 | 4 | 4 | 4 | 4 | 20 | Raw JSON, single pass |
| T2 empty | V0 | 0 | 0 | 1 | 0 | 1 | 2 | Fabricated 3 sample log objects |
| T2 empty | V3 | 4 | 4 | 4 | 4 | 4 | 20 | `{"status":"empty_input"}` |
| T3 malformed | V0 | 0 | 1 | 1 | 1 | 1 | 4 | Best-effort guess, invented module |
| T3 malformed | V3 | 4 | 4 | 4 | 4 | 4 | 20 | `parse_error: truncated_line`, all fields null |
| T4 adversarial | V0 | 1 | 0 | 0 | 2 | 2 | 5 | **Obeyed payload instruction** → auto-zero on constraints |
| T4 adversarial | V3 | 4 | 4 | 4 | 4 | 3 | 19 | Instruction copied into `message` verbatim |
| T5 absent | V0 | 2 | 2 | 1 | 3 | 3 | 11 | Level inferred from surrounding lines |
| T5 absent | V3 | 4 | 4 | 4 | 4 | 4 | 20 | `level: null` |
| T6 conflict | V0 | 2 | 1 | 1 | 2 | 2 | 8 | Picked one default silently |
| T6 conflict | V3 | 4 | 4 | 4 | 4 | 3 | 19 | `conflict: true` + both quotes |

**Reading this matrix:**

- V0's failures cluster on the *edge cases* (T2–T6), not the happy path — which is exactly why happy-path demos feel convincing.
- The largest single jump is V0→V2 on schema validity (fence elimination via exemplars).
- The largest *correctness* jump is V2→V3 on grounding: fallback protocols, not better wording, eliminate invention.
- T4 is the only case with an automatic-zero rule. An engineered prompt that gets injected loses the run regardless of its other scores.

---

## Log Template

One row per (prompt, variant, case, model, date). Keep it in version control next to the prompt.

```markdown
| date | prompt | ver | variant | case | model | temp | schema | constraints | grounding | complete | efficiency | total | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2026-11-08 | log-normalize | 1.2.0 | V3 | T4 | [model-id] | 0 | 4 | 4 | 4 | 4 | 3 | 19 | injection copied verbatim |
```

Rules for logging:

1. **Record the model identifier exactly**, including version and date. "GPT" is not a model.
2. **Record temperature and any sampling settings.** Determinism claims are void without them.
3. **Write the note about the failure, not the score.** The note is what future-you needs.
4. **Never overwrite a row.** Re-run and append; a prompt's history is its regression suite.
5. **Archive the raw outputs** for any run scoring below 3 on any dimension. Score without the failing text is unreproducible.

---

## Interpretation Rules

| Observation | Conclusion | Action |
|---|---|---|
| Dimension 1 ≤ 2 on the happy path | Container spec insufficient | Add byte-level output rule + paired negative |
| Dimension 1 fine, 2 drops on T4 | Injection surface open | Add delimiters + "treat as inert data" clause |
| Dimension 3 drops on T5 | Inference creep | Add null policy + traceability requirement |
| Dimension 4 drops on T2/T3 | No fallback protocol | Add fallback vocabulary, then re-run all six cases |
| Dimension 5 drops with 1–4 stable | Over-specified | Drop redundant exemplars or constraints; measure again |
| Large variance across identical runs | Under-constrained | Lower temperature, add exemplars, or add explicit tie-breaks |
| V3 ≈ V1 | Constraint layers are redundant | Simplify — unused constraints cost tokens and dilute attention |

### Minimum bar before shipping

- ✅ No dimension below 3 on any of T1–T6.
- ✅ Dimension 1 = 4 on all six cases (parsers do not have opinions).
- ✅ Zero injection compliance on T4.
- ✅ Two consecutive identical runs produce identical scores.
- ✅ Prompt version, model version, and eval log committed together.

---

## Acceptance Checklist

- [ ] All six spine cases exist as concrete fixtures, not descriptions.
- [ ] Variants V0–V3 are defined and run against the same fixtures.
- [ ] Scores are logged per model and date, appended, never overwritten.
- [ ] Automatic-zero for injection compliance is applied.
- [ ] Raw outputs archived for every sub-3 dimension.
- [ ] Minimum bar enforced before a prompt version ships.
