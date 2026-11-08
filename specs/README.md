# Prompt specs

Machine-readable prompts. Every blueprint in [`../blueprints/`](../blueprints/)
has a spec here, so it can be composed, diffed, and versioned instead of copied
by hand.

## What a spec is

JSON, deliberately: it diffs cleanly in review and needs no YAML dependency.

```json
{
  "name": "classification-routing",
  "version": "1.0.0",
  "role": "...",
  "context": ["..."],
  "objective": "...",
  "constraints": { "must": ["..."], "must_not": ["..."] },
  "fallback": [{ "condition": "...", "output": "..." }],
  "examples": [{ "label": "...", "input": "...", "output": "..." }],
  "output": { "spec": "...", "first_char": "{", "last_char": "}" }
}
```

Fields the composer relies on:

| Field | Purpose |
|---|---|
| `role` / `context` / `objective` | Components 1–3 |
| `constraints.must` | Component 4, positive half (at least one required) |
| `constraints.must_not` | Component 4, negative half — omitted at V1, present at V2+ |
| `fallback` | The table rendered at V3; also what makes V3 pass the ship bar |
| `examples` | Rendered at V2+ |
| `output.spec` | Component 5 prose |
| `output.first_char` / `last_char` | Byte-level container line at V3 |
| `output.precedence` | Rule-conflict resolution at V3 |
| `payload_tag` | Wraps untrusted content; adds the inert-data guard at V3 |

## The four variants

| Variant | Adds | Purpose |
|---|---|---|
| `v0` | — | The zero-shot baseline the benchmark compares against |
| `v1` | 5 components, positive rules | Structured, unconstrained |
| `v2` | negative rules + exemplars | Patterned |
| `v3` | fallback protocol, payload guard, precedence, container | Hardened |

Changing a spec changes all four renders, which is why the goldens are committed.

## Inventory

| Spec | Blueprint | Gated by a suite |
|---|---|---|
| [log-normalize](log-normalize.json) | worked example | ✅ `log-normalize` |
| [classification-routing](classification-routing.json) | [blueprints/classification-routing.md](../blueprints/classification-routing.md) | ✅ `classification-routing` |
| [summarization](summarization.json) | [blueprints/summarization.md](../blueprints/summarization.md) | ✅ `summarization` |
| [data-extraction](data-extraction.json) | [blueprints/data-extraction.md](../blueprints/data-extraction.md) | — |
| [code-generation](code-generation.json) | [blueprints/code-generation.md](../blueprints/code-generation.md) | — |
| [rag-answering](rag-answering.json) | [blueprints/rag-answering.md](../blueprints/rag-answering.md) | — |
| [system-architecture](system-architecture.json) | [blueprints/system-architecture.md](../blueprints/system-architecture.md) | — |
| [agent-system-prompt](agent-system-prompt.json) | [blueprints/agent-system-prompt.md](../blueprints/agent-system-prompt.md) | — |
| [creative-writing](creative-writing.json) | [blueprints/creative-writing.md](../blueprints/creative-writing.md) | — |
| [vision-and-multimodal](vision-and-multimodal.json) | [blueprints/vision-and-multimodal.md](../blueprints/vision-and-multimodal.md) | — |

A spec without a suite is compose-able and version-controlled, but its behavior
is not gated in CI. Adding a suite is the next step for those rows.

## Workflow

```bash
# render and inspect
python -m prompt_architect compose specs/classification-routing.json --variant v3

# after editing a spec, regenerate every golden and review the diff
for variant in v0 v1 v2 v3; do
  python -m prompt_architect compose specs/classification-routing.json \
    --variant "$variant" --write
done
git diff specs/golden/

# verify nothing drifted
python -m prompt_architect compose specs/classification-routing.json --variant v3 --check
```

Bump `version` whenever behavior changes, and record the new version in the
suite (`prompt_version`) and in any run files you capture.

## Adding a spec

1. Copy the closest existing spec and change the content, not the structure.
2. Fill `constraints.must` and `constraints.must_not` as pairs; a rule without
   its inverse is an invitation to a near-miss.
3. Define every fallback branch: empty, missing, conflict, insufficient.
4. Pin the container (`first_char`/`last_char`) if the output is parsed.
5. Render all four variants, read the V3 output end to end, and commit the goldens.
6. Add a suite if a parser or a downstream system depends on the output.
