# Nexa Roadmap

Status: Official Single Source of Truth  
Scope: Vision, strategy, roadmap, project scope, current priorities, and long-term direction  
Supersedes: `VISION.md`, `STRATEGY.md`, `PROJECT_SCOPE.md`, and all previous standalone roadmap drafts

---

## 0. Document Role

This document is the single authoritative direction document for Nexa.

It replaces the previous three-document split:

```text
VISION.md         -> absorbed into this ROADMAP.md
STRATEGY.md       -> absorbed into this ROADMAP.md
PROJECT_SCOPE.md  -> absorbed into this ROADMAP.md
ROADMAP.md        -> replaced by this integrated ROADMAP.md
```

After adopting this document, the project should keep only:

```text
ROADMAP.md
```

`VISION.md`, `STRATEGY.md`, and `PROJECT_SCOPE.md` should be deleted rather than maintained as parallel direction/scope documents.

Reason:

- Vision, strategy, and roadmap are currently tightly coupled.
- Maintaining them separately creates document drift.
- Future AI assistants and contributors need one clear source of truth for direction and scope.
- Volatile implementation details should live in commit notes, CI output, and handoff documents, not in multiple top-level direction files.

---

## 1. Product Identity

Nexa is a structurally verifiable AI execution engine becoming a general-user AI workflow product.

It is not a simple automation tool, prompt runner, agent wrapper, or decorative workflow dashboard.

Nexa controls AI execution through:

- explicit circuit structure
- dependency-based node scheduling
- contract-governed behavior
- traceable execution
- append-only artifacts
- proposal-first governance
- bounded provider and plugin extension points

The core identity is:

```text
AI work as structured, inspectable, reproducible, contract-governed computation.
```

The current product identity is:

```text
A general user can describe a goal, inspect what Nexa will build, approve it, run it, and understand the result.
```

The engine remains structurally rich. The product surface should progressively expose that structure only when it helps the user.

---

## 2. Why Nexa Exists

AI systems are becoming more capable, but the infrastructure for running them reliably has not kept pace.

Most AI applications still rely on fragile orchestration patterns that become difficult to inspect, reproduce, govern, or extend as they grow.

Typical failure modes include:

- unpredictable outputs
- weak reproducibility
- poor visibility into intermediate computation
- unclear responsibility between multiple AI systems
- unsafe extension boundaries
- insufficient auditability after execution
- hidden mutation of structure or state
- unclear distinction between drafts, approvals, and run history

Nexa exists to solve this by treating AI work as structured computation rather than unbounded conversation or ad hoc automation.

---

## 3. Core Execution Model

Nexa treats AI tasks as nodes in a computation graph.

Execution order is determined by dependency resolution, not by a fixed global pipeline.

```text
Input
  -> Circuit (DAG of nodes)
  -> Runtime (dependency scheduler)
  -> Providers / Plugins
  -> Artifacts (append-only outputs)
  -> Trace (complete execution record)
```

Core interpretation:

- Circuit is the structural program unit.
- Node is the sole execution unit.
- Runtime schedules nodes by dependency.
- Providers and plugins are execution resources bound through contracts.
- Artifacts are append-only evidence.
- Trace is first-class execution truth.
- UI may present and route actions, but it does not own structural, approval, execution, or storage truth.

---

## 4. Long-Term Vision

Nexa's long-term goal is to become a universal runtime and product platform for AI computation systems.

Future applications include:

- general-user AI workflow creation
- production AI execution systems
- multi-agent AI systems
- scientific AI computation frameworks
- long-running AI automation environments
- governed plugin ecosystems
- circuit experimentation and evolution systems
- reusable workflow/template ecosystems

The long-term direction is:

```text
Verifiable AI Execution Engine
  -> General-User Product Shell
  -> Automation / Delivery / Plugin Builder
  -> Experimentation and Evolution Layer
```

All future layers must preserve the same foundation:

```text
dependency-based execution
+ explicit contracts
+ traceable runtime behavior
+ append-only artifacts
+ safe extension boundaries
+ proposal-first governance
```

---

## 5. Strategic Direction

Nexa has moved beyond early engine proof.

The main strategic question is no longer:

```text
Can a structured AI execution engine exist?
```

The current strategic question is:

```text
Can a general user successfully use Nexa without first understanding the full engine model?
```

The current strategy is:

```text
1. Preserve the verified engine foundation.
2. Close the first-success loop for general users.
3. Make product state understandable without exposing internal complexity too early.
4. Expand into automation, plugin builder, and evolution after the product loop is stable.
```

The immediate product loop is:

```text
start -> understand -> run -> read the result
```

Until this loop is reliable, deeper architecture expansion should remain secondary unless it directly removes a blocker in the first-success loop.

---

## 6. Primary Target

The primary target is general users.

This does not mean the engine becomes simplistic.

It means the first visible surface must not require the user to understand the full internal model before achieving value.

Nexa should support two layers at the same time:

```text
Beginner-facing product language
  -> workflow, step, AI model, result, fix, run

Canonical engine language
  -> circuit, node, provider, artifact, validation, execution record
```

The beginner layer is a display and interaction strategy. It must not redefine engine truth.

---

## 7. Non-Negotiable Architecture Boundaries

The following boundaries remain fixed:

- Circuit is the structural program unit.
- Node remains the sole execution unit.
- Runtime execution is dependency-driven.
- Artifacts are append-only evidence.
- Trace is first-class execution truth.
- Validation and policy gates must remain explicit.
- UI does not own structural truth, approval truth, execution truth, or storage truth.
- Designer AI proposes; it does not silently mutate committed structural truth.
- Designer-originated structural changes must pass through:

```text
Intent -> Patch -> Precheck -> Preview -> Approval -> Commit
```

- Plugins and external capabilities must remain namespace-bounded and policy-governed.
- Storage roles must remain conceptually separate even when beginner UI compresses terminology.
- Working Save, Commit Snapshot, and Execution Record must not collapse into one ambiguous state.
- Subcircuits must preserve the rule that Node is the runtime execution unit.
- Evolution must occur through governed inter-run proposal/evaluation loops, not uncontrolled runtime self-modification.

These constraints are product assets, not implementation burdens.

---


## 8. Project Scope

This section replaces the previous standalone `PROJECT_SCOPE.md`.

### What Nexa is

Nexa is a traceable AI execution engine with a product shell for building, running, inspecting, and improving structured AI workflows.

Internally, Nexa models workflows as **circuits**: dependency graphs of nodes. Beginner-facing UI may display circuits as **workflows**, but the canonical engine/spec term remains **circuit**.

Nexa focuses on:

- node-based AI execution
- dependency-driven circuit runtime
- traceable AI computation
- reproducible and inspectable execution where possible
- append-only artifacts and execution records
- contract-driven reliability
- provider and plugin extensibility under explicit boundaries
- general-user productization through a first-success loop

### What Nexa is not

Nexa is not:

- a generic automation tool
- a chatbot framework
- a model training framework
- a fixed pipeline orchestrator
- an unrestricted plugin marketplace
- a cloud infrastructure product by default
- a promise of deterministic LLM outputs

Nexa may later support automation triggers, external delivery, SaaS deployment, collaboration, plugin ecosystems, or evolution systems. Those are scoped extensions, not replacements for the core execution engine.

### Core responsibilities

The project includes:

- circuit-based AI workflow execution
- node-based execution with dependency scheduling
- Working Context-based resource interaction
- provider abstraction
- plugin execution under namespace and runtime controls
- prompt/resource management
- artifact management
- execution trace recording
- run comparison and diff
- replay/audit evidence where possible
- validation and policy gating
- role-aware savefile/storage lifecycle
- UI adapter/view model and product-shell foundations
- beginner/advanced presentation boundaries
- Designer proposal workflow boundaries
- documentation/spec synchronization

### Current active scope

The current active scope is **general-user productization**.

The immediate product goal is to close the first-success loop:

```text
start -> understand -> run -> read the result
```

This includes:

- beginner shell enforcement
- Designer-first empty workspace behavior
- beginner terminology and i18n completeness
- validation compression into status, one-sentence cause, and next action
- guided provider/API access paths
- template/gallery support where appropriate
- execution feedback and result-reading flow
- clear separation between validation blockage and execution failure
- progressive unlock of advanced graph/trace/diff/history surfaces

This does not change engine truth. It changes how the product exposes the engine to general users.

### Scoped extension areas

The following are in scope as governed extension areas, but they must not displace the first-success loop:

- Product Shell and UI: adapter/view-model, Graph/Inspector/Validation/Execution/Designer surfaces, beginner/advanced shell behavior, accessibility, localization, onboarding, result reading.
- Designer AI: proposal-producing design assistance governed by `Intent -> Patch -> Precheck -> Preview -> Approval -> Commit`.
- Plugin Builder: governed plugin proposal, validation, verification, registration, loading, execution binding, observability, governance, and lifecycle management.
- Automation and Delivery: explicit trigger and delivery rules that preserve execution, artifact, trace, quota, and safety boundaries.
- Evolution / Experimentation: long-term scope for benchmarked, policy-bounded circuit evaluation and improvement.

## 9. Current State Snapshot

Nexa has completed substantial engine, storage, validation, trace, and UI foundation work.

The active center is now:

```text
General-user productization
  -> first-success loop closure
  -> returning-user continuity
  -> automation / plugin builder / evolution expansion
```

Current interpretation:

- Engine foundation is no longer the primary bottleneck.
- UI foundation and product-flow shell work are advanced enough that the next work is enforcement, integration, and live product usability.
- Beginner shell behavior must be enforced in code, not only described in policy.
- Deep surfaces such as graph, trace, diff, storage, artifact, and history remain important, but should not block first-session success.
- Volatile commit hashes and test counts should be tracked in commit notes, CI, and handoff documents rather than hardcoded as roadmap truth.

---

## 10. Current Strategic Priority

### Priority 1 — First-Success Loop Closure

A general user must be able to:

1. open Nexa
2. describe a goal
3. understand the proposed workflow
4. approve or revise it
5. run it
6. read the result
7. know what to do if blocked

This is the current strategic center.

Required product capabilities:

- Designer-first empty workspace
- beginner terminology remapping
- compressed validation display
- one visible proposal confirmation moment
- clear run action and run status
- understandable result display
- first-success unlock for deeper surfaces

---

### Priority 2 — Returning-User Continuity

After first success, a returning user must be able to:

- find prior workflows
- understand what was saved
- revisit previous results
- continue where they left off
- inspect deeper structure when ready

This requires:

- stable workspace identity
- clear saved state
- result history surfaced in product language
- progressive access to graph, trace, diff, artifact, and storage views

---

### Priority 3 — Practical Access and Setup

Raw provider setup must not remain a beginner-facing blocker.

Possible paths include:

- managed provider access
- guided API key setup
- provider diagnostics presented in product language
- safe degraded demo mode where feasible

The exact commercial and infrastructure path may remain open, but the strategy is fixed:

```text
Raw environment-variable setup cannot be the default beginner experience.
```

---

### Priority 4 — Product-Ready UI Integration

The UI should continue to follow the architecture:

```text
Engine
  -> UI Adapter / View Model Layer
  -> UI Module Slots
  -> Theme / Layout Layer
```

The UI strategy is not to build a decorative shell.

It is to expose engine truth through safe view models and controlled action intents.

The current UI priority is enforcement and integration, not more speculative UI documentation.

---

## 11. Active Roadmap

### Phase A — General-User First-Success Closure

Goal:
A non-technical user can open Nexa, describe a goal, approve the proposed workflow, run it, and read the result without expert assistance.

Required outcomes:

- Designer-first empty workspace behavior
- beginner-facing terminology mapping:
  - Circuit -> Workflow
  - Node -> Step
  - Provider -> AI model
- validation compressed into:
  - status
  - one-sentence cause
  - one clear next action
- proposal flow shown as one visible confirmation moment
- run action and run status presented clearly
- result display suitable for a first-time user
- first-success unlock for advanced surfaces
- no mandatory exposure to trace, diff, storage roles, or internal validator details during first session

Primary implementation areas:

- builder shell routing
- i18n / terminology layer
- panel coordination and advanced-surface gating
- Designer panel and proposal workflow
- execution panel and result display
- first-success detection and unlock state

Exit criteria:

```text
empty workspace
-> natural-language request
-> workflow preview
-> approve or revise
-> run
-> result
-> optional deeper inspection
```

A user must complete this flow without needing to understand internal engine vocabulary.

---

### Phase B — Returning-User Continuity

Goal:
A returning user can continue meaningful work after first success.

Required outcomes:

- user can find prior workflows
- user can distinguish current work from prior results in product language
- user can reopen recent workflows
- user can revisit result history
- user can continue where they left off
- deeper views become available without overwhelming the default surface

Key surfaces:

- workspace list / recent workflows
- saved-state indicator
- result history summary
- run history summary
- progressive graph visibility
- trace / artifact / diff access after unlock

---

### Phase C — Practical Access and Setup

Goal:
A beginner can start using Nexa without raw environment-variable setup becoming the first obstacle.

Required outcomes:

- provider readiness is explained in product language
- missing provider setup produces clear next actions
- guided setup path exists if user-owned API keys are required
- managed or demo access path remains open as a product decision
- provider diagnostics do not leak as raw technical failure unless the user enters advanced mode

---

### Phase D — Product-Ready Localization

Goal:
Nexa can support at least Korean and English without duplicating UI logic or hardcoding user-facing strings.

Required outcomes:

- beginner-facing terminology is localizable
- validation messages are localizable
- empty/loading/error states are localizable
- action labels are localizable
- first-success flow text is localizable
- advanced engine terms remain canonical and translatable without semantic drift

---

### Phase E — Automation and Output Delivery

Goal:
Nexa can run useful workflows beyond manual one-off execution.

Required outcomes:

- explicit automation trigger model
- schedule/event-based circuit launch
- output destination contract
- delivery success/failure traceability
- quota and safety boundaries
- observable automation lifecycle

Canonical direction:

```text
external event or schedule
-> trigger evaluation
-> circuit launch
-> execution
-> result selection
-> delivery
```

Automation must not bypass execution truth, artifact truth, or approval boundaries.

---

### Phase F — Plugin Builder and Governed Plugin Ecosystem

Goal:
Nexa can let users and Designer AI propose plugins while preserving trust boundaries.

Required outcomes:

- Plugin Builder as the single external product surface for plugin construction
- Designer-to-Plugin-Builder intake boundary
- namespace policy validation
- runtime artifact / manifest contract
- verification and test policy
- registry contract
- runtime loading / installation rules
- runtime execution binding
- plugin context I/O
- failure / recovery
- observability
- governance
- lifecycle state machine

Core rule:

```text
Designer AI proposes.
Plugin Builder validates, verifies, and governs.
Runtime only executes approved, bounded, observable plugin capabilities.
```

---

### Phase G — Experiment and Evolution Layer

Goal:
Nexa can evaluate, compare, and improve circuits across runs without violating core invariants.

Required outcomes:

- benchmark task abstraction
- evaluation result model
- multi-objective scoring
- population and lineage model
- Pareto-based selection
- mutation and crossover operators
- regression and complexity guards
- evolution trace / attribution
- hidden benchmark and anti-overfitting layer
- end-to-end evolution MVP validation

Core rule:

```text
Evolution changes occur between executions through governed proposal/evaluation loops,
not through uncontrolled runtime self-modification.
```

---

## 12. Historical Foundation Work

This section preserves the completed or substantially closed foundation work.

It remains important, but it is no longer the leading roadmap story.

### Foundation 1 — Core Engine Stabilization and Runtime Durability

Completed or substantially closed areas:

- DAG-based circuit execution
- dependency-based node scheduling
- artifact system
- execution trace
- provider abstraction
- plugin system with restricted namespaces
- validation engine
- contract-driven architecture

---

### Foundation 2 — Observability and Determinism Tooling

Completed or substantially closed areas:

- execution timeline
- replay
- determinism validator
- artifact hashing / snapshot / diff
- regression detector
- regression formatter and policy engine
- audit pack
- provenance graph
- run comparator
- CLI support for run, compare, diff, export, replay, info, and task commands

---

### Foundation 3 — Role-Aware Savefile / Storage Lifecycle

Completed or substantially closed areas:

- unified `.nex` family
- `working_save` / `commit_snapshot` distinction
- Execution Record as run-history layer
- role-aware loading and validation
- typed-model split
- commit-boundary rules for UI-owned continuity state

---

### Foundation 4 — UI Foundation / i18n Foundation

Completed or substantially closed areas:

- UI adapter / view-model boundary
- Graph / Inspector / Validation / Execution / Designer module surfaces
- Trace / Timeline / Artifact / Storage / Diff expansion surfaces
- builder shell and end-user-flow surfaces
- workspace-level editor and runtime monitoring surfaces
- English / Korean localization foundation
- Working Save-side UI continuity and snapshot-side UI exclusion

---

### Foundation 5 — Product-Flow Shell Convergence

Completed or substantially closed areas:

- journey projection
- runbook projection
- handoff projection
- readiness projection
- E2E path projection
- closure projection
- transition projection
- gateway projection tied to proposal/commit and execution-launch gates
- E2E proof projection tied to completed-run commit anchoring and follow-through evidence

Interpretation:

Phase 5 established much of the product-flow shell language.

The current work is to convert that structure into reliable first-success product behavior.

---

## 13. Deferred / Guarded Work

The following should not displace first-success closure:

- advanced collaboration systems
- public sharing and marketplace surfaces
- fully autonomous evolution
- distributed runtime
- unrestricted dynamic graph mutation
- plugin marketplace before plugin trust lifecycle is complete
- UI polish unrelated to first-success comprehension
- speculative architecture documents with no implementation path
- autonomous circuit evolution before evaluation and product feedback loops are stable

This does not mean those areas are unimportant.

It means they are not the current strategic bottleneck.

---

## 14. Current-Stage Non-Priorities

The current stage should not prioritize:

- adding new deep architecture layers that do not unblock first-success
- exposing graph/trace/diff/history before the user understands the basic product loop
- making the UI look sophisticated while the first run remains unclear
- building collaboration before single-user review/run/result is reliable
- broad plugin marketplace work before plugin trust boundaries are implemented
- evolution automation before benchmark/evaluation/product feedback loops are stable

---

## 15. Success Criteria

The roadmap is working when a general user can complete this sequence without expert assistance:

```text
Open Nexa
-> describe a desired workflow
-> inspect a plain-language preview
-> approve it
-> run it
-> see progress
-> read the result
-> understand what happened next
```

The roadmap is not yet working if the user must first understand:

- raw circuit internals
- storage role semantics
- trace/diff/history surfaces
- provider environment variables
- validator internals
- proposal/patch/precheck terminology

Those concepts may become visible later, but they should not be mandatory for first success.

---

## 16. Baseline Tracking Policy

This roadmap should avoid embedding volatile commit hashes and test counts as permanent roadmap truth.

Authoritative volatile implementation state should live in:

- latest commit notes
- CI output
- handoff documents
- current implementation state snapshots

This roadmap should track:

- product identity
- strategic priority
- phase boundaries
- architectural invariants
- exit criteria
- deferred work
- long-term direction

It should not become a stale changelog.

---

## 17. Update Policy

This document should be updated when one of the following changes:

- current active phase changes
- strategic priority changes
- architecture invariants change
- a major phase exits or enters active implementation
- a previously deferred area becomes active
- the product target changes

This document should not be updated for every commit, test count, local patch, or temporary implementation detail.

---

## 18. Final Direction

Nexa should become a general-purpose runtime and product platform for AI computation systems:

- understandable for general users
- structurally verifiable for developers
- traceable for reviewers
- extensible for plugins and automation
- evolvable through governed experiment loops

The near-term mission is narrower and more urgent:

```text
Close the first-success loop.
```

Everything else should support that mission or wait behind it.

---

End of Roadmap
