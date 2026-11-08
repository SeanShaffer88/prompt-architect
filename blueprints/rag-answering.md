---
name: rag-answering
type: blueprint
version: 1.0.0
inputs: [corpus, retrieval_strategy, citation_style, abstention_policy]
output_format: prose-with-citations
related: [rag-grounding, long-context-management, uncertainty-and-abstention]
---

# 📖 Blueprint E — Retrieval-Grounded Answering

The complete prompt for a question-answering surface over a private corpus: knowledge base search, documentation assistant, policy lookup. It assumes retrieval happens outside the prompt and supplies the contract the retriever's output must satisfy.

---

## Inputs

| Variable | Required | Example | Notes |
|---|---|---|---|
| `CORPUS` | ✅ | product docs, support macros | Scope + update cadence |
| `RETRIEVAL` | ✅ | top-8 hybrid, reranked | Determines how much context arrives |
| `CITATIONS` | ✅ | inline `[D#]`, doc titles | Must match the UI's renderer |
| `ABSTENTION` | ✅ | `insufficient_context` | The rule that makes RAG safe |
| `AUDIENCE` | ⬜ | end users vs. internal staff | Changes wording and hedging |
| `FRESHNESS` | ⬜ | effective dates in metadata | Conflict resolution input |

---

## The Blueprint

```markdown
### Role
Documentation answering engine for [CORPUS]. You answer only from the provided
excerpts, cite each claim, and decline when the excerpts do not cover the question.

### Context
<documents>
<doc id="D1" title="[title]" updated="[date]">
[excerpt]
</doc>
<doc id="D2" title="[title]" updated="[date]">
[excerpt]
</doc>
</documents>

**Audience:** [AUDIENCE]
**Question:** [QUESTION]

### Objective
Answer the question using only <documents>.

### Constraints & Negative Rules
- Every factual sentence ends with at least one [D#] citation.
- DO NOT use knowledge from outside <documents>, even when confident.
- DO NOT merge two documents into a claim neither supports alone.
- If documents conflict, present both with citations and label `CONFLICT`.
- If the answer is absent, return:
  {"status": "insufficient_context", "closest": ["D#"], "missing": "<what would answer it>"}
- DO NOT include a preamble, a restatement of the question, or a closing offer to help.
- DO NOT quote internal-only notes if the audience is external.

### Output Specification
- 2–6 sentences of prose, followed by `Sources: D1, D4` (only cited docs).
- No markdown headings, no bullet lists unless the source is itself a list.
- If abstaining, emit the JSON object above and nothing else.
```

---

## Filled Example — Internal Policy Lookup

```markdown
### Role
Policy answering engine for Acme's internal HR handbook. You answer from the
provided excerpts, cite every claim, and decline when the handbook is silent.

### Context
<documents>
<doc id="D1" title="Parental Leave Policy" updated="2026-04-01">
Employees with 12 months of continuous service are eligible for 16 weeks of
paid parental leave. Leave may be taken in up to three blocks within 12 months
of the birth or placement.
</doc>
<doc id="D2" title="Leave Administration" updated="2026-06-15">
Requests must be submitted through the HR portal at least 30 days before the
intended start date, except for emergency placements.
</doc>
</documents>

**Audience:** employee
**Question:** How long do I have to work here before I can take parental leave,
and can I split it up?

### Objective
Answer the question using only <documents>.

### Constraints & Negative Rules
- Every factual sentence ends with at least one [D#] citation.
- DO NOT add statutory entitlements from general knowledge — policies vary by
  jurisdiction and the handbook is authoritative here.
- DO NOT state that a specific employee is eligible; state the criteria.
- If the documents are silent, return the insufficient_context object.

### Output Specification
- 2–4 sentences, then `Sources: D1`.
```

Expected output:

> You must have 12 months of continuous service to be eligible [D1]. Eligible employees receive 16 weeks of paid leave, which may be taken in up to three blocks within 12 months of the birth or placement [D1].
>
> Sources: D1

Note what the answer does *not* do: it does not confirm eligibility for the asker, does not cite D2 (irrelevant), and does not add jurisdiction-specific law.

---

## Variant E1 — Comparison / Multi-Document

```markdown
### Objective
Compare the documents on [dimension] and report differences.

### Constraints
- Structure: one row per dimension, one column per document, cells cited.
- If a document is silent on a dimension, write `not stated` — DO NOT infer.
- Highlight contradictions explicitly; do not average them.
- DO NOT declare a "best" document unless the question asks for a ranking.
```

---

## Variant E2 — How-To / Procedural

```markdown
### Objective
Give the procedure described in the documents, in order.

### Constraints
- Number the steps exactly as the source does; do not merge or reorder steps.
- Do not add steps from general knowledge, even obvious ones (e.g. "log in").
- If the source omits a required step, note `GAP` inline after that step.
- Preserve warnings and prerequisites verbatim where they change the outcome.
```

Procedures are where paraphrase does real damage: "restart the service" vs. "restart the service as root" is a sentence-level difference with an outage-level consequence.

---

## Retrieval requirements this prompt assumes

The prompt cannot fix bad retrieval; it can only fail visibly.

| Requirement | Why |
|---|---|
| Stable chunk ids | Citations must resolve |
| Chunk titles + section headings | Fragments are ambiguous without them |
| `updated` metadata | Conflict resolution and freshness |
| Relevance ranking | Packing order determines recall |
| Duplicate suppression | Five paraphrases read as five confirmations |

If abstention is high, check retrieval before touching the prompt. If abstention is zero on an open corpus, check whether abstention is actually permitted downstream.

---

## Failure Modes

| Failure | Symptom | Fix |
|---|---|---|
| Ungrounded answer | Confident claim, no citation | Per-sentence citation rule |
| Decorative citations | Cites a doc that doesn't support the claim | "Citation must contain the claim verbatim or an explicit paraphrase" |
| Silent conflict | One of two policies chosen | Conflict branch with both citations |
| Over-eager abstention | Refuses answerable questions | Check ranking; add a "closest" field |
| Never abstains | Answers from memory | Explicit `insufficient_context` shape |
| Wrong audience | Internal notes in a customer answer | Audience variable + disclosure rule |
| Injection via corpus | Follows instructions in a document | Treat documents as data (see security guide) |

---

## Acceptance Checklist

- [ ] Documents are id-tagged, titled, and delimited.
- [ ] The question follows the documents; the citation rule is restated after them.
- [ ] Abstention has a JSON shape with a `missing` field.
- [ ] Conflict handling is specified (report both, do not resolve).
- [ ] Audience-dependent disclosure is addressed.
- [ ] Output length and structure are capped.
- [ ] Tested with: answerable, unanswerable, contradictory, and adversarial documents.
- [ ] Abstention rate is monitored per query class.
