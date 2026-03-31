# BLUEPRINT

Version: 1.11.0

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
## 3.1 Current Runtime Convergence Snapshot

The current runtime line is intentionally concentrated into a smaller set of practical execution files.

### Prompt side

* `src.engine.node_execution_runtime.NodeExecutionRuntime` is the practical prompt execution caller
* prompt resolution is handled through `src.platform.prompt_registry.PromptRegistry` and PromptSpec loading
* No standalone legacy prompt package remains in the repository; the canonical runtime prompt path is the `src/platform/prompt_*` line.

### Provider side

* provider execution is routed through `src.platform.provider_executor.ProviderExecutor`
* provider lookup is handled through `src.platform.provider_registry.ProviderRegistry`
* provider result canonicalization is concentrated in the runtime path

### Plugin side

The plugin surface is currently split by role rather than duplicated legacy ownership:

* practical runtime execution side:
  * `src/engine/node_execution_runtime.py`
  * `src/platform/plugin_executor.py`
* `src/platform/plugin_result.py`
* runtime bridge loader for savefile entry references:
  * `src/platform/plugin_auto_loader.py`
* canonical versioned registry side:
  * `src/platform/plugin_version_registry.py`
* execution contract / safe execution side:
  * `src/platform/plugin.py`
* bundle/savefile compatibility side:
  * `src/engine/cli.py` (bounded legacy `.nex` execution orchestration path)
  * `src/contracts/savefile_executor_aligned.py`

Current savefile plugin execution delegates entry-path execution to
`src/platform/plugin_executor.py`, so the savefile layer does not re-implement
callable wrapping or safe-execution adaptation.

Removed legacy ownership paths:

* `src/engine/plugin_loader.py`
* `src/platform/plugin_registry.py`

This means new runtime work MUST build from the converged files above rather than recreating the deleted legacy paths.

Legacy `.nex` compatibility runtime concentration:

* `.nex` execution remains bounded inside `src/engine/cli.py`, but load/bundle handling now lives in `src/circuit/loader.py` and Engine adaptation now lives in `src/circuit/runtime_adapter.py`
* legacy `.nex` support is execution-only; reverse conversion / writer / roundtrip preservation are no longer part of the supported runtime surface
* deleted legacy contract leaves:
  * `src/contracts/nex_loader.py`
  * `src/contracts/nex_engine_adapter.py`
  * `src/contracts/nex_bundle_loader.py`
  * `src/contracts/nex_format.py`
  * `src/contracts/nex_serializer.py`
  * `src/contracts/nex_validator.py`


---

## 4. Savefile & Bundle System (NEW)

### 4.1 Savefile (.nex)

`.nex` is the primary executable savefile format.

It is not a circuit-only artifact.
A valid `.nex` savefile includes both execution structure and execution state.

Current savefile root sections:

* `meta`
* `circuit`
* `resources`
* `state`
* `ui`

This means a savefile includes:

* circuit structure
* node definitions
* prompt / provider / plugin resources
* execution state (`input`, `working`, `memory`)
* UI metadata

Properties:

* deterministic
* serializable
* reproducible
* portable as the primary execution artifact

Canonical savefile lifecycle entry points currently implemented in code:

* create → `src/contracts/savefile_factory.py`
  * `create_savefile(...)`
  * `make_minimal_savefile(...)`
* serialize / save → `src/contracts/savefile_serializer.py`
  * `serialize_savefile(...)`
  * `save_savefile_file(...)`
* load → `src/contracts/savefile_loader.py`
* validate → `src/contracts/savefile_validator.py`

Contract status:

* `ui` is required at create / serialize / load / validate time
* `runtime` is not part of the canonical savefile root
* canonical savefiles and legacy `.nex` writer behavior are kept distinct

Current official savefile CLI surface:

* `nexa savefile new <output.nex>`
* `nexa savefile validate <file.nex>`
* `nexa savefile info <file.nex>`
* `nexa savefile template list`
* `nexa savefile set-name <file.nex> --name ...`
* `nexa savefile set-entry <file.nex> --entry ...`
* `nexa savefile set-description <file.nex> --description ...`

Boundary status:

* the current official edit surface is intentionally limited to minimal metadata / entry editing
* broader structural editing, `resources` mutation, `state` mutation, and `ui` mutation are not yet part of the official CLI surface

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

## 4.5 Public Demo Baseline

The repository currently keeps one official demo path for public GitHub usage:

* `examples/real_ai_bug_autopsy_multinode/`

Other demo/example assets were intentionally removed to prevent deleted demo files from remaining as hidden test dependencies.

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

## 6. Universal Artifact Diff Architecture (NEW)

Nexa defines artifact comparison as a first-class architectural component.

All artifact comparison MUST follow a media-agnostic pipeline:

Artifact
→ Representation
→ ComparableUnit[]
→ Alignment
→ DiffResult
→ Formatter

### 6.1 Core Principle

- Raw artifact comparison is prohibited
- All comparison must operate on structured representations
- Comparison must be deterministic and reproducible

### 6.2 ComparableUnit Abstraction

ComparableUnit is the universal comparison unit across all media types.

Properties:

- unit_kind is extensible (section, scene, function, region, etc.)
- canonical_label enables cross-artifact alignment
- payload contains comparison-relevant data

This abstraction allows Nexa to support:
- text
- image
- video
- audio
- code
- structured data
- unknown future media

without modifying the core engine.

### 6.3 Layer Separation

The comparison system is strictly layered:

1. Extractor (Artifact → Representation)
2. Alignment (unit matching)
3. Comparison (unit-level diff)
4. Formatter (output only)

Formatter MUST NOT generate semantic meaning.

### 6.4 Architectural Constraint

The diff engine MUST remain media-agnostic.

Adding new media types MUST require ONLY:
- new extractor implementation

No modification to:
- alignment engine
- comparison engine
- formatter core

### 6.5 Relationship to Execution Engine

Artifact Diff operates as a downstream system of execution:

Execution Engine → Artifacts → Diff Engine

The diff engine does NOT influence execution semantics.

### 6.6 Representation Definition

Representation is a structured, deterministic transformation of an Artifact.

It is the ONLY valid input to the diff engine.

Properties:

- MUST be deterministic
- MUST be reproducible
- MUST be independent from formatter
- MUST consist of ComparableUnit[]

Structure:

Representation {
    representation_id: str
    artifact_type: str
    units: List[ComparableUnit]
    metadata: dict
}

---



* legacy `.nex` plugin validation is owned by `src/platform/external_loader.py`; CLI keeps only branching, savefile fallback, and policy/output handling


- Legacy engine CLI compatibility has been further narrowed: regression policy application and summary dispatch now live in src/cli/savefile_runtime.py, while src/engine/cli.py remains a thin compatibility wrapper.
