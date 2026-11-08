---
name: creative-writing
type: blueprint
version: 1.0.0
inputs: [form, audience, angle, length, constraints]
output_format: prose-or-verse
related: [style-control, few-shot-calibration, self-consistency]
---

# ✍️ Blueprint H — Creative & Narrative Writing

Creative prompts fail differently from technical ones. There is rarely a "wrong answer" — there is **the generic answer**: competent, flavourless, and instantly recognisable as model output. The fix is not more adjectives. It is specificity of form, constraint, and point of view.

---

## Inputs

| Variable | Required | Example | Notes |
|---|---|---|---|
| `FORM` | ✅ | 200-word flash fiction, 30s script | Form constrains more than topic |
| `AUDIENCE` | ✅ | developers at a conference | Determines references and register |
| `ANGLE` | ✅ | a maintenance engineer's POV | The single biggest lever |
| `LENGTH` | ✅ | ≤200 words | Countable |
| `MUST_INCLUDE` | ⬜ | one concrete object, one number | Specificity anchors |
| `MUST_AVOID` | ⬜ | clichés, moralising, em-dash tics | Explicit boundary |

---

## The Blueprint

```markdown
### Role
[FORM] writer for [AUDIENCE]. You write with concrete detail and restraint.

### Context
- **Brief:** [what this is for, where it will appear]
- **Voice:** [2 adjectives + 1 exemplar sentence of the target voice]
- **Constraints of the form:** [length, structure, tense, POV]

### Objective
Write [FORM] about [SUBJECT] from [ANGLE].

### Constraints & Negative Rules
- Use concrete nouns and specific numbers; DO NOT use abstract summary language
  ("journey", "landscape", "tapestry", "delve", "in today's world").
- DO NOT open with a definition, a question, or a dictionary framing.
- DO NOT end with a moral, a summary, or an invitation to reflect.
- DO NOT use more than [N] metaphors; prefer literal detail.
- Keep one point of view throughout; do not shift person or tense.
- If the brief is contradictory (e.g. length vs. required content), invoke the
  fallback: state the conflict in one line and follow the length constraint.
- If there is no usable brief (empty or placeholder-only), return
  {"status": "insufficient_brief"} rather than inventing a subject.

### Output Specification
[Length] of [FORM]. No title unless requested. No preamble, no explanation of
choices, no notes after the text.
```

---

## Filled Example — Conference Opener

```markdown
### Role
Short-form narrative writer for a technical conference audience.

### Context
- **Brief:** 90-second opening for a talk about incident response.
- **Voice:** Understated, specific, no hype. Example: "The pager went off at
  02:14. The graph was already flat."
- **Form:** spoken prose, present tense, second person.

### Objective
Write a 120–150 word opening that puts the audience inside a 02:00 outage.

### Constraints & Negative Rules
- Present tense, second person, one scene only.
- Include at least two concrete details (a timestamp, a number, a sound).
- DO NOT explain the lesson; the talk does that.
- DO NOT use "imagine", "picture this", or rhetorical questions.
- DO NOT name the company or the technology.
- No more than one metaphor.

### Output Specification
120–150 words of continuous prose. No title, no stage directions, no notes.
```

---

## Why specificity works

| Generic instruction | Effect | Specific instruction |
|---|---|---|
| "Make it engaging" | Model reaches for exclamation and rhetorical questions | "One concrete object per paragraph" |
| "Write in a literary style" | Purple prose, em-dash rhythm | "Short declarative sentences; no adverb modifying a verb of speech" |
| "Be creative" | Randomness | "Constraint: no adjectives in the first paragraph" |
| "Make it emotional" | Stated emotion ("she felt sad") | "Show the emotion through one physical action" |
| "Make it funny" | Jokes explained | "Humour from a mismatch between tone and stakes" |

Constraint-driven creativity produces variety; adjective-driven creativity produces the average of the training set.

---

## Structures that work for short fiction

| Structure | Shape | Best for |
|---|---|---|
| **In medias res** | Start mid-action, no setup | Flash fiction, openers |
| **Object through-line** | One object recurs, changing meaning | 300–800 words |
| **Two-hander** | Two voices in tension, no narrator | Dialogue pieces |
| **Countdown** | Time markers structure the piece | Suspense |
| **List as narrative** | Inventory that reveals character | Distinctive voice |
| **Second person procedure** | Instructions that become a story | Technical audiences |

Name the structure in the prompt. It is the difference between "a story" and *your* story.

---

## Dialogue

```markdown
### Dialogue constraints
- No dialogue tags except "said" (or none at all).
- Each character speaks in a distinguishable register: [A] uses short sentences
  and no contractions; [B] uses long sentences and hedges.
- Subtext rule: characters never state what they want directly.
- Maximum 12 exchanges.
```

Dialogue is where models default hardest to exposition. The subtext rule alone changes the output more than any style adjective.

---

## Variant H1 — Brand & Marketing Copy

```markdown
### Constraints
- Lead with the reader's problem in their words, not ours.
- One claim per sentence; every claim must be supportable by [proof points].
- DO NOT use: "revolutionary", "seamless", "empower", "unlock", "game-changing".
- Provide 3 variants with different angles: [cost], [speed], [risk].
- Each variant ≤40 words, no exclamation marks.
### Output
Three labelled variants, no commentary.
```

Marketers need *options with distinct angles*, not variations of one idea. Ask for the angles; not for "three versions".

---

## Variant H2 — Poetry & Constrained Verse

```markdown
### Form
[N] lines, [meter], rhyme scheme [ABAB/blank/assonant].
### Constraints
- One image per line; no abstractions (love, time, loss) as subjects.
- No end-stopped line may end on an article or preposition.
- If the form cannot be satisfied with the given subject, say so in one line
  rather than silently breaking the meter.
```

Meter is a genuine constraint models handle unevenly; always check counts in code or by eye rather than assuming compliance.

---

## Failure Modes

| Failure | Symptom | Fix |
|---|---|---|
| Generic register | "In today's fast-paced world…" | Banned-phrase list |
| Moralising ending | Last line states the theme | "No moral, no reflection" |
| Adverb dependence | "she said quietly, sadly" | Ban adverbs on speech verbs |
| Tense drift | Past → present mid-piece | Lock tense and POV |
| Metaphor pile-up | Three metaphors per paragraph | Cap the count |
| Explaining the joke | Setup → punchline → explanation | "Do not explain the humour" |
| Length overrun | 400 words for a 150-word brief | Numeric cap + code check |

---

## Acceptance Checklist

- [ ] Form, length, tense, and POV are all specified.
- [ ] Point of view / angle is concrete (a person, a moment, a stake).
- [ ] At least one banned-phrase or anti-cliché rule exists.
- [ ] Structure is named (in medias res, countdown, two-hander…).
- [ ] Endings are constrained (no moral, no summary).
- [ ] Length is capped and checked after generation.
- [ ] Three variants requested only when distinct angles are named.
