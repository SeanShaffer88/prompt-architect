---
name: long-context-management
type: pattern
version: 1.0.0
inputs: [context_budget, document_set, question, summary_policy]
output_format: grounded-answer
related: [rag-grounding, how-llms-read-prompts, summarization]
---

# 📚 Long-Context Management

Big context windows changed the economics of prompting; they did not repeal attention. A 200k-token window does not mean 200k tokens are used equally — relevance, position, and redundancy still decide what the model actually reads.

This pattern is about spending context deliberately.

---

## 1. The budget

Treat the window as a budget with line items:

```text
┌────────────────────────────────────────────────────┐
│ system contract          5%   (stable, cacheable)  │
│ task instructions        5%                        │
│ retrieved evidence      70%   (ranked, deduped)    │
│ conversation history    10%   (summarized)         │
│ output reserve          10%   (must be non-zero)   │
└────────────────────────────────────────────────────┘
```

Two rules that prevent the most common failures:

1. **Reserve output space.** `max_tokens` truncated mid-JSON is a budget bug, not a model bug.
2. **Never fill to 100%.** Degradation is gradual, not a cliff; at 95% utilization the effective recall is already worse than at 60%.

---

## 2. What actually degrades

| Effect | Description | Countermeasure |
|---|---|---|
| **Lost in the middle** | Mid-context material is recalled less reliably | Rank + sandwich (best first and last); restate the key fact near the question |
| **Dilution** | Irrelevant tokens reduce attention on relevant ones | Retrieve less; dedupe; drop low-relevance chunks |
| **Recency bias** | The last tokens dominate the answer | Put the question last; put the contract twice |
| **Distractor interference** | A plausible-but-wrong passage wins | Include source ids and require per-claim citation |
| **Instruction drift** | Rules stated 50k tokens ago weaken | Re-assert the one-line contract after the context |
| **Cost/latency** | Linear-ish in input tokens | Cache stable prefixes; summarize history |

These are measurable: build a recall test at 25%, 50%, 75%, and 95% of your budget. If recall drops at 75%, your usable window is 75%.

---

## 3. Packing strategies

| Situation | Strategy |
|---|---|
| One question, many chunks | Rank by relevance, dedupe, take top-k (k ≈ 5–10) |
| A specific fact in a long doc | Retrieve the section + neighbors, not the whole doc |
| Compare many documents | Per-document extraction → structured table → judgment |
| Whole-repo/codebase question | Build an outline first, then load only the relevant subtree |
| Iterative research | Carry a running summary + open questions, not the transcript |
| Conversation | System + summary + last k turns (k ≈ 6–10) |

The unifying idea: **compress before you add.** A 20-line summary of a document is usually a better context item than the document.

---

## 4. Structure that survives length

```markdown
### Context
<documents>
<doc id="D1" title="Q3 Pricing Policy" updated="2026-09-01">
[text]
</doc>
<doc id="D2" title="Enterprise Addendum" updated="2026-10-14">
[text]
</doc>
</documents>

Question: [QUESTION]

Reminder: answer only from <documents>; cite [D#] per claim; if unsupported,
return {"status": "insufficient_context"}.
```

Four things this does: names every source, gives recency metadata for conflict resolution, places the question last, and repeats the contract at the moment of use. That repetition is not redundancy — it is the cheapest reliability win available in long prompts.

---

## 5. Summarization checkpoints

For long interactions, maintain state in code rather than trusting the model to remember:

```text
every N turns (or when context > 60% utilized):
  summary = summarize(history, keep={decisions, constraints, open_questions, user_prefs})
  history = [summary] + last_k_turns
```

Summarization prompt contract:

```markdown
### Objective
Compress the conversation so far into a state block for continued work.
### Must preserve
- Decisions made, with their reasons.
- Constraints and preferences the user stated.
- Open questions and unresolved conflicts.
- Exact identifiers, numbers, and names (do not paraphrase them).
### Must not
- Add facts that were not stated.
- Drop a constraint for brevity.
- Editorialize about the conversation.
### Output
{"decisions": [...], "constraints": [...], "open_questions": [...], "entities": [...]}
```

A state block is parseable, auditable, and portable between models — three things a prose summary is not.

---

## 6. When to retrieve instead of stuff

| Stuff it | Retrieve it |
|---|---|
| < ~10k tokens of highly relevant material | Corpus larger than the budget |
| Every chunk is needed for the task | Only a few chunks answer the question |
| One-shot analysis | Repeated queries over the same corpus |
| Cost is not the constraint | Cost or latency dominates |

Stuffing a 100k-token corpus to answer one question is a retrieval failure wearing a context window as a disguise. It costs more, answers worse, and hides the fact that your retrieval is broken.

---

## 7. Anti-Patterns

| Anti-pattern | Failure |
|---|---|
| "The window is huge, paste everything" | Dilution, cost, lost-in-the-middle |
| Instructions only at the top of a 100k prompt | Drift; rules no longer salient |
| No output reserve | Truncated JSON |
| Unlabeled chunks | Unusable citations, ambiguous attribution |
| Paraphrased identifiers in summaries | Silent corruption of ids/amounts |
| Full history every turn | Cost grows quadratically over a session |
| Testing recall only at short context | Production behaves differently than the demo |

---

## Acceptance Checklist

- [ ] A budget exists for each line item, including output reserve.
- [ ] Evidence is ranked, deduplicated, and labeled with ids/metadata.
- [ ] The question follows the context; the contract is restated after it.
- [ ] Recall has been measured at 25/50/75/95% utilization.
- [ ] Long conversations maintain a structured state block, not a raw transcript.
- [ ] Retrieval is used when the corpus exceeds what is worth stuffing.
- [ ] Conflict resolution uses metadata (dates) explicitly rather than implicitly.
