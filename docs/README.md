# Nexa

### Deterministic AI Execution Engine

Nexa is an **execution runtime for AI systems** — deterministic, traceable, contract-enforced.

* Execution order determined by **dependency resolution**
* Every execution step is **fully traceable**
* Results are **reproducible** given the same inputs
* Behaviors are governed by **explicit versioned contracts**

---

# Why Nexa Exists

Most AI applications rely on unstructured patterns that break down as systems grow: unpredictable outputs, impossible to reproduce, no visibility into intermediate computation.

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

Within each node, resources execute through optional pre/core/post phases (node-internal contract). AI calls execute in core only.

---

# Key Features

**Deterministic Execution** — Identical inputs → identical results.

**Dependency-Based Scheduling** — No fixed pipeline. Nodes run when their dependencies are met.

**Artifact Tracking** — Append-only, immutable, hashed outputs.

**Execution Trace** — Per-node status, phase status, artifact lineage. Fully immutable.

**Validation Engine** — First-class contract enforcement at runtime.

**Regression Detection** — Compare runs, detect regressions, evaluate policy (PASS/WARN/FAIL).

**Provider Abstraction** — OpenAI, Anthropic, Gemini, Perplexity, Codex.

**Plugin System** — Non-AI extensions, restricted to `plugin.<plugin_id>.*`.

---

# Repository Structure

```
src/
    artifacts/      — artifact writer
    circuit/        — circuit model, scheduler, validator
    cli/            — CLI commands
    config/         — ExecutionConfig loader/registry
    contracts/      — spec versions, context key schema, reason codes
    engine/         — engine, runtimes, trace, diff, regression, policy
    models/         — shared decision models
    platform/       — plugin system, provider executor, observability
    policy/         — gate policy, reason codes
    prompts/        — prompt registry, renderer
    providers/      — AI provider adapters
    utils/          — utilities

tests/
docs/
    architecture/   — ARCHITECTURE.md, FOUNDATION_RULES.md, PROJECT_SCOPE.md
    strategy/       — STRATEGY.md, VISION.md, ROADMAP.md
    ai/             — NEXA_FOR_AI.md, CLAUDE_GUIDE.md, CLAUDE_MASTER_PROMPT.md
    specs/          — all active specifications
examples/
```

---

# Getting Started

```bash
pip install -r requirements.txt
python -m pytest
```

---

# Documentation

```
docs/ARCHITECTURE_CONSTITUTION.md   — non-negotiable architectural rules
docs/architecture/ARCHITECTURE.md   — full system architecture
docs/BLUEPRINT.md                   — active spec list, system overview
docs/CODING_PLAN.md                 — implementation history and next steps
docs/specs/_active_specs.yaml       — authoritative active spec list
```

---

# Current Status

Baseline: **688 passed, 3 skipped**.

Active development: Step188 (CLI regression gating).

---

End of README
