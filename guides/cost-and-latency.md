---
name: cost-and-latency
type: guide
version: 1.0.0
output_format: markdown
related: [sampling-and-determinism, model-landscape-and-migration, task-decomposition]
---

# 💰 Cost & Latency Engineering

Prompt design is cost design. The two dominant terms are **input tokens** (context you send every call) and **output tokens** (what the model writes) — and both are decisions you make in the prompt, not just in the model choice.

Latency is a different sum: time-to-first-token, generation time proportional to output length, and orchestration overhead (sequential calls, retries, tools).

---

## 1. Where the money goes

| Term | Typical driver | Prompt-level lever |
|---|---|---|
| Input tokens | Long system prompts, few-shot blocks, retrieved context, history | Cache stable prefixes; retrieve less; summarize history |
| Output tokens | Verbosity, reasoning, structured elaboration | Hard caps; forbid preamble/explanation; constrain schema |
| Retries | Format failures, repairs | Schema mode; container rules; fewer repair loops |
| Multi-sampling | Self-consistency, best-of-n | Route to it only for high-stakes cases |
| Tools | Round trips, large results | Tighter tool outputs; parallel calls |

A 2,000-token system prompt sent 1M times is 2B input tokens. That is a prompt-design line item, not an infrastructure one.

---

## 2. Order of operations

Apply in this order; each step is cheaper than the next.

```text
1. Cut output length          (biggest, safest win)
2. Cache the stable prefix    (system prompt + exemplars)
3. Retrieve better, not more  (top-5 ranked > top-30)
4. Route by difficulty        (small model for easy cases)
5. Parallelize independent calls
6. Shrink the model
7. Only then, negotiate price
```

Cutting output is first because output tokens usually cost several times more than input tokens, and every "explain your reasoning" instruction is a recurring charge.

---

## 3. Cutting output without losing quality

| Instruction | Effect | Cost |
|---|---|---|
| "No preamble, no closing summary" | Large | Free |
| "Answer in ≤3 sentences" | Large | Free |
| "Return only the JSON object" | Large | Free |
| "No restating the question" | Medium | Free |
| "One example maximum" | Medium | Free |
| Fewer/terser exemplars | Medium | Small accuracy risk |
| Shorter schema descriptions | Small | Small accuracy risk |

**What not to cut:** the negative rules, the fallback shape, and the container contract. Those are the tokens that prevent retries, and a retry costs more than the sentence that avoided it.

---

## 4. Prefix caching

Most providers cache identical prompt *prefixes*. Exploit it by ordering content by stability:

```text
[stable]    system role + hard rules + output contract + exemplars
[per-tenant] tenant policy, glossary, tool list
[per-request] retrieved context, user message
```

Rules:

1. **Never put timestamps, request ids, or user names at the top.** They invalidate the cache for every request.
2. **Keep exemplars byte-identical** across calls; a single reordered list breaks the prefix.
3. **Measure the hit rate.** If it is low, something volatile drifted into the prefix.

On a chat product with a 1,500-token system prompt, correct ordering can remove most of the input cost and a meaningful slice of latency.

---

## 5. Retrieval economics

| Strategy | Input tokens | Quality |
|---|---|---|
| Stuff everything | Very high | Often worse (dilution) |
| Top-30 chunks | High | Marginal gain over top-10 |
| Top-8 reranked | Moderate | Best quality/cost point for most QA |
| Top-3 + neighbor expansion | Low | Good for focused questions |

Retrieval precision is a cost lever: **the cheapest context is context you don't send.** Measure answer quality at k=3, 5, 8, 15 — most systems plateau early.

---

## 6. Latency budget

```text
total p95 = queue + prefill(input tokens) + decode(output tokens) + orchestration
```

| Lever | Effect | Trade-off |
|---|---|---|
| Shorter output | Large (decode is per token) | Enforce caps |
| Streaming | Improves *perceived* latency | Does not reduce total |
| Smaller/faster model | Large | Accuracy on hard cases |
| Parallel tool calls | Large on multi-step | Only for independent calls |
| Prefix caching | Medium (prefill) | Requires stable prefix |
| Fewer stages | Large | Loses decomposition benefits |
| Speculative/streamed JSON | Medium | Parse only on completion |

Perceived latency rule: **show the first useful token fast**, even if the full answer takes longer. Users tolerate a streaming answer far better than a spinner.

---

## 7. Routing by difficulty

```text
request ──► cheap classifier (small model)
              ├── easy  (~70%) ──► small model, strict schema
              └── hard  (~30%) ──► reasoning model
```

How to classify "difficulty" without labels:

- **Confidence**: low-confidence classifications go to the stronger model.
- **Input length / complexity heuristics**: multi-part requests, tables, code.
- **Self-consistency disagreement**: samples disagree → escalate.
- **Historical difficulty by intent**: route by intent class.

Measure the accuracy/cost curve; a 90/10 split often captures most of the quality at a fraction of the price.

---

## 8. Cost anti-patterns

| Anti-pattern | Cost | Fix |
|---|---|---|
| "Think step by step" on every call | Output tokens on all traffic | Enable only for hard cases |
| Whole repo pasted for a one-function question | Input explosion | Retrieve the file + imports only |
| Retry with identical prompt after parse failure | 2× cost, same failure | Repair with the validator error, cap at 1–2 |
| Full conversation history each turn | Quadratic growth | Summarize + last k turns |
| 12 exemplars for 4 labels | Fixed cost on every call | 1 per label + 2 boundary cases |
| Reasoning budget maxed on classification | Latency + cost, no gain | Budget by task class |
| No output cap | Unbounded decode | `max_tokens` from the contract |

---

## 9. Measuring

Log per request: input tokens, output tokens, cached tokens, latency, retries, and model. Then compute:

| Metric | Why |
|---|---|
| Cost per successful outcome (not per call) | Retries and failures are part of unit cost |
| Tokens per outcome | Shows prompt-level waste |
| Cache hit rate | Confirms prefix hygiene |
| p50/p95 latency by stage | Finds the bottleneck |
| Repair rate | Early warning of prompt drift |

**Cost per *successful outcome*** is the only number that matters for a business case. A prompt that costs 30% more per call but eliminates a 20% retry rate is cheaper.

---

## Acceptance Checklist

- [ ] Output length is capped and preamble/explanation are suppressed.
- [ ] Stable content precedes volatile content for prefix caching.
- [ ] Retrieval `k` has been tuned against quality, not just set to a default.
- [ ] Difficulty routing is in place for mixed workloads (or justified as unnecessary).
- [ ] `max_tokens` derives from the output contract, not from a guess.
- [ ] Repair loops are capped and logged.
- [ ] Cost is tracked per successful outcome, not per call.
- [ ] Latency is broken down by stage (prefill, decode, orchestration).
