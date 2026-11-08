---
name: multi-turn-conversations
type: guide
version: 1.0.0
output_format: markdown
related: [instruction-hierarchy, long-context-management, conversational-assistant]
---

# 💬 Multi-Turn Conversations

A single-turn prompt is a function. A multi-turn prompt is a **state machine with a memory budget** — and most of its failures come from state, not from wording.

This guide covers what to keep, what to drop, how to keep rules alive, and how to stop a conversation from quietly becoming a different one.

---

## 1. The four things that drift

| Drift | Mechanism | Signature |
|---|---|---|
| **Instruction decay** | Early rules lose salience as turns accumulate | "It knew that in turn 1" |
| **Goal substitution** | The latest message becomes the whole task | Original objective abandoned |
| **Scope creep** | Incremental concessions ("just this once") | Policies relax gradually |
| **Persona erosion** | Default chat register reasserts itself | Tone becomes chattier over time |

All four are predictable, and all four have structural countermeasures.

---

## 2. The pinned block

Re-inject the invariant parts every request. Do not trust the model to remember what it no longer reads.

```markdown
### Standing rules (apply to every turn)
- Identity: [role + scope]
- Hard rules: [the 3–5 that must never relax]
- Output contract: [format, length, language]
- Escalation: [what triggers a handoff]
```

Keep it under ~200 tokens. If it grows beyond that, the rules are not "standing" — they are task instructions that belong in the current turn.

---

## 3. Context assembly

Every request is a budget problem:

```text
[system: pinned block]           ~200 tokens, stable (cacheable)
[state block: summary]           ~200-400 tokens, updated per checkpoint
[retrieved context for this turn] variable
[last k turns verbatim]          k = 6-10
[current user message]           last
```

**Summarize, don't truncate.** Dropping the middle of a conversation silently deletes decisions. A structured state block preserves them at a fraction of the cost.

```json
{
  "decisions": [{"what": "use the EU region", "why": "data residency", "turn": 4}],
  "constraints": ["budget cap 5k EUR", "no downtime before Jan"],
  "open_questions": ["who owns the migration?"],
  "entities": {"project": "Atlas", "account_id": "AC-4471"}
}
```

Preserve identifiers, numbers, and dates **verbatim**. Paraphrasing an account id in a summary is silent corruption.

---

## 4. Keeping rules alive

| Technique | How | When |
|---|---|---|
| Pinned block | Re-inject invariants each turn | Always |
| Reminder at point of use | Restate the relevant rule next to the task | Long conversations |
| Explicit delegation | "You may change tone; you may not change schema" | User-facing assistants |
| Refusal shape | `{"status":"declined","rule":"..."}` | Policy boundaries |
| Periodic checkpoint | "Restate the current objective in one line" | Long agent sessions |

The checkpoint trick is underused: asking the model to restate the objective in one line, at intervals, surfaces goal substitution before it produces a wrong answer.

---

## 5. Handling corrections

Users correct the model. How the correction is stored determines whether it sticks.

| Correction | Bad handling | Good handling |
|---|---|---|
| "No, the account is AC-4472" | Appended to history, forgotten in 20 turns | Written to `entities` in the state block |
| "Use formal tone" | Applies once | Written to `preferences`; re-asserted in the pinned block |
| "I already told you" | Model apologises, repeats | State block includes established facts; prompt forbids re-asking |
| "Forget that, we're changing direction" | Old constraint lingers | Explicitly remove from state; note the supersession |

**Rule:** a correction that must persist belongs in state, not in history.

---

## 6. Multi-turn patterns

### Pattern: clarify once, then commit

```markdown
If the request is materially ambiguous, ask exactly one clarifying question and
wait. After the answer, commit to an interpretation. Do not ask a second
clarifying question in the same turn.
```

### Pattern: staged delivery

```markdown
This task has 3 stages. Announce the stage you are in ("Stage 2 of 3") at the
start of each turn. Do not begin a stage until the previous one is complete.
```

### Pattern: conversation-level guardrails

```markdown
Across the whole conversation:
- Do not agree to terms, prices, or deadlines. Refer to [policy].
- Do not repeat a promise made earlier unless it is in <state>.
- If the user contradicts an earlier decision, ask which one supersedes it.
```

### Pattern: graceful exit

```markdown
If the conversation exceeds [N] turns without resolution, summarise the state
and offer a handoff: {"status": "handoff", "summary": "...", "owner": "..."}.
```

---

## 7. Failure modes

| Failure | Cause | Fix |
|---|---|---|
| Re-asks for known information | No state block | Persist facts; forbid re-asking |
| Forgets a decision from turn 3 | Truncated history | Structured summary, decisions preserved |
| Rules relax over time | Recency | Pinned block |
| Contradicts itself | No supersession rule | Ask which decision wins; record it |
| Apologises instead of acting | Correction loops | "After a correction, apply it; do not restate the error" |
| Context grows unbounded | Raw history retention | Checkpoints at 60% utilization |
| Hallucinated agreement | Model "confirms" a promise | Explicit no-commitment rule |

---

## 8. Evaluating multi-turn behavior

Single-turn evals miss all of this. A minimal multi-turn suite:

| Case | Tests |
|---|---|
| **M1** 10-turn task with a decision at turn 2 | Decision retention |
| **M2** User correction at turn 4, referenced at turn 9 | State persistence |
| **M3** User pushes a policy boundary three times | Rule stability |
| **M4** Topic switch and return | Goal resumption |
| **M5** 30-turn session | Summarization, cost, drift |
| **M6** User claims a prior agreement that never happened | Hallucinated-consent resistance |

Score each on: task completion, fact retention, rule adherence, and turns-to-resolution.

---

## Acceptance Checklist

- [ ] A pinned block carries identity, hard rules, contract, and escalation.
- [ ] A structured state block (not raw history) carries decisions, constraints, entities.
- [ ] History is summarized at a utilization threshold, with ids preserved verbatim.
- [ ] Corrections are promoted into state, not left in history.
- [ ] Supersession behavior is defined for contradictory turns.
- [ ] Clarification is bounded (one question, then commit).
- [ ] Multi-turn cases M1–M6 exist in the eval suite.
- [ ] Turn/cost ceilings exist with a defined handoff state.
