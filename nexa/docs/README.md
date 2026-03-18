# Nexa

### Deterministic AI Execution Engine

Nexa is an **execution runtime for AI systems** — deterministic, traceable, contract-enforced.

* Execution order is determined by **dependency resolution**
* Every execution step is **fully traceable**
* Results are **reproducible** given the same inputs
* Behaviors are governed by **explicit versioned contracts**

---

# Why Nexa Exists

Most AI applications rely on unstructured patterns that break down as systems grow: unpredictable outputs, impossible to reproduce, and poor visibility into intermediate computation.

Nexa replaces ad-hoc scripts with **structured computation graphs**. AI tasks become nodes. Execution order emerges from dependencies — not from a hardcoded sequence.

---

# Core Model

```
Input
  ↓
Circuit (DAG of nodes)
  ↓
Runtime (dependency scheduler)
  ↓
Providers / Plugins
  ↓
Artifacts (immutable outputs)
  ↓
Trace (complete execution record)
```

**Node is the only execution unit.**

Within each node, resources may execute through optional pre/core/post phases (node-internal contract). AI calls execute in core only.

---

# Key Features

**Deterministic Execution** — Identical inputs → identical results.

**Dependency-Based Scheduling** — No fixed pipeline. Nodes run when their dependencies are met.

**Artifact Tracking** — Append-only, immutable, hashed outputs.

**Execution Trace** — Per-node status, phase status, artifact lineage. Fully immutable.

**Validation Engine** — First-class contract enforcement at runtime.

**Regression Detection** — Compare runs, detect regressions, evaluate policy (PASS/WARN/FAIL).

**Provider Abstraction** — Unified provider interface for AI model services.

**Plugin System** — Non-AI extensions, restricted to `plugin.<plugin_id>.*`.

---

# Plugin and Provider Summary

## Plugin System
- Plugins extend node behavior with non-AI computation.
- Plugins may execute in pre/core/post phases depending on node configuration.
- Plugins may write only to `plugin.<plugin_id>.*`.
- Plugins must not mutate runtime-owned domains.

## Provider System
- Providers interface Nexa with AI model services.
- Provider execution is restricted to the core phase of a node.
- Providers normalize model responses into a standard contract.

---

# Documentation Structure

## Core Documents
- `docs/README.md` — project overview and entry point
- `docs/ARCHITECTURE_CONSTITUTION.md` — non-negotiable architectural rules
- `docs/BLUEPRINT.md` — system overview and active spec source reference
- `docs/CODING_PLAN.md` — implementation history and next steps
- `docs/DEVELOPMENT.md` — environment setup, contribution rules, and test workflow

## Architecture
- `docs/architecture/ARCHITECTURE.md` — full system architecture
- `docs/architecture/PROJECT_SCOPE.md` — scope boundaries and MVP definition
- `docs/architecture/EXECUTION_RULES.md` — derived execution and implementation rules

## Specifications
- `docs/specs/_active_specs.yaml` — authoritative active spec list
- `docs/specs/` — active specification documents only

---

# Repository Structure

```
src/
    artifacts/      engine/         platform/
    circuit/        models/         policy/
    cli/            prompts/        providers/
    config/         utils/
    contracts/

tests/
docs/
examples/
```

---

# Quick Start

1. Read `docs/README.md`
2. Read `docs/ARCHITECTURE_CONSTITUTION.md`
3. Read `docs/BLUEPRINT.md`
4. Read `docs/CODING_PLAN.md`
5. Read `docs/DEVELOPMENT.md`

---

# Getting Started

```bash
pip install -r requirements.txt
python -m pytest
```

---

# Current Status

Baseline: **688 passed, 3 skipped**

Active development target: Step188 (CLI regression gating)

---

End of README
