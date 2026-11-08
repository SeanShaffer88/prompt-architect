---
name: style-control
type: pattern
version: 1.0.0
inputs: [audience, register, length_budget, format_constraints]
output_format: styled-text
related: [few-shot-calibration, creative-writing, output-length-control]
---

# 🎨 Style, Persona & Length Control

Voice is the easiest thing to ask for and the hardest thing to bound. "Be professional but friendly" produces a different register on every run, and "keep it concise" is ignored by every model that has ever written an introduction.

This pattern converts style from adjectives into constraints.

---

## 1. Persona has a job description, not a personality

A persona narrows what the model considers relevant. That is its only mechanical function.

| Weak persona | Strong persona |
|---|---|
| "You are a brilliant, friendly, world-class expert who loves helping." | "You are a support engineer for Acme's billing API. You answer from the provided docs and escalate anything about refunds." |
| Establishes mood | Establishes scope, evidence, and authority |
| Competes with constraints | Encodes constraints |

Rule: **persona states domain, scope, and what the role does not do.** Personality adjectives are decoration; they cost tokens and add variance.

---

## 2. Style as testable constraints

| Vague | Testable |
|---|---|
| "Be concise" | "≤120 words. No preamble. One paragraph maximum." |
| "Professional tone" | "Second person, no exclamation marks, no emoji, no marketing superlatives." |
| "Friendly" | "Contractions allowed; acknowledge the problem in the first sentence; no jokes." |
| "Technical audience" | "Define a term only if it appears fewer than twice in the source; do not explain HTTP." |
| "Match our brand voice" | Provide 2–3 exemplar sentences and 1 counter-example. |

Three constraints per axis is usually enough: **length, register, and prohibited devices.** More than that dilutes attention.

---

## 3. Length control that works

Length is the most reliably ignored instruction, because the model has no ruler. Give it one:

1. **Hard word/line/token caps** — "≤150 words", "exactly 3 bullets", "≤5 sentences".
2. **Structural caps** — "one paragraph", "no section headings", "one table with ≤6 rows".
3. **Content budgets** — "one example, no more", "at most one caveat".
4. **Anti-padding rules** — "no summary of what you just wrote", "no restating the question", "no closing offer to help".

```markdown
### Output Specification
- Exactly 3 bullet points. Each ≤ 20 words.
- No introduction, no conclusion, no headings.
- Do not restate the question.
```

When a hard cap risks cutting mid-sentence, the fallback is to shorten the
section rather than truncate the sentence: drop the least informative clause and
keep the output grammatical.

**Why structure beats numbers:** a format the model can count (bullets, sentences, items) is enforceable. "Around 200 words" is not. If you need a precise length, generate slightly over and truncate in code — but never truncate mid-sentence in a user-visible surface; display a summarized variant instead.

---

## 4. Style exemplars

Two exemplars outperform twenty adjectives:

```markdown
<voice>
Good: "Your card was charged twice on 3 Nov. Both charges are pending; the
duplicate will drop off within 3–5 business days."

Bad (do not imitate): "Oh no, that sounds frustrating! 😊 We totally understand
and we're here to help you get this sorted out as quickly as possible!"
</voice>

Match the Good register. Do not include emoji, exclamations, or reassurances
that do not contain information.
```

A "bad" exemplar with an explicit do-not-imitate label is unusually effective — it defines the boundary instead of the center.

---

## 5. Register by audience

| Audience | Do | Don't |
|---|---|---|
| Developer / API docs | Imperative, code-first, exact types | Marketing framing, benefits language |
| Executive | Conclusion first, one decision per paragraph | Implementation detail unless asked |
| End user in distress | Acknowledge, then act, then next step | Jargon, blame, false reassurance |
| Legal / compliance | Precise, hedged where genuinely uncertain, cite the clause | Colloquialisms, absolutes |
| Internal ops | Terse, lists, exact ids and timestamps | Politeness tokens that cost reading time |

Set the register once, in the system prompt, and re-assert it in the output specification — the two places that carry the most weight.

---

## 6. Multilingual

- **State the output language explicitly** ("Answer in Brazilian Portuguese"). Do not infer it from the question.
- **Keep code, ids, and product names untranslated** unless localization is the task.
- **Numbers, dates, currency:** specify the locale format (`1.234,56 €`, `08/11/2026`) or require ISO, and say which.
- **Exemplars must be in the target language** — a style exemplar in English will pull the register back toward English.

```markdown
- Answer in [LANGUAGE].
- Keep identifiers, error codes, and API paths verbatim in English.
- Format dates as YYYY-MM-DD; currency as "1,234.56 USD".
```

---

## 7. Avoiding persona drift

Over long conversations, style erodes toward the model's default chat register.

| Drift | Countermeasure |
|---|---|
| Formality decays | Re-assert register in the pinned block |
| Length creeps up | Re-state the cap each turn; check length in code |
| Persona becomes chatty | Negative device list (no emoji, no offers to help) |
| Language switches | Explicit language lock + a post-check on the output language |

If length or language is a hard product requirement, validate it in code and, on violation, regenerate once — do not trust the prompt alone.

---

## 8. Anti-Patterns

| Anti-pattern | Failure |
|---|---|
| Five personality adjectives | Different voice every run |
| "Concise" without a number or structure | Ignored |
| Style exemplar without a counter-example | Boundary undefined |
| Number-only length caps in a user-visible surface | Mid-sentence truncation |
| Persona that contradicts constraints ("be warm and always decisive") | Arbitrary conflict resolution |
| Persona in the user turn | Easily overridden |
| Language inferred from input | Wrong output language on short prompts |

---

## Acceptance Checklist

- [ ] Persona states domain, scope, and what it does not do.
- [ ] Length is capped structurally or numerically, with anti-padding rules.
- [ ] Register and prohibited devices are enumerated.
- [ ] At least one good and one bad exemplar exist.
- [ ] Output language is stated explicitly, with untranslatable items listed.
- [ ] Hard requirements (length, language) are also checked in code.
- [ ] Style is re-asserted in the pinned block for multi-turn surfaces.
