# Nexa Architecture

## Overview

Nexa is an **AI execution engine** that orchestrates multiple AI systems through deterministic, traceable computation graphs.

Nexa is **not** a workflow automation tool, pipeline orchestrator, or prompt chaining system.

It is an **execution runtime** that guarantees:

* deterministic output
* full execution observability
* contract-enforced behavior
* reproducible results

---

# Core Execution Model

```
Circuit
  ↓
Node  (execution unit)
  ↓
Runtime  (dependency scheduler)
  ↓
Resources  (Prompt / Provider / Plugin)
  ↓
Artifact  (immutable output)
  ↓
Trace  (execution record)
```

**Node is the only execution unit.**

Circuit defines topology only. Runtime schedules execution dynamically.

---

# 1. Circuit

A **Circuit** is a directed acyclic graph (DAG) of nodes.

Responsibilities:

* define node set
* define dependency edges
* define execution topology

A circuit does **not** execute logic. All execution occurs inside nodes.

Example:

```
Node A → Node B → Node C

        → Node B →
Node A               → Node D
        → Node C →
```

---

# 2. Node

A **Node** is the core execution unit. All computation occurs inside nodes.

A node may use any combination of:

* Prompt — constructs instructions for an AI model
* Provider — executes an AI model call
* Plugin — performs non-AI computation

**Node execution is dependency-based**: a node runs only when all its upstream dependencies are satisfied by the runtime scheduler.

**Node-internal execution contract** (from `docs/specs/architecture/node_execution_contract.md`):

Within a node, resources execute in three optional phases:

| Phase | Purpose | Constraints |
|---|---|---|
| Pre | validation, prompt resolution, data preparation | No AI calls |
| Core | AI provider call, plugin tool calls | Primary execution |
| Post | output validation, persistence, trace emission | No AI calls |

These phases are an **internal contract of a single node**, not a system-level pipeline. The system-level execution order between nodes is always determined by dependency resolution.

---

# 3. Runtime

The **Execution Runtime** schedules and executes nodes.

Runtime responsibilities:

* dependency-based node scheduling
* working context management
* artifact creation
* execution trace recording
* contract enforcement

**Execution is dependency-driven.** Nodes execute when their dependencies are satisfied — not in a fixed sequential order.

### Working Context

Shared data space. All resources read and write through this context.

Schema: `input.<field>` / `output.<field>` / `<context-domain>.<resource-id>.<field>`

```
input.text
prompt.main.rendered
provider.openai.output
plugin.format.result
output.value
```

See `docs/specs/contracts/context_key_schema_contract.md`.

### Determinism

Given identical inputs and configuration, execution must produce identical artifacts.

Mechanisms: deterministic dependency scheduling, artifact hashing, execution fingerprinting.

---

# 4. Provider

**Providers** interface with AI model services.

Implemented: OpenAI, Anthropic, Google Gemini, Perplexity, Codex.

Provider contract (`docs/specs/contracts/provider_contract.md`):

* execute model call
* return normalized `ProviderResult` with `reason_code`
* record `ProviderTrace`

---

# 5. Plugin

**Plugins** extend nodes with non-AI capabilities.

Plugin contract (`docs/specs/contracts/plugin_contract.md`):

* execute deterministic computation
* return `PluginResult` envelope

**Write restriction (strict):**

```
plugin.<plugin_id>.*    ← allowed
prompt.*                ← forbidden
provider.*              ← forbidden
output.*                ← forbidden
```

---

# 6. Artifact

**Artifacts** are immutable execution outputs.

Rules:
* **append-only** — existing artifacts are never modified
* new results always create new artifacts
* artifacts are hashed for determinism validation

---

# 7. Trace

**Execution Traces** record all runtime behavior.

Trace is **immutable** after creation. Contents:

* node execution status per node
* per-node phase status (pre/core/post)
* artifact lineage
* runtime metadata and timestamps

See `docs/specs/architecture/trace_model.md`.

---

# 8. ExecutionConfig Architecture

Node behavior is expressed through **ExecutionConfig composition**.

There are no node types — all nodes are execution containers. Behavior is configured via:

```
Engine
  → GraphExecutionRuntime
  → NodeSpec (holds execution_config_ref)
  → NodeSpecResolver
  → ExecutionConfigRegistry
  → ExecutionConfig (schema-validated, canonical hash)
  → NodeExecutionRuntime (resource execution)
```

See `docs/specs/contracts/execution_config_canonicalization_contract.md`.

---

# 9. Validation Engine

First-class execution validation system.

* validates execution correctness against rule catalog
* detects constraint violations
* enforces contracts at runtime

See `docs/specs/contracts/validation_engine_contract.md`.

---

# Design Principles

**Determinism Over Convenience** — Identical inputs → identical outputs. Always.

**Dependency-Based Execution** — No fixed pipeline. Execution order emerges from dependency resolution.

**Observability First** — Every node execution is fully traceable via artifacts and traces.

**Immutability of Results** — Artifacts are append-only. History is never rewritten.

**Contract-Driven** — All behaviors governed by explicit versioned contracts in `docs/specs/`.

**Safe Extensibility** — Plugins and providers extend the system without compromising core guarantees.

**Minimal Core** — Complex functionality lives in plugins, providers, external tooling — not the core engine.

---

# Forbidden Patterns

* Fixed-order pipeline execution (prompt → provider → plugin as a system model)
* Mutable artifact storage
* Unrestricted plugin writes
* Undocumented runtime mutation
* Implicit execution order dependencies

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
examples/
```

---

End of Architecture Document
