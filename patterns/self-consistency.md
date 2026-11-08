---
name: self-consistency
type: pattern
version: 1.0.0
inputs: [task, sample_count, agreement_policy, temperature]
output_format: answer-plus-agreement
related: [chain-of-thought, uncertainty-and-abstention, sampling-and-determinism]
---

# 🔁 Self-Consistency (Sampling + Voting)

Sample the same prompt several times at non-zero temperature and take the answer that the samples agree on. Where a single sample is a coin flip, an ensemble is a probability estimate — and the **disagreement rate is itself a useful signal** you get for free.

Use it when answers are discrete (a classification, a number, a choice among candidates) and mistakes are expensive. Do not use it when answers are long prose: there is nothing to vote on.

---

## How it works

```text
              ┌── sample 1 ──► "VLAN 40 misconfigured"
prompt ──────►├── sample 2 ──► "VLAN 40 misconfigured"
  (T≈0.7)     ├── sample 3 ──► "VLAN 40 misconfigured"
              ├── sample 4 ──► "DHCP scope exhausted"
              └── sample 5 ──► "VLAN 40 misconfigured"
                                     └─► answer: VLAN 40 (4/5), confidence 0.8
```

Two things come out: an answer, and an agreement score. The second one is what most teams throw away.

---

## Core Template

```markdown
### Role
[Diagnostic engine]. You return one primary cause and a short justification.

### Context
- **Symptom:** [observable failure]
- **Evidence:** <evidence>[logs, config, metrics]</evidence>
- **Candidate causes:** [enumerated list, if known]

### Objective
Identify the single most likely cause.

### Constraints & Negative Rules
- Choose exactly one candidate. Do not hedge with "possibly" or "and/or".
- Cite at least one line from <evidence> for the chosen cause.
- If no candidate is supported by the evidence, answer `INSUFFICIENT_EVIDENCE`;
  that is a valid answer, not a failure.
- Do not speculate about causes outside the candidate list.

### Output Specification
Raw JSON: {"cause": "<candidate or INSUFFICIENT_EVIDENCE>", "evidence": "<verbatim line>", "confidence": "high|medium|low"}
No fences, no prose.
```

Then run it *n* times at `temperature 0.7–1.0` and vote in your code. The prompt stays simple; the consistency comes from the sampling, not from asking the model to be sure of itself.

---

## Voting mechanics

| Answer type | Aggregation | Notes |
|---|---|---|
| Label / enum | Exact-match majority | Simplest and most reliable |
| Number | Median (or mode for discrete counts) | Median resists one wild sample |
| Short text | Normalize (case, punctuation) then majority | Use a canonical form |
| Ordered list | Kendall-tau / position-weighted vote | Complex; consider pairwise comparison instead |
| Free prose | Don't | Use a judge or a rubric-scored pairwise method |
| Boolean | Majority with a threshold | Require ≥70% agreement to act |

**Thresholds, not just winners.** A 60/40 split is qualitatively different from 100% agreement, even if both "have a winner". Route the 60/40 case to a human or a stronger model.

---

## Confidence from agreement

| Agreement | Interpretation | Disposition |
|---|---|---|
| 100% (n=5) | Strongly modal | Act automatically |
| 80% | Solid | Act automatically |
| 60–79% | Contested | Escalate, or re-sample with more context |
| < 60% | Underspecified | The prompt is missing context or a rule — do not ship this case class |

Low agreement usually means the *prompt* is ambiguous, not that the case is hard. That is the diagnostic value: agreement is a free ambiguity detector.

---

## Cost model

| Samples | Cost | Latency | Best for |
|---|---|---|---|
| 1 | 1× | 1× | High-volume, low-stakes |
| 3 | 3× | ~1× (parallel) | Recommended default for classification |
| 5 | 5× | ~1× (parallel) | High-stakes, small volume |
| 9+ | 9× | ~1–2× | Offline audit, calibration studies |

Because samples run in parallel, latency is roughly unchanged — you are buying accuracy with tokens, not with wall-clock time. That trade is usually right for small outputs.

---

## Worked example: policy classification

Task: classify a support ticket into `billing`, `bug`, `feature_request`, `abuse`.

- Prompt: 5-component extraction-style classification prompt with 4 exemplars (one per class) and an explicit `unclear` fallback.
- Settings: temperature 0.8, n=5.
- Aggregation: majority; require ≥3/5.

Observed over 200 tickets:

| Pattern | Share | Action |
|---|---|---|
| 5/5 agreement | 71% | Auto-route |
| 4/5 | 18% | Auto-route, log |
| 3/5 | 8% | Auto-route with flag, sample for audit |
| Split (no majority) | 3% | Human triage |

Result: 3% manual triage instead of 100%, with the 3% concentrated exactly where the taxonomy is ambiguous — which is also where you should invest in exemplars next.

---

## When not to use it

- **Long-form output** (articles, design docs, refactors) — no meaningful vote.
- **Latency-critical single calls** — 5 samples cost 5× the tokens even if parallel.
- **Near-deterministic tasks** — if 5 samples always agree, you are paying 5× for nothing. Measure agreement on a sample of 50 first; if it is ≥99%, drop to n=1.
- **Tasks needing global consistency** (a batch of records that must agree with each other) — sample the *batch*, not each record, or you will create contradictions.

---

## Anti-Patterns

| Anti-pattern | Why it fails |
|---|---|
| Asking the model "are you sure?" instead of re-sampling | Correlated errors; the model rationalizes its first answer |
| Voting on prose | No canonical form; the vote is noise |
| Temperature 0 with n=5 | Five identical samples; you paid 5× for one |
| Ignoring the split cases | The 60/40 cases are your real risk surface |
| Using agreement as ground truth | Five samples can agree on the same hallucination |

---

## Acceptance Checklist

- [ ] Answers are discrete and canonicalizable.
- [ ] Temperature is high enough to produce genuinely different samples.
- [ ] Aggregation rule is defined per answer type (mode, median, threshold).
- [ ] A minimum-agreement threshold exists, with a disposition for below it.
- [ ] Parallel execution is used so latency does not scale with n.
- [ ] Agreement is measured once on a sample of 50 before enabling in production.
- [ ] A fallback path exists for a split vote (human queue, escalation, `INSUFFICIENT_EVIDENCE`).
