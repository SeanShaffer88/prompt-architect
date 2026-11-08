---
name: prompt-registry
type: reference
version: 1.0.0
output_format: markdown
related: [evaluation-matrix, model-landscape-and-migration, prompt-chaining-and-routing]
---

# 🗂️ The Prompt Registry

Prompts rot silently. Nobody notices that a prompt still targets a model that was
deprecated, or that its owner left, or that its suite stopped discriminating — until
it fails in production.

A registry is a table with a review date attached. If your prompts live in code,
this is the metadata that must live beside them (a `PROMPT.md`, a database row, or
a section in the service readme).

---

## 1. What to record

| Field | Why it exists | Example |
|---|---|---|
| `id` | Stable handle across versions | `support-triage` |
| `version` | Semver; changes on behavior change | `1.3.0` |
| `owner` | One person, not a team | `@dana` |
| `purpose` | One sentence, one objective | "Route tickets into five labels" |
| `model` | Exact id + date | `[model]@2026-11-02` |
| `settings` | Temperature, budgets, tool set | `T=0, max_tokens=300` |
| `suite` | Where the eval lives | `benchmarks/suites/classification-routing.json` |
| `last_eval` | Date + result | `2026-11-08, ship bar PASS` |
| `surface` | Where it runs | `POST /triage`, batch job |
| `consumers` | What parses the output | `routing service`, `dashboard` |
| `status` | Lifecycle state | `active` |
| `review_by` | Next scheduled review | `2027-02-01` |

Minimum viable registry: `id`, `version`, `owner`, `model`, `suite`, `last_eval`, `status`.
Everything else is a function of how much it costs you when it breaks.

---

## 2. Lifecycle states

| State | Meaning | Allowed transitions |
|---|---|---|
| `draft` | Being written; no suite yet | → `candidate` |
| `candidate` | Has a suite; running against real traffic samples | → `active`, → `retired` |
| `active` | In production; gated by the ship bar | → `deprecated`, → `candidate` (rework) |
| `deprecated` | Still serving, being replaced; no new features | → `retired` |
| `retired` | Not called; kept for history | — |

A prompt in `active` without a passing `last_eval` is a lie in a table. Either
re-run it or move it to `candidate`.

---

## 3. A worked row

```markdown
| id | ver | owner | purpose | model | settings | suite | last_eval | status | review_by |
|---|---|---|---|---|---|---|---|---|---|
| support-triage | 1.3.0 | @dana | Route tickets into 5 labels | [model]@2026-11-02 | T=0, max=300 | classification-routing | 2026-11-08 PASS | active | 2027-02-01 |
```

Read that row cold and you can answer: what it does, who owns it, what it runs
on, how it was tested, when it was last tested, and when it must be looked at
again. That is the whole point.

---

## 4. Change protocol

| Change | Version bump | Required artifacts |
|---|---|---|
| Wording that changes behavior | minor | New goldens, appended run |
| Output schema change | **major** | Consumer migration plan, new suite cases |
| Model or provider change | minor | New baseline run, new registry row |
| Constraint addition | patch/minor | Goldens + run |
| Comment/format only | none | Goldens (`--check` proves it) |

Do not ship a behavior change without a version bump and an appended run: the
registry is the only record of what ran when. A change without a bump is an
untracked regression, regardless of how small the diff looks.

---

## 5. Review cadence

| Trigger | Action |
|---|---|
| Model upgrade or deprecation notice | Re-run suite; re-baseline; update `model` |
| New failure in production | Promote it to a regression case; bump patch |
| Suite stops discriminating (V0 passes) | Tighten the suite before trusting any score |
| Quarterly | Review `active` prompts: traffic, cost, failures, ownership |
| Owner change | Reassign `owner`; the prompt is not "the team's" |
| Customer-visible incident | Post-mortem entry naming the prompt version |

---

## 6. Anti-patterns

| Anti-pattern | Consequence |
|---|---|
| Registry in someone's notes | It does not exist |
| Team-level ownership | Nobody updates it |
| "Latest" as a version | You cannot say what ran last Tuesday |
| Suite path that no longer exists | The gate silently stops gating |
| Eval dates older than the model | You measured a different system |
| Prompt edited in production console | The repo and reality diverge |
| No deprecation state | Old prompts serve traffic forever |

---

## Acceptance Checklist

- [ ] Every production prompt has a registry row with the seven minimum fields.
- [ ] `model` includes an exact id and date, and is refreshed after upgrades.
- [ ] `suite` points at a file that exists and runs in CI.
- [ ] `last_eval` is newer than the last model or prompt change.
- [ ] Behavior changes are version-bumped, with goldens and a run appended.
- [ ] Owners are individuals, and review dates are real dates.
- [ ] Retired prompts are marked retired rather than deleted, so history survives.
