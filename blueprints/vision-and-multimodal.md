---
name: vision-and-multimodal
type: blueprint
version: 1.0.0
inputs: [image_type, task, output_schema, uncertainty_policy]
output_format: raw-json
related: [structured-output, data-extraction, uncertainty-and-abstention]
---

# 🖼️ Blueprint I — Vision & Multimodal Prompts

Images change the failure modes. Models read text in images poorly at small sizes, hallucinate detail in low-resolution regions, and are far more confident than their evidence supports. The prompt has to compensate for all three.

Two distinct jobs are covered here: **understanding** (describe, extract, classify) and **generation** (text-to-image prompts, which obey different rules entirely).

---

## Part 1 — Image Understanding

### The Blueprint

```markdown
### Role
Visual inspection engine. You report only what is visible in the image and mark
anything uncertain instead of guessing.

### Context
- **Image type:** [screenshot / photo / scan / chart / diagram]
- **Task:** [what to extract or decide]
- **Resolution caveats:** [small text regions, glare, motion blur, partial occlusion]
- **Uncertainty policy:** [what to do when a value is not legible — default: `null`
  plus a `legible: false` flag; never guess]

### Objective
Extract [fields] from the image into the schema below.

### Constraints & Negative Rules
- DO NOT infer text that is not legible. If a character is ambiguous, use `?` in
  the transcription and set `legible: false` for that field.
- DO NOT correct OCR errors or "fix" apparent typos — transcribe as rendered.
- DO NOT describe the image beyond the requested fields.
- DO NOT use surrounding context to guess a value that is cut off.
- If a required element is absent from the frame, set it to `null` and add
  `"missing_from_frame": true`.

### Output Specification
{
  "fields": { ... requested keys, each: value | null, with `legible` boolean },
  "confidence": "high|medium|low",
  "notes": [string]     // visible ambiguities only
}
Raw JSON. No fences, no description.
```

### Reading text in images

| Condition | Reliability | Mitigation |
|---|---|---|
| Crisp screenshot, standard font | High | None needed |
| Photo of a screen, mild glare | Medium | Ask for `legible` flags; cap field count |
| Handwriting | Low–medium | Transcribe with `?` for uncertain characters; never normalize |
| Small print / dense tables | Low | Crop and send the region; ask per-cell |
| Rotated / skewed | Medium | Pre-rotate in code if possible |

Two rules that prevent most silent corruption:

1. **Never let the model normalize OCR artifacts.** `1O0` → `100` is indistinguishable from fabrication.
2. **Ask for per-field legibility.** A `null` you can see is better than a guess you cannot.

### Chart and diagram reading

```markdown
### Constraints
- Report axis labels, units, and scale verbatim; do not convert units.
- Read values to the precision the grid supports; label estimates as `~`.
- DO NOT compute aggregates (totals, averages) — report only what is plotted.
- If a legend is unreadable, set `legend: null` and stop; DO NOT guess series names.
```

Aggregates are where vision models fail confidently: summing bars in an image is arithmetic on imprecise pixels.

---

## Part 2 — Image Generation Prompts

Generation prompts are **not** instructions to a reasoning engine; they are conditioning text for a diffusion-style model. Structure and specificity matter, negation mostly does not.

### The anatomy

```text
[subject + action] , [composition/camera] , [lighting] , [style/medium] ,
[color palette] , [quality/detail cues]
```

| Slot | Weak | Strong |
|---|---|---|
| Subject | "a dog" | "a scruffy border collie mid-leap" |
| Composition | "nice framing" | "low-angle three-quarter view, subject left of center" |
| Lighting | "good lighting" | "overcast window light, soft shadows, cool highlights" |
| Style | "artistic" | "35mm documentary photograph, slight grain" |
| Palette | "colorful" | "muted teal and rust, desaturated midtones" |
| Detail | "high quality" | "sharp focus on the face, gentle falloff in the background" |

### What works, what doesn't

| Belief | Reality |
|---|---|
| "Add 'no blurry hands'" | Negations are weak; positive description of hands works better |
| "More adjectives = better" | Beyond ~40 distinct concepts, prompts over-constrain and degrade |
| "Include every style keyword you know" | Style keywords fight each other; pick one medium |
| "Mention the aspect ratio" | Set it in the API parameter, not the text |
| "Ask for text in the image" | Short strings work; long text rarely renders correctly |

### Template for a generation prompt

```markdown
[SUBJECT + ACTION], [FRAMING + ANGLE], [LIGHTING], [MEDIUM/STYLE],
[PALETTE], [MOOD], [DETAIL CUE]
```

Example: `A lone lighthouse keeper coiling rope on a wet stone jetty, wide shot from
the water line at dusk, cold blue hour light with a single warm window glow,
documentary photograph, muted slate and amber palette, quiet and exposed,
fine detail in the rope and spray`.

### Editing and consistency

- **Iterate one variable at a time** — change lighting *or* framing, not both.
- **Keep a fixed prefix** for series consistency (character, style), vary the suffix.
- **Use reference images** where the API supports them; prose cannot reliably restate a face.
- **Seed** for reproducibility where the platform offers it; treat the seed as part of the prompt version.

---

## Failure Modes

| Failure | Cause | Fix |
|---|---|---|
| Invented text in screenshots | Low resolution, small type | `legible` flags, crop regions, `null` over guesses |
| Normalized OCR | Helpful instinct | "Transcribe as rendered" |
| Over-described image | Model adds scenery | "Only the requested fields" |
| Confident wrong measurement | Pixel-level estimation | Report plotted values only; no aggregates |
| Generation prompt ignored negation | Diffusion conditioning | Positive description instead |
| Inconsistent series | Varying prefix | Fixed prefix + varied suffix |
| Text-in-image gibberish | Model limitation | Keep strings ≤3 words, or composite text in code |

---

## Acceptance Checklist

- [ ] Image type and resolution caveats are stated.
- [ ] Every extracted field has a null path and a legibility flag.
- [ ] OCR artifacts are preserved, not corrected.
- [ ] Aggregates are computed in code, never read off an image.
- [ ] Generation prompts use the six-slot anatomy and one medium.
- [ ] Aspect ratio, seed, and reference images are set via parameters, not prose.
- [ ] Tested on: crisp screenshot, blurry photo, partial crop, and an image containing adversarial text.
