---
name: prompt-chaining-and-routing
type: pattern
version: 1.0.0
inputs: [intent_classes, specialist_prompts, routing_confidence]
output_format: routed-handoff
related: [task-decomposition, classification-routing, agent-system-prompt]
---

# 🚦 Routing & Handoff

One prompt cannot be excellent at billing policy, API debugging, and legal escalation. Routing sends each request to a specialist prompt — and the hard part is not the classifier. It is the **handoff**: what the specialist receives, and what happens when routing is wrong.

---

## 1. The shape

```text
                 ┌── billing ────► billing_prompt
request ──► router├── technical ──► technical_prompt
                 ├── account ────► account_prompt
                 └── unclear ────► clarifying_prompt
```

Three components, each testable:

1. **Router** — a classifier prompt returning a label + confidence.
2. **Specialists** — prompts optimized for one intent, with their own evidence and tone.
3. **Handoff contract** — the payload the specialist receives, including what the router knew.

---

## 2. Router prompt

```markdown
### Role
Intent classifier. You output a label and a confidence; you never answer the request.

### Context
[intent taxonomy with definitions and 2 boundary examples each]

### Objective
Assign exactly one intent to the request.

### Constraints & Negative Rules
- Choose `unclear` when two intents are plausible and the difference changes the
  answer materially. Do not guess the most common intent.
- Do not use the request's *tone* as evidence for its intent.
- Do not answer the question, summarize it, or suggest a next step.

### Output Specification
{"intent": "<label>", "confidence": "high|medium|low", "evidence": "<phrase from request>"}
Raw JSON only.
```

Design notes:

- **Define boundary cases in the taxonomy.** Most routing errors are between two adjacent intents ("refund request" vs "billing question"), not random.
- **Include `unclear`.** Without it, the router is forced to guess and misroutes silently.
- **Ask for evidence.** A router that cannot quote the phrase driving its decision is guessing.
- **Keep the router cheap.** Small model, low temperature, schema-constrained, 5–10 exemplars.

---

## 3. Handoff contract

The specialist must not re-derive what the router already knows, and must not inherit the router's mistakes.

```markdown
### Context
- **Intent:** billing (confidence: high)
- **Router evidence:** "charged twice on 3 Nov"
- **Conversation state:** [verified customer; 1 prior ticket closed]
- **Retrieved context:** <docs>[policy excerpts]</docs>

### Instructions
- Answer within the billing scope only.
- If the request actually belongs to another intent, reply
  {"status": "misrouted", "suggested_intent": "<label>"} instead of answering
  outside your scope.
- Do not repeat the router's classification to the user.
```

The `misrouted` branch is the most valuable line in the file. It turns a routing error from a silent wrong answer into a measurable event you can retrain against.

---

## 4. Confidence thresholds

| Router output | Action |
|---|---|
| high confidence, clear intent | Route directly |
| medium confidence | Route, but include the second-best intent as a hint |
| low confidence | Clarify with the user, or route to a generalist |
| `unclear` | Ask one clarifying question — never two |

Never route on `unclear` silently. The cheapest clarification is one question; the most expensive outcome is a confident specialist answering the wrong question.

---

## 5. Avoiding router drift

| Drift | Cause | Countermeasure |
|---|---|---|
| Everything routes to the biggest class | Imbalanced exemplars | Balance exemplars; report per-class precision |
| Taxonomy grows unruly | Adding a class per edge case | Cap classes; merge or use `unclear` |
| Router starts answering | Prompt ambiguity | Explicit "never answer" rule + output schema without an answer field |
| Specialists duplicate the router's work | Handoff omits state | Include intent, evidence, and known state |
| Misroutes invisible | No `misrouted` branch | Require the specialist to report it |

Instrument per-class precision and recall. A router at 92% overall accuracy can be 60% on your most expensive class — and average accuracy will hide it.

---

## 6. Chaining without routing

Not every chain needs a classifier. Sequential prompts with fixed contracts (extract → judge → render) are simpler and more predictable than a router when every request takes the same path. See [task decomposition](task-decomposition.md).

Routing earns its complexity when:

- request types need *different evidence* (billing policy vs. API docs),
- request types need *different tone* (user-facing vs. internal),
- volume justifies different *model classes* per intent (cost),
- regulatory boundaries require a separate prompt per domain.

---

## 7. Anti-Patterns

| Anti-pattern | Failure |
|---|---|
| Router that also answers | Two jobs, both worse |
| No `unclear` class | Silent misroutes |
| Handoff without router evidence | Specialist re-derives (and may disagree) |
| No misrouted branch | Errors invisible |
| Per-edge-case taxonomy | Fifty classes, none reliable |
| Routing on average accuracy | Expensive class failures hidden |
| Clarifying question for a high-confidence request | Annoying and unnecessary |

---

## Acceptance Checklist

- [ ] Taxonomy has definitions and boundary examples for adjacent classes.
- [ ] Router output includes label, confidence, and evidence.
- [ ] `unclear` exists with a defined behavior.
- [ ] Handoff includes intent, evidence, state, and scope limits.
- [ ] Specialist can report `misrouted` without answering outside scope.
- [ ] Thresholds map confidence → action.
- [ ] Per-class precision/recall are monitored, not just overall accuracy.
