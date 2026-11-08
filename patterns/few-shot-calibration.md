---
name: few-shot-calibration
type: pattern
version: 1.0.0
inputs: [task, input_examples, output_schema, edge_cases]
output_format: matches-exemplar
related: [constraint-enforcement, chain-of-thought]
---

# 🎯 Few-Shot In-Context Learning

Provide concrete input-output pairs to calibrate formatting, style, and logic constraints when zero-shot results drift.

Exemplars do more work than instructions: the model infers the *implicit* rules from them. That is the power and the danger. Two happy-path examples teach the model that the happy path is all that exists — so include an edge case, a missing value, and a unit conversion in every calibrated prompt.

---

## Design Rules

1. **Three to five exemplars.** Fewer under-specifies; more burns context and crowds out the real input.
2. **Cover the edges, not the middle.** One typical case, one missing-value case, one malformed case, one unit/format conversion.
3. **Exemplars must be real.** Fabricated examples with placeholder junk teach the model to emit placeholder junk.
4. **Identical shape every time.** Same key order, same label style, same delimiter. Structural noise in exemplars is read as permission.
5. **Negative exemplars are explicit.** If a near-miss is common, include it as *"Incorrect — do not do this"* with one line on why.
6. **Separate the instructive payload from the task payload.** Delimit with `<examples>` and `<input>` so the model knows which is which.

---

## Core Template

```markdown
### Role
[Precise transformation engine]. You emit data, never commentary.

### Context
- **Source format:** [structure of incoming data]
- **Target schema:** [field list with types and units]

<examples>
Example 1 — typical case
Input: [real input]
Output: [real expected output]

Example 2 — missing value (null policy)
Input: [input where a field is absent]
Output: [same field set to null]

Example 3 — unit / format conversion
Input: [input with non-target unit or locale date]
Output: [converted, canonical form]

Example 4 — malformed (fallback policy)
Input: [truncated or unparseable input]
Output: {"error": "unparseable", "raw": "..."}
</examples>

### Objective
Transform <input> into the target schema, matching the exemplars exactly.

### Constraints & Negative Rules
- DO NOT add keys not present in the exemplars.
- DO NOT change key order.
- DO NOT output prose, fences, or explanations.
- DO NOT guess absent values; apply the Example 2 null policy.
- DO NOT merge or split records.

### Output Specification
[one record | JSON array of records], raw text, first character `{` or `[`.
```

---

## Worked Example — Log Normalization

```markdown
Transform raw log entries into structured JSON objects matching this exact schema.

Example 1:
Input: [2026-11-07T14:32:01] [ERROR] [AuthModule] Failed token validation for user_id=4092
Output: {"timestamp": "2026-11-07T14:32:01", "level": "ERROR", "module": "AuthModule", "message": "Failed token validation", "meta": {"user_id": 4092}}

[Target Input to Process...]
```

Upgraded with the edge cases that actually break this pipeline:

```markdown
### Role
Log parsing and schema normalization engine.

### Context
Source: mixed-format application logs. Some lines lack a level, some use
local timestamps, some are stack-trace continuations.

<examples>
Example 1 — typical
Input: [2026-11-07T14:32:01] [ERROR] [AuthModule] Failed token validation for user_id=4092
Output: {"timestamp": "2026-11-07T14:32:01", "level": "ERROR", "module": "AuthModule", "message": "Failed token validation", "meta": {"user_id": 4092}}

Example 2 — missing level (null policy)
Input: [2026-11-07T14:33:10] [AuthModule] Session cache warmed user_id=12
Output: {"timestamp": "2026-11-07T14:33:10", "level": null, "module": "AuthModule", "message": "Session cache warmed", "meta": {"user_id": 12}}

Example 3 — non-UTC timestamp and string coercion
Input: [11/07/2026 09:32:01 CST] [WARN] [Scheduler] Queue depth 1820 exceeds threshold
Output: {"timestamp": "2026-11-07T15:32:01Z", "level": "WARN", "module": "Scheduler", "message": "Queue depth 1820 exceeds threshold", "meta": {"queue_depth": 1820}}

Example 4 — malformed (fallback)
Input: [2026-11-07T14:3
Output: {"timestamp": null, "level": null, "module": null, "message": null, "meta": {}, "parse_error": "truncated_line"}
</examples>

### Objective
Convert each line in <input> to one object matching the exemplars.

### Constraints & Negative Rules
- DO NOT invent a level; unknown level is null.
- DO NOT keep non-UTC offsets; normalize to UTC with a `Z` suffix.
- DO NOT wrap numeric values in strings.
- DO NOT drop the malformed lines; emit Example 4's shape.
- DO NOT emit anything outside the array.

### Output Specification
A JSON array, one object per input line, in input order. No fences, no prose.
```

---

## Negative Exemplars

When a model repeatedly makes the same near-miss, show it:

```markdown
Incorrect — nests the whole record under "data" and stringifies meta:
Input:  [ERROR] [AuthModule] Failed token validation for user_id=4092
Output: {"data": {"message": "...", "meta": "{\"user_id\": \"4092\"}"}}

Correct — flat record, integer ids:
Output: {"timestamp": null, "level": "ERROR", "module": "AuthModule", "message": "Failed token validation", "meta": {"user_id": 4092}}
```

One negative exemplar is worth three sentences of prohibition, because it shows the *boundary* rather than describing it.

---

## Ordering and Recency Effects

Models weight later exemplars more heavily. Order for intent:

- Put the **most representative** exemplar first (it anchors the style).
- Put the **edge case you care most about** last (it anchors the behavior).
- Keep all exemplars *after* the constraints if the constraints are non-negotiable, or *before* the target input if format-matching matters more. Never interleave.

---

## Combining With Constraints

Exemplars teach; constraints enforce. Exemplars alone fail silently when an edge case is unrepresented. Always pair a calibrated prompt with:

- a null policy (unstated → `null`, never inference),
- a fallback shape for unparseable input,
- an explicit "no new keys" rule.

See [constraint-enforcement.md](constraint-enforcement.md).

---

## Acceptance Checklist

- [ ] 3–5 exemplars, identical structure and key order.
- [ ] At least one missing-value exemplar and one malformed-input exemplar.
- [ ] At least one unit or format conversion shown, not described.
- [ ] Exemplars are real or realistic, with no `[example]` placeholders.
- [ ] `<examples>` and `<input>` are delimited and distinguished in the objective.
- [ ] Null policy and fallback shape are stated in constraints, not inferred.
- [ ] Tested against an input that combines two edge cases at once.
