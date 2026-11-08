---
name: chain-of-thought
type: pattern
version: 1.0.0
inputs: [problem_statement, artifact, success_criteria]
output_format: ordered-analysis-then-artifact
related: [constraint-enforcement, few-shot-calibration]
---

# 🧠 Chain-of-Thought (CoT) with Verification

Force intermediate reasoning before execution to eliminate logic gaps in complex problem-solving.

Naive chain-of-thought ("think step by step") produces confident, unstructured narration that is hard to audit and easy to abandon halfway. **CoT with verification** replaces it with a numbered protocol, an explicit self-check pass, and a hard boundary between reasoning and deliverable.

---

## The Protocol Shape

Every CoT prompt in this repo uses five stages:

```text
1. ENUMERATE   -> list the concrete objects under analysis (no judgment yet)
2. TRACE       -> follow the failure/decision path object by object
3. CHECK       -> adversarially verify the trace; try to break it
4. RESOLVE     -> commit to a decision, or state "insufficient evidence"
5. EMIT        -> output only the requested artifact, not the reasoning
```

Stages 1–4 are reasoning. Stage 5 is the only thing a downstream consumer should ever see.

---

## Core Template

```markdown
### Role
[Domain expert] performing a rigorous, auditable analysis.

### Context
- **Artifact:** <input>[paste code, spec, log, or document]</input>
- **Success criteria:** [what a correct answer must satisfy]
- **Hard constraints:** [environment, versions, forbidden changes]

### Objective
Analyze the artifact and produce [the one deliverable].

### Procedure
Follow these stages in order. Do not skip ahead to the deliverable.

1. **Enumerate** — List every [shared mutable state / config parameter / dependency]
   in the artifact. Include file and line references. Do not evaluate yet.
2. **Trace** — For each item, describe the concrete path by which it can
   [cause the failure mode]. Name the trigger condition.
3. **Verify** — For each traced path, attempt to disprove it. State what
   evidence would falsify it, and whether that evidence is present.
   Explicitly discard paths that cannot be reached.
4. **Resolve** — Rank the surviving paths by severity. If evidence is
   insufficient to rank, say so instead of guessing.
5. **Emit** — [Strict output format. No reasoning text here.]

### Constraints & Negative Rules
- DO NOT invent line numbers, symbol names, or files not present in the artifact.
- DO NOT emit the reasoning transcript in the final section.
- DO NOT propose fixes for paths discarded in stage 3.
- If the artifact is insufficient for stage 2, stop and output
  `{"status": "insufficient_context", "missing": [...]}`.

### Output Specification
[Exact schema for the deliverable only.]
```

---

## Worked Example — Race Condition Audit

```markdown
Analyze the provided codebase for race conditions using the following protocol:
1. Identify all shared mutable state across async threads.
2. Trace execution paths where lock contention or deadlock can occur.
3. Propose atomic alternatives using standard synchronization primitives.
4. Output the final patched code block.
```

Hardened version of the same task:

```markdown
### Role
Concurrency auditor specializing in lock-ordering and data-race analysis.

### Context
- **Artifact:** <codebase>[files...]</codebase>
- **Runtime:** [language + version, async runtime, thread pool size]
- **Constraint:** Public API and existing tests must not change.

### Objective
Identify and patch real data races and deadlock cycles in the artifact.

### Procedure
1. List every shared mutable value and every lock/atomic guarding it, with
   file:line. Include values with *no* guard — mark them `UNGUARDED`.
2. For each `UNGUARDED` or multi-lock site, write the interleaving that
   produces a race or cyclic wait. Name both threads and both acquire points.
3. Attempt to disprove each interleaving: is there an external guarantee
   (single caller, immutable-after-init, owned clone) that makes it safe?
   Drop any path you cannot concretely construct.
4. Rank survivors by blast radius. If two locks are acquired in inconsistent
   order in different call sites, state the cycle explicitly.
5. Emit the patched code only.

### Constraints & Negative Rules
- DO NOT flag code that is safe by ownership or immutability.
- DO NOT propose `unsafe` escape hatches or global interpreter locks as fixes.
- DO NOT add dependencies not already in the manifest.
- DO NOT change public signatures.
- If no race is constructible, output `NO_RACE_FOUND` plus the list from stage 1
  as evidence of coverage.

### Output Specification
One ```[language] fence containing the complete patched file(s), with a single
comment line above each changed block stating the hazard it removes.
Nothing before or after the fence.
```

---

## Why Verification Is a Separate Stage

Self-checking only works when it is **adversarial and falsifiable**. Three rules make the difference:

| Weak form | Strong form |
|---|---|
| "Double-check your work." | "Attempt to disprove each traced path; name the evidence that would falsify it." |
| "Make sure it's correct." | "Discard any path you cannot construct concretely with named triggers." |
| Unconditional output | "If evidence is insufficient, output `insufficient_context` and stop." |

The escape hatch matters as much as the procedure. Without a legal way to say "I cannot determine this," the model fabricates a path to satisfy stage 4.

---

## Reasoning Isolation

For parsers and agents, keep the transcript out of the payload:

```markdown
### Output Specification
Return exactly two sections:
<analysis> ...stages 1-4, terse, bullet form...</analysis>
<result> ...stage 5 deliverable...</result>
Consumers parse only <result>. Do not nest other tags inside it.
```

If the API supports a separate reasoning channel, prefer that over `thinking` tags in the visible payload.

---

## When Not To Use CoT

- **Extraction and classification** — CoT invites the model to "reason" itself into inventing values. Use [constraint enforcement](constraint-enforcement.md) and [few-shot calibration](few-shot-calibration.md) instead.
- **Latency-critical paths** — the reasoning pass costs tokens. Cheaper: a single exemplar per class.
- **Open-ended creative generation** — a rigid protocol flattens the output. Constrain the *format*, not the thought process.

---

## Acceptance Checklist

- [ ] A numbered protocol exists, with an explicit final stage that emits the artifact.
- [ ] Each stage names its *inputs* ("list every X in the artifact").
- [ ] Stage 3 contains a falsification instruction, not a "double-check".
- [ ] A deterministic fallback exists for insufficient evidence.
- [ ] The final stage forbids the reasoning transcript.
- [ ] Constraints forbid invented symbols, files, and line numbers.
- [ ] Tested against an artifact containing **no** real instances of the target failure.
