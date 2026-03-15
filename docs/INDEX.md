# Nexa Documentation Index

## Purpose

This document serves as the central index for all Nexa documentation.

It helps developers, contributors, and AI coding tools navigate the documentation system efficiently.

---

# Core Architecture

These documents define the structure and invariants of the Nexa system.

**BLUEPRINT.md**
High-level architecture blueprint and system design overview.

**ARCHITECTURE_CONSTITUTION.md**
The foundational rules and non-negotiable invariants that govern Nexa architecture.

**ARCHITECTURE.md**
Unified architecture explanation covering the Circuit model, Node execution, Runtime layer, Provider layer, Plugin layer, Artifact system, Trace system, and design principles.

---

# Development

These documents explain how to work with the Nexa codebase.

**CODING_PLAN.md**
Implementation roadmap and development phases.

**DEVELOPMENT.md**
Development environment setup, testing, and contribution workflow.

**CONTRIBUTING.md**
Guidelines for open-source contributors.

---

# Specifications

The `docs/specs/` directory contains detailed technical specifications and contracts.

These specifications are the authoritative source of truth for system behavior.
They define strict contracts and are enforced by automated tests.

Examples:

* `docs/specs/architecture/` — execution model, node contracts, circuit contracts
* `docs/specs/contracts/` — plugin, provider, prompt, and validation contracts
* `docs/specs/policies/` — validation rules, observability, determinism policies
* `docs/specs/indexes/` — spec catalog and dependency map

---

# Product Vision

These documents describe the long-term direction and planned product evolution.

**docs/product/SaaS Product Definition.md**
Definition of the Nexa SaaS product offering.

**docs/product/Visual Editor Architecture.md**
Architecture for the planned visual circuit editor.

**docs/product/User Profile (Preset).md**
User profile and preset system design.

---

# Additional Reference

**GLOSSARY.md**
Definitions of key Nexa terminology.

**VISION.md**
Long-term goals and philosophical direction of the project.

**ROADMAP.md**
Long-term development roadmap.

---

# Recommended Reading Order

For new contributors:

1. `README.md` — project introduction
2. `docs/ARCHITECTURE_CONSTITUTION.md` — core invariants
3. `docs/ARCHITECTURE.md` — full architecture explanation
4. `docs/BLUEPRINT.md` — system design blueprint
5. `docs/DEVELOPMENT.md` — how to contribute

---

# Documentation Philosophy

**Clarity** — Documents should be understandable by new contributors.

**Consistency** — Documentation must match the implementation.

**Stability** — Architectural principles should change rarely.

**Single Source of Truth** — Specifications in `docs/specs/` are the authoritative contracts. Top-level architecture documents provide human-readable explanation.

---

End of Documentation Index
