# ⚡ Prompt Architect

> A deterministic, systems-oriented framework for engineering high-performance prompts to control LLM outputs, minimize hallucinations, and execute complex technical and creative workflows.

Prompts are not conversation. They are **API contracts** against a probabilistic execution engine. This repository is the contract library: a philosophy, a fixed component architecture, reusable patterns, domain blueprints, and an evaluation matrix for proving that an engineered prompt beats a zero-shot request.

---

## 📑 Table of Contents

- [Who This Is For](#-who-this-is-for)
- [Core Philosophy](#-core-philosophy)
- [The 5-Component Prompt Architecture](#️-the-5-component-prompt-architecture)
- [Prompt Engineering Patterns](#-prompt-engineering-patterns)
- [Task-Specific Blueprints](#-task-specific-blueprints)
- [The Harness](#-the-harness)
- [The Architect Loop](#-the-architect-loop)
- [Anti-Patterns & Failure Modes](#-anti-patterns--failure-modes)
- [Repository Layout](#-repository-layout)
- [File Conventions](#-file-conventions)
- [Evaluation Discipline](#-evaluation-discipline)
- [Contributing](#-contributing)

---

## 🎯 Who This Is For

Anyone who needs **repeatable** model behavior rather than impressive one-off demos: engineers shipping LLM features, agents driving tool calls, data teams parsing unstructured input into schemas, and technical writers producing structured documentation at scale.

If a wrong output costs you money, downtime, or a human review cycle, treat the prompt like production code — version it, test it, and constrain it.

---

## 🧠 Core Philosophy

Treat prompts as **programmatic interfaces**, not casual conversation. An LLM is a probabilistic execution engine; your prompt is the API contract. To achieve deterministic and repeatable results:

1. **Explicit Constraint Enforcement** — Define hard boundaries (what *not* to do) with equal weight to instructions (what to do).
2. **Context Isolation** — Provide only the necessary state, dependencies, and environment variables required for the specific task.
3. **Structural Determinism** — Dictate exact output schemas (JSON, Markdown tables, strict AST formats) to allow downstream parsing.

Three practical corollaries follow from these principles:

| Principle | Corollary | Failure it prevents |
|---|---|---|
| Constraint Enforcement | Every positive instruction earns a paired negative one. | Model "helpfully" adds prose around your JSON. |
| Context Isolation | Irrelevant context is a bug, not a bonus. | Model anchors on the wrong file, version, or example. |
| Structural Determinism | If a parser consumes it, the prompt must specify the bytes. | Downstream `JSON.parse` throws on a fenced block. |

**The governing rule:** *an instruction the model can interpret is an instruction it will eventually interpret differently.* Ambiguity is a defect, not a style choice.

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

### Field Notes Per Component

**1. Role** — One sentence. The role narrows the distribution of plausible answers; it is not a costume. *"You are a senior SRE"* changes what the model considers relevant. *"You are a helpful genius who is also a poet and a lawyer"* averages three distributions into mush. Never use the role to smuggle in the objective.

**2. Context** — Version-pin everything that could drift: language/runtime, OS, dependency policy, data source, audience, prior decisions. Delimit untrusted payloads with explicit tags (`<log_payload>…</log_payload>`) so the model cannot confuse data with instructions. If a fact is unknown, say it is unknown — do not omit it and hope.

**3. Objective** — Exactly one imperative verb: `Extract`, `Refactor`, `Classify`, `Generate`, `Audit`. Two objectives is two prompts. If you genuinely need a pipeline, sequence it explicitly (see [Chain-of-Thought](patterns/chain-of-thought.md)) rather than stacking goals in one sentence.

**4. Constraints** — The highest-leverage component and the one most often skipped. Write them as testable assertions, not preferences. *"Be concise"* is untestable; *"No prose before or after the code block; maximum 400 lines"* is a test.

**5. Output Specification** — Specify the container (fence language, raw text, table), the shape (schema keys, ordering, types), the units (MB, ISO 8601, UTC), and the empty case (`null`, `[]`, `"UNKNOWN"`). Anything a parser touches must be pinned.

### Minimal Skeleton

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

---

## 🧩 Prompt Engineering Patterns

Patterns are cross-domain mechanisms. Blueprints compose them.

| Pattern | Mechanism | Use when | Reference |
|---|---|---|---|
| **Chain-of-Thought with Verification** | Enforce ordered intermediate reasoning, then a self-check pass, then the answer. | Multi-step logic, debugging, architecture trade-offs, anything where a wrong first hop poisons the answer. | [patterns/chain-of-thought.md](patterns/chain-of-thought.md) |
| **Few-Shot Calibration** | Supply input→output exemplars that demonstrate edge cases, not just easy cases. | Formatting drifts, zero-shot style is wrong, or the schema has subtle conventions. | [patterns/few-shot-calibration.md](patterns/few-shot-calibration.md) |
| **Deterministic Constraint Enforcement** | Positive/negative symmetry, boundary delimiters, explicit fallback protocols. | Output feeds a parser, a test suite, or another agent. | [patterns/constraint-enforcement.md](patterns/constraint-enforcement.md) |

### Quick Sample — Chain-of-Thought with Verification

```markdown
Analyze the provided codebase for race conditions using the following protocol:
1. Identify all shared mutable state across async threads.
2. Trace execution paths where lock contention or deadlock can occur.
3. Propose atomic alternatives using standard synchronization primitives.
4. Output the final patched code block.
```

### Quick Sample — Few-Shot Calibration

```markdown
Transform raw log entries into structured JSON objects matching this exact schema.

Example 1:
Input: [2026-11-07T14:32:01] [ERROR] [AuthModule] Failed token validation for user_id=4092
Output: {"timestamp": "2026-11-07T14:32:01", "level": "ERROR", "module": "AuthModule", "message": "Failed token validation", "meta": {"user_id": 4092}}

[Target Input to Process...]
```

---

## 🛠️ Task-Specific Blueprints

Blueprints are fill-in-the-blank, production-shaped prompts. Replace bracketed variables; leave the structure intact.

| Blueprint | Purpose | File |
|---|---|---|
| **A — Code Generation & Refactoring** | High-precision, memory-safe implementation and refactoring with dependency and signature freezes. | [blueprints/code-generation.md](blueprints/code-generation.md) |
| **B — Data Extraction & Normalization** | Unstructured documents → strict, normalized JSON with an explicit null policy. | [blueprints/data-extraction.md](blueprints/data-extraction.md) |
| **C — System Architecture** | Technical design specs with mandatory trade-off analysis and rejected alternatives. | [blueprints/system-architecture.md](blueprints/system-architecture.md) |

Each blueprint ships with its variable table, a filled worked example, failure modes, and an acceptance checklist.

---

## 🧰 The Harness

The framework ships as a zero-dependency Python package, so the rules above are executable rather than aspirational.

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

### The spec and the variant ladder

A spec is the machine-readable form of a blueprint (`specs/log-normalize.json`): role, context, objective, must/must-not constraints, fallback table, exemplars, and the output container. `compose` renders it at four levels:

| Variant | Adds | Purpose |
|---|---|---|
| `v0` | — | The zero-shot baseline you are trying to beat |
| `v1` | 5 components, positive rules | Structured, but nothing forbidden and nothing specified for the unknown |
| `v2` | negative rules + exemplars | Patterned: fences disappear, the null policy lands |
| `v3` | fallback protocol, payload guard, precedence, byte-level container | Hardened: the version that passes the ship bar |

Exactly one class of enforcement changes per step, which is what makes a score movement attributable to a layer instead of to luck.

### Offline by design

`eval` never calls a model. You record raw outputs once — with whatever client you use — and commit the run file; CI re-grades it deterministically. See [benchmarks/runs/README.md](benchmarks/runs/README.md) for the record format and the provenance of the committed fixtures.

## 🔁 The Architect Loop

Do not write a prompt once. Run it like a build pipeline:

1. **Specify** — Draft the 5 components. Write the output specification *first*, then work backwards to the constraints that make that output possible.
2. **Constrain** — For every instruction, add its inverse. Add the fallback for missing data. Tag the payload.
3. **Calibrate** — Run against 3–5 adversarial inputs, including an empty input and a malformed one.
4. **Score** — Grade with the rubric in [benchmarks/evaluation-matrix.md](benchmarks/evaluation-matrix.md): schema validity, constraint adherence, factuality, verbosity.
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

---

## 📂 Repository Layout

```text
├── README.md                     # Master philosophy and architecture guide
├── pyproject.toml                # Packaging for the harness (no dependencies)
├── prompt_architect/             # Zero-dependency CLI: lint / compose / eval
│   ├── cli.py                    # Command surface and exit codes
│   ├── spec.py                   # 5-component composition, v0-v3 ladder
│   ├── lint.py                   # PA001-PA010 conformance rules
│   ├── evaluate.py               # T1-T6 grading, rubric, ship bar
│   └── frontmatter.py            # Minimal YAML front-matter reader
├── specs/                        # Machine-readable prompt specs
│   ├── log-normalize.json        # The worked example, as data
│   └── golden/                   # Committed renders; --check detects drift
├── blueprints/                   # Domain-specific templates
│   ├── code-generation.md        # Code refactoring & implementation blueprints
│   ├── data-extraction.md        # Schema normalization & parsing blueprints
│   └── system-architecture.md    # Technical design specs
├── patterns/                     # Advanced prompt engineering design patterns
│   ├── chain-of-thought.md       # Step-by-step reasoning workflows
│   ├── few-shot-calibration.md   # In-context learning examples
│   └── constraint-enforcement.md # Multi-layered negative & positive constraints
├── benchmarks/                   # Test suites and output validation logs
│   ├── evaluation-matrix.md      # Zero-shot vs. engineered prompt comparison
│   ├── suites/log-normalize.json # T1-T6 fixtures and expectations
│   └── runs/                     # Recorded outputs, one file per run
├── tests/                        # 62 unit tests over the harness
└── .github/workflows/ci.yml      # Lint, goldens, ship bar, discrimination guard
```

---

## 📐 File Conventions

Every blueprint and pattern begins with YAML front-matter so tooling can index it:

```yaml
---
name: code-generation
type: blueprint          # blueprint | pattern | benchmark
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

---

## 📊 Evaluation Discipline

Prompts are compared, not admired. The matrix in [benchmarks/evaluation-matrix.md](benchmarks/evaluation-matrix.md) scores zero-shot, pattern-augmented, and fully engineered variants across five dimensions:

1. **Schema validity** — parses on the first attempt, no repair.
2. **Constraint adherence** — no forbidden content, no dropped rules.
3. **Factuality / grounding** — every claim traceable to provided context.
4. **Completeness** — all required fields or cases covered.
5. **Efficiency** — tokens in, tokens out, latency to first valid result.

Scoring is 0–4 per dimension (see rubric), with results logged per model and date, because prompts regress across model versions.

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
