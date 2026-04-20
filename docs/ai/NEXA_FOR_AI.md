# Nexa Guide for AI Systems

## Purpose

This document is for **AI coding assistants** working on the Nexa repository.

Read this before generating or modifying any code.

---

# What Nexa Is

Nexa is an **AI execution engine**.

It is NOT: a pipeline orchestrator, workflow tool, or prompt chaining system.

It IS: a deterministic, traceable, contract-enforced execution runtime.

---

# Core Execution Model

```
Circuit
  ↓
Node  (only execution unit)
  ↓
Runtime  (dependency scheduler)
  ↓
Prompt / Provider / Plugin
  ↓
Artifact  (immutable)
  ↓
Trace  (immutable record)
```

**Node is the only execution unit.**

**Execution order is determined by dependency resolution — not a fixed pipeline.**

---

# System-Level vs Node-Level

This distinction is critical:

**System level (circuit/runtime):**
* Nodes execute when their dependencies are satisfied
* Execution order is dynamic, determined by the scheduler
* Parallel execution is possible

**Node-internal (per-node contract):**
* Within a single node, resources may run in pre/core/post phases
* Pre: validation, prompt resolution, plugin data prep
* Core: AI provider call
* Post: output validation, persistence, trace
* This is an **internal node contract**, not a system pipeline

Never describe the system as "prompt → provider → plugin sequential pipeline". That is forbidden.

---

# Critical Architectural Rules

1. **Node is the only execution unit.**
2. **Circuits define topology only** — no execution logic.
3. **Execution is dependency-driven** — no fixed global ordering.
4. **Artifacts are immutable** — never modify existing artifacts.
5. **Runtime must be deterministic** — same input → same output.
6. **Plugins write only to `plugin.<plugin_id>.*`** — no other namespace.
7. **Code must respect all contracts** — see `docs/specs/`.

---

# Plugin Write Restrictions (Strict)

```
# Allowed
plugin.<plugin_id>.*

# Forbidden
prompt.*
provider.*
output.*
artifact.*
input.*
```

---

# Working Context Schema

```
input.<field>
output.<field>
<context-domain>.<resource-id>.<field>

input.text
prompt.main.rendered
provider.openai.output
plugin.format.result
output.value
```

Contract: `docs/specs/contracts/context_key_schema_contract.md`

---

# Artifact Rules

```python
# Allowed
artifact.append(...)

# Forbidden
artifact.update(...)
artifact.replace(...)
```

---

# Contract System

All behaviors are governed by versioned contracts in `docs/specs/`.

Active contracts: `docs/specs/_active_specs.yaml`

Every active spec must:
1. Exist at the listed path
2. Have a `Version: X.Y.Z` line
3. Match the version in `src/contracts/spec_version_registry.py`

---

# Repository Structure

```
src/
    artifacts/        — artifact writer
    circuit/          — circuit model, scheduler, validator
    cli/              — CLI
    config/           — ExecutionConfig loader/registry
    contracts/        — spec versions, context key schema, reason codes
    engine/           — engine, runtimes, trace, diff, regression, policy
    models/           — decision models
    platform/         — plugin system, provider executor
    policy/           — gate policy, reason codes
    prompts/          — prompt registry, renderer
    providers/        — AI adapters (OpenAI, Anthropic, Gemini, etc.)
    utils/            — utilities
```

---

# Test Requirements

All code must pass:

```
python -m pytest
```

Do NOT force tests to pass by weakening assertions.

Do NOT modify tests to accept incorrect behavior.

---

# Hallucination Guard

Never:
* Invent files or APIs that do not exist
* Guess architectural constraints
* Modify spec version numbers without a stated reason
* Introduce fixed pipeline ordering at system level

If uncertain: **ask instead of guessing**.

---

End of AI Guide
