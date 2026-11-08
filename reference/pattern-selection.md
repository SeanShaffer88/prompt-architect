---
name: pattern-selection
type: reference
version: 1.0.0
output_format: markdown
related: [cheat-sheet, task-decomposition, classification-routing]
---

# 🧭 Pattern & Blueprint Selection

A decision table from *situation* to *starting point*. Read the symptom, take the row, open the file. Do not read the library front to back looking for a fit.

---

## 1. Start from the task

| If the task is… | Start with | Then add |
|---|---|---|
| Turn documents into records | [data-extraction](../blueprints/data-extraction.md) | [structured-output](../patterns/structured-output.md) |
| Pick one label per item | [classification-routing](../blueprints/classification-routing.md) | [few-shot-calibration](../patterns/few-shot-calibration.md) |
| Answer questions over a corpus | [rag-answering](../blueprints/rag-answering.md) | [rag-grounding](../patterns/rag-grounding.md) |
| Compress a source for a decision | [summarization](../blueprints/summarization.md) | [style-control](../patterns/style-control.md) |
| Write or refactor code | [code-generation](../blueprints/code-generation.md) | [chain-of-thought](../patterns/chain-of-thought.md) |
| Design a system or migration | [system-architecture](../blueprints/system-architecture.md) | [task-decomposition](../patterns/task-decomposition.md) |
| Call tools in a loop | [agent-system-prompt](../blueprints/agent-system-prompt.md) | [react-tool-use](../patterns/react-tool-use.md) |
| Produce narrative or copy | [creative-writing](../blueprints/creative-writing.md) | [style-control](../patterns/style-control.md) |
| Read values off an image | [vision-and-multimodal](../blueprints/vision-and-multimodal.md) | [structured-output](../patterns/structured-output.md) |
| Route between specialist prompts | [prompt-chaining-and-routing](../patterns/prompt-chaining-and-routing.md) | [classification-routing](../blueprints/classification-routing.md) |

---

## 2. Start from the symptom

| Symptom | Likely pattern |
|---|---|
| Output is valid but invents values | [uncertainty-and-abstention](../patterns/uncertainty-and-abstention.md) · [rag-grounding](../patterns/rag-grounding.md) |
| Format drifts run to run | [structured-output](../patterns/structured-output.md) · [few-shot-calibration](../patterns/few-shot-calibration.md) |
| One of several requested tasks is dropped | [task-decomposition](../patterns/task-decomposition.md) |
| Long prompt, weak instructions | [long-context-management](../patterns/long-context-management.md) · [constraint-enforcement](../patterns/constraint-enforcement.md) |
| Multi-step logic fails early | [chain-of-thought](../patterns/chain-of-thought.md) |
| Answers are unstable across runs | [self-consistency](../patterns/self-consistency.md) · [sampling-and-determinism](../fundamentals/sampling-and-determinism.md) |
| Agent loops, stalls, or overspends | [react-tool-use](../patterns/react-tool-use.md) · [agent-system-prompt](../blueprints/agent-system-prompt.md) |
| Voice is wrong or length is unmanageable | [style-control](../patterns/style-control.md) |
| Model ignores its own rules over time | [instruction-hierarchy](../fundamentals/instruction-hierarchy.md) · [multi-turn-conversations](../guides/multi-turn-conversations.md) |
| A document can tell the model what to do | [prompt-injection-and-safety](../guides/prompt-injection-and-safety.md) |
| Reasoning model over-explains | [reasoning-model-prompting](../patterns/reasoning-model-prompting.md) |

---

## 3. Composition map

Patterns compose in a predictable order. This is the default stack; remove what earns nothing.

```text
1. Instruction hierarchy     who may change what
2. Constraint enforcement    positive/negative symmetry
3. Structured output         container + schema + validation
4. Grounding / abstention    where values may come from, and when to stop
5. Exemplars                 calibrate the boundaries
6. Self-consistency          only if the answer is discrete and stakes are high
```

Two rules of composition:

- **Do not stack mechanisms that solve the same problem.** Schema mode plus grammar constraints plus a "must be JSON" paragraph is one mechanism with three costs.
- **Add the cheapest mechanism first.** A null policy is free; a second model call is not.

---

## 4. What not to use, and when

| Pattern | Skip it when |
|---|---|
| Chain-of-thought | Extraction, classification, on reasoning models |
| Self-consistency | Output is prose; latency budget is tight; samples always agree |
| RAG | The corpus fits in context and changes rarely |
| Routing | Every request takes the same path |
| Decomposition | One objective, one format, no human checkpoint |
| Meta-prompting | You have not yet written a baseline to improve |
| Vision | The data is already text |

---

## 5. Escalation ladder

When the current design is not enough, escalate in this order — each step costs more than the last.

| Step | Action | Cost |
|---|---|---|
| 1 | Add the missing fallback branch | minutes |
| 2 | Add an exemplar for the failing boundary | minutes |
| 3 | Tighten the output contract | minutes |
| 4 | Split the prompt into stages | hours |
| 5 | Add retrieval or tools | days |
| 6 | Change the model class | days + money |
| 7 | Change the product contract (ask the user) | weeks |

Most "the model can't do this" conclusions are step 1–3 problems dressed up as step 6 problems.

---

## Acceptance Checklist

- [ ] The task row exists and the chosen blueprint matches the output consumer.
- [ ] At most three patterns are stacked, and each removes a named failure.
- [ ] Mechanisms that solve the same problem have been collapsed to one.
- [ ] The escalation ladder was considered before any model change.
- [ ] The selection is recorded with the prompt version, so a later reader knows why.
