# Nexa Architecture

## Overview

Nexa is an **AI execution engine platform** designed to orchestrate collaboration between multiple AI systems while preserving deterministic execution, traceability, and contract-driven reliability.

Nexa is **not a workflow automation tool**.
It is an **execution runtime for AI computation graphs**.

The system is designed to make AI-based computation:

* deterministic
* observable
* auditable
* reproducible

---

# Core Execution Model

The fundamental execution structure of Nexa is:

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

This model defines how AI computation flows through the system.

Node is the **only execution unit**.

Circuit is responsible only for connecting nodes.

---

# System Components

## 1. Circuit

A Circuit represents the **execution graph**.

Responsibilities:

* define node topology
* resolve dependencies
* determine execution order

Characteristics:

* DAG-based structure
* supports parallel execution
* manages node dependencies

Circuit **does not execute logic**.

---

## 2. Node

Node is the **core execution unit** in Nexa.

All computation occurs inside nodes.

A node can combine the following resources:

* prompt
* provider
* plugin

Example execution flow inside a node:

Prompt Rendering
↓
Provider Call
↓
Plugin Processing
↓
Artifact Creation

---

## 3. Execution Runtime

The runtime is responsible for executing nodes and maintaining execution state.

Responsibilities:

* node execution
* working context management
* artifact creation
* execution trace recording
* deterministic scheduling

Runtime ensures that execution remains reproducible.

---

## 4. Prompt

Prompts define the input instructions for AI models.

Responsibilities:

* prompt rendering
* variable interpolation
* structured prompt construction

Prompts operate inside nodes.

---

## 5. Provider

Providers are interfaces to AI model services.

Examples:

* OpenAI
* Anthropic
* Google Gemini
* local models

Responsibilities:

* model invocation
* input/output translation
* error handling

---

## 6. Plugin

Plugins extend node functionality.

Examples:

* text processing
* ranking
* formatting
* data transformation
* evaluation

Plugin write access is restricted.

Allowed write namespace:

```
plugin.<plugin_id>.*
```

Plugins cannot modify unrelated system domains.

---

## 7. Artifact

Artifacts represent the persistent outputs produced during execution.

Examples:

* generated text
* structured data
* evaluation results
* intermediate computation results

Artifacts are **append-only**.

Existing artifacts must never be modified.

---

## 8. Execution Trace

Execution traces record the runtime behavior of a circuit.

Trace contains:

* node execution events
* resource execution order
* artifact lineage
* runtime metadata

Trace enables debugging and reproducibility.

---

# Working Context

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

# Execution Model

Execution in Nexa follows **dependency-based scheduling**.

Allowed execution model:

dependency-based resource execution

Forbidden model:

prompt → provider → plugin fixed pipelines

Execution order is determined dynamically based on resource readiness.

---

# Contract Driven Architecture

Nexa uses **contract-driven design**.

Important contracts include:

* artifact contract
* plugin result contract
* execution trace schema
* validation engine contract
* spec-version registry

Code must not violate existing contracts.

---

# Observability

The runtime records complete execution information.

Observability includes:

* execution traces
* artifact lineage
* node execution history
* runtime metadata

This allows:

* debugging
* replay
* auditing

---

# Deterministic Execution

Nexa ensures deterministic behavior.

Given identical inputs and configuration:

execution must produce identical artifacts.

Mechanisms include:

* deterministic scheduling
* artifact hashing
* trace comparison

---

# Repository Architecture

Repository structure:

```
src/

engine/
runtime/
plugins/
contracts/
cli/


docs/

BLUEPRINT.md
CODING_PLAN.md
FOUNDATION_RULES.md
ARCHITECTURE.md
specs/


tests/
```

This structure separates:

* runtime logic
* contracts
* documentation
* tests

---

# Development Principles

Nexa development follows these principles.

Engine-first development

Engine
↓
CLI
↓
Developer tooling
↓
Product features
↓
UI / visual editor

The execution engine must remain stable before product features are added.

---

# Forbidden Architectural Patterns

The following patterns are not allowed.

* pipeline-based execution engines
* step-list workflow models
* mutable artifact storage
* unrestricted plugin writes
* undocumented runtime mutation

Violating these patterns breaks Nexa architecture.

---

# Summary

Nexa is designed as a deterministic AI execution runtime.

Key characteristics:

* graph-based execution
* node-centered computation
* contract-driven architecture
* append-only artifact storage
* full execution observability

These principles ensure reliable and auditable AI system orchestration.

---

End of Architecture Document
