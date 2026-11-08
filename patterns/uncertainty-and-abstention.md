---
name: uncertainty-and-abstention
type: pattern
version: 1.0.0
inputs: [decision_task, evidence_source, abstention_threshold]
output_format: decision-with-confidence
related: [self-consistency, rag-grounding, evaluation-matrix]
---

# ⚖️ Uncertainty & Abstention

Models are trained to be helpful, which makes them answer. In high-stakes systems the valuable behavior is often the opposite: **say "I don't know" in a shape the system can route on.**

This pattern makes abstention legal, structured, and measurable — instead of accidental, apologetic, and invisible.

---

## 1. Why models don't abstain by default

| Mechanism | Effect |
|---|---|
| Helpfulness training | A refusal reads as a failure; a fluent guess reads as success |
| No cost model | The model has no notion of a wrong answer being expensive |
| Confidence ≠ correctness | Fluency is not calibrated; the most confident sentence is often the least supported |
| No empty state in the schema | If there is no legal "unknown", the model must pick something |

You cannot fix the first three with instructions alone. You fix the fourth — and that is usually enough.

---

## 2. The abstention vocabulary

Pick one set and use it everywhere. Downstream code branches on it.

| State | Meaning | Routing |
|---|---|---|
| `ok` | Answer supported by evidence | Automatic |
| `insufficient_context` | Evidence does not cover the question | Retrieval improvement queue |
| `ambiguous_request` | Two readings, materially different | Clarifying question |
| `conflicting_sources` | Evidence disagrees | Human review |
| `out_of_scope` | Not a task this system does | Handoff / polite refusal |
| `low_confidence` | Answer exists but below threshold | Human review |

```json
{"status": "insufficient_context", "missing": "effective date of the 2027 tier", "closest": ["D4"]}
```

The `missing` field is what makes this operational rather than decorative: it names exactly what would change the answer, which is a retrieval and product roadmap input.

---

## 3. Core Template

```markdown
### Role
Decision engine for [domain]. You return a decision plus its evidentiary basis,
and you stop when the evidence does not support one.

### Context
- **Task:** [the decision to make]
- **Evidence:** <evidence>[sources with ids]</evidence>
- **Decision rule:** [the policy, made explicit — not "use your judgment"]

### Objective
Apply the decision rule to the evidence and return the decision.

### Constraints & Negative Rules
- Answer only if at least one piece of evidence explicitly supports the decision.
  Implication alone is not support.
- If evidence is missing, return `insufficient_context` and name what is missing.
- If evidence conflicts, return `conflicting_sources` and list both with ids.
- Do not estimate a value that the evidence does not state.
- Do not express confidence with adjectives ("very likely"); use the enum.

### Output Specification
{"status": "ok|insufficient_context|ambiguous_request|conflicting_sources|out_of_scope",
 "decision": string|null,
 "evidence": ["<source id>", ...],
 "confidence": "high|medium|low"|null,
 "missing": string|null}
Raw JSON, no fences.
```

Note what the schema does: `decision` is nullable *only* when status is not `ok`, and `confidence` is an enum, not a vibe. Every field forces a commitment.

---

## 4. Calibrating the threshold

Abstention rate is a product decision, not a prompt decision. Make it explicit:

```markdown
Answer when you can cite one explicit supporting sentence.
Abstain when the best support is inference, absence of a callout, or
a convention the document does not state.
```

Then measure:

| Metric | Definition | Healthy signal |
|---|---|---|
| Abstention rate | Share of `insufficient_context` | Non-trivial (2–15% is common in real corpora) |
| False abstention | Unanswerable per model, but the corpus had the answer | Low → retrieval problem |
| False confidence | Answered, but wrong | Should trend to zero as rules tighten |
| Abstention by query class | Grouped by intent | Reveals missing documents |

A system that abstains 0% of the time on an open corpus is not confident; it is uncalibrated.

---

## 5. Confidence without a probability

Models produce poorly calibrated probabilities; asking for "0.0–1.0" yields numbers that look scientific and correlate weakly with correctness. Prefer:

1. **Evidence count** — how many independent sources support it.
2. **Sample agreement** — self-consistency over 3–5 samples.
3. **Enum confidence** — high/medium/low, defined operationally:

```markdown
high   = at least two independent sources state it explicitly
medium = one source states it explicitly
low    = one source implies it, or sources partially conflict
```

Defined levels are auditable. Invented decimals are not.

---

## 6. Making "I don't know" safe to say

The model needs to know abstention is an acceptable outcome, and the *system* must not punish it:

| Pressure | Effect | Fix |
|---|---|---|
| "Always give an answer" | Fabrication | Explicitly permit abstention |
| "Be concise and decisive" | Guessing | Add "decisive only when supported" |
| Downstream code requires a value | Model forced to invent | Nullable fields + fallback branch in code |
| Eval counts abstention as failure | Prompt learns to guess | Score abstention separately (correct vs incorrect abstention) |

That last row matters most: **if your eval treats every abstention as a miss, you are training the prompt to hallucinate.**

---

## 7. Anti-Patterns

| Anti-pattern | Failure |
|---|---|
| "If unsure, say so" with no shape | Unstructured apology the system cannot route |
| No nullable fields | Forced invention |
| Asking for probabilities | False precision |
| Abstention absent from the eval suite | Invisible behavior |
| Abstaining on everything | Useless system; track false abstention too |
| Inferring from absence ("no policy mentioned, so it's allowed") | Silent, confident, wrong |

---

## Acceptance Checklist

- [ ] A closed abstention vocabulary exists and is shared with downstream code.
- [ ] Every decision field is nullable with an explicit status precondition.
- [ ] The decision rule is stated (what counts as support).
- [ ] Confidence is an enum with operational definitions.
- [ ] The eval suite includes unanswerable cases and scores abstention correctly.
- [ ] Abstention rate is monitored by query class.
- [ ] False confidence and false abstention are tracked separately.
