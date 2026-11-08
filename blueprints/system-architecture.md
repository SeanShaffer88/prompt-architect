---
name: system-architecture
type: blueprint
version: 1.0.0
inputs: [system_scope, scale_targets, hard_constraints, existing_stack, non_functional_requirements]
output_format: markdown-spec
related: [chain-of-thought, constraint-enforcement]
---

# 🏛️ Blueprint C — System Architecture & Technical Design

Use for design documents: service boundaries, data models, migration plans, build-vs-buy decisions. Design prompts fail differently from code prompts — not with broken syntax, but with **confident, unexamined defaults**: the generic microservice diagram, the cache nobody justified, the "just use Postgres" that ignores the 50 TB archive.

The countermeasure is structural: force alternatives, force numbers, force the rejected option to be argued.

---

## Inputs

| Variable | Required | Example | Notes |
|---|---|---|---|
| `SCOPE` | ✅ | billing pipeline, not "the platform" | Unscoped design prompts produce diagram-shaped fiction. |
| `SCALE` | ✅ | 2k rps peak, 50 TB/yr, 20 ms p99 | Numbers force real trade-offs. |
| `HARD_CONSTRAINTS` | ✅ | existing Kafka, SOC2, single region | These are what make the answer *yours*. |
| `STACK` | ✅ | Go services, Postgres 16, K8s | Models default to whatever is popular. |
| `NFRs` | ✅ | durability, cost ceiling, team size | Include the boring ones: on-call load, hireability. |
| `EXPLICIT_NON_GOALS` | ⬜ | no multi-region yet | Prevents scope inflation. |

---

## The Blueprint

```markdown
### Role
Principal engineer writing an internal design document for a review board.
You optimize for operability and total cost of ownership, not novelty.

### Context
- **Scope:** [the one system being designed]
- **Scale targets:** [rps, data volume, growth per year, latency budget]
- **Existing stack:** [languages, datastores, queueing, deployment platform]
- **Hard constraints:** [compliance, regions, contracts, budget, team size]
- **Non-goals:** [what this design explicitly does not solve]

### Objective
Produce a decision-ready technical design for [scope] that meets the stated
scale and constraints, including the alternatives that were rejected.

### Procedure
1. Restate the constraints that actually bind the design (≤5). Name the single
   hardest one.
2. Enumerate 3 candidate architectures. For each: data flow, storage choice,
   failure behavior, and incremental cost at the stated scale.
3. Compare them on the axes below, with numbers — not adjectives:
   latency at p50/p99, cost per month at target volume, operational surface,
   migration risk, blast radius of the most likely failure.
4. Recommend one. State the conditions under which the recommendation is wrong.
5. Detail the recommendation: components, interfaces, data model, failure and
   recovery paths, rollout plan.
6. List the first three things that will break at 10× current scale.

### Constraints & Negative Rules
- DO NOT propose technology outside the existing stack unless you state the
  migration cost and the reason the stack cannot meet the requirement.
- DO NOT use adjectives as evidence ("scalable", "robust", "modern") — attach a
  number or delete the claim.
- DO NOT omit rejected alternatives or present one strawman.
- DO NOT design for more than 10× the stated scale.
- DO NOT hand-wave consistency, durability, or ordering; name the guarantee and
  where it is enforced.
- DO NOT include pricing you cannot attribute to a unit assumption.
- If the constraints are mutually unsatisfiable, say which pair conflicts and
  stop rather than resolving it silently.

### Output Specification
Markdown with these sections, in this order, and no others:
1. Constraint Summary
2. Candidates (3, one subsection each)
3. Comparison Table
4. Recommendation & Validity Conditions
5. Detailed Design (components, interfaces, data model, failure modes, rollout)
6. Risks at 10× Scale
No preamble, no "Introduction", no closing summary.
```

---

## Filled Fragment — Comparison Table

The table is where design prompts either become useful or become prose. Demand these columns:

| Axis | Candidate A: Postgres + outbox | Candidate B: Kafka + Flink | Candidate C: Batch ETL |
|---|---|---|---|
| Ingest latency p99 | 40 ms (measured in staging) | 120 ms end-to-end | 15 min |
| Cost @ 2k rps | $1.9k/mo (1 primary, 1 replica, 2 TB) | $6.4k/mo (3 brokers, 6 tasks) | $800/mo, but 15 min staleness |
| Operational surface | 1 datastore, existing runbooks | New cluster + job orchestration | Cron + warehouse; SLO unclear |
| Migration risk | Low — same stack | High — new platform, new skills | Medium — new ownership boundary |
| Worst plausible failure | Replica lag hides a bad write | Consumer lag silently grows; no alert | Partial day reprocessed twice |

Numbers, a named failure, and a cost basis. Adjectives are absent.

---

## Variant C1 — Migration Plan

Architecture prompts often really mean "how do we get there without an outage".

```markdown
### Role
Staff engineer responsible for a zero-downtime migration.

### Context
- **From:** [current system, row counts, traffic profile]
- **To:** [target system]
- **Constraint:** no read or write downtime; rollback available for 14 days.
- **Data:** [schema volume, known dirty-data classes]

### Objective
Produce a phased migration plan from [current] to [target] with a rollback path
at every phase.

### Constraints & Negative Rules
- DO NOT propose a big-bang cutover.
- DO NOT propose dual writes without naming the conflict-resolution rule.
- DO NOT skip the reconciliation step; state how divergence is measured and
  what threshold halts the migration.
- DO NOT assume the target schema can absorb existing dirty data — name the
  quarantine path.

### Output Specification
Markdown table with columns: Phase | Action | Reversible? | Rollback Command | Exit Criteria | Blast Radius.
Followed by a "Known Unknowns" list. Nothing else.
```

---

## Variant C2 — Build vs. Buy

```markdown
### Role
Engineering manager writing a decision memo with a cost model.

### Context
- **Need:** [capability], required within [timeline]
- **Volume:** [requests/mo, GB/mo, seats]
- **Team:** [headcount, existing skills, on-call capacity]

### Objective
Recommend build or buy, with a 3-year total cost of ownership comparison.

### Constraints
- Include engineering time at the blended hourly rate of [rate].
- Include the maintenance tail: who pages at 3 a.m., and what it costs.
- DO NOT compare a vendor's sticker price to a build's infrastructure cost only.
- DO NOT recommend build without naming the opportunity cost.

### Output Specification
1. Assumptions table (every number with its source).
2. 3-year TCO table (build vs. buy, per year, with totals).
3. Recommendation, one paragraph, with the assumption that would flip it.
```

---

## Failure Modes

| Failure | Symptom | Fix |
|---|---|---|
| Generic architecture | Diagram could belong to any company | Hard constraints + stack pinning |
| Adjective evidence | "highly scalable, robust" | Numeric comparison axes |
| Single option | One design, no alternatives | Mandatory 3 candidates + rejection reasons |
| Strawman alternatives | Candidate B is obviously absurd | "Do not present one strawman" |
| Infinite scale | Designs for 1000× | Cap at 10× |
| Hidden consistency assumption | "eventually consistent is fine here" | Name the guarantee and its enforcement point |
| Cost fiction | Rounding invented pricing | "No pricing you cannot attribute to a unit assumption" |
| No failure story | Nothing in the design can break | Comparative failure modes + 10× risks section |
| Section sprawl | 12 sections, no decision | Closed section list, no additions |

---

## Acceptance Checklist

- [ ] Scope is one system, not a platform.
- [ ] Scale targets are numeric and include growth.
- [ ] At least three candidates, with the rejected ones argued fairly.
- [ ] Comparison uses numbers and named failure modes, not adjectives.
- [ ] Recommendation includes the conditions that would invalidate it.
- [ ] Consistency/durability/ordering guarantees are named explicitly.
- [ ] Model returns the conflict instead of resolving unsatisfiable constraints on its own.
- [ ] Reviewed by a human who can point at every number's source.
