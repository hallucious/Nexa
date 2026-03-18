# Nexa Execution Rules

## Purpose

This document defines derived operational rules and implementation constraints for Nexa.

These rules are derived from `docs/ARCHITECTURE_CONSTITUTION.md`.

The Architecture Constitution takes precedence over this document in all cases.

---

# Rule 1 — Execution Engine Structure

The following implementation structure must be preserved:

Circuit
→ Node
→ Execution Runtime
→ Prompt / Provider / Plugin
→ Artifact
→ Trace

No implementation may bypass this structure.

---

# Rule 2 — Node Execution Boundary

Execution logic must be encapsulated inside nodes.

Execution logic is not allowed at:

* circuit level
* global runtime level

---

# Rule 3 — Dependency-Based Scheduling

Execution must be scheduled dynamically based on dependency resolution.

Hardcoded global execution order is forbidden.

---

# Rule 4 — Artifact Handling

Artifacts must remain append-only and immutable.

Allowed:

* new artifact creation
* append-only recording

Forbidden:

* mutation
* overwrite
* deletion

---

# Rule 5 — Plugin Namespace Enforcement

Plugins may write only to:

`plugin.<plugin_id>.*`

Plugins must not write to:

* `prompt.*`
* `provider.*`
* `output.*`
* `artifact.*`
* `input.*`

---

# Rule 6 — Working Context Schema Enforcement

Working context keys must follow:

`<context-domain>.<resource-id>.<field>`

Implementations must not introduce undocumented key patterns.

---

# Rule 7 — Deterministic Runtime Enforcement

Runtime behavior must remain deterministic for identical inputs and configuration.

Sources of non-determinism must be eliminated or recorded explicitly.

---

# Rule 8 — Trace Completeness

Execution must generate trace data that includes:

* node execution status
* node-internal phase status (pre/core/post)
* artifact creation
* runtime metadata

---

# Rule 9 — Contract Compliance

All implementations must comply with active contracts, including:

* artifact contract
* plugin contract
* provider contract
* prompt contract
* validation engine contract
* execution trace schema
* ExecutionConfig schema

---

# Rule 10 — Spec-Version Synchronization

When any active spec changes:

* `src/contracts/spec_versions.py` must be updated
* relevant contract tests must be updated

---

# Rule 11 — Observability Enforcement

Execution state must remain inspectable during development and debugging.

---

# Rule 12 — Forbidden Implementations

The following are prohibited:

* system-level pipeline execution
* mutable artifacts
* unrestricted plugin writes
* undocumented runtime mutation
* implicit global execution order

---

End of Execution Rules
