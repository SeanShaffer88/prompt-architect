---
name: task-decomposition
type: pattern
version: 1.0.0
inputs: [complex_task, stage_boundaries, interstage_contract]
output_format: staged-outputs
related: [prompt-chaining-and-routing, chain-of-thought, react-tool-use]
---

# 🧩 Task Decomposition

One prompt, one objective. When a request genuinely needs several, split it into stages with **explicit contracts between them** — not one giant prompt with numbered wishes.

The distinction matters: a numbered list inside one prompt is *objective stacking*, where a dropped item is invisible. A pipeline is *decomposition*, where each stage can be tested, retried, and measured separately.

---

## 1. When to split

Split when any of these is true:

| Signal | Why it justifies a stage boundary |
|---|---|
| Two different output formats | Each needs its own container contract |
| A mechanical step (parse, normalize, validate) | Better done in code than by a model |
| A step where errors are cheap to detect | Retry locally instead of restarting |
| Context for step B is a *summary* of step A | Avoids carrying the whole transcript |
| Different models would be optimal | Cheap model for extraction, strong model for judgment |
| Any step needing a human checkpoint | The boundary is the checkpoint |

Do **not** split when the steps are deeply interdependent (each informs the other's wording) — you will pay coordination cost and lose coherence.

---

## 2. The canonical pipeline

```text
[1. INGEST]      code: fetch, strip, chunk, validate encoding
      │  contract: raw text + source id
      ▼
[2. EXTRACT]     model: pull structured facts, null when absent
      │  contract: JSON schema (validated; rejected on failure)
      ▼
[3. NORMALIZE]   code: units, dates, dedupe, canonical enums
      │  contract: normalized records
      ▼
[4. JUDGE]       model (strong): compare, rank, decide
      │  contract: decision + rationale + citations
      ▼
[5. RENDER]      code or model: format for the consumer
      │  contract: exact output container
      ▼
[6. VERIFY]      code: schema + semantic checks; model: only if checks are fuzzy
```

Each arrow is a **typed contract**. If a stage cannot satisfy it, it returns a failure state rather than passing garbage downstream — which is the whole point of splitting.

---

## 3. Contracts between stages

A contract has four parts:

```markdown
Stage 2 → Stage 3

INPUT:      <document> raw text, ≤50k chars, UTF-8
OUTPUT:     {"parameters": [{"name": str, "default": any|null, "unit": "s|MB|count"}]}
INVARIANTS: one object per parameter; no invented values; `default` null when unstated
ON FAILURE: {"status": "unparseable", "reason": str} — stage 3 skips the record and logs
```

Rules:

1. **Succeed or fail explicitly.** A stage never emits a partial object silently.
2. **Types, not descriptions.** `amount_cents: int`, not "the amount in cents".
3. **Null policy inherited.** If stage 2 may emit `null`, stage 3 must handle it, not "clean it up".
4. **Version the contract** with the prompt. A prompt change that alters the schema is a breaking change.

---

## 4. Prompt chaining mechanics

```python
facts = extract(doc)                      # validated against schema
if facts.status != "ok": return skip(facts)
norm  = normalize(facts)                  # pure code — no model
verdict = judge(norm, rubric)             # strong model, small input
return render(verdict)                    # deterministic template
```

Why this beats one large prompt:

| Property | Single mega-prompt | Pipeline |
|---|---|---|
| Failure diagnosis | Guess which instruction lost | Localized to a stage |
| Retry cost | Whole task again | One stage |
| Model choice | One size fits none | Per stage |
| Testability | End-to-end only | Per contract |
| Token cost | Everything in one context | Summaries passed forward |
| Latency | One call | Parallelizable where independent |

The trade: more moving parts, more latency, more orchestration code. Split where the payoff exists, not by reflex.

---

## 5. Fan-out / fan-in

For N documents, sample per document, then aggregate:

```text
fan-out:  doc_1 → summarize()  ┐
          doc_2 → summarize()  ├─► N independent calls (parallel)
          doc_3 → summarize()  ┘
fan-in:   summaries[] → synthesize()  →  one answer
```

Fan-in is where quality is won or lost. The synthesis prompt must:

- receive **all** summaries (or a schedule if too many),
- be told that it may not introduce facts absent from the summaries,
- preserve per-document attribution (`source: doc_3`),
- handle contradictory summaries explicitly (report, don't average).

```markdown
### Objective
Synthesize the per-document findings into one answer.
### Constraints
- Every claim must trace to a `source` id present in <findings>.
- If findings conflict, list both with sources; do not reconcile silently.
- If a document contributed nothing, omit it rather than padding.
```

---

## 6. Avoiding decomposition theatre

Splitting for its own sake is a common failure: five model calls where one plus a parser would do.

| Ask | Better |
|---|---|
| "Extract, normalize, and dedupe" | One extraction call + code for normalize/dedupe |
| "Summarize each paragraph, then summarize summaries" | One call with a hard length cap (unless the doc exceeds context) |
| "First plan, then execute" in one prompt | One call with a procedure section, unless you need to validate the plan |
| "Classify, then route, then answer" | Classifier call + specialist prompt (real routing) |

**Rule:** if a stage can be done by a deterministic function, it should be code. Use models for judgment, extraction from messy text, and generation — not for sorting or arithmetic.

---

## 7. Anti-Patterns

| Anti-pattern | Symptom |
|---|---|
| Objective stacking in one prompt | One objective silently dropped |
| Passing full transcripts between stages | Context bloat, cost, drift |
| Unvalidated hand-offs | Garbage propagates and compounds |
| Implicit contracts ("it returns a list") | Integration breaks on the first edge case |
| Model calls for mechanical steps | Slower, costlier, less reliable than code |
| Retrying the whole pipeline on one stage's failure | Cost explosion |
| Fan-in that averages conflicting sources | Confident fiction |

---

## Acceptance Checklist

- [ ] Each stage has exactly one objective and one output artifact.
- [ ] Every stage boundary has a typed contract (input, output, invariants, failure).
- [ ] Stages fail explicitly rather than passing partial data.
- [ ] Mechanical work is code, not model calls.
- [ ] Independent stages run in parallel.
- [ ] Fan-in preserves attribution and reports conflicts.
- [ ] Each stage has its own tests, not only an end-to-end test.
- [ ] Contract versions are recorded with prompt versions.
