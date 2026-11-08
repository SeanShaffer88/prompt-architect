---
name: structured-output
type: pattern
version: 1.0.0
inputs: [schema, output_mode, null_policy, repair_budget]
output_format: json-schema
related: [constraint-enforcement, data-extraction, evaluation-matrix]
---

# 🧱 Structured Output

Dowstream systems do not read prose. They parse objects. This pattern covers getting a *reliably parseable and semantically correct* structure out of a model, using the strongest available mechanism rather than the strongest available adjective.

---

## 1. Choose the strongest mechanism available

In descending order of reliability:

| Mechanism | Guarantees | Use when |
|---|---|---|
| **Native schema / strict tool call** (provider-enforced JSON schema) | Keys, types, required fields | Always, if the provider supports it |
| **JSON mode** | Valid JSON, no schema | Schema is simple or you validate after |
| **Grammar / regex-constrained decoding** (GBNF, regex logits) | Exact syntax, incl. non-JSON formats | Custom DSLs, strict tags, SQL |
| **Prompt-only specification** | Nothing; it is a request | Only as a fallback, or for formats the API cannot constrain |
| **Post-hoc repair** (parse, fix, re-ask) | Nothing until it succeeds | Last resort, capped at 1–2 attempts |

The single most common production bug in this category: **a team writes a beautiful JSON contract in the prompt while their API offers strict schema mode and they are not using it.**

> Constrained decoding guarantees *shape*. It does not guarantee *truth*. Pair every schema with a grounding rule (`null` when absent; quote when required).

---

## 2. The schema is part of the prompt

Even with strict mode, the model benefits from seeing the schema in the prompt — field descriptions are instructions.

```markdown
### Output Schema
{
  "severity": "critical | high | medium | low",   // how much impact
  "service": string,                              // must appear in <incident>
  "cause": string | null,                         // null if not stated
  "evidence": string[],                           // verbatim lines only
  "confidence": "high" | "medium" | "low"
}
```

Rules that eliminate most defects:

1. **Enums, not free text**, for anything with a fixed set of values.
2. **Every field gets a one-line meaning** — the model reads these as instructions.
3. **`| null` on anything that can be absent**, with the null policy stated.
4. **No optional keys** unless the consumer can handle their absence; prefer required + null.
5. **Flat beats nested** beyond one level, for extraction reliability.
6. **Units and timezones are named in the field**, not in a footnote (`duration_seconds`, not `duration`).

---

## 3. Container contract

The schema says what the object is; the container says what surrounds it. Pin both.

```markdown
### Output Specification
- Return a single JSON object (or an array of objects, one per input record).
- First character `{` (or `[`), last character `}` (or `]`).
- No markdown fences, no preamble, no postamble, no trailing commentary.
- If the input yields no records, return `[]` — do not return prose explaining why.
```

The three most common container failures, and the rule that prevents each:

| Failure | Rule |
|---|---|
| ```` ```json ```` wrapper | "No markdown fences" + strict schema mode |
| "Here is the extracted data:" | "No preamble; first character is `{`" |
| Truncated mid-object | Set `max_tokens` generously and cap the *content*, not the container |

---

## 4. Validation and repair, with budgets

Treat model output like a network response: validate, then decide.

```text
parse -> validate schema -> validate semantics -> accept
                 |                  |
                 |                  +-> invented/null violations: do not "fix", re-ask or reject
                 +-> syntax error: ONE repair attempt with the error message attached
```

A repair prompt should be mechanical, not conversational:

```markdown
### Repair request
The previous output failed validation with: `[validator error]`.
Return the corrected JSON only. Do not change values that were not implicated
by the error. Do not add commentary.
```

Hard rules:

- **Cap repairs at 1–2.** More attempts usually reproduce the same defect; the prompt is wrong.
- **Never let a repair loop mutate data.** Repairing syntax is fine; repairing semantics silently fabricates.
- **Log every repair.** A rising repair rate is your earliest warning that a model upgrade changed behavior.

---

## 5. Semantic validation checklist

Schema validity is necessary and insufficient. Validate:

| Check | Example failure caught |
|---|---|
| Enum membership | `"severity": "severe"` |
| Type strictness | `"count": "12"` (string) |
| Null policy | Invented value where the source was silent |
| Grounding | `service` not present in the source text |
| Cross-field consistency | `status: "resolved"` with `resolved_at: null` |
| Aggregate consistency | Sum of line items ≠ stated total |
| Uniqueness | Duplicate ids in a batch |
| Range | `confidence: 1.4`, negative quantities |

If a check can be encoded as a schema constraint (minimum, maximum, pattern), do that instead of describing it in prose.

---

## 6. Streaming and partial results

If you stream structured output to a UI:

- Stream the **text**, but validate the **complete** object before acting on it.
- Tool-call arguments arrive as incrementally valid JSON fragments; do not parse until the tool call closes.
- A progress UI may render partial keys, but must not persist them.

```text
acceptable:   show tokens as they arrive, commit only on final validation
unacceptable: write each partial parse to the database
```

---

## 7. Anti-Patterns

| Anti-pattern | Why it fails |
|---|---|
| Hand-writing JSON contracts when schema mode exists | Leaves reliability on the table |
| "Return valid JSON" with no example | Model guesses the shape |
| Schema by example only | Edge cases (nulls, empty arrays) are unrepresented |
| Free-text enums | Silent taxonomy drift |
| Retrying the same prompt verbatim after a parse failure | Same defect, same result |
| Repair that rewrites values | Turns a syntax bug into a data corruption |
| Ignoring `max_tokens` | Truncated JSON is indistinguishable from a model error |

---

## Acceptance Checklist

- [ ] Strongest available mechanism is used (schema/grammar > JSON mode > prompt-only).
- [ ] Every field has a description, type, and nullability.
- [ ] Enums are closed and listed.
- [ ] Units/timezones are encoded in field names.
- [ ] Container is pinned at byte level (first/last character, no fences).
- [ ] A null/absence policy is stated, not implied.
- [ ] Semantic validation exists beyond schema validation.
- [ ] Repair is capped, mechanical, and logged.
