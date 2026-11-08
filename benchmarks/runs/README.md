# Recorded runs

Each file here is one **recorded model run** against suite in `../suites/`: the
raw outputs keyed by case id, plus the model, variant, date, and sampling
settings. The evaluator is offline and deterministic — it never calls a model,
so CI can re-grade a run months later and get the same numbers.

## Telling a captured run from a fixture

Every run file carries a `provenance` field. Trust nothing else in the filename.

| `provenance.kind` | Meaning | May be cited as a benchmark |
|---|---|---|
| `captured` | Produced by `prompt-architect record` against a real endpoint | Yes, with the model id and date |
| (absent) or a note saying synthetic | Curated fixture written by hand | **No** |

All runs committed before 2026-11-08's recorder work are `synthetic-fixture`.
They exist to keep the harness honest in CI, not to make claims about models.

## Committed fixtures

| File | Variant | Illustrates |
|---|---|---|
| `…log-normalize.v0/v1/v2/v3` | V0–V3 | Fence + preamble, fabricated empty-input records, inferred levels, injection compliance → hardening |
| `…classification-routing.v0/v3` | V0/V3 | Guessed labels and an obeyed payload instruction → closed labels + `unclear` |
| `…summarization.v0/v3` | V0/V3 | Prose instead of state, fabricated incidents, dropped conflicting ETAs |

The gates in CI are directional on purpose: every `v3` run must pass the ship
bar, and every `v0` run must fail it. If a rubric change makes `v0` pass, the
suite has stopped discriminating and CI fails.

## Capture a real run

The recorder speaks the OpenAI-compatible chat-completions API. Any provider
with that surface (direct, or behind a gateway) works by changing `--base-url`.

```bash
export OPENAI_API_KEY=...                      # never committed

python -m prompt_architect record \
  --spec specs/classification-routing.json \
  --suite benchmarks/suites/classification-routing.json \
  --variant v3 \
  --model "exact-model-id-including-version" \
  --base-url https://api.openai.com/v1 \
  --temperature 0 \
  --out benchmarks/runs/2026-11-09.classification-routing.v3.json
```

What it does:

1. Renders the spec at the requested variant into the **system** message.
2. Sends each suite case's `input` as the **user** message, one request per case.
3. Writes the run file with `provenance.kind: "captured"`, the endpoint host, and a UTC timestamp.
4. Prints the `eval` command to grade it.

Safety properties, covered by tests:

- the API key is read from the environment and never written to the run file;
- a non-200 response aborts the capture and writes nothing (no partial runs);
- `--dry-run` prints the rendered prompt and needs no key;
- an unreachable endpoint is an error, not an empty output.

If your provider is not chat-completions compatible, capture by hand (below) and
set `provenance.kind` accordingly.

## Capture by hand

1. Compose the prompt for the variant under test:

   ```bash
   python -m prompt_architect compose specs/classification-routing.json --variant v3 > /tmp/prompt.md
   ```

2. Send each case input from the suite to your model at temperature 0, and save
   the raw string returned for each case id.
3. Write the run file:

   ```json
   {
     "suite": "classification-routing",
     "prompt_version": "1.0.0",
     "variant": "v3",
     "model": "exact-model-id-and-date",
     "temperature": 0,
     "date": "2026-11-09",
     "provenance": {"kind": "captured", "endpoint_host": "gateway.internal", "recorded_at": "2026-11-09T09:00:00+00:00"},
     "outputs": {"T1": "…raw response…", "T2": "…"}
   }
   ```

4. Grade it:

   ```bash
   python -m prompt_architect eval benchmarks/suites/classification-routing.json \
     --run benchmarks/runs/2026-11-09.classification-routing.v3.json
   ```

Append new runs; never overwrite an existing one. A prompt's run history is its
regression suite.
