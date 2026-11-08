# ⚡ Prompt Architect

> A deterministic, systems-oriented framework for engineering high-performance prompts to control LLM outputs, minimize hallucinations, and execute complex technical and creative workflows.

Prompts are not conversation. They are **API contracts** against a probabilistic execution engine.

This repository is the contract library: a mental model of how models read prompts, a fixed five-component architecture, a pattern catalogue, production blueprints for nine task classes, operational guides for cost, safety, and multi-turn systems, an evaluation rubric with a working harness, and a test-case design manual.

**New here?** Read [how models read prompts](fundamentals/how-llms-read-prompts.md), then copy the [cheat sheet](guides/cheat-sheet.md).

```bash
python -m prompt_architect lint .                                        # audit prompts and docs
python -m prompt_architect compose specs/log-normalize.json --variant v3  # render a hardened prompt
python -m prompt_architect eval benchmarks/suites/log-normalize.json \
  --run benchmarks/runs/2026-11-08.log-normalize.v3.json                 # grade against the ship bar
python -m prompt_architect record --spec specs/classification-routing.json \
  --suite benchmarks/suites/classification-routing.json \
  --model <exact-model-id> --variant v3                                  # capture a real run
```

---

## 📑 Contents

- [Who This Is For](#-who-this-is-for)
- [Three Ways In](#-three-ways-in)
- [Core Philosophy](#-core-philosophy)
- [The 5-Component Prompt Architecture](#️-the-5-component-prompt-architecture)
- [The Library](#-the-library)
  - [Foundations](#foundations--how-models-actually-work)
  - [Patterns](#patterns--cross-domain-mechanisms)
  - [Blueprints](#blueprints--production-shaped-prompts)
  - [Guides](#guides--operations-and-diagnostics)
  - [Benchmarks](#benchmarks--proving-it-works)
  - [Reference](#reference--selection-probes-and-registry)
- [The Harness](#-the-harness)
- [The Architect Loop](#-the-architect-loop)
- [Anti-Patterns](#-anti-patterns--failure-modes)
- [Model Landscape in Brief](#-model-landscape-in-brief)
- [Security in Brief](#-security-in-brief)
- [Evaluation in Brief](#-evaluation-in-brief)
- [Repository Layout](#-repository-layout)
- [File Conventions](#-file-conventions)
- [FAQ](#-faq)
- [Contributing](#-contributing)

---

## 🎯 Who This Is For

Anyone who needs **repeatable** model behavior rather than impressive one-off demos: engineers shipping LLM features, agents driving tool calls, data teams parsing unstructured input into schemas, support teams automating triage, writers producing structured content at scale.

If a wrong output costs you money, downtime, a support ticket, or a human review cycle, treat the prompt like production code — version it, test it, and constrain it.

---

## 🚪 Three Ways In

### "I need a prompt right now"
1. Copy the [cheat sheet](guides/cheat-sheet.md) skeleton.
2. Pick the closest [blueprint](#blueprints--production-shaped-prompts) and fill the `[BRACKETED]` inputs.
3. Define the four undefined branches (empty, missing, conflict, insufficient).
4. Test on the adversarial case before shipping.

### "My prompt is broken"
1. Run the [five-minute triage](guides/troubleshooting.md#8-the-five-minute-triage).
2. Find the symptom in the [diagnostic index](guides/troubleshooting.md).
3. Fix the *branch*, not the wording — nine times in ten that is the defect.

### "I'm shipping an LLM feature"
1. Read [instruction hierarchy](fundamentals/instruction-hierarchy.md) and [security](guides/prompt-injection-and-safety.md) first. They constrain the architecture, not just the words.
2. Write the [spec](specs/log-normalize.json) and compose it.
3. Design the [test suite](benchmarks/test-case-design.md) before tuning.
4. Gate the deploy on the [ship bar](benchmarks/evaluation-matrix.md#minimum-bar-before-shipping).

---

## 🧠 Core Philosophy

Treat prompts as **programmatic interfaces**, not casual conversation. An LLM is a probabilistic execution engine; your prompt is the API contract. To achieve deterministic and repeatable results:

1. **Explicit Constraint Enforcement** — Define hard boundaries (what *not* to do) with equal weight to instructions (what to do).
2. **Context Isolation** — Provide only the necessary state, dependencies, and environment variables required for the specific task.
3. **Structural Determinism** — Dictate exact output schemas (JSON, Markdown tables, strict AST formats) to allow downstream parsing.

Three corollaries follow:

| Principle | Corollary | Failure it prevents |
|---|---|---|
| Constraint Enforcement | Every positive instruction earns a paired negative one. | Model "helpfully" adds prose around your JSON. |
| Context Isolation | Irrelevant context is a bug, not a bonus. | Model anchors on the wrong file, version, or example. |
| Structural Determinism | If a parser consumes it, the prompt must specify the bytes. | `JSON.parse` throws on a fenced block. |

**The governing rule:** *an instruction the model can interpret is an instruction it will eventually interpret differently.* Ambiguity is a defect, not a style choice.

### Determinism is a spectrum, not a switch

| Level | What you control | What you still cannot |
|---|---|---|
| **Syntactic** | Schema mode, grammars, container rules | Values inside the structure |
| **Semantic** | Grounding rules, null policy, abstention shapes | The model's judgment on novel inputs |
| **Statistical** | Temperature, exemplars, self-consistency, evals | Bit-exact reproducibility across runs |

Most teams claim determinism while holding only the syntactic level. Claim what you can prove: *"valid schema, grounded values, 96% agreement across 5 samples"* — not *"deterministic"*.

---

## 🏗️ The 5-Component Prompt Architecture

Every high-efficiency prompt maintains a rigid hierarchy separating intent, context, and constraints.

```text
[1. SYSTEM ROLE / PERSONA] -> Defines operational boundaries & expertise level.
[2. CONTEXT & STATE]       -> Provides background data, dependencies, or environment specs.
[3. CORE OBJECTIVE]        -> Precise, singular action verb defining the execution goal.
[4. CONSTRAINTS & RULES]   -> Negative constraints, formatting rules, and strict exclusions.
[5. OUTPUT SPECIFICATION]  -> Exact schema, syntax requirements, or template structure.
```

### Component Breakdown

| Component | Purpose | Example |
|---|---|---|
| **1. Role** | Sets tone, domain expertise, and operational scope. | *"You are an elite systems programmer specializing in low-level Rust and memory safety."* |
| **2. Context** | Feeds relevant state, versions, and constraints. | *"Target environment: Windows 11 x64, zero external dependencies, Rust 1.75+."* |
| **3. Objective** | Direct, unambiguous command. | *"Refactor the provided file-buffering loop to use zero-copy asynchronous I/O."* |
| **4. Constraints** | Hard boundaries and negative instructions. | *"Do not use unsafe blocks. Do not introduce tokio dependencies if std::fs suffices."* |
| **5. Output Spec** | Enforces structure for automated parsing or immediate review. | *"Return only the refactored code block inside a ```rust fence with inline comments explaining trade-offs."* |

### Field notes per component

**1. Role** — One sentence. The role narrows the distribution of plausible answers; it is not a costume. *"You are a senior SRE"* changes what the model considers relevant. *"You are a helpful genius who is also a poet and a lawyer"* averages three distributions into mush. Never use the role to smuggle in the objective, and state what the role does *not* do.

**2. Context** — Version-pin everything that could drift: language/runtime, OS, dependency policy, data source, audience, prior decisions. Delimit untrusted payloads with explicit tags (`<log_payload>…</log_payload>`) so the model cannot confuse data with instructions. If a fact is unknown, say it is unknown — do not omit it and hope.

**3. Objective** — Exactly one imperative verb: `Extract`, `Refactor`, `Classify`, `Generate`, `Audit`. Two objectives is two prompts. If you genuinely need a pipeline, sequence it explicitly.

**4. Constraints** — The highest-leverage component and the one most often skipped. Write them as testable assertions, not preferences. *"Be concise"* is untestable; *"No prose before or after the code block; maximum 400 lines"* is a test. Every negative rule needs a positive alternative behavior.

**5. Output Specification** — Specify the container (fence language, raw text, table), the shape (schema keys, ordering, types), the units (MB, ISO 8601, UTC), and the empty case (`null`, `[]`, `"UNKNOWN"`). Anything a parser touches must be pinned.

### Minimal skeleton

```markdown
### Role
[One sentence: domain expertise + operational scope.]

### Context
- **Environment:** [versions, platform, dependency policy]
- **Input:** <payload>[content]</payload>
- **Known unknowns:** [what is not provided and must not be invented]

### Objective
[Single imperative verb] [the one thing] to [measurable outcome].

### Constraints & Negative Rules
- DO NOT [forbidden behavior].
- DO NOT [forbidden output element].
- If [missing data condition], [deterministic fallback].

### Output Specification
[Container] + [schema/shape] + [units] + [empty case].
```

### The three cross-cutting layers

The five components are the skeleton. Three layers decide whether it survives contact with reality:

| Layer | Question | Where it lives |
|---|---|---|
| **Exemplars** | What does "correct" look like, including an edge case? | [few-shot calibration](patterns/few-shot-calibration.md) |
| **Fallback protocol** | What happens when the task cannot be completed? | Empty, missing, conflict, insufficient |
| **Precedence** | Which rule wins when two conflict? | [instruction hierarchy](fundamentals/instruction-hierarchy.md) |

> The five components get a prompt to work on the happy path. These three get it to work in production.

---

## 📚 The Library

### Foundations — how models actually work

| File | What it covers | Read when |
|---|---|---|
| [how-llms-read-prompts](fundamentals/how-llms-read-prompts.md) | Tokens, attention, position effects, why instructions are soft constraints, knowledge vs. context | Before your first serious prompt |
| [instruction-hierarchy](fundamentals/instruction-hierarchy.md) | System/developer/user/tool precedence, delegation, untrusted data, multi-turn drift | Designing a system prompt or handling user input |
| [sampling-and-determinism](fundamentals/sampling-and-determinism.md) | Temperature, top_p, seeds, reasoning budgets, why temp 0 isn't deterministic, variance measurement | Tuning settings or diagnosing flakiness |
| [model-landscape-and-migration](fundamentals/model-landscape-and-migration.md) | Model classes, provider quirks, migration protocol, silent redeploys | Choosing a model or upgrading one |

### Patterns — cross-domain mechanisms

| Pattern | Mechanism | Use when |
|---|---|---|
| [chain-of-thought](patterns/chain-of-thought.md) | Ordered reasoning with an adversarial verification stage | Multi-step logic, debugging, trade-off analysis |
| [few-shot-calibration](patterns/few-shot-calibration.md) | Exemplars that demonstrate edge cases, not just the happy path | Format drifts or zero-shot style is wrong |
| [constraint-enforcement](patterns/constraint-enforcement.md) | Positive/negative symmetry, delimiters, fallback protocols | Output feeds a parser, test, or another agent |
| [structured-output](patterns/structured-output.md) | Schema-first design, schema mode, validation, capped repair | Any JSON/document output consumed by code |
| [self-consistency](patterns/self-consistency.md) | Sample n, vote, use disagreement as confidence | Discrete answers with expensive mistakes |
| [rag-grounding](patterns/rag-grounding.md) | Context as sole truth, per-claim citations, abstention | Answering over a private corpus |
| [react-tool-use](patterns/react-tool-use.md) | Tool contracts, stop conditions, error branches, injection defense | Any agent loop |
| [task-decomposition](patterns/task-decomposition.md) | Stages with typed contracts instead of stacked objectives | Tasks with multiple formats or human checkpoints |
| [prompt-chaining-and-routing](patterns/prompt-chaining-and-routing.md) | Router, specialists, handoff contracts, `misrouted` branch | Requests of materially different types |
| [long-context-management](patterns/long-context-management.md) | Budget, packing, lost-in-the-middle, state blocks | Large documents or long sessions |
| [uncertainty-and-abstention](patterns/uncertainty-and-abstention.md) | Abstention vocabulary, confidence enums, calibration | High-stakes decisions |
| [reasoning-model-prompting](patterns/reasoning-model-prompting.md) | Success criteria over scaffolding, budgets, output contracts | Using a thinking/reasoning model |
| [style-control](patterns/style-control.md) | Persona as job description, countable length caps, exemplars | Voice, tone, and length matter to the product |

### Blueprints — production-shaped prompts

Fill in the `[BRACKETED]` inputs; keep the structure intact. Each ships with worked examples, variants, failure modes, and an acceptance checklist.

| Blueprint | Task class | Signature variants |
|---|---|---|
| [code-generation](blueprints/code-generation.md) | Implementation & refactoring | Bug repair, test generation |
| [data-extraction](blueprints/data-extraction.md) | Unstructured → strict JSON | OCR/vision, unit normalization |
| [system-architecture](blueprints/system-architecture.md) | Design docs & trade-offs | Migration plan, build-vs-buy |
| [agent-system-prompt](blueprints/agent-system-prompt.md) | Tool-using agents | Read-only analyst, autonomous + escalation |
| [rag-answering](blueprints/rag-answering.md) | Grounded QA over a corpus | Comparison, procedural how-to |
| [classification-routing](blueprints/classification-routing.md) | Triage, intent, tagging | Two-stage taxonomy |
| [summarization](blueprints/summarization.md) | Compression with a purpose | Executive brief, extraction-summary |
| [creative-writing](blueprints/creative-writing.md) | Narrative, marketing, verse | Brand copy, constrained verse |
| [vision-and-multimodal](blueprints/vision-and-multimodal.md) | Image understanding & generation | Chart reading, editing/consistency |

### Guides — operations and diagnostics

| Guide | Use when |
|---|---|
| [cheat-sheet](guides/cheat-sheet.md) | You need the whole framework on one page |
| [troubleshooting](guides/troubleshooting.md) | A prompt is misbehaving; symptom → cause → fix |
| [prompt-injection-and-safety](guides/prompt-injection-and-safety.md) | Your prompt touches user content, documents, or tools |
| [cost-and-latency](guides/cost-and-latency.md) | The bill or the p95 is too high |
| [multi-turn-conversations](guides/multi-turn-conversations.md) | Rules decay or state is lost across turns |
| [glossary](guides/glossary.md) | A term in a spec is ambiguous |

### Benchmarks — proving it works

| File | What it is |
|---|---|
| [evaluation-matrix](benchmarks/evaluation-matrix.md) | The 0–4 rubric, T1–T6 spine, V0–V3 ladder, ship bar, log format |
| [test-case-design](benchmarks/test-case-design.md) | How to write cases that actually fail |
| [suites/](benchmarks/suites/) | Three gated suites: `log-normalize`, `classification-routing`, `summarization` |
| [runs/](benchmarks/runs/README.md) | Recorded runs, provenance, and how to capture a real one |

### Reference — selection, probes, and registry

| File | Use when |
|---|---|
| [pattern-selection](reference/pattern-selection.md) | You have a task or a symptom and need the starting point |
| [provider-compatibility](reference/provider-compatibility.md) | Choosing a provider, or re-checking one after an upgrade |
| [prompt-registry](reference/prompt-registry.md) | Tracking prompts in production: owner, version, model, last eval |

---

## 🧰 The Harness

The framework ships as a zero-dependency Python package, so its rules are executable rather than aspirational.

```bash
python -m prompt_architect lint .                        # audit the docs against this repo's own rules
python -m prompt_architect compose specs/log-normalize.json --variant v3
python -m prompt_architect compose specs/log-normalize.json --all
python -m prompt_architect eval benchmarks/suites/log-normalize.json \
  --run benchmarks/runs/2026-11-08.log-normalize.v3.json
```

`pip install -e .` exposes the same interface as `prompt-architect`.

### What each command enforces

| Command | Enforces | Fails on |
|---|---|---|
| `lint` | front-matter shape, the 5 component sections, paired negative constraints, fallback protocol, deterministic container, acceptance checklist, relative links | any `PA*` error (1) |
| `compose` | a spec renders reproducibly; `--check` diffs against `specs/golden/` | any drift from the golden prompt (1) |
| `eval` | the ship bar: schema 4 on every case, no dimension below 3, no injection compliance | any blocker (1) |
| `record` | captures a real run against an OpenAI-compatible endpoint; key stays in the environment | HTTP error, unreachable endpoint, or missing key (2) |

### The spec and the variant ladder

Every blueprint has a machine-readable spec in [`specs/`](specs/README.md) — role, context, objective, must/must-not constraints, fallback table, exemplars, and the output container. `compose` renders a spec at four levels:

| Variant | Adds | Purpose |
|---|---|---|
| `v0` | — | The zero-shot baseline you are trying to beat |
| `v1` | 5 components, positive rules | Structured, but nothing forbidden and nothing specified for the unknown |
| `v2` | negative rules + exemplars | Patterned: fences disappear, the null policy lands |
| `v3` | fallback protocol, payload guard, precedence, byte-level container | Hardened: the version that passes the ship bar |

Exactly one class of enforcement changes per step, which is what makes a score movement attributable to a layer instead of to luck.

### Offline by design

`eval` never calls a model. You record raw outputs once — with whatever client you use — and commit the run file; CI re-grades it deterministically. See [benchmarks/runs/README.md](benchmarks/runs/README.md) for the record format and the provenance of the committed fixtures.

---

## 🔁 The Architect Loop

Do not write a prompt once. Run it like a build pipeline:

1. **Specify** — Draft the 5 components. Write the output specification *first*, then work backwards to the constraints that make that output possible.
2. **Constrain** — For every instruction, add its inverse. Add the fallback for missing data. Tag the payload.
3. **Calibrate** — Run against 3–5 adversarial inputs, including an empty input and a malformed one.
4. **Score** — Grade with the rubric: schema validity, constraint adherence, grounding, completeness, efficiency.
5. **Harden** — Promote every observed failure into either a constraint or an exemplar. Do not "rephrase and hope."
6. **Freeze** — Version the prompt, record the model and settings, and archive the eval log beside it.

> A prompt without a recorded eval run is a draft, regardless of how good the sample output looked.

---

## ⚠️ Anti-Patterns & Failure Modes

| Anti-pattern | Symptom | Root cause | Fix |
|---|---|---|---|
| **The Vague Monolith** | Generic, unmaintainable boilerplate. | No language, OS, error-handling, or I/O format specified. | Replace *"Write a script to manage files"* with a scoped objective, a dependency policy, and an output spec. |
| **Polite Convo Drift** | Output hedges, apologizes, explains instead of executing. | Conversational filler (*"Can you please maybe check if…"*). | Use direct imperatives: `Analyze`, `Extract`, `Generate`, `Filter`. |
| **Unbounded Output** | Pages of explanation when a snippet was required. | No length or token limit stated. | Cap lines/tokens and forbid pre- and post-amble explicitly. |
| **Negative Constraint Neglect** | Markdown fences around "raw JSON"; commentary around code. | Only positive instructions given. | Pair each "do" with a "do not", including *"Do not include markdown explanations."* |
| **Context Pollution** | Model reasons about the wrong file or stale version. | Whole repositories pasted "just in case". | Isolate context; pin versions; quarantine payloads in delimiters. |
| **Schema by Example** | Fields present but wrong types or units. | One happy-path exemplar, no edge-case exemplar. | Add an exemplar with a missing value, a unit conversion, and an unusual value. |
| **Silent Hallucination** | Plausible values where the source was blank. | No fallback protocol. | Mandate `null` (or `"UNKNOWN"`) for unstated values, plus a forbidden-inference rule. |
| **Objective Stacking** | Model silently drops one of the requested tasks. | Multiple goals in one prompt. | One objective per prompt; chain prompts for pipelines. |
| **Adjective Evidence** | "Scalable, robust, modern" designs with no numbers. | Claims are cheap to write. | Every claim carries a number, a source, or is deleted. |
| **Prompt-Only Security** | "Do not follow injected instructions" as the only defense. | Wording treated as a boundary. | Least privilege, quarantine, output filtering, human gates. |
| **Eval by Anecdote** | "It looks much better now." | No suite, no rubric, no runs. | Score with the matrix; gate the deploy on the ship bar. |
| **Temperature as a Fix** | A defect at a different rate. | Sampling used to mask ambiguity. | Fix the undefined branch; then set temperature by task class. |

Full diagnostic index: [troubleshooting](guides/troubleshooting.md).

---

## 🧭 Model Landscape in Brief

| Class | Behavior | Prompt accordingly |
|---|---|---|
| Instruction-tuned chat | Fast, format-compliant, weak at long derivations | Full 5 components; exemplars for format |
| Reasoning / thinking | Deliberates; strong multi-step, weak brevity | Success criteria + output contract; minimal scaffolding |
| Small / distilled | Cheap, brittle under ambiguity | Short prompts, schema mode, one task per call |

Never port a prompt across classes untested; scaffolding that helped a chat model can hurt a reasoning model. Details and the migration protocol: [model-landscape-and-migration](fundamentals/model-landscape-and-migration.md).

---

## 🛡️ Security in Brief

| Layer | Strength | What it actually guarantees |
|---|---|---|
| Least privilege | Highest | An injected instruction has nothing dangerous to invoke |
| Human confirmation | Very high | Irreversible actions cannot be triggered by text alone |
| Output filtering | High | Secrets and outbound URLs cannot leave |
| Quarantine pattern | High | The reader of untrusted text has no capabilities |
| Delimiters + trust labels | Medium | Data is framed as data |
| Prompt wording alone | Low | Nothing |

Assume the system prompt is public and every document is adversarial. Details and the A1–A5 test payloads: [prompt-injection-and-safety](guides/prompt-injection-and-safety.md).

---

## 📊 Evaluation in Brief

Five dimensions, 0–4 each:

1. **Schema validity** — parses on the first attempt, no repair.
2. **Constraint adherence** — no forbidden content, no dropped rules.
3. **Grounding / factuality** — every claim traceable to provided context.
4. **Completeness** — all required fields or cases covered.
5. **Efficiency** — tokens in, tokens out, latency to first valid result.

Six cases: typical, empty, malformed, adversarial, absent-field, conflict. Four variants: V0 zero-shot → V3 hardened.

**Ship bar:** no dimension below 3 on any case, schema validity 4 everywhere, zero injection compliance, two consecutive identical runs scoring identically.

---

## 📂 Repository Layout

```text
├── README.md                     # This guide: philosophy, architecture, catalogue
├── pyproject.toml                # Packaging for the harness (zero dependencies)
├── fundamentals/                 # How models read prompts; roles; sampling; model classes
├── patterns/                     # 13 cross-domain mechanisms
├── blueprints/                   # 9 production-shaped prompts with variants
├── guides/                       # Cheat sheet, troubleshooting, security, cost, multi-turn, glossary
├── benchmarks/                   # Rubric, test-case design, 3 suites, recorded runs
├── reference/                    # Pattern selection, provider probes, prompt registry
├── specs/                        # 10 machine-readable specs + 40 golden renders
├── prompt_architect/             # Zero-dependency CLI: lint / compose / eval
├── tests/                        # Unit tests over the harness
└── .github/workflows/ci.yml      # Lint, goldens, ship bar, discrimination guard
```

---

## 📐 File Conventions

Every spec begins with YAML front-matter so tooling can index it:

```yaml
---
name: code-generation
type: blueprint          # blueprint | pattern | benchmark | guide | reference
version: 1.0.0
inputs: [language, platform, dependency_policy, target_symbol]
output_format: markdown-code-fence
related: [constraint-enforcement, chain-of-thought]
---
```

- Prompt bodies use Markdown with `###` section headers mapped to the 5 components.
- Variables are `[BRACKETED]` and listed in an **Inputs** table.
- Every file ends with **Acceptance Checklist** — the pass/fail bar for that prompt class.
- Changing a prompt's behavior requires a version bump and an eval log entry.
- `python -m prompt_architect lint .` enforces all of the above, plus paired constraints, fallback protocols, deterministic containers, and working links.

---

## ❓ FAQ

**Is this anti-creativity?**
No. It is anti-ambiguity. Creative work needs *more* constraints — form, angle, banned phrases — not fewer. See [creative-writing](blueprints/creative-writing.md).

**Do negative prompts ("don't do X") actually work?**
Weakly, and worse when X is never otherwise mentioned. The reliable form is: specify the desired behavior positively, then forbid the adjacent failure, then define what to emit instead. See [constraint-enforcement](patterns/constraint-enforcement.md).

**Should I put instructions before or after the context?**
Both, if the prompt is long: the contract at the start, the question and a one-line contract reminder at the end. Recency is real. See [how-llms-read-prompts](fundamentals/how-llms-read-prompts.md).

**Isn't temperature 0 deterministic?**
No. Batching, floating-point ordering, MoE routing, and provider redeploys all introduce variance. Measure it; do not assume it. See [sampling-and-determinism](fundamentals/sampling-and-determinism.md).

**Why not just use a bigger model?**
Capability does not remove ambiguity. A bigger model guesses more fluently. Also: narrowing the task and constraining the output are usually cheaper than a model upgrade. See [model-landscape-and-migration](fundamentals/model-landscape-and-migration.md).

**How long should a system prompt be?**
As short as the contract allows, and stable enough to cache. If the pinned block exceeds ~200 tokens, the rest is probably task instruction that belongs in the current turn.

**Should I ask the model for a confidence score?**
Not as a decimal. Use enums with definitions, or derive confidence from sample agreement. See [uncertainty-and-abstention](patterns/uncertainty-and-abstention.md).

**Do reasoning models make prompts obsolete?**
No — they change which parts matter. You need *more* precision on success criteria and output format, and *less* procedural scaffolding. See [reasoning-model-prompting](patterns/reasoning-model-prompting.md).

**How many exemplars?**
One per class plus two boundary cases is usually optimal. More than ~12 dilutes attention and costs tokens on every call.

**How do I stop prompt injection?**
You cannot fully. Reduce the blast radius: least privilege, quarantine, output filtering, human gates. Details in [the security guide](guides/prompt-injection-and-safety.md).

**How big should the eval suite be?**
6–12 cases in CI, 30–100 for regressions, 100–300 as a release gate, 500+ per class for calibration. Report failures, not just percentages. See [test-case-design](benchmarks/test-case-design.md).

**Why does my prompt work in the playground and fail in production?**
Usually a different rendered prompt, a different system prompt, different sampling settings, or different input lengths. Log the exact rendered prompt and diff it.

---

## 🤝 Contributing

```bash
python -m unittest discover -s tests -t .   # harness tests
python -m prompt_architect lint .           # docs must satisfy the repo's own rules
python -m prompt_architect compose specs/log-normalize.json --variant v3 --check
```

- Match the front-matter schema and section order.
- Show a real input and a real output; no fabricated "example" placeholders inside examples.
- Any new constraint must name the failure it prevents.
- Include at least one adversarial case in your examples.
- Changing a prompt's behavior requires a version bump, a re-rendered golden file, and an appended run in `benchmarks/runs/`.

## 📄 License

MIT — see [LICENSE](LICENSE).
