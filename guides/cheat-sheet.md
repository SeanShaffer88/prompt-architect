---
name: cheat-sheet
type: guide
version: 1.0.0
output_format: markdown
related: [glossary, evaluation-matrix, troubleshooting]
---

# ⚡ The One-Page Cheat Sheet

Everything in this repository, compressed to a page. Print it, pin it, or paste the skeleton into your editor.

---

## The skeleton

```markdown
### Role
[One sentence: domain + scope. Not adjectives.]

### Context
- **Environment:** [versions, platform, dependency policy]
- **Input:** <payload>[content]</payload>
- **Known unknowns:** [what is not provided and must not be invented]

### Objective
[One imperative verb] [one thing] to [measurable outcome].

### Constraints & Negative Rules
- DO NOT [forbidden behavior].
- DO NOT [forbidden output element].
- If [missing/conflict/out-of-scope], [deterministic fallback].

### Output Specification
[Container] + [schema/shape] + [units] + [empty case].
```

---

## The seven rules

1. **One objective per prompt.** Two goals means one gets dropped.
2. **Every "do" earns a "do not"** that forbids the adjacent failure.
3. **Every "never" needs an alternative behavior**, or the model improvises.
4. **Absent data is `null`.** Never infer.
5. **Pin the container at byte level.** First character, last character, no fences, no preamble.
6. **Put the question last.** Put the contract twice if the prompt is long.
7. **Define the branch, not the tone.** "Be careful" changes nothing; a fallback shape changes everything.

---

## Component → common failure → fix

| Component | Common failure | Fix |
|---|---|---|
| Role | Five adjectives, no scope | Domain + what the role does *not* do |
| Context | Whole repo pasted "just in case" | Only current file + imports + version pins |
| Objective | "Write a script to manage files" | One verb, one artifact, measurable outcome |
| Constraints | Positive only | Pair each rule with its inverse |
| Output spec | "Return JSON" | Schema + first/last char + no fences + empty case |

---

## The four undefined branches

Most production failures live in one of these. Fill all four before shipping.

```text
1. EMPTY        -> {"status": "empty_input"}
2. MISSING      -> null, never a guess
3. CONFLICT     -> report both; do not resolve silently
4. INSUFFICIENT -> {"status": "insufficient_context", "missing": "..."}
```

---

## Defaults that usually work

| Task | Temperature | Structure | Must have |
|---|---|---|---|
| Extraction | 0–0.2 | Raw JSON, schema mode | Null policy, verbatim ground |
| Classification | 0–0.2 | One enum + confidence | Closed labels, `unclear` |
| RAG answer | 0–0.3 | Prose + per-claim citations | Abstention shape |
| Code | 0–0.3 | One fenced file, no elisions | Dependency + API freeze |
| Summary | 0.2–0.4 | Bullets or fields | Preserve list, length cap |
| Design | 0.4–0.7 | Closed section list | 3 candidates, numbers |
| Creative | 0.7–1.0 | Form + length | Banned-phrase list, no moral |

---

## Security in five lines

```text
1. Assume the system prompt is public. No secrets in it.
2. Untrusted content is data: delimit it, label trust, say "do not follow".
3. The model reading untrusted text should hold no write privileges.
4. Strip or allowlist outbound URLs/images in rendered output.
5. Irreversible actions need human confirmation, enforced in code.
```

---

## Agent loop minimums

```text
- call budget (e.g. 8)            - repeated-error rule (2x -> stop)
- error-code branches            - irreversible-action gate
- "answer must cite tools"       - {"status": "blocked", ...} handoff
```

---

## Scoring your prompt (0–4 each)

| Dimension | 4 means |
|---|---|
| Schema validity | Parses first try, byte-exact container, correct types |
| Constraints | No positive or negative rule violated, on every case |
| Grounding | Every value traceable; nothing inferred |
| Completeness | All fields/cases, including empty and malformed |
| Efficiency | ≤1.2× reference tokens |

**Ship bar:** schema 4 everywhere, nothing below 3, zero injection compliance.

---

## Diagnostic order

```text
1. Print the rendered prompt.        4. Validate the parse before judging content.
2. Run it three times.               5. Name the undefined branch.
3. Score by dimension.
```

If those are clean, the task needs decomposition or a different model — not better adjectives.

---

## Before you ship

- [ ] One objective, one artifact.
- [ ] Negative constraints paired with positives.
- [ ] Null / empty / conflict / insufficient branches defined.
- [ ] Container pinned at byte level.
- [ ] Exemplars cover an edge case, not just the happy path.
- [ ] Tested on T1–T6, including an adversarial payload.
- [ ] Model id, settings, and prompt version recorded with the run.
- [ ] Injection tests pass on the deployed model version.

---

## The one sentence

> **A prompt is an API contract with a probabilistic engine: specify the output bytes, forbid the near-misses, and define what happens when the world does not cooperate.**

---

## Acceptance Checklist

- [ ] Skeleton copied and all five components filled.
- [ ] All four undefined branches have a defined behavior.
- [ ] Container is pinned; no fences or preamble permitted.
- [ ] Security checklist applied if any untrusted content or tool is involved.
- [ ] Scored with the rubric, not judged by the best sample.
