---
name: summarization
type: blueprint
version: 1.0.0
inputs: [source_type, audience, length_budget, must_preserve]
output_format: structured-summary
related: [long-context-management, style-control, rag-grounding]
---

# 📝 Blueprint G — Summarization

A summary is not "the text, shorter". It is a **selection under a purpose**: what the reader needs to decide or act. Prompts that say "summarize this" produce the model's idea of important, which is usually the opening paragraph plus a list of topics.

Define the purpose, the length, and what must survive compression.

---

## Inputs

| Variable | Required | Example | Notes |
|---|---|---|---|
| `PURPOSE` | ✅ | decide whether to escalate | Drives selection, not just length |
| `AUDIENCE` | ✅ | on-call engineer | Determines jargon and detail |
| `LENGTH` | ✅ | ≤120 words / 5 bullets | Must be countable |
| `PRESERVE` | ✅ | ids, amounts, dates, decisions | The facts compression must not lose |
| `DISTORTION` | ✅ | no added inference | The main failure mode |

---

## The Blueprint

```markdown
### Role
Summarization engine for [SOURCE_TYPE], writing for [AUDIENCE].

### Context
- **Purpose:** [what the reader will do with this summary]
- **Source:** <source>[text]</source>
- **Known constraints:** [length, format, terminology]

### Objective
Produce a summary that lets [AUDIENCE] [PURPOSE], using only <source>.

### Constraints & Negative Rules
- Preserve verbatim: [ids, numbers, dates, names, decisions, deadlines].
- DO NOT add facts, causes, or recommendations not present in <source>.
- DO NOT soften or strengthen claims ("may" must not become "will").
- DO NOT include the source's examples unless they are the point.
- DO NOT editorialise, evaluate, or thank the reader.
- If the source is too short to summarize (<[N] words), return it verbatim with
  {"status": "already_concise"} rather than padding.
- If the source is unusable (empty, garbled), return
  {"status": "unusable_source", "reason": "..."}.

### Output Specification
[exact structure: N bullets / one paragraph / fields]
No preamble, no "This document discusses…", no closing summary.
```

---

## Filled Example — Incident Summary for On-Call

```markdown
### Role
Incident summarization engine for an SRE on-call rotation.

### Context
- **Purpose:** decide whether to join the incident bridge now or monitor.
- **Source:** <source>[incident channel export: 340 messages]</source>
- **Known constraints:** the reader has 20 seconds and no prior context.

### Objective
Summarize the incident so the on-call engineer can decide within 20 seconds.

### Constraints & Negative Rules
- Preserve verbatim: service names, error codes, timestamps, customer counts.
- State impact in customer-facing terms, citing the message that established it.
- DO NOT speculate about root cause; report only what was stated.
- DO NOT include speculation from the channel without marking it `UNCONFIRMED`.
- DO NOT describe the response process ("the team then…") unless it changed impact.
- If impact is not yet known, say `impact: unknown` — DO NOT infer it from the
  number of messages.

### Output Specification
Exactly 4 lines:
1. `impact:` <who/what is affected, with numbers>
2. `status:` <investigating | mitigating | resolved> + timestamp
3. `next:` <the next decision or action named in the channel>
4. `unconfirmed:` <one line, or "none">
No headings, no prose.
```

Expected shape:

```text
impact: Checkout API 5xx since 14:02Z; ~1,200 orders failed, 3 enterprise accounts affected
status: mitigating since 14:19Z (rollback of pricing-service v412 in progress)
next: confirm error rate <0.1% before 15:00Z standup
unconfirmed: one engineer suspects DB connection pool exhaustion (no evidence cited)
```

---

## Variant G1 — Executive Brief

```markdown
### Purpose
Decide whether to fund the next phase.
### Audience
VP, 60 seconds, no technical context.
### Constraints
- Lead with the decision requested and the deadline.
- Include one number that most changes the decision.
- DO NOT explain methodology unless it changes the recommendation.
- DO NOT use adjectives as evidence ("significant", "robust").
### Output
3 bullets: Recommendation | Because (one number) | Decision needed by <date>.
```

---

## Variant G2 — Structured Extraction-Summary

For meeting notes, tickets, or contracts, return fields instead of prose:

```markdown
### Output Specification
{
  "decisions": [{"decision": str, "owner": str|null, "date": str|null}],
  "actions":   [{"action": str, "owner": str|null, "due": str|null}],
  "open_questions": [str],
  "risks": [str]
}
Raw JSON. Empty arrays when a category is absent — never omit a key.
```

Fields force completeness in a way prose does not: an empty `actions: []` is a claim you can check.

---

## Evaluation: the four summarization failures

| Failure | Example | Test |
|---|---|---|
| **Omission** | Drops the one constraint that matters | Preserve-list check: every required fact present |
| **Distortion** | "may fail" → "fails" | Entailment check: summary claims supported by source |
| **Addition** | Invents a cause or a number | Every number/id must appear in the source |
| **Miscalibration** | 300 words for a 200-word source | Length check in code, not trust |

A practical harness: for each source, mark N must-preserve facts. Score `preserved / N`. Then check that every number and proper noun in the summary exists in the source (cheap, catches most addition).

---

## Length control

| Unit | Works when | Breaks when |
|---|---|---|
| Word cap | Usually | Model undershoots with filler |
| Bullet count | Best for lists of facts | Number of facts ≠ number of bullets |
| Field schema | Best for structured content | Content is genuinely narrative |
| Character cap | UI-constrained surfaces | Truncation mid-word |

Pair a cap with an anti-padding rule; otherwise the model uses the budget instead of respecting the content.

---

## Failure Modes

| Failure | Symptom | Fix |
|---|---|---|
| Generic topic list | "This document covers X, Y, Z" | Purpose + audience in the context |
| Compression without selection | Keeps the intro, drops the number | Preserve-list |
| Silent inference | Summary contains a cause | "No causes not stated" |
| Tone shift | "Fortunately, the team quickly…" | Prohibited devices list |
| Length drift | 3× the cap | Structural cap + code check |
| Duplicate content | Same fact in two bullets | Deduplication rule |

---

## Acceptance Checklist

- [ ] Purpose and audience are stated, not implied.
- [ ] Length is bounded by a countable structure.
- [ ] A must-preserve list exists (ids, numbers, dates, decisions).
- [ ] Inference, speculation, and editorialising are explicitly forbidden.
- [ ] Degenerate inputs (too short, empty, garbled) have defined outputs.
- [ ] Output is machine-checkable (schema or fixed line count) where it matters.
- [ ] Evaluation measures omission, distortion, addition, and length separately.
