---
name: glossary
type: guide
version: 1.0.0
output_format: markdown
related: [how-llms-read-prompts, evaluation-matrix, prompt-injection-and-safety]
---

# 📖 Glossary

Terms used across this repository, defined as they are used here. Where the industry uses a term loosely, the entry notes the ambiguity rather than pretending it does not exist.

---

## Prompt architecture

**System prompt** — Application-authored instructions with the highest practical authority. Contains identity, hard rules, and the output contract. Not a security boundary; assume it can be disclosed.

**Developer prompt** — Application-authored, per-request instructions (task, context, tenant policy). Precedence sits below system and above user, where the provider supports the role.

**User message** — The end user's request. Task intent, not policy authority. In injection scenarios, untrusted.

**Context / payload** — Data supplied to the model: documents, logs, retrieved chunks, tool results. Always data; never instructions.

**5-component architecture** — Role → Context → Objective → Constraints → Output Specification. The fixed section order used by every blueprint here.

**Fallback protocol** — The defined behavior when the task cannot be completed as specified (empty input, missing field, conflict, insufficient evidence). The single most important anti-hallucination device.

**Null policy** — An explicit rule that absent or unstated values become `null` rather than being inferred.

**Output container** — The byte-level contract around the payload: first/last character, fence prohibition, preamble prohibition.

**Delegation** — An explicit statement of what the user may override (tone, length, language) and what they may not (schema, policy, citations).

---

## Model behavior

**Token** — The unit of text the model processes. Roughly 4 characters of English; more for code and non-Latin scripts.

**Context window** — The maximum tokens a model can attend to in one request, input plus output.

**Lost in the middle** — The empirical tendency for material in the middle of a long context to be recalled less reliably than material at the start or end.

**Temperature** — A sampling parameter that flattens (higher) or sharpens (lower) the next-token distribution. Not a creativity dial with a linear scale.

**top_p (nucleus sampling)** — Samples from the smallest set of tokens whose cumulative probability reaches `p`. Usually tuned instead of, not alongside, temperature.

**Greedy decoding** — Always selecting the highest-probability token. What people mean by "temperature 0", though it is rarely bit-exact in production.

**Determinism** — Reproducibility across runs. Approximation at best: batching, floating-point ordering, MoE routing, and provider redeploys all introduce variance.

**Parametric knowledge** — What the model learned in training; frozen at the cutoff, unverifiable at runtime.

**Contextual knowledge** — What is in the prompt now. Authoritative for the task, if the prompt says so.

**Hallucination** — Confident output not supported by the available evidence. Usually parametric knowledge winning where it should have lost, or a gap the prompt left undefined.

**Sycophancy** — Tendency to agree with the user's framing over the evidence. Countered by explicit "the sources are authoritative; do not adopt the user's framing".

**Instruction hierarchy** — The precedence ladder (system > developer > user > data) that governs conflicts between instructions.

---

## Reasoning & prompting patterns

**Chain-of-thought (CoT)** — Eliciting intermediate reasoning steps before an answer. Useful on standard chat models for multi-step logic; often redundant on reasoning models.

**Self-consistency** — Sampling several answers at non-zero temperature and aggregating by vote. Disagreement rate doubles as an ambiguity detector.

**Few-shot calibration** — Supplying input→output exemplars to fix format and boundary behavior. Exemplars teach implicit rules, so unrepresented edge cases become permission.

**Zero-shot** — A request with no exemplars. Fine for common formats, fragile for strict ones.

**Meta-prompting** — Using a model to write, critique, or revise a prompt. Powerful for coverage; risky for self-preference bias.

**ReAct** — Reason → Act → Observe loop in which a model calls tools and reads results. Requires stop conditions and error branches to be safe.

**Decomposition** — Splitting a task into stages with explicit contracts between them, as opposed to stacking objectives in one prompt.

**Routing** — Directing requests to specialist prompts or models, usually via a classifier. The handoff contract matters more than the classifier.

**Structured output / schema mode** — Provider-enforced output shape (JSON schema, strict tool calls, grammars). Guarantees syntax, not truth.

**Grounding** — Constraining answers to provided evidence, with citations and an abstention path.

**Abstention** — Declining to answer when evidence is insufficient, in a machine-readable shape (e.g. `insufficient_context`).

**Refusal shape** — A defined JSON response for declined requests, enabling measurement and UI rendering instead of prose apologies.

---

## Evaluation

**Ship bar** — The minimum standard for releasing a prompt: schema validity 4 on every case, no dimension below 3, no injection compliance. Defined in [evaluation-matrix](../benchmarks/evaluation-matrix.md).

**T1–T6 spine** — The six canonical test cases: typical, empty, malformed, adversarial, absent-field, conflict.

**Rubric dimension** — One of five scored axes: schema validity, constraint adherence, grounding, completeness, efficiency.

**Injection compliance** — A model following instructions embedded in data. An automatic zero for the run.

**Repair** — Parsing model output after stripping fences or prose. Allowed, but recorded: it costs schema validity because a pipeline needed human-like intervention.

**Variant ladder (V0–V3)** — Zero-shot, structured, patterned, hardened. Exactly one class of enforcement changes per step, making score deltas attributable.

**Pass@k / agreement** — The share of k samples that match the majority answer. Used as a confidence signal and an ambiguity detector.

**Golden file** — A committed rendered prompt used to detect unintended drift (`compose --check`).

**Regression case** — A failing input promoted into the eval suite, so the fix cannot silently revert.

---

## Security

**Prompt injection** — Instructions smuggled into data (documents, tool output, web pages) and executed by the model.

**Indirect injection** — Injection delivered through retrieved or fetched content rather than typed by the user.

**Exfiltration** — Getting data out through the answer, a markdown image URL, a tool argument, or a link preview.

**Quarantine pattern** — A privilege-free model reads untrusted content and returns structured data; a privileged actor never sees the raw text.

**Delimiter spoofing** — Crafting payload text that closes your delimiter early, escaping the data block. Countered by random or escaped delimiters.

**Least privilege** — Scoping tools and credentials so that an injected instruction has nothing dangerous to invoke. The only defense that does not depend on the model's cooperation.

---

## Confusions worth naming

| Term A | Term B | Difference |
|---|---|---|
| Constraint | Suggestion | A constraint has a defined behavior when violated; a suggestion has a tone |
| Retry | Repair | Retry repeats the call; repair supplies the validator error |
| Summary | State block | A summary is prose; a state block is parseable and auditable |
| Temperature 0 | Determinism | The former is a sampling mode; the latter requires infrastructure guarantees |
| Schema valid | Correct | Syntax versus semantics; you need both |
| Abstention | Refusal | Abstention = "no evidence"; refusal = "policy forbids" |

**Do not use these pairs interchangeably in specs.** Downstream code cannot branch on a vibe; it branches on a `status`.

---

## Acceptance Checklist

- [ ] Every term used in your specs is defined consistently with this list.
- [ ] `/status` values (abstention, refusal, blocked) have distinct, documented meanings.
- [ ] No spec uses "deterministic" without stating what is actually guaranteed.
- [ ] Metric names map to a single definition across prompt, eval, and dashboard.
