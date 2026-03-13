# Nexa Architecture Constitution

## Purpose

This document defines the **foundational architectural principles** of the Nexa system.

These rules represent the **highest-level invariants** of the project.

All implementation decisions must respect this constitution.

---

# Principle 1 — Node Is the Only Execution Unit

All computation in Nexa must occur inside nodes.

Nodes are the smallest executable entities in the system.

Other components such as circuits, prompts, providers, and plugins support node execution but do not replace it.

This rule ensures architectural consistency.

---

# Principle 2 — Circuit Defines Structure, Not Execution

A circuit represents the structure of computation.

It defines:

* nodes
* dependencies
* execution topology

Circuits do not execute logic.

All execution must occur inside nodes.

---

# Principle 3 — Execution Is Dependency Driven

Execution must follow dependency resolution.

Nodes execute only when their dependencies are satisfied.

Execution order is determined by the runtime scheduler.

Pipeline-based execution models are not allowed.

---

# Principle 4 — Artifacts Are Immutable

Artifacts represent execution outputs.

Once created, artifacts must never be modified.

If new results are generated, they must be stored as new artifacts.

This guarantees reproducibility.

---

# Principle 5 — Execution Must Be Traceable

All runtime activity must be recorded.

Trace logs must capture:

* node execution
* resource usage
* artifact creation
* runtime metadata

Traceability is essential for debugging and auditing.

---

# Principle 6 — Deterministic Execution

Nexa must produce deterministic behavior.

Given identical inputs and configuration, execution must produce identical artifacts.

Runtime scheduling must not introduce nondeterministic behavior.

---

# Principle 7 — Plugins Are Restricted

Plugins extend functionality but must operate within strict boundaries.

Plugins may only write to:

plugin.<plugin_id>.*

Plugins must not modify unrelated runtime domains.

This protects system integrity.

---

# Principle 8 — Contract Driven Architecture

All major system behaviors must be defined by explicit contracts.

Examples include:

artifact schema
execution trace schema
plugin result schema
validation rule catalog

Code must comply with defined contracts.

---

# Principle 9 — Observability First

The system must prioritize observability.

Developers must be able to inspect:

* execution state
* artifacts
* traces
* node execution order

Observability reduces debugging complexity.

---

# Principle 10 — Safe Extensibility

The architecture must allow safe extension.

New features must not violate existing guarantees such as:

deterministic execution
artifact immutability
contract compliance

---

# Forbidden Architectural Patterns

The following architectural patterns are explicitly forbidden.

Pipeline-based execution engines.

Mutable artifact storage.

Unrestricted plugin writes.

Undocumented runtime mutations.

Implicit execution order dependencies.

These patterns break the Nexa architecture.

---

# Governance

Architectural changes affecting these principles require careful review.

Major changes should update:

ARCHITECTURE.md
FOUNDATION_RULES.md
relevant specification documents

The constitution exists to maintain long-term architectural stability.

---

# Summary

Nexa is designed around a set of non-negotiable architectural principles.

These principles ensure:

deterministic execution
reliable AI orchestration
traceable computation
stable system evolution

All contributors must respect these rules.

---

End of Architecture Constitution
