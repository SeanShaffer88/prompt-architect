# Recorded runs

Each file here is one **recorded model run** against a suite in `../suites/`:
the raw outputs keyed by case id, plus the model, variant, date, and sampling
settings. The evaluator is offline and deterministic — it never calls a model,
so CI can re-grade a run months later and get the same numbers.

## Provenance of the committed fixtures

The four `2026-11-08.log-normalize.*.json` files are **synthetic fixtures**, not
measured model output. Their `model` field says `synthetic-fixture` and each file
carries a `provenance` note. They are curated to demonstrate the failure each
enforcement layer removes:

| File | Variant | Illustrates |
|---|---|---|
| `…v0.json` | zero-shot | Preamble + fence, fabricated empty-input records, inferred levels, injection compliance |
| `…v1.json` | structured | Components present, but no negative rules: fences persist, fallbacks missing |
| `…v2.json` | patterned | Clean happy path; still no fallback protocol, no payload guard, no conflict rule |
| `…v3.json` | hardened | Meets the ship bar on all six cases |

Their purpose is to keep the harness honest in CI: `v3` must pass the ship bar
and `v0` must fail it. If a rubric change makes `v0` pass, the suite has stopped
discriminating and CI fails on purpose.

Do not present these numbers as model benchmarks. Replace them with real
captures to make a performance claim.

## Recording a real run

1. Compose the prompt for the variant you are testing:

   ```bash
   python -m prompt_architect compose specs/log-normalize.json --variant v3 > /tmp/prompt.md
   ```

2. Send each case input from `benchmarks/suites/<suite>.json` to your model with
   temperature 0, and save the raw string returned for each case id.
3. Write the run file:

   ```json
   {
     "suite": "log-normalize",
     "prompt_version": "1.3.0",
     "variant": "v3",
     "model": "exact-model-id-and-date",
     "temperature": 0,
     "date": "2026-11-08",
     "outputs": { "T1": "…raw response…", "T2": "…" }
   }
   ```

4. Grade it:

   ```bash
   python -m prompt_architect eval benchmarks/suites/log-normalize.json \
     --run benchmarks/runs/2026-11-08.log-normalize.v3.json
   ```

Append new runs; never overwrite an existing row. A prompt's run history is its
regression suite.
