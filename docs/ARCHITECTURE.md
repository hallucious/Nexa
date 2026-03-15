# Nexa Architecture

## Overview

Nexa is an **AI execution engine** designed to orchestrate multiple AI systems through structured computation graphs, while preserving deterministic execution, traceability, and contract-driven reliability.

Nexa is **not a workflow automation tool**.
It is an **execution runtime for AI computation graphs**.

The system is designed to make AI-based computation:

* deterministic
* observable
* auditable
* reproducible

---

# Why Nexa Exists

Direct AI calls are difficult to scale and reproduce.

Traditional AI usage looks like this:

```
User → Prompt → AI Model → Result
```

This approach breaks down when systems grow larger.

Problems include:

* inconsistent outputs
* lack of traceability
* difficult debugging
* poor orchestration

Nexa changes this into a structured system:

```
Input
↓
Circuit
↓
Nodes
↓
AI Providers / Plugins
↓
Artifacts
↓
Trace
```

---

# 1. System Overview

The fundamental execution structure of Nexa is:

```
Circuit
↓
Node
↓
Execution Runtime
↓
Prompt / Provider / Plugin
↓
Artifact
↓
Trace
```

This model defines how AI computation flows through the system.

**Node is the only execution unit.**

Circuit is responsible only for connecting nodes.

---

# 2. Circuit Model

A **Circuit** represents the execution graph.

You can think of it as a map of tasks — defining what nodes exist, how they depend on one another, and the order in which they become eligible to execute.

Example linear circuit:

```
Node A → Node B → Node C
```

Example parallel circuit:

```
        → Node B →
Node A               → Node D
        → Node C →
```

Circuit responsibilities:

* define node topology
* resolve dependencies
* determine execution order

Characteristics:

* DAG-based structure (Directed Acyclic Graph)
* supports parallel execution
* manages node dependencies

**Circuit does not execute logic.**

All execution occurs inside nodes.

---

# 3. Node Execution Model

**Node** is the core execution unit in Nexa.

All computation occurs inside nodes.

A node can combine the following resources:

* prompt
* provider
* plugin

Example tasks a node might perform:

* generating text
* analyzing documents
* evaluating outputs
* transforming data
* calling AI models

Execution flow inside a node:

```
Prompt Rendering
↓
Provider Call
↓
Plugin Processing
↓
Artifact Creation
```

---

# 4. Runtime Layer

The **Execution Runtime** is responsible for executing nodes and maintaining execution state.

Runtime responsibilities:

* dependency-based node scheduling
* working context management
* artifact creation
* execution trace recording
* contract enforcement

## Execution Model

Execution in Nexa follows **dependency-based scheduling**.

Nodes execute only when their dependencies are satisfied.

Execution order is determined dynamically based on resource readiness.

**Forbidden model:** fixed prompt → provider → plugin pipelines.

## Deterministic Scheduling

The runtime ensures consistent execution order.

Given identical inputs and configuration, execution must produce identical artifacts.

Mechanisms include:

* deterministic scheduling
* artifact hashing
* trace comparison

## Working Context

Working Context is the shared data space used during execution.

All runtime components read and write through this context.

Key format:

```
<context-domain>.<resource-id>.<field>
```

Examples:

```
input.text
prompt.main.rendered
provider.openai.output
plugin.format.result
output.value
```

This schema ensures consistent data flow across the system.

---

# 5. Provider Layer

**Providers** are interfaces to AI model services.

Examples:

* OpenAI
* Anthropic
* Google Gemini
* Local models

Provider responsibilities:

* model invocation
* input/output translation
* error handling
* retry logic

Providers implement a common interface, allowing Nexa to switch between AI services without modifying circuits.

---

# 6. Plugin Layer

**Plugins** extend node functionality with capabilities that are not AI model calls.

Examples:

* text processing
* ranking outputs
* formatting results
* data transformation
* evaluation
* validation

Plugin write access is strictly restricted.

Allowed write namespace:

```
plugin.<plugin_id>.*
```

Plugins cannot modify unrelated system domains. This protects system integrity.

---

# 7. Artifact System

**Artifacts** represent the persistent outputs produced during execution.

Examples:

* generated text
* structured data
* evaluation results
* intermediate computation results

Artifacts are **append-only**.

Existing artifacts must never be modified. New results must be stored as new artifacts.

This guarantees:

* reproducibility
* execution history preservation
* reliable debugging

---

# 8. Trace System

**Execution Traces** record the runtime behavior of a circuit.

Trace contains:

* node execution events
* resource execution order
* artifact lineage
* runtime metadata
* timestamps

Trace enables:

* debugging
* auditing
* execution replay

---

# Design Principles

These principles explain why Nexa is designed the way it is.

**Determinism Over Convenience** — Given identical inputs and configuration, the system must produce identical outputs. This ensures reproducibility and reliable automation.

**Structure Over Ad-Hoc Automation** — AI tasks are represented as nodes connected through explicit dependencies. This keeps complex AI systems understandable and maintainable.

**Observability First** — Every execution step must be traceable. Artifacts and traces allow developers to inspect the entire computation history.

**Immutability of Results** — Artifacts are append-only. Instead of modifying existing results, Nexa produces new artifacts. This protects execution history and enables reliable debugging.

**Contract-Driven Development** — System behavior is governed by explicit contracts (artifact schema, trace schema, validation rules, plugin behavior). Contracts prevent architectural drift as the system evolves.

**Safe Extensibility** — Plugins, providers, and new node types integrate safely without compromising core guarantees.

**Explicit Data Flow** — All components communicate through well-defined data paths in the Working Context.

**Engine Stability First** — Development priorities follow: Engine → Runtime → Core architecture → Developer tools → User interfaces.

**Minimal Core, Powerful Extensions** — The Nexa core remains minimal. Complex functionality is implemented through plugins, providers, and external tooling.

---

# Contract-Driven Architecture

Nexa uses **contract-driven design**.

Important contracts include:

* artifact contract
* plugin result contract
* execution trace schema
* validation engine contract
* spec-version registry

Code must not violate existing contracts.

See `docs/specs/` for detailed contract specifications.

---

# Forbidden Architectural Patterns

The following patterns are not allowed in Nexa:

* pipeline-based execution engines
* step-list workflow models
* mutable artifact storage
* unrestricted plugin writes
* undocumented runtime mutation

Violating these patterns breaks Nexa architecture.

---

# Repository Structure

```
src/
    artifacts/
    circuit/
    cli/
    config/
    contracts/
    engine/
    models/
    platform/
    policy/
    prompts/
    providers/
    utils/

tests/
docs/
examples/
scripts/
tools/
```

---

# Summary

Nexa is designed as a deterministic AI execution runtime.

Key characteristics:

* graph-based execution (Circuit → Node DAG)
* node-centered computation (Node is the only execution unit)
* dependency-based scheduling (not pipeline-based)
* contract-driven architecture
* append-only artifact storage
* full execution observability

These principles ensure reliable and auditable AI system orchestration.

---

End of Architecture Document
