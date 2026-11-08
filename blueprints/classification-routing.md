---
name: classification-routing
type: blueprint
version: 1.0.0
inputs: [taxonomy, label_definitions, boundary_examples, confidence_threshold]
output_format: raw-json
related: [prompt-chaining-and-routing, few-shot-calibration, structured-output]
---

# 🏷️ Blueprint F — Classification & Routing

Use for tagging, triage, intent detection, sentiment, moderation pre-checks, and any "pick one label" task. Classification is the highest-leverage prompt class in most systems: it is cheap, it runs on every request, and its errors cascade into everything downstream.

The design goal is not accuracy on the easy cases. It is **defined behavior on the boundary cases** — which is where every real taxonomy fails.

---

## Inputs

| Variable | Required | Example | Notes |
|---|---|---|---|
| `TAXONOMY` | ✅ | 4–12 labels | >12 labels: use a hierarchy or two-stage router |
| `DEFINITIONS` | ✅ | one sentence per label | Without these, the model invents boundaries |
| `BOUNDARIES` | ✅ | adjacent-label examples | The highest-value lines in the file |
| `CONFIDENCE` | ✅ | high/medium/low | Enables routing on uncertainty |
| `UNKNOWN` | ✅ | `unclear` | Must exist, or you get silent misroutes |
| `EXEMPLARS` | ⬜ | 1 per label + 2 boundary | Balance matters more than count |

---

## The Blueprint

```markdown
### Role
Deterministic classifier. You assign exactly one label and return data — never
prose, never an answer to the request.

### Context
- **Input type:** [ticket / message / document / log line]
- **Labels:** [label list with one-sentence definitions]
- **Boundary rules:** [which labels are confusable, and how to tell them apart]

### Objective
Assign exactly one label to <input>.

### Constraints & Negative Rules
- Choose exactly one label from the closed list. No free text, no synonyms.
- Use `unclear` when two labels are plausible and the distinction changes the
  downstream handling. DO NOT default to the most common label.
- Base the decision on the request's content, not its tone or the user's identity.
- DO NOT explain, summarise, answer, or suggest next steps.
- Cite the phrase that drove the decision when asked for `evidence`.
- Empty or unreadable input is a fallback case: use the `unclear` label with
  low confidence. Do not invent a label to fill the field.

### Output Specification
{"label": "<closed label>", "confidence": "high|medium|low", "evidence": "<verbatim phrase>"}
Raw JSON object. No fences, no preamble. If <input> is empty, return
{"label": "unclear", "confidence": "low", "evidence": ""}.
```

---

## Filled Example — Support Triage

```markdown
### Role
Deterministic ticket triage classifier for a SaaS billing product.

### Context
**Labels**
- `billing` — charges, invoices, refunds, payment methods, pricing questions.
- `bug` — product behaves differently than documented, reproducibly.
- `feature_request` — asks for behaviour the product does not have.
- `account` — login, permissions, workspace settings, seat management.
- `unclear` — two labels are equally plausible and the difference changes routing.

**Boundaries**
- "Charged twice" → `billing` (money moved), not `bug`.
- "Refund never arrived" → `billing` (refund state), not `account`.
- "Export button does nothing" → `bug` (documented feature broken).
- "Please add CSV export" → `feature_request`, even if the button is broken.
- "Can't log in" → `account` unless the error names a billing state.

### Objective
Assign exactly one label to <input>.

### Constraints & Negative Rules
- DO NOT label `bug` without a described failure of existing, documented behaviour.
- DO NOT label `feature_request` when the feature exists but is broken.
- DO NOT use `unclear` for requests that merely lack detail; use the label the
  stated problem belongs to.
- DO NOT answer, apologise, or route — classification only.

### Output Specification
{"label": "...", "confidence": "...", "evidence": "..."}
Raw JSON. If input is empty: {"label": "unclear", "confidence": "low", "evidence": ""}.
```

---

## Exemplar design

One exemplar per label plus two boundary exemplars is the minimum. More than ~12 total rarely helps and dilutes attention.

```markdown
<examples>
Input: "We were charged twice for October."
Output: {"label": "billing", "confidence": "high", "evidence": "charged twice"}

Input: "The invoice PDF won't download, clicking it does nothing."
Output: {"label": "bug", "confidence": "high", "evidence": "clicking it does nothing"}

Input: "It would be great if invoices had a CSV export."
Output: {"label": "feature_request", "confidence": "high", "evidence": "would be great if"}

Input: "I can't get into my account and also I think I was overcharged."
Output: {"label": "unclear", "confidence": "low", "evidence": "can't get into my account ... overcharged"}
</examples>
```

The last exemplar is doing the most work: it legitimises `unclear` and shows the exact shape of a tie.

---

## Confidence that means something

| Level | Definition | Routing |
|---|---|---|
| high | One label clearly fits; evidence phrase is decisive | Auto-route |
| medium | Fits, but a second label could be argued | Auto-route + sample audit |
| low | Boundary case | Human queue |

Do not ask for numeric probabilities. Enums with definitions are auditable; decimals are decoration.

---

## Evaluating a classifier

| Metric | Why it matters |
|---|---|
| Per-label precision/recall | Averages hide the expensive class |
| Confusion matrix | Shows *which* boundaries fail |
| `unclear` rate | Too low → forced guesses; too high → taxonomy too fine |
| Evidence validity | Is the quoted phrase really in the input? |
| Stability at temperature 0.7 × 5 | Same input, same label? (self-consistency sanity) |
| Drift over time | New product features invent new intents |

Build a labelled set of ~200 items, **oversampling boundaries**. Your classifier will look 95% accurate on natural data and 60% accurate where it matters.

---

## Taxonomy design rules

1. **Mutually exclusive by construction.** If two labels can both be true, define precedence explicitly.
2. **Operational, not conceptual.** "Refund requested" beats "negative sentiment" because someone can act on it.
3. **Cap at 7±2 for a single call.** Beyond that, use two stages (category → subtype).
4. **One label per item.** Multi-label is a different task with different evaluation.
5. **Every label has an owner** who can say what happens downstream.

---

## Failure Modes

| Failure | Symptom | Fix |
|---|---|---|
| Undefined boundaries | Adjacent labels disagree run to run | Add boundary rules + counter-examples |
| No `unclear` | Everything gets a label; misroutes in silence | Add `unclear` + a tie exemplar |
| Majority-class bias | Rare labels almost never predicted | Balance exemplars; report per-class recall |
| Tone-based labelling | Angry feature requests tagged `bug` | "Content, not tone" rule |
| Model answers instead of classifying | Prose with an embedded label | Closed output schema with no answer field |
| Free-text labels | Synonyms drift ("billing" / "payments") | Enum + post-validation |
| Taxonomy staleness | New product area has no label | Quarterly taxonomy review |

---

## Acceptance Checklist

- [ ] Closed label list with one-sentence definitions.
- [ ] Adjacent-label boundary rules written as examples.
- [ ] `unclear` exists with a defined downstream behavior.
- [ ] At least one exemplar per label, plus a tie exemplar.
- [ ] Output is a schema-validated enum, not free text.
- [ ] Confidence enum has operational definitions.
- [ ] Label validity is checked in code (reject anything outside the enum).
- [ ] Evaluation oversamples boundaries and reports per-class metrics.
