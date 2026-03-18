# Nexa Architecture Constitution

## Purpose

The foundational architectural principles of the Nexa system. Non-negotiable invariants.

All implementation decisions must respect this constitution.

---

# Principle 1 — Node Is the Only Execution Unit

All computation in Nexa occurs inside nodes.

Nodes are the smallest executable entities.

Circuits, prompts, providers, and plugins support node execution but do not replace it.

---

# Principle 2 — Circuit Defines Structure, Not Execution

A circuit defines: nodes, dependencies, execution topology (DAG).

Circuits do not execute logic. All execution occurs inside nodes.

---

# Principle 3 — Execution Is Dependency-Driven

At the system level, nodes execute only when their dependencies are satisfied.

Execution order is determined by the runtime scheduler dynamically.

Fixed global pipeline execution models are not allowed.

---

# Principle 4 — Node-Internal Phases Are a Contract, Not a Pipeline

Within a single node, resources may execute in pre, core, and post phases.

* pre: validation, prompt resolution, plugin data preparation
* core: AI provider call (only here); plugin tool calls
* post: output validation, persistence, trace emission

These phases are an **internal contract of a single node**. They are NOT a system-level sequential pipeline.

AI provider calls are restricted to the core phase.

---

# Principle 5 — Artifacts Are Immutable

Artifacts represent execution outputs.

Once created, artifacts must never be modified.

New results must be stored as new artifacts.

---

# Principle 6 — Execution Must Be Traceable

All runtime activity must be recorded.

Trace logs must capture: node execution status, per-node phase status, artifact creation, runtime metadata.

---

# Principle 7 — Deterministic Execution

Given identical inputs and configuration, execution must produce identical artifacts.

Runtime scheduling must not introduce nondeterministic behavior.

---

# Principle 8 — Plugins Are Restricted

Plugins may only write to: `plugin.<plugin_id>.*`

Plugins must not modify any other runtime domain.

---

# Principle 9 — Working Context Schema Is Fixed

Working context keys must follow the fixed structure:

`<context-domain>.<resource-id>.<field>`

Examples:

* `input.text`
* `prompt.main.rendered`
* `provider.openai.output`
* `plugin.format.result`
* `output.value`

This schema is a system-wide invariant.

---

# Principle 10 — Contract-Driven Architecture

All major system behaviors must be defined by explicit versioned contracts.

Code must comply with defined contracts.

---

# Principle 11 — Spec-Version Synchronization

Document and code version mismatches are not allowed for active specifications.

When an active specification changes, the corresponding registry and contract tests must be updated together.

---

# Principle 12 — Observability First

Developers must be able to inspect execution state, artifacts, traces, and node execution order at any time.

---

# Principle 13 — Safe Extensibility

New features must not violate existing guarantees: deterministic execution, artifact immutability, contract compliance, and plugin isolation.

---

# Principle 14 — Engine-First Development

Nexa development proceeds in this order:

Engine
↓
Runtime
↓
Core architecture
↓
Developer tools
↓
Product features
↓
UI / Visual editor

Product features must not be prioritized before the engine is structurally stable.

---

# Forbidden Architectural Patterns

* System-level fixed-order pipeline execution
* Mutable artifact storage
* Unrestricted plugin writes
* Undocumented runtime mutations
* Implicit execution order dependencies

---

End of Architecture Constitution
