---
name: code-generation
type: blueprint
version: 1.0.0
inputs: [language, stack, platform, dependency_policy, target_symbol, functional_goal, error_policy]
output_format: markdown-code-fence
related: [chain-of-thought, constraint-enforcement]
---

# 🛠️ Blueprint A — High-Precision Code Generation & Refactoring

Use for implementation, refactoring, and targeted repair where the code must **compile, keep its API, and avoid dependency creep**. For design work above the file level, use [Blueprint C](system-architecture.md).

---

## Inputs

| Variable | Required | Example | Notes |
|---|---|---|---|
| `LANGUAGE/STACK` | ✅ | Rust 1.75, Go 1.22, TypeScript 5.4 | Pin the version; unpinned means "the average of the training set". |
| `PLATFORM` | ✅ | Windows 11 x64, Linux arm64, browser | Drives syscall, path, and threading choices. |
| `DEPENDENCY_POLICY` | ✅ | `None` / allowlist | An empty policy is not a policy. Write `None` explicitly. |
| `TARGET` | ✅ | file, function, struct, module | Narrow the blast radius. |
| `GOAL` | ✅ | eliminate lock contention, cut allocations | State the measurable outcome. |
| `ERROR_POLICY` | ✅ | `Result<E>`, exceptions, panics | Determines every signature the model writes. |
| `ALLOWED_CHANGES` | ⬜ | public API frozen / private only | Default to frozen. |
| `TESTS` | ⬜ | must include unit tests | Otherwise the model ships untested code. |

---

## The Blueprint

```markdown
### Role
Expert software engineering agent specializing in high-performance, memory-safe [LANGUAGE/STACK] applications.

### Context
- **Target Platform:** [e.g., Windows 11 x64 / Cross-platform]
- **Architecture Constraints:** [e.g., Zero external crate dependencies, single binary, low memory footprint]
- **Existing Codebase State:** [Briefly describe the target module, struct, or function being modified]

### Objective
[Clear, imperative action verb] the target code to [state the exact functional goal, e.g., eliminate async lock contention and reduce memory allocations].

### Constraints & Negative Rules
- DO NOT introduce third-party dependencies unless explicitly listed: [Allowed List / "None"].
- DO NOT modify public function signatures or break existing trait implementations.
- DO NOT include conversational filler, introductory remarks, or post-code explanations.
- Handle all edge cases, potential panics, and error propagation explicitly using [e.g., Result/Option types].

### Output Specification
Provide the complete, compiling code block enclosed in a single ```[language] markdown fence. Include concise inline comments explaining algorithmic optimizations or trade-offs directly within the code.
```

---

## Filled Example — Async Buffering Loop

```markdown
### Role
Expert Rust engineer specializing in async I/O and memory-safe systems programming.

### Context
- **Target Platform:** Linux x86_64, Rust 1.75, tokio 1.36 (already a dependency), edition 2021.
- **Architecture Constraints:** Existing dependency manifest must not change; no `unsafe`;
  crate is a library and public API is frozen.
- **Existing Codebase State:** `src/reader.rs` contains `BufferedReader::read_chunk`, which
  acquires `Mutex<BufWriter>` per chunk and clones the payload into a `Vec<u8>`. The hot path
  allocates once per chunk and holds the lock across `.await`, serializing all readers.

### Objective
Refactor `BufferedReader::read_chunk` to eliminate the lock held across the await point and
remove per-chunk allocation, without changing public signatures.

### Constraints & Negative Rules
- DO NOT add dependencies; `tokio` and `bytes` are already available and are the only ones allowed.
- DO NOT modify public function signatures, trait impls, or error types.
- DO NOT use `unsafe`, `std::mem::transmute`, or `Arc<Mutex<_>>` as a workaround.
- DO NOT hold any lock across an `.await`.
- DO NOT include introductory remarks, prose, or post-code explanations.
- Handle partial reads, `ErrorKind::Interrupted`, and closed connections explicitly using `Result`.

### Output Specification
The complete contents of `src/reader.rs` inside a single ```rust fence, with a comment
above each changed block naming the hazard or allocation it removes. No elisions
(`// ... unchanged`) — output the whole file. Nothing before or after the fence.
```

---

## Variant A1 — Targeted Bug Repair

Use when the failure is known and reproducible. The fix must be minimal.

```markdown
### Role
Debugging engineer. You change the smallest number of lines that removes the defect.

### Context
- **Symptom:** [observable failure, exact error text]
- **Reproduction:** <repro>[minimal failing input or test]</repro>
- **Environment:** [runtime, versions, platform]
- **Suspect region:** <code>[file and function]</code>

### Objective
Repair the defect in the suspect region so the reproduction passes.

### Constraints & Negative Rules
- DO NOT refactor, rename, reformat, or modernize code outside the defect.
- DO NOT change behavior for any input that currently succeeds.
- DO NOT suppress the error (no catch-all handlers, no `unwrap_or_default`, no retry loops).
- DO NOT guess at the root cause; if the reproduction does not explain the symptom,
  respond `{"status": "root_cause_unconfirmed", "hypotheses": [...]}` and stop.

### Output Specification
1. A ```diff fence with the minimal patch.
2. A ```[language] fence containing a regression test that fails before and passes after.
3. Nothing else.
```

---

## Variant A2 — Test Generation

```markdown
### Role
Test engineer. You write tests that would catch real regressions, not tests that pass.

### Context
- **Unit under test:** <code>[file, symbols, signatures]</code>
- **Framework:** [framework + version]
- **Known past defects:** [list — these are mandatory test cases]

### Objective
Generate a test suite for the unit under test.

### Constraints & Negative Rules
- DO NOT test private helpers directly; test through the public surface.
- DO NOT assert on implementation details (call counts, log strings) unless the contract requires it.
- DO NOT write tests that cannot fail (no `assert!(true)`, no swallowing of panics).
- DO NOT use network, filesystem, or wall-clock time without an injected seam.
- Every test name must state the behavior and the failure it prevents.

### Output Specification
One ```[language] fence with the complete test module. No prose, no example usage,
no explanation of how to run the tests.
```

---

## Failure Modes Specific to Code Prompts

| Failure | Cause | Blueprint fix |
|---|---|---|
| Hallucinated APIs / methods that don't exist | Unpinned version, no context file | Pin version; paste the target's actual imports and type signatures |
| Silent dependency addition | No policy stated | `DEPENDENCY_POLICY` line with allowlist or `None` |
| Broken public API | No freeze rule | Explicit signature-freeze constraint |
| Lock held across `.await` | Model optimizes locally | Name the hazard in the negative rules |
| Elided code (`// ... unchanged`) in a refactor | Token pressure | "Output the whole file; no elisions" |
| Tests that assert nothing | Objective omitted the assertion | "Tests that would catch a regression" + forbidden shapes |
| Panics on edge cases | No error policy | `ERROR_POLICY` variable in the inputs table |
| Unrequested refactor | Objective too broad | Scope to a named symbol, forbid out-of-scope changes |

---

## Acceptance Checklist

- [ ] Language, runtime version, and platform are pinned.
- [ ] Dependency policy is explicit (`None` counts).
- [ ] Public API freeze is stated when the code is shared.
- [ ] Error-handling style is named, not implied.
- [ ] Output is a complete file or minimal diff — pick one and forbid the other.
- [ ] Elisions, prose, and fences-around-fences are forbidden.
- [ ] The prompt has been run against a file where **no change is needed**, and the model reports that instead of inventing work.
- [ ] Generated code compiles in CI, and generated tests fail when the fix is reverted.
