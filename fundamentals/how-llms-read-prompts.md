---
name: how-llms-read-prompts
type: guide
version: 1.0.0
output_format: markdown
related: [instruction-hierarchy, sampling-and-determinism, long-context-management]
---

# 🧬 How LLMs Actually Read a Prompt

You cannot engineer against a mechanism you imagine. This guide is the mental model the rest of the repository assumes: what the model receives, what it can attend to, and why "instructions" are probabilistic nudges rather than code.

Read this once. Everything else here is a consequence of it.

---

## 1. What the model actually receives

A prompt is not a message. It is a **token sequence** produced by a chat template, and the template is provider-specific.

```text
[system token] You are a support triage engine.   [end]
[user token]   Ticket: "I was charged twice."     [end]
[assistant]     …
```

Practical consequences:

| What you think you send | What often happens |
|---|---|
| Markdown headings (`### Role`) | Flattened to tokens; `##` carries little structural meaning on its own |
| Indentation and blank lines | Mostly whitespace tokens — cheap, weak signal |
| RoLE in WeIrD cApS | Fragments into subword tokens; may help or hurt unpredictably |
| A 40-page PDF pasted in | Tokenized into 30k+ tokens; attention is finite and uneven |
| "JSON" | One token; "JSONL" may be several |

**Rule:** structure helps because it is *consistent and learnable*, not because the model parses Markdown. Consistency is the signal; decoration is not.

---

## 2. Attention is finite and uneven

The model does not read your prompt the way a human reads a page. It weighs tokens against each other, and that weighting is not uniform across position:

- **Primacy matters** — early instructions (system prompt) set the frame and are reinforced by every later token that refers back to them.
- **Recency matters** — the last few hundred tokens disproportionately steer the next one.
- **The middle gets lost** — with long inputs, material buried in the center of the context is retrieved less reliably than material at the start or end ("lost in the middle"). This is measured behavior, not folklore.

### Where to put things

| Content | Best position | Why |
|---|---|---|
| Role, hard constraints, safety rules | Start (system) | Frames everything downstream |
| Retrieval chunks / documents | Middle, with clear delimiters | Cheapest place, and relevance-ranked |
| The actual question | **End** | Recency: the model answers what it just read |
| Output format reminder | End, after the question | Recency: the last thing it sees before generating |
| "Do not hallucinate" boilerplate | Nowhere | No operational meaning; replace with a fallback rule |

> If your prompt is long enough that the instruction and the task are thousands of tokens apart, restate the one-line contract immediately before the task. Repetition is a real technique for long prompts; it costs ~15 tokens.

---

## 3. Instructions are probabilities, not code

The model predicts the next token. An instruction shifts the distribution over plausible continuations; it does not set a variable.

That single fact explains nearly every failure mode in the wild:

| Observed behavior | Mechanism |
|---|---|
| "It ignored the rule once" | The rule raised the probability of compliance; it did not enforce it |
| "It works in my test, fails in prod" | Your test sampled a high-probability path; prod found the tail |
| "Negative rules seem weaker" | Never naming the thing you forbid can make it salient; naming the *allowed* behavior plus the forbidden one works better |
| "It added a friendly preamble" | Chat-shaped training data makes preambles likely; only an explicit container rule suppresses them |
| "It got worse after I added detail" | More tokens can dilute the salient instruction; constraints compete for attention |

**Engineering response:** do not add emphasis, add *branches*. Every "always" needs a defined behavior for the case where it cannot hold (the fallback protocol). Every "never" needs a positive specification of what to emit instead.

---

## 4. Knowledge vs. context

The model has two knowledge sources:

1. **Parametric** — learned during training; frozen at the knowledge cutoff; unverifiable and confidently stated.
2. **Contextual** — whatever is in the prompt right now; authoritative for the current task.

Hallucination is usually **parametric knowledge winning a fight it should lose**, or filling a gap the prompt left undefined.

| Situation | What the model does without guidance | What to specify |
|---|---|---|
| Field missing from the document | Invents a plausible value | Absent → `null`; no inference |
| Document contradicts training knowledge | Sometimes "corrects" the document | The document is authoritative; quote it verbatim |
| Question outside the provided sources | Answers from memory | Answer only from `<context>`; otherwise abstain with a defined shape |
| Out-of-date fact ("current price") | Guesses | Decline or call a tool; never estimate |

The phrase that does the most work in production: **"If the answer is not present in the provided context, output `{"status": "insufficient_context"}`."**

---

## 5. Structured generation is still generation

JSON mode and schema-constrained decoding (grammar/JSON-schema enforcement, strict tool calls) make the *syntax* reliable. They do not make the *content* correct: a schema-valid object can contain invented values, empty strings, or wrong units.

| Guarantee | Source of the guarantee |
|---|---|
| Valid JSON, correct keys and types | Constrained decoding / schema mode |
| Values actually present in the source | Your prompt: quote-or-null rule |
| Records all present, none merged | Your prompt: granularity + one-per-line rule |
| Semantically correct classification | Your examples + definitions + eval suite |

Use schema mode **and** a grounding rule. Neither substitutes for the other.

---

## 6. What changes with scale and training

Newer and larger models are better at following instructions, holding long contexts, and doing multi-step work — which changes *where* the effort goes, not whether the principles hold.

| Era | Typical failure | Where to spend effort now |
|---|---|---|
| Older/smaller models | Misread structure, missed constraints | Tighter structure, more exemplars, shorter prompts |
| Current frontier chat models | Pass happy paths, fail edge cases, over-answer | Fallback protocols, abstention, adversarial cases, evals |
| Reasoning/thinking models | Over-explains, ignores format, burns budget | Success criteria and output contract; minimal scaffolding |
| Small/fast models (routing, extraction) | Format drift under load | Schema mode, few-shot calibration, deterministic post-checks |

**Do not carry folklore forward.** "You must say 'take a deep breath'" and "offer $200" style tricks were artifacts of specific models. Test on the model and version you deploy — that is what `benchmarks/` is for.

---

## 7. The four questions behind every prompt bug

When a prompt misbehaves, diagnose in this order:

1. **Can the model see it?** Is the instruction in context, in the right position, not buried mid-document?
2. **Is it unambiguous?** Would two competent humans implement it identically? If not, it is not a spec.
3. **Is the desired behavior probable?** Does the training distribution favor it? If not, add an exemplar.
4. **Is there a defined branch for the failure case?** If not, the model improvises — and improvisation is where fabrication lives.

If the answer to 1–4 is yes and it still fails, it is a model-capability or eval problem, not a wording problem. Stop paraphrasing and start measuring.

---

## Acceptance Checklist

- [ ] You can state where each instruction sits (system/developer/user) and why.
- [ ] The task and the output contract are near the end of the prompt, not only at the top.
- [ ] Every "never" has a positive alternative behavior specified.
- [ ] Missing-data and out-of-scope branches are defined, not left to inference.
- [ ] If structured output is required, a schema/grammar is used *and* a grounding rule is stated.
- [ ] Assumptions about the model are tested on the deployed model version, not inherited from folklore.
