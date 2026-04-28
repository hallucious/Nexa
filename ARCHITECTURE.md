# Nexa Architecture

Status: Canonical architecture overview  
Scope: Engine architecture, architecture invariants, execution rules, product-layer boundaries, and repository orientation  
Direction and project-scope source of truth: `ROADMAP.md`  
Supersedes: `FOUNDATION_RULES.md` and `EXECUTION_RULES.md`

---

## 0. Document Role

This document is the canonical root-level architecture document for Nexa.

`ROADMAP.md` owns vision, strategy, roadmap, and project scope.
`ARCHITECTURE.md` owns engine structure, architecture invariants, execution rules, forbidden patterns, and repository orientation.

---

## 1. Overview

Nexa is a **traceable AI execution engine** for building, running, inspecting, and evolving structured AI workflows.

Internally, Nexa models work as **circuits**: dependency graphs of nodes. In beginner-facing UI, a circuit may be displayed as a **workflow**, but the canonical engine term remains **circuit**.

Nexa is not a generic workflow automation platform, chatbot framework, model training framework, or fixed pipeline orchestrator. Its core responsibility is to make AI execution structured, inspectable, reproducible where possible, and contract-governed.

Nexa does not promise fake determinism for non-deterministic AI models. Instead, it provides deterministic-friendly scheduling, immutable artifacts, execution traces, diffing, replay, and policy checks so that non-deterministic behavior is visible rather than opaque.

---

## 2. Architecture Layers

```text
User / Operator
  ↓
Product Shell / UI Layer
  ↓
Designer / Proposal Layer
  ↓
Storage and Approval Boundary
  ↓
Circuit
  ↓
Node  (only execution unit)
  ↓
Runtime  (dependency scheduler)
  ↓
Resources  (Prompt / Provider / Plugin)
  ↓
Artifact  (append-only output)
  ↓
Trace  (execution record)
```

The lower engine layers own structural truth, approval truth, execution truth, artifact truth, and trace truth.

The product shell may simplify display, rename concepts for beginners, hide advanced surfaces, and guide users through a first-success loop, but it must not redefine engine truth.

---

## 3. Core Execution Model

```text
Circuit
  ↓
Node
  ↓
Runtime
  ↓
Resources
  ↓
Artifact
  ↓
Trace
```

**Node is the only execution unit.**

A circuit defines topology. The runtime schedules node execution dynamically based on dependencies. All computation occurs inside nodes.

---

## 4. Circuit

A **Circuit** is a directed acyclic graph of nodes.

Responsibilities:

- define node set
- define dependency edges
- define execution topology
- expose declared inputs and outputs
- provide a structural unit that can be saved, validated, committed, run, compared, and reused

A circuit does **not** execute logic. All execution occurs inside nodes.

Example:

```text
Node A -> Node B -> Node D
       -> Node C ->
```

Circuit is the canonical engine/spec term. Beginner UI may display it as **Workflow** where the beginner-shell compression policy applies.

---

## 5. Node

A **Node** is the core execution unit. All computation occurs inside nodes.

A node may use any combination of:

- **Prompt** — constructs instructions for an AI model
- **Provider** — executes an AI model call
- **Plugin** — performs deterministic or bounded non-AI capability work

Depending on the node's role, any of these components may be absent.

Node execution is dependency-based: a node runs only when all required upstream dependencies are satisfied by the runtime scheduler.

### Node-internal phases

Within a node, resources may execute in three optional internal phases:

| Phase | Purpose | Constraint |
|---|---|---|
| Pre | validation, prompt resolution, data preparation | no provider model call |
| Core | provider call and controlled plugin/tool execution | primary execution |
| Post | output validation, persistence, trace emission | no provider model call |

These phases are an internal contract of a single node. They are not a system-level pipeline. System-level execution order is always determined by graph dependencies.

---

## 6. Runtime

The **Execution Runtime** schedules and executes nodes.

Runtime responsibilities:

- dependency-based node scheduling
- working context management
- resource execution orchestration
- artifact creation
- execution trace recording
- contract enforcement
- failure/recovery classification where supported
- policy and validation integration

Execution is dependency-driven. Nodes execute when their dependencies are satisfied, not according to a fixed global sequence.

---

## 7. Working Context

The **Working Context** is the shared data space inside node execution. All resources read from and write to this context through explicit keys.

Canonical key families:

```text
input.<field>
output.<field>
<context-domain>.<resource-id>.<field>
```

Examples:

```text
input.text
prompt.main.rendered
provider.openai.output
plugin.format.result
output.value
```

Context is not arbitrary shared memory. Resource reads and writes must remain bounded by contract.

---

## 8. Determinism and Reproducibility

Nexa is **deterministic-friendly**, not a false guarantee that all AI model outputs are deterministic.

The engine should provide deterministic behavior where it controls the process:

- dependency scheduling
- artifact hashing
- canonical serialization
- execution fingerprinting
- validation and policy decisions

When model calls or external services introduce non-determinism, Nexa must make those factors traceable through provider traces, artifacts, metadata, and diff/replay tooling.

---

## 9. Provider

**Providers** interface with AI model services.

Provider responsibilities:

- execute model calls through a normalized adapter boundary
- return a normalized provider result
- record provider trace metadata
- surface reason codes and errors in a structured form
- avoid leaking provider-specific behavior into core engine semantics

Provider availability may depend on configured credentials, managed access, or future product access paths.

---

## 10. Plugin

**Plugins** extend node capability.

Plugins must operate through controlled runtime/executor paths. Plugin trust is not inferred from AI authorship, generation success, or registry visibility alone.

Strict namespace rule:

```text
plugin.<plugin_id>.*    allowed
prompt.*                forbidden
provider.*              forbidden
output.*                forbidden unless mediated by approved runtime output binding
```

Plugin-related systems may include builder, intake, namespace policy, manifest, registry, verification, runtime loading, execution binding, context I/O, failure recovery, observability, governance, and lifecycle state-machine contracts.

Those systems extend the platform around the engine. They must not weaken the node execution invariant.

---

## 11. Artifact

**Artifacts** are immutable execution outputs.

Rules:

- artifacts are append-only
- existing artifacts are never modified
- new results create new artifacts
- artifacts are linked to execution context
- artifacts may be hashed for integrity and determinism validation

Artifacts are execution evidence, not temporary UI display state.

---

## 12. Trace

**Execution Traces** record runtime behavior.

Trace responsibilities:

- node execution status per node
- phase status where relevant
- resource execution metadata
- artifact lineage
- timing and runtime metadata
- failure/recovery events where relevant
- replay/diff/audit evidence

Trace is execution truth. UI may render trace summaries, timelines, and beginner-safe explanations, but must not fabricate trace truth.

---

## 13. Storage and Approval Boundary

Nexa uses role-aware storage semantics.

Canonical storage roles:

- **Working Save** — editable current state; may be incomplete or invalid; may carry UI-owned continuity state
- **Commit Snapshot** — approved structural state; must not carry canonical UI state
- **Execution Record** — run-history layer generated from executing an approved or runnable structure

Designer-originated changes must cross an explicit proposal boundary:

```text
Intent -> Patch -> Precheck -> Preview -> Approval -> Commit
```

The UI may compress this flow for beginners into one visible confirmation moment, but the underlying governance boundary remains intact.

---

## 14. UI / Product Shell Layer

The UI is a replaceable product shell above the engine.

Canonical direction:

```text
Engine
  -> UI Adapter / View Model Layer
  -> UI Module Slots
  -> Theme / Layout Layer
```

The UI may control:

- presentation
- beginner/advanced density
- terminology display
- onboarding guidance
- panel visibility
- workspace continuity
- result-reading ergonomics

The UI must not own:

- structural truth
- approval truth
- execution truth
- artifact truth
- storage lifecycle truth

Current product focus is general-user productization: completing the first-success loop and connecting Designer, validation, execution, and result reading into one coherent product path.

---

## 15. Validation Engine

Validation is a first-class system.

Validation responsibilities:

- validate structural correctness
- detect contract violations
- classify findings by severity and reason code
- block unsafe or incomplete execution/commit paths
- provide UI-compressible next actions for beginners

Validation findings must remain distinct from execution failures. A structure can be invalid before execution; an execution can fail after a valid structure starts running.

---

## 16. ExecutionConfig Architecture

Node behavior is expressed through **ExecutionConfig composition** where applicable.

Canonical flow:

```text
Engine
  -> GraphExecutionRuntime
  -> NodeSpec
  -> NodeSpecResolver
  -> ExecutionConfigRegistry
  -> ExecutionConfig
  -> NodeExecutionRuntime
```

ExecutionConfig must remain schema-validated and canonicalizable where required.

---

## 17. Design Principles

**Node as Sole Execution Unit** — No execution occurs outside a node.

**Dependency-Based Execution** — System order emerges from graph dependencies, not fixed pipelines.

**Traceability Over Opaqueness** — AI behavior must be inspectable through traces, artifacts, and diffs.

**Deterministic-Friendly Runtime** — Determinism is enforced where the engine controls the process; external non-determinism must be traceable.

**Append-Only Evidence** — Artifacts and execution records are not silently rewritten.

**Contract-Driven Architecture** — Behavior is governed by explicit specs and contracts.

**Safe Extensibility** — Providers, plugins, automation, UI modules, and future evolution systems extend Nexa without breaking core invariants.

**Product-Layer Compression Without Truth Mutation** — Beginner UX may simplify what is shown, but not what is true.

---

## 18. Forbidden Patterns

- Fixed-order pipeline execution as the system model
- Execution outside nodes
- Circuit-level logic execution
- Mutable artifact history
- Unrestricted plugin writes
- UI-owned structural, approval, or execution truth
- Designer AI directly mutating committed structural truth
- Commit Snapshots carrying canonical UI state
- Hidden runtime mutation without trace or artifact evidence
- Claiming deterministic LLM outputs without traceable constraints

---


## 19. Consolidated Architecture Invariants and Execution Rules

This section replaces the former `FOUNDATION_RULES.md` and `EXECUTION_RULES.md` root files.

### 19.1 Execution engine invariant

Nexa must be treated as an execution engine.

Nexa must not be treated as:

- a generic workflow tool
- a fixed pipeline system
- a prompt chaining system
- a chatbot framework

### 19.2 Node invariant

- Node is the only execution unit.
- No execution may occur outside a node.
- Node-internal phases are allowed only as a node contract.
- Node-internal phases must not become a system-level pipeline.

### 19.3 Circuit invariant

- Circuit defines connections, topology, declared inputs, and declared outputs.
- Circuit does not execute logic.
- Circuit-level hidden mutation is forbidden.

### 19.4 Execution-order invariant

- System-level execution is dependency-based.
- Runtime follows DAG dependency satisfaction.
- Fixed-order pipeline execution must not become the system model.
- Implicit execution-order dependencies are forbidden.

### 19.5 Artifact and trace invariant

- Artifacts are append-only and immutable after creation.
- Existing artifacts must not be modified in place.
- Execution behavior must remain traceable.
- Trace and artifact evidence must not be fabricated by UI or external tooling.

### 19.6 Determinism invariant

- Execution must be deterministic-friendly where the engine controls the process.
- Non-deterministic provider or external-service behavior must be traceable.
- Nexa must not claim deterministic LLM outputs without traceable constraints.

### 19.7 Plugin namespace invariant

Plugins may write only to approved plugin-owned namespaces by default:

```text
plugin.<plugin_id>.*
```

Plugins must not directly write to:

- `prompt.*`
- `provider.*`
- `output.*`

Any future mediated output binding or delivery capability must be governed by explicit runtime contracts.

### 19.8 Working Context invariant

Working Context keys must follow canonical key families:

```text
input.<field>
output.<field>
<context-domain>.<resource-id>.<field>
```

The three-segment form is used for prompt/provider/plugin/system domains.

### 19.9 Storage and approval invariant

- Working Save may be incomplete or invalid and may carry UI-owned continuity state.
- Commit Snapshot represents approved structural state and must not carry canonical UI state.
- Execution Record is run-history evidence and must not be confused with editable structural state.
- Designer-originated structural changes must cross `Intent -> Patch -> Precheck -> Preview -> Approval -> Commit`.

### 19.10 Spec synchronization invariant

- Specs and implementation must remain consistent.
- Contract drift is a system risk.
- Violations of these invariants must be treated as architectural violations, not as harmless implementation details.

## 20. Repository Orientation

Representative repository structure:

```text
src/
    artifacts/      — artifact writing and artifact identity
    circuit/        — circuit model, scheduling, validation
    cli/            — CLI commands
    config/         — execution configuration loading and registry
    contracts/      — contract versions, context keys, reason codes
    designer/       — proposal-oriented design assistance
    engine/         — runtime, trace, diff, regression, policy
    models/         — shared decision and view models
    platform/       — plugin/provider/platform integration
    policy/         — gate policy and reason-code policy
    prompts/        — prompt registry and rendering
    providers/      — AI provider adapters
    storage/        — role-aware save/load/commit lifecycle
    ui/             — Python-side UI adapter, shell, panels, i18n, view models
    utils/          — utilities

tests/
docs/
examples/
```

Actual structure may evolve, but changes must preserve the architecture invariants in this document and the project direction/scope in `ROADMAP.md`.

---

End of Architecture Document
