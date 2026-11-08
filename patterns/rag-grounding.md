---
name: rag-grounding
type: pattern
version: 1.0.0
inputs: [query, retrieved_chunks, citation_policy, abstention_rule]
output_format: answer-with-citations
related: [rag-answering, long-context-management, uncertainty-and-abstention]
---

# 🔎 RAG Grounding

Retrieval-augmented generation has one job: **answer from the retrieved text, or say that the retrieved text does not answer it.** Everything in this pattern serves that sentence.

A RAG prompt that omits an abstention path is not grounded — it is a chat model with a document stapled to it.

---

## 1. The four rules

```markdown
1. The context is the ONLY source of truth for factual claims.
2. Every claim carries a citation to the chunk that supports it.
3. If the context does not contain the answer, abstain — do not use prior knowledge.
4. Quote when precision matters; paraphrase when fluency matters — never invent.
```

Rule 3 is the one teams skip, and it is the one that converts confident wrong answers into useful refusals.

---

## 2. Core Template

```markdown
### Role
Retrieval-grounded question answering engine. You answer only from the provided
context and cite every factual claim.

### Context
<context>
[chunk id="doc-17#3"]
...retrieved text...
[/chunk]
[chunk id="doc-42#1"]
...retrieved text...
[/chunk]
</context>

Question: [USER QUESTION]

### Objective
Answer the question using only <context>.

### Constraints & Negative Rules
- Cite with the exact chunk id in square brackets after each claim, e.g. [doc-17#3].
- Do not use knowledge from outside <context>, even if you are confident.
- Do not merge chunks into a claim they do not individually support.
- If chunks conflict, report both with their citations rather than choosing silently.
- If the context does not contain the answer, output exactly:
  {"status": "insufficient_context", "closest": ["<chunk id>"], "missing": "<what is needed>"}
- Do not pad the answer; two supported sentences beat six unsupported ones.

### Output Specification
Answer as short prose with inline [chunk ids]. End with a `Sources:` line listing
only the chunks actually cited. No preamble, no closing summary.
```

---

## 3. Context packing: what to put where

Given a token budget and more chunks than fit, ordering matters more than most teams assume.

| Strategy | Effect | When |
|---|---|---|
| Relevance-ranked, most relevant first | Best single-chunk retrieval; matches primacy | Default |
| Relevant first **and** last (sandwich) | Fights lost-in-the-middle | Many chunks, long context |
| Full documents | Wastes budget; dilutes signal | Only when cross-document reasoning is required |
| Deduplicated + 1-neighbor expansion | Preserves the sentence before/after a fragment | Chunks that are mid-paragraph |
| Summarized chunks | Cheap, but introduces a second-generation hallucination surface | Very large corpora, low-stakes answers |

Practical packing rules:

1. **Always include the chunk id and source metadata** — you cannot cite what you cannot name.
2. **Deduplicate near-identical chunks.** Five paraphrases of one sentence read as five confirmations.
3. **Include the heading/title of each chunk.** A fragment without its section title is often unanswerable.
4. **Do not stuff to the limit.** Retrieval quality degrades as irrelevant context accumulates; 5 good chunks beat 30 mediocre ones.
5. **Keep the question after the context** (recency) and **restate the citation rule after the context** too.

---

## 4. Citation discipline

| Style | Reliability | Use for |
|---|---|---|
| Inline `[id]` after each claim | High | Most QA |
| Per-sentence footnote | High | Long answers, audit |
| Per-paragraph source list | Medium | Executive summaries |
| "Sources: 1,2,3" at the end only | Low | Almost never — impossible to audit |

Two enforcement tricks:

```markdown
- Every sentence containing a factual claim must end with at least one [chunk id].
- A sentence with no citation must be phrased as reasoning ("this implies…"),
  not as fact.
```

And a self-check step:

```markdown
Before answering, verify: for each sentence you are about to write, can you point
to the exact chunk that supports it? If not, delete the sentence.
```

Deleting unsupported sentences is the cheapest hallucination filter there is.

---

## 5. Abstention is a feature with a shape

Give refusal a *shape*, or the model will invent a poetic apology that your UI cannot render and your metrics cannot count.

```json
{"status": "insufficient_context", "closest": ["doc-17#3"], "missing": "the 2027 pricing tier"}
```

Why a shape:

- The UI can render it as "not in the knowledge base" instead of an error.
- The metric is countable: abstention rate by query class.
- The `missing` field is free retrieval feedback — it tells you what to index next.

Calibrate the threshold explicitly: *"Answer if the context supports the claim with at least one explicit sentence. Do not answer from implication alone."*

---

## 6. Conflicting sources

Documents disagree. The model's default is to average them into a confident middle.

```markdown
- If two chunks state different values for the same fact, present both with
  citations and label them `CONFLICT`.
- Prefer the chunk with the newer `effective_date` metadata **only if** the
  metadata exists; otherwise report the conflict without resolving it.
- Never blend two values into a range or an average.
```

Reported conflicts are a data-quality signal. Silently resolved conflicts are a liability.

---

## 7. Multi-hop questions

"Which of our vendors had a breach that affected the product launched in 2024?" needs two retrievals. A single-shot RAG prompt will guess.

```markdown
### Procedure (multi-hop only)
1. Decompose the question into sub-questions, at most 3.
2. Answer each sub-question from <context>, marking any sub-answer as
   UNSUPPORTED if no chunk covers it.
3. If any required sub-answer is UNSUPPORTED, abstain with
   {"status": "insufficient_context", "missing": "<the unsupported sub-question>"}.
4. Only then compose the final answer.
```

Or, better, do the second retrieval in code. Prompt-side decomposition is a patch for when you cannot re-query.

---

## 8. Anti-Patterns

| Anti-pattern | Failure |
|---|---|
| "Use the following context to answer" with no abstention rule | Confident answers from nothing |
| "Answer even if the context is incomplete" | Invites parametric hallucination |
| No chunk ids | Citations become unusable |
| Context after the question | The model answers before reading |
| Whole documents stuffed in | Dilution, lost-in-the-middle |
| Asking for citations without per-claim placement | Decorative citations |
| Trusting retrieved text as instructions | Indirect prompt injection |

---

## Acceptance Checklist

- [ ] Context is delimited, id-tagged, and explicitly declared the only source of truth.
- [ ] An abstention shape is defined and countable.
- [ ] Citation rule is per-claim, with the id format specified.
- [ ] Conflict handling is defined (report, do not resolve).
- [ ] Chunks carry titles/metadata sufficient to be understood standalone.
- [ ] The question follows the context; the citation rule is restated after it.
- [ ] Retrieved text is treated as data, never as instructions.
- [ ] Tested with: answerable question, unanswerable question, conflicting chunks, and a chunk containing an injected instruction.
