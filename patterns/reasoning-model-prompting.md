---
name: reasoning-model-prompting
type: pattern
version: 1.0.0
inputs: [task, success_criteria, output_contract, thinking_budget]
output_format: conclusion-plus-rationale
related: [chain-of-thought, model-landscape-and-migration, constraint-enforcement]
---

# 🧠 Prompting Reasoning Models

Models with an explicit thinking phase invert the classic prompting habits. They already plan; scaffolding can compete with their plan. They reason well; they still need to be told what "done" looks like.

The failure signature is consistent: **correct analysis, wrong container** — a thorough deliberation delivered as an essay when you needed three fields of JSON.

---

## 1. What changes

| Classic habit | On reasoning models | Why |
|---|---|---|
| "Think step by step" | Redundant | Planning is internal and automatic |
| Long procedural recipes | Competing plans | The model's own decomposition is usually better |
| Few-shot for *logic* | Usually unnecessary | Use exemplars for **format**, not reasoning |
| "Explain your reasoning in detail" | Ignored or harmful | Reasoning is hidden; ask for a brief rationale instead |
| "Be concise" | More reliable than before | Still needed; reasoning models over-elaborate |
| Strict output schema | Usually honored | Specify the container anyway |
| Temperature tuning | Less influential | Many expose reasoning effort instead |
| `max_tokens` = output length | Can truncate reasoning | Reasoning tokens may count against the budget |

---

## 2. What to write instead

Keep the 5 components, compress components 1–3, and invest in **success criteria + output contract**.

```markdown
### Role
Senior reviewer for [domain].

### Context
- **Artifact:** <artifact>[content]</artifact>
- **Constraints:** [what must remain true]
- **Definition of done:** [the specific conditions that make an answer correct]

### Objective
[One imperative verb] [one artifact].

### Constraints & Negative Rules
- Optimize for [correctness dimension], not for completeness of commentary.
- Do not restate the artifact.
- Do not include your reasoning process; include only the conclusion and a
  rationale of at most 5 sentences.
- If the artifact is insufficient to decide, output
  {"status": "insufficient_context", "missing": [...]} instead of a best guess.

### Output Specification
[Exact shape: fields, order, length caps, no fences.]
```

Three things earn their tokens: **definition of done**, **the negative rules about commentary**, and **the output contract**. Everything else can be shorter than you think.

---

## 3. Definition of done beats instructions

A reasoning model optimizes against the criteria you give it. If the criteria are vague, it invents its own — usually "be thorough".

| Vague | Operational |
|---|---|
| "Review this design" | "Approve or reject on these 3 criteria: [c1, c2, c3]. Reject if any is violated." |
| "Find bugs" | "Find defects that change output for valid inputs. Ignore style. Cite line numbers." |
| "Improve this prompt" | "Raise schema validity from X to 4/5 on cases T2–T6 without lengthening beyond 600 tokens." |
| "Answer the question" | "Answer in ≤120 words, cite a source id per claim, abstain if unsupported." |

The pattern: **make the evaluation criterion the instruction.** If you can't state what a correct answer looks like, the prompt isn't ready — and no model will rescue that.

---

## 4. Budgets

| Budget | Meaning | Guidance |
|---|---|---|
| Thinking / reasoning budget | Tokens for internal deliberation | Classification: minimal. Multi-constraint design: high. Too low silently degrades correctness. |
| `max_tokens` | Visible output cap | Set from the contract (e.g. 300 tokens for a review), not from the reasoning budget |
| Turn budget (agents) | Calls before stopping | Reasoning models use fewer turns but longer ones; budget cost, not just count |

Symptom of a too-small thinking budget: confident, shallow answers with no visible error. Symptom of a too-large one: latency and cost on trivial requests. Measure accuracy vs. budget on your eval set; the curve usually plateaus earlier than expected.

---

## 5. Reading the output

- **Do not ask for hidden reasoning.** It is either unavailable or summarized; asking produces a fabricated narrative.
- **Ask for a short rationale** if you need auditability: `"rationale": "<=5 sentences"`.
- **Verify the conclusion independently** when stakes are high — reasoning quality correlates with correctness better than chat models, but it is not a guarantee.
- **Check format before content** in automated pipelines: a perfect analysis in the wrong container is a failed call.

---

## 6. When *not* to use a reasoning model

| Task | Better choice |
|---|---|
| High-volume classification | Small model + schema + exemplars |
| Simple extraction | Small model, temperature 0 |
| Latency-critical UX (autocomplete, chat) | Fast chat model |
| Format-only transformation | Cheap model with a strict contract |
| Retrieval-and-quote | Small model with a grounding rule |

Reasoning models are for tasks where being wrong is expensive and being slow is acceptable. Routing by difficulty (classifier → small vs. reasoning) usually beats using one model for everything.

---

## 7. Migration notes

When moving a chat-model prompt to a reasoning model:

1. **Strip the CoT scaffolding** ("think step by step", "first list…"). Keep the procedure only if it encodes *policy*, not reasoning.
2. **Keep the exemplars that teach format.** Drop the ones that teach logic.
3. **Tighten the length caps.** The model will use the room you give it.
4. **Re-run T1–T6.** Format drift is the most common regression.
5. **Re-check the failure cases** — some edge cases that needed explicit rules may now be handled; remove scaffolding you no longer need, and keep what still earns its tokens.

---

## 8. Anti-Patterns

| Anti-pattern | Failure |
|---|---|
| Porting "think step by step" verbatim | Redundant tokens, sometimes worse |
| No definition of done | Model invents its own, usually "be exhaustive" |
| Asking for full chain-of-thought | Fabricated or unavailable reasoning |
| `max_tokens` sized for output only | Reasoning truncation → confidently wrong |
| Reasoning model for a regex-grade task | 10× cost for the same answer |
| Expecting concision without a cap | Essays |

---

## Acceptance Checklist

- [ ] Success criteria ("definition of done") are explicit and testable.
- [ ] The output contract specifies fields, order, and length caps.
- [ ] Commentary and process narration are explicitly excluded.
- [ ] Reasoning budget and output budget are set independently.
- [ ] Abstention has a shape.
- [ ] Classic CoT scaffolding has been removed or justified.
- [ ] The prompt was re-evaluated on the reasoning model rather than assumed portable.
