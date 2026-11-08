---
name: sampling-and-determinism
type: guide
version: 1.0.0
output_format: markdown
related: [self-consistency, evaluation-matrix, model-landscape-and-migration]
---

# 🎛️ Sampling, Temperature & the Myth of Determinism

Prompt quality and sampling settings are one system. A prompt tuned at `temperature=0.9` is a different prompt at `0.2`, and "it's deterministic, I set temperature 0" is false in ways that quietly corrupt your eval numbers.

---

## 1. The knobs

| Parameter | Mechanically does | Typical range | Notes |
|---|---|---|---|
| **temperature** | Flattens or sharpens the next-token distribution | 0–1 (some APIs up to 2) | 0 ≈ greedy; >1 becomes incoherent for most models |
| **top_p** | Samples from the smallest token set whose cumulative probability ≥ p | 0.9–1.0 | Adjust *either* temperature or top_p, rarely both |
| **top_k** | Samples from the top k tokens | 20–100 | Often fixed by the provider |
| **max_tokens** | Hard cap on output length | task-dependent | Truncation mid-JSON is a schema failure, not a model failure |
| **stop sequences** | Halt on a string | e.g. `\n\n###` | Useful for multi-stage prompts; choose strings that cannot appear legitimately |
| **seed** | Requests reproducible sampling | provider-specific | Best-effort; not a guarantee across batches or versions |
| **frequency / presence penalty** | Discourage repeats / encourage novelty | 0–0.5 | Breaks structured output; leave at 0 for extraction |
| **reasoning / thinking budget** | Token allowance for hidden reasoning | model-specific | Too low truncates the reasoning and degrades the answer |

---

## 2. Settings by task

Starting points, not laws. Measure on your own eval set.

| Task | Temp | top_p | Reasoning budget | Rationale |
|---|---|---|---|---|
| Extraction / normalization | 0–0.2 | 1.0 | off or low | You want the modal answer, not creativity |
| Classification / routing | 0–0.2 | 1.0 | off | Stability beats diversity |
| Code generation | 0–0.3 | 1.0 | medium | Small diversity helps escape local optima; too much breaks coherence |
| RAG answering | 0–0.3 | 1.0 | medium | Grounded paraphrase; warmth is noise |
| Summarization | 0.2–0.4 | 1.0 | low–medium | Slight flexibility in phrasing |
| Structured planning / design | 0.4–0.7 | 0.95 | high | Multiple valid architectures; diversity is useful |
| Creative writing / naming | 0.7–1.0 | 0.95 | off–low | Divergence is the point |
| Self-consistency voting | 0.7–1.0 | 0.95 | high | You need genuinely different samples |

Two rules of thumb:

1. **If a parser consumes it, keep temperature low.** Diversity is a liability when the output must match a schema.
2. **If you are exploring (naming, ideation, design alternatives), raise temperature and filter afterwards** — but never let the exploration run at the same settings as production without re-validating the prompt.

---

## 3. Why temperature 0 is not deterministic

Greedy decoding picks the highest-probability token each step — in theory. In practice:

| Source of variance | Effect |
|---|---|
| Floating-point non-associativity on GPUs | Tiny numeric differences can flip near-ties |
| Batching | Your request is batched with others; batch composition can change reduction order |
| Mixture-of-experts routing | Token routing may depend on load or kernel selection |
| Provider-side model updates | The same model id can be redeployed under you |
| Hidden system prompts / safety layers | Provider-side instructions vary by product surface and can change |
| Tokenization / template changes | A new template changes the prompt you think you sent |

**Consequence for evaluation:** never treat one run as ground truth. Record the model id and date, run each case several times, and report the distribution, not a single score. Two runs of the same prompt on different days can differ by a full rubric point — especially on the edge cases your suite is built around.

### Measuring variance cheaply

```text
1. Pick the 3 lowest-scoring cases from your last run.
2. Run each 5x at production settings.
3. Record the score vector.

Stable low score      -> prompt defect (fix the prompt)
Unstable score        -> under-constrained (add exemplars, narrow the task, lower temperature)
Stable high score     -> done
```

Treat "unstable" as a defect class of its own: a prompt that is right 60% of the time is not a prompt, it is a slot machine.

---

## 4. Reasoning budgets

Models with an explicit thinking phase (extended thinking, reasoning effort, thinking tokens) expose a separate budget.

- **Too small:** the model is cut off mid-derivation and returns a confident wrong answer with no visible symptom.
- **Too large:** you pay for deliberation on trivial prompts and add latency for no accuracy gain.
- **Right-sized:** budget by task class — a classification needs almost none; a multi-constraint refactor needs a lot.

Do not confuse *thinking budget* with *max output tokens*. The first buys correctness, the second buys length. Set both, independently.

---

## 5. Sampling and prompt design interact

| Design choice | Sampling implication |
|---|---|
| Few-shot exemplars | Lower variance; the model has a concrete target to imitate |
| Open-ended instructions | Higher variance; every sample is a different interpretation |
| "Be creative" | Raises variance without bounding it — pair with a constraint (form, length, angle) |
| Long outputs | More chances to drift; cap length and pin structure |
| Self-consistency | Requires high temperature *and* a way to select among samples |

A prompt is only tuned for the setting it was evaluated at. If production differs from your eval (temperature, max tokens, system prompt, model snapshot), you have not evaluated production.

---

## 6. Practical protocol

```text
1. Fix the model id (exact string, including date/version) and settings.
2. Record them in the run file next to the outputs.
3. Evaluate at production settings, not at "nice demo" settings.
4. Re-run after any settings change; treat it as a prompt change.
5. Keep a fallback: if the parse fails twice, degrade to a lower-temperature
   retry or a deterministic post-processor rather than a third blind attempt.
```

Full harness usage: [evaluation-matrix](../benchmarks/evaluation-matrix.md).

---

## 7. Anti-patterns

| Anti-pattern | Why it bites |
|---|---|
| "temperature 0 means reproducible" | It does not; see §3 |
| Tuning temperature to fix a prompt defect | Masks an ambiguity; produces the same defect at a different rate |
| Sampling at 0.9 in dev, 0 in prod | Your eval measured a different system |
| Both temperature and top_p heavily tuned | Two interacting knobs, uninterpretable results |
| Penalties on extraction tasks | Punishes correct repetition (same `null`, same enum) |
| max_tokens set exactly to the expected length | Guarantees truncation on the hard cases |

---

## Acceptance Checklist

- [ ] Model id (with version/date) and all sampling settings are recorded with every run.
- [ ] Settings match production; deviations are documented.
- [ ] Each task class has a justified temperature and reasoning budget.
- [ ] No parser-facing task relies on high temperature.
- [ ] At least three cases have been run 5× to measure variance.
- [ ] A retry/degradation policy exists for parse failures.
