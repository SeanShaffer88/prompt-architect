---
name: model-landscape-and-migration
type: guide
version: 1.0.0
output_format: markdown
related: [reasoning-model-prompting, evaluation-matrix, sampling-and-determinism]
---

# 🧭 Model Landscape & Prompt Migration

Prompts are not portable in the way source code is. They are tuned artifacts, and every model generation shifts the distribution underneath them. This guide covers the two axes that matter — *model class* and *migration* — and how to keep a prompt library from silently rotting.

---

## 1. The three useful classes

| Class | Behavior | Prompt accordingly |
|---|---|---|
| **Instruction-tuned chat** | Fast, format-compliant, weak at long derivations | Full 5 components; exemplars for format; explicit edge cases |
| **Reasoning / thinking** | Deliberates before answering; strong at multi-step, weak at brevity | Success criteria + output contract, minimal scaffolding; don't hand-hold the reasoning |
| **Small / distilled / edge** | Cheap, fast, brittle under ambiguity | Short prompts, schema mode, one task per call, deterministic post-checks |

Size is not the axis people think it is. A small model with a narrow, well-specified task and schema-constrained decoding routinely beats a frontier model asked to "be careful". Task narrowness and output determinism are cheaper than capability.

---

## 2. Reasoning models change the prompt, not just the price

Reasoning models reallocate effort to inference time. That inverts several classic habits:

| Habit | On a standard chat model | On a reasoning model |
|---|---|---|
| "Think step by step" | Helps | Redundant, sometimes harmful — the model already plans |
| Long procedural scaffolding | Helps structure | Competes with the model's own plan; keep it short |
| Few-shot exemplars for reasoning | Helps | Often unnecessary; use for *format*, not for logic |
| Asking it to show work | Useful for audit | Hidden by design; ask for a conclusion plus a brief rationale instead |
| "Be concise" | Often ignored | Respects it more reliably — use it |
| Strict output format | Needs strong enforcement | Usually honored; still specify the container |

The failure signature of a reasoning model is **over-elaboration**: correct analysis, wrong format. The fix is an output contract with a hard cap, not more instructions about thinking.

See [reasoning-model-prompting](../patterns/reasoning-model-prompting.md).

---

## 3. Model-specific quirks worth knowing

Not a compatibility matrix — those rot. These are *categories* of quirk to test for on any provider.

| Quirk | What to check |
|---|---|
| **Instruction precedence** | Does a developer/system message actually outrank user text? Test with a deliberate conflict |
| **System prompt presence** | Some surfaces inject their own system prompt; yours is not the only one |
| **Structured output mode** | JSON mode vs strict schema vs grammar: does it guarantee the schema or just validity? |
| **Refusal style** | Does it refuse, hedge, or answer partially? A refusal is a valid `status` — specify the shape |
| **Token accounting** | Do reasoning tokens count against `max_tokens`? If yes, your length caps are wrong |
| **Tool-call format** | Parallel calls, argument streaming, malformed-arg behavior |
| **Context limit and degradation** | Advertised context ≠ usable context; test retrieval at 50%, 80%, 95% of the window |
| **Caching** | Prompt-prefix caching changes cost and latency; put stable content first |
| **Content filters** | A benign prompt can trip a classifier and return an empty or canned response |

**Test, don't assume.** Each of these is a 5-minute probe with a deliberately adversarial input, and each one has caused a production incident somewhere.

---

## 4. Migration: when the model changes under you

Three triggers: a deliberate upgrade, a forced deprecation, or a silent provider-side redeploy.

### The migration protocol

1. **Freeze the baseline.** Re-run the current prompt on the current model and archive the run file. Without this, you cannot tell improvement from noise.
2. **Re-run unchanged.** Same prompt, same settings, new model. Score it.
3. **Diff the failures, not the averages.** Look for cases that flipped from pass to fail; those are the regressions that matter.
4. **Re-tune only what broke.** Resist rewriting the whole prompt; you will lose calibration you paid for.
5. **Re-baseline the suite.** If the new model passes everything trivially, the suite is now too easy — add harder cases.
6. **Record the pair.** `model: old@date → new@date`, same prompt version, in the run history.

### What usually breaks first

| Failure | Likelihood on upgrade | Fix |
|---|---|---|
| Format/container drift (new preamble style) | High | Re-assert the byte-level container |
| Over-verbosity | High | Hard length cap + "no preamble" |
| Refusal changes | Medium | Specify the refusal shape; re-test policy edges |
| Prompt-injection resistance | Medium | Re-run T4; never assume it held |
| Reasoning quality | Low (usually improves) | Re-check the cases that needed exemplars; drop them if unnecessary |

**A silent redeploy is the dangerous case.** If scores drop with no announcement, your run history is the only evidence you have. That is the argument for logging model id and date on every run.

---

## 5. Cost and capability aren't linear

Before paying for a bigger model, try — in this order:

1. **Narrow the task.** Two small calls with one objective each often beat one broad call.
2. **Constrain the output.** Schema mode + short caps cut output tokens, which usually dominate cost.
3. **Add an exemplar.** Cheaper than a larger model for format problems.
4. **Cache the stable prefix.** System prompt + exemplars are identical per request; prefix caching can remove most input cost.
5. **Route by difficulty.** A classifier sends easy cases to a small model and hard cases to a large one. Route on *confidence*, not on vibes.

See [cost-and-latency](../guides/cost-and-latency.md).

---

## 6. Anti-patterns

| Anti-pattern | Why it fails |
|---|---|
| "It's a better model, so the prompt still works" | Better at the average, different at the edges |
| Copying prompts between providers verbatim | Different templates, precedence, and refusal behavior |
| Tuning on one model and shipping on another | You evaluated a system you don't run |
| Chasing benchmark leaderboards | Your task is not the benchmark |
| Never re-running evals after an upgrade | Regressions are silent by default |
| Keeping old scaffolding "just in case" | Carries folklore that can actively hurt |

---

## Acceptance Checklist

- [ ] The model class is known and the prompt is shaped for it.
- [ ] Provider quirks are probed (precedence, structured output, refusal, token accounting, caching).
- [ ] A frozen baseline run exists for the current model.
- [ ] Migration re-runs the untouched prompt before any rewrites.
- [ ] Regressions are identified per case, not by average.
- [ ] Prompt version and model id/date are recorded together.
- [ ] Fallback/degradation behavior is defined for model failures (timeouts, empty output, refusal).
