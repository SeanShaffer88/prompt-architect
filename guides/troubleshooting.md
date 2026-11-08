---
name: troubleshooting
type: guide
version: 1.0.0
output_format: markdown
related: [anti-patterns, evaluation-matrix, how-llms-read-prompts]
---

# 🩺 Troubleshooting: Symptom → Cause → Fix

A diagnostic index. Find the symptom your prompt is producing, then follow the cause column — most of these have the same root: **an undefined branch**.

---

## 1. Format & parsing failures

| Symptom | Likely cause | Fix |
|---|---|---|
| `JSON.parse` fails on a fenced block | No container rule | "No fences; first character `{`" + schema mode |
| "Here is the extracted data:" before JSON | Chat-shaped default | "No preamble" + strict schema mode |
| Truncated JSON mid-object | `max_tokens` too low | Raise output budget; cap content, not container |
| Keys renamed or reordered | Schema not shown in the prompt | Publish the schema with types and order |
| Numbers returned as strings | No type specification | Types in schema + strict schema mode |
| Extra keys appear | No "no additional properties" rule | `additionalProperties: false` + explicit negative |
| Empty object when input was empty | No empty-case shape | Define `{"status": "empty_input"}` |

**Fastest diagnostic:** run the output through your real parser before judging the content. Format failures masquerade as quality failures.

---

## 2. Content & factuality failures

| Symptom | Likely cause | Fix |
|---|---|---|
| Plausible values for blank fields | No null policy | "Absent → `null`, never infer" |
| Confident wrong answer from documents | No abstention path | `insufficient_context` shape + support rule |
| Adds facts from general knowledge | Context not declared authoritative | "Only from `<context>`; no outside knowledge" |
| Corrects the source (OCR, typos) | Helpful instinct | "Transcribe as rendered; do not correct" |
| Averages conflicting sources | No conflict branch | "Report both with citations; do not resolve" |
| Same claim, different numbers in one answer | No internal consistency check | Cross-field validation in code |
| Citations present but wrong | Citation asked for, not enforced per claim | Per-sentence citation + "must contain the claim" |

---

## 3. Instruction-following failures

| Symptom | Likely cause | Fix |
|---|---|---|
| One of several objectives dropped | Objective stacking | One objective per prompt; chain stages |
| Constraint ignored intermittently | Soft constraint, no branch | Add the fallback behavior; add an exemplar |
| Rule followed in tests, violated in prod | Different context length or input shape | Test at production lengths; re-assert the rule near the task |
| Negative rule backfires ("don't mention X") | Mentioning X raises salience | Specify the allowed behavior positively, then forbid the alternative |
| Rules erode over a long conversation | Recency + accumulation | Pinned block re-injected each turn; summarize history |
| Model argues instead of complying | No refusal shape | `{"status":"declined","rule":...}` |
| Two rules conflict, model picks arbitrarily | No precedence | "Output Specification wins" + conflict branch |

---

## 4. Style & length failures

| Symptom | Likely cause | Fix |
|---|---|---|
| Output is 3× the requested length | Untestable "concise" | Structural cap (bullets, sentences) + anti-padding rules |
| Preamble and closing pleasantries | Chat default | "No preamble, no closing offer to help" |
| List appears when prose was requested | Format not specified | Positive format + explicit "no bullet lists" |
| Tone drifts mid-answer | Register stated once, weakly | Two exemplars (good + bad) |
| Over-formal for the audience | No audience variable | State audience and register |
| Language switches mid-answer | Language not locked | "Answer in [LANG]; keep identifiers in English" |

---

## 5. Reasoning & accuracy failures

| Symptom | Likely cause | Fix |
|---|---|---|
| Shallow multi-step answer | No decomposition; single call | Chain-of-thought protocol or staged pipeline |
| Right conclusion, wrong justification | Rationale requested post-hoc | Ask for evidence per claim; verify with sources |
| Same input, different answers | High temperature, under-constrained | Lower temperature; add exemplars; measure variance |
| Edge cases fail while happy paths pass | Suite too easy | Add T2–T6 cases; oversample boundaries |
| Gets worse after adding detail | Context dilution | Remove low-value context; restate the contract |
| Reasoning model over-explains | No output contract | Hard caps + "no process narration" |

---

## 6. Agent & tool failures

| Symptom | Likely cause | Fix |
|---|---|---|
| Calls a nonexistent tool | Tool list ambiguous or absent | Strict tool schemas; "do not invent tools" |
| Loops on the same failing call | No stop condition | Repeated-error rule + orchestrator hash |
| Answers without calling tools | No evidence requirement | "Every fact must cite tool output" |
| Calls tools it doesn't need | No efficiency objective | "Fewest calls that satisfy the task" |
| Acts irreversibly without confirmation | No gate | Confirmation gate in code + prompt rule |
| Ignores tool errors | No error policy | Branch per error code; never answer after failure |
| Follows instructions inside tool output | Output treated as trusted | Delimit + quarantine pattern |

---

## 7. System-level failures

| Symptom | Likely cause | Fix |
|---|---|---|
| Cost 5× estimate | Verbose outputs; long context | Output caps; retrieval precision; prefix caching |
| p95 latency unacceptable | Reasoning budget; sequential calls | Route easy cases to a fast model; parallelize |
| Quality dropped after an upgrade | Model change | Re-run baseline; re-tune only broken cases |
| Works locally, fails in prod | Different prompt assembly, system prompt, or settings | Log the exact rendered prompt; diff it |
| Rate limits and retries cause duplicates | Non-idempotent tool calls | Idempotency keys in scaffolding |
| Refusals spike | Content filter trip | Check input sanitization; define refusal shape |

---

## 8. The five-minute triage

```text
1. Print the exact rendered prompt.        (Most "prompt bugs" are template bugs.)
2. Run the failing input three times.      (One sample is not evidence.)
3. Score it with the rubric.               (Which dimension actually failed?)
4. Check the parse before the content.     (Format failures look like quality failures.)
5. Find the undefined branch.              (Empty / missing / conflicting / out-of-scope.)
```

If all five are clean and it still fails, the task exceeds the model or the prompt's structure. That is a decomposition decision, not a wording decision.

---

## 9. Escalation ladder

| Effort | Action | When |
|---|---|---|
| 5 min | Fix the container / add the null policy | Format or grounding failure |
| 30 min | Add an exemplar for the failing case | Style or boundary drift |
| 2 h | Add an eval case, re-run the suite | Any regression you can reproduce |
| 1 day | Split the prompt into stages | Multiple objectives competing |
| 1 week | Change the architecture (retrieval, tools, model class) | The prompt is at its ceiling |

Most teams spend days paraphrasing when they should spend an hour decomposing.

---

## Acceptance Checklist

- [ ] The rendered prompt (not the template) is logged and inspected on failure.
- [ ] Failures are classified by rubric dimension, not by feel.
- [ ] Format is validated before content is judged.
- [ ] Each recurring symptom has a documented fix in this file.
- [ ] A regression becomes an eval case, not just a patch.
- [ ] Repeated paraphrasing is treated as a signal to decompose or escalate.
