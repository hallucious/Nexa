# BLUEPRINT

Version: 1.6.0

────────────────
Architecture Constitution
────────────────

Nexa follows an Execution Engine-based architecture.

The core design principles follow the Constitution defined in `docs/architecture/FOUNDATION_RULES.md`.

System invariants that MUST NOT be changed:

1. Nexa is not a workflow tool but an execution engine.
2. Node is the only execution unit.
3. Circuit does not perform execution and is responsible only for connections.
4. System-level execution is dependency-based. Fixed pipelines are prohibited.
5. Pre/core/post phases exist inside a Node, but they are the internal contract of a single node.
6. Artifacts are append-only immutable structures.
7. Deterministic execution must be maintained.
8. The plugin write scope is restricted to `plugin.<plugin_id>.*`.
9. The working context schema follows a fixed key structure.
10. Contract-driven architecture must be maintained.
11. Spec-version synchronization must be maintained.

Any implementation that violates these rules is considered a violation of the Nexa architecture.

---

## 0. Execution Philosophy (NEW)

Nexa treats execution as a portable, reproducible unit rather than a runtime-only process.

Execution is not defined by code alone, but by:

* Circuit definition
* Plugin environment
* Execution contract
* Deterministic runtime behavior

This enables:

* Reproducibility
* Portability
* Debuggability
* Environment isolation

---

## 1. Foundation Layer

The foundational design documents of this project are managed hierarchically by the following document:

* `docs/FOUNDATION_MAP.md`

When performing structure changes or contract changes, FOUNDATION_MAP must be referenced, and the status and SemVer of the affected documents must be checked.

---

## 2. Active Specifications

Currently active spec documents that are synchronized with the code.

Source-of-Truth: `docs/specs/_active_specs.yaml`

### 2.1 Foundation / Terminology

* `docs/specs/foundation/terminology.md`

### 2.2 Architecture Core

* `docs/specs/architecture/execution_model.md`
* `docs/specs/architecture/trace_model.md`
* `docs/specs/architecture/node_abstraction.md`
* `docs/specs/architecture/node_execution_contract.md`
* `docs/specs/architecture/circuit_contract.md`
* `docs/specs/architecture/universal_provider_architecture.md`

### 2.3 Contracts

* `docs/specs/contracts/execution_environment_contract.md`
* `docs/specs/contracts/provider_contract.md`
* `docs/specs/contracts/plugin_contract.md`
* `docs/specs/contracts/prompt_contract.md`
* `docs/specs/contracts/plugin_registry_contract.md`
* `docs/specs/contracts/validation_engine_contract.md`
* `docs/specs/contracts/execution_config_canonicalization_contract.md`
* `docs/specs/contracts/execution_config_schema_contract.md`
* `docs/specs/contracts/context_key_schema_contract.md`

### 2.4 Policies

* `docs/specs/policies/validation_rule_catalog.md`
* `docs/specs/policies/validation_rule_lifecycle.md`

### 2.5 Indexes

* `docs/specs/indexes/spec_catalog.md`
* `docs/specs/indexes/spec_dependency_map.md`

### 2.6 ExecutionConfig

* `docs/specs/execution_config_prompt_binding_contract.md`
* `docs/specs/execution_config_registry_contract.md`

---

## 3. ExecutionConfig Architecture

There is no Node type.

A Node is a single common execution container,
and behavioral diversity is expressed only through ExecutionConfig composition.

* Node = execution container
* Behavior = ExecutionConfig composition
* NodeSpec = ExecutionConfig reference
* ExecutionConfig identity = canonical hash

Execution layer:

Engine
→ GraphExecutionRuntime
→ NodeSpec
→ NodeSpecResolver
→ ExecutionConfigRegistry
→ ExecutionConfig Schema Validation
→ ExecutionConfig Hash
→ NodeExecutionRuntime

---

## 4. Savefile & Bundle System (NEW)

### 4.1 Savefile (.nex)

`.nex` is the canonical circuit definition format.

It includes:

* circuit structure
* node definitions
* plugin references
* execution configuration bindings

Properties:

* deterministic
* serializable
* reproducible

---

### 4.2 Bundle (.nexb)

`.nexb` is a deployable execution unit.

It contains:

* `.nex` circuit file
* plugin directories
* plugin metadata (`plugin.json`)

Properties:

* self-contained execution unit
* environment reproducibility
* portable distribution

---

### 4.3 Execution Flow

CLI execution flow:

```
CLI
→ detect file extension
→ .nex → direct execution
→ .nexb → bundle extraction
→ plugin validation
→ engine execution
→ cleanup
```

---

### 4.4 Plugin Contract Enforcement

All plugins MUST:

* include `plugin.json`
* satisfy strict version matching
* comply with plugin contract spec

Validation is performed BEFORE execution.

---

## 5. Regression Policy Architecture

`contracts/regression_reason_codes.py`  (single source of truth)
↓
`engine/execution_regression_detector.py`  (RegressionResult)
↓
`engine/execution_regression_policy.py`   (PolicyDecision: PASS/WARN/FAIL)
↓
formatter / CLI

Policy rules (default):

* HIGH severity regression → FAIL
* MEDIUM severity regression → WARN
* LOW severity / no regression → PASS

---
