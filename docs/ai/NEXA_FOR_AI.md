# Nexa Guide for AI Systems

Status: Canonical AI Contributor Guide
Scope: AI coding assistants, code-review assistants, documentation assistants, and implementation agents working on Nexa

---

## 1. Purpose

This document is the single canonical guide for AI systems working on the Nexa repository.

Read this before generating code, modifying files, reviewing patches, writing implementation handoffs, or updating project documentation.

This document replaces model-specific root guides such as Claude-only prompt or guide documents. Model-specific instructions may exist outside the repository as user prompts, but the repository should use this file as the AI-facing source of truth.

---

## 2. Canonical Root Documents

The root documentation model is intentionally small.

Use these documents as the first reference set:

```text
README.md        — first entry point for humans and external readers
ROADMAP.md       — consolidated vision, strategy, scope, and roadmap
ARCHITECTURE.md  — technical architecture, invariants, execution rules
NEXA_FOR_AI.md   — AI contributor guide
```

Do not treat deleted or deprecated root documents as authoritative.

Deprecated root documents include:

```text
VISION.md
STRATEGY.md
PROJECT_SCOPE.md
FOUNDATION_RULES.md
EXECUTION_RULES.md
CLAUDE_GUIDE.md
CLAUDE_MASTER_PROMPT.md
```

Their surviving content belongs in `ROADMAP.md`, `ARCHITECTURE.md`, or this file.

---

## 3. What Nexa Is

Nexa is a contract-driven AI execution engine for structured, traceable AI computation.

Its core model is:

```text
Circuit
→ Node
→ Runtime
→ Prompt / Provider / Plugin
→ Artifact
→ Trace
```

Nexa is not:

- a chatbot framework
- a fixed pipeline orchestrator
- a prompt-chain wrapper
- a generic no-code automation clone
- a model training framework

Nexa may expose product-shell, builder, automation, plugin, or UI layers above the engine, but those layers must not redefine engine truth.

---

## 4. Non-Negotiable Architecture Invariants

All implementation work must preserve these rules.

### 4.1 Node is the only execution unit

Execution happens through nodes.

A circuit defines topology. It does not execute logic by itself.

### 4.2 Execution is dependency-driven

System-level execution order is determined by dependency resolution.

Do not introduce a fixed global pipeline order.

### 4.3 Node-internal phases are not a system pipeline

A node may internally use optional phases:

```text
pre   — validation, prompt resolution, data preparation
core  — primary execution, including AI provider calls where applicable
post  — output validation, persistence, trace emission
```

These phases are internal to one node.

Never describe Nexa's system-level runtime as a `prompt → provider → plugin` pipeline.

### 4.4 Artifacts are append-only

Artifacts are immutable execution outputs.

Allowed:

```python
artifact.append(...)
```

Forbidden:

```python
artifact.update(...)
artifact.replace(...)
```

### 4.5 Trace is execution truth

Execution trace is not a UI convenience layer.

Trace must remain a first-class record of runtime behavior, node status, artifact lineage, and relevant execution metadata.

### 4.6 Determinism must be handled precisely

Do not overclaim deterministic LLM output.

Correct framing:

```text
Nexa is deterministic-friendly and traceable.
Identical deterministic inputs and configuration should produce identical deterministic artifacts.
Non-deterministic provider behavior must be captured, compared, and made inspectable through trace and artifacts.
```

Incorrect framing:

```text
Nexa guarantees deterministic output for all LLM-backed executions.
```

### 4.7 Contracts govern behavior

Runtime, storage, provider, plugin, validation, artifact, and UI boundaries must follow explicit contracts.

If code and contract disagree, do not silently patch around the disagreement. Identify the mismatch and fix the correct layer.

---

## 5. Engine Truth vs Product/UI Shell

Nexa may have a user-facing product shell, beginner shell, designer flow, visual graph workspace, or automation surface.

Those surfaces are presentation and control layers above the engine.

They must not own:

- structural truth
- approval truth
- execution truth
- artifact truth
- storage lifecycle truth

The engine remains authoritative.

UI-owned state may include:

- panel layout
- selected object
- visual density
- theme
- workspace continuity
- beginner/advanced visibility state

UI-owned state must not be treated as execution or structural truth.

---

## 6. Storage and Savefile Rules

The `.nex` family is role-aware.

Important storage roles include:

```text
Working Save      — editable current work state; may include UI-owned continuity data
Commit Snapshot   — approved structural anchor; must not carry canonical UI state
Execution Record  — run-history layer produced by execution
```

A Working Save may be incomplete or invalid while the user is editing.

A Commit Snapshot must represent approved structural state.

Execution history must not be collapsed into savefile editing state.

---

## 7. Working Context Schema

Execution resources interact through Working Context.

Canonical context key families:

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

Do not invent ad hoc context namespaces.

---

## 8. Provider Rules

Providers adapt AI model services into Nexa runtime behavior.

Provider implementations should:

- return normalized provider results
- preserve provider trace information
- expose reason codes where applicable
- avoid hidden side effects
- keep provider-specific behavior behind provider adapters

Provider non-determinism must be made inspectable rather than hidden.

---

## 9. Plugin Rules

Plugins extend nodes with bounded non-AI capabilities.

Plugin namespace rules are strict.

Allowed plugin writes:

```text
plugin.<plugin_id>.*
```

Forbidden plugin writes:

```text
prompt.*
provider.*
output.*
artifact.*
input.*
system.*
```

Plugins must not receive unlimited namespace access by omission.

Plugin behavior must remain bound by the plugin contract family, including namespace policy, verification, runtime loading, execution binding, context I/O, failure/recovery, observability, governance, and lifecycle rules where applicable.

---

## 10. Designer AI and Proposal Flow

Designer AI is not an execution resource.

Designer AI is a proposal-producing design layer above the engine.

Canonical proposal flow:

```text
Intent
→ Patch
→ Precheck
→ Preview
→ Approval
→ Commit
```

Designer AI must not:

- silently mutate committed structural truth
- bypass approval
- install plugins directly
- mark generated plugins as trusted
- invent successful validation or verification results
- redefine runtime contracts

Designer AI may:

- interpret user intent
- propose circuit changes
- propose plugin-builder input
- explain risk
- produce previewable patch plans
- request clarification when needed

---

## 11. Automation and External Delivery

Automation may start circuit execution and deliver selected outputs, but automation must not bypass engine truth.

Automation-related behavior must remain:

- trigger-explicit
- run-identity-bound
- traceable
- quota-aware
- safety-aware
- artifact-aware
- policy-bounded

External delivery is not an arbitrary side effect.

It is a governed result-export action attached to a concrete execution context.

---

## 12. Commercial and Product Constraints

Nexa is intended to become a SaaS/mobile-capable product.

Implementation should preserve:

- trustworthy engine behavior
- extensibility without core pollution
- clear user-facing product flows
- cost-aware provider use
- safe plugin boundaries
- low legal/IP/API-policy risk

Cost responsibility model:

- Operation AI for running Nexa operations may be paid by the Nexa operator.
- Designer AI and Provider AI inside user circuits should be paid by the end user or their configured provider access path.

Do not hard-code assumptions that make the operator silently responsible for all user circuit provider costs unless explicitly instructed.

---

## 13. Development Workflow for AI Assistants

Use the narrowest safe analysis depth.

### 13.1 Fast Path

Use when the task is narrow and low-risk.

Inspect:

- the immediately preceding commit note when available
- changed files directly relevant to the request
- directly referenced tests or contracts

### 13.2 Safe Path

Default for most coding work.

Inspect:

- changed files
- directly related dependencies
- relevant contracts
- relevant tests
- related public API or loader/validator boundaries

### 13.3 Deep Path

Use only when justified by risk.

Triggers include:

- architecture or contract changes
- runtime/import/storage changes
- unclear file state
- failing tests without a local cause
- conflicting docs or code
- high regression risk
- package-wide behavior changes

Do not scan the whole repository by default merely to appear thorough.

---

## 14. Testing Rules

Do not claim unrun tests passed.

Default testing policy:

- run directly relevant tests first
- run broader tests when the change affects runtime, contracts, storage, loaders, validation, public APIs, or shared infrastructure
- full pytest is not mandatory before every patch delivery unless scope or risk justifies it

Never weaken assertions to force a pass.

Never modify tests to accept incorrect behavior.

When tests are not run, state that clearly in the handoff.

---

## 15. Documentation Update Rules

Update documentation when a change affects:

- architecture invariants
- public CLI/API behavior
- storage semantics
- savefile shape
- contract versions
- plugin/provider behavior
- UI/product shell boundary
- user-facing product flow

Do not create duplicate root documents for the same truth.

Prefer updating the canonical document:

```text
README.md        — entry and usage
ROADMAP.md       — vision, strategy, scope, roadmap
ARCHITECTURE.md  — structure, invariants, execution rules
NEXA_FOR_AI.md   — AI contributor rules
```

---

## 16. File and Artifact Delivery Rules

When producing replacement files:

- preserve repository-relative paths when packaging
- provide direct links to individual files and a zip when useful
- do not include unnecessary files
- do not put version numbers in filenames unless the repository already requires it
- put version/status information inside the document body when needed

---

## 17. Commit and Handoff Rules

When preparing commit instructions or handoff notes:

- use GitHub `main` as the default branch
- prefer `git add .` when the user is committing a coherent patch
- pair code commits with an Obsidian-style note when requested
- note title format: `YYYY-MM-DD__[]_<short-description>`
- keep note title and body separate
- write handoffs in English spec style unless the user requests otherwise

Do not include commands that rely on unavailable local state unless the user provided that context.

---

## 18. Hallucination Guard

Never:

- invent files
- invent APIs
- invent passing test results
- invent contract versions
- pretend to inspect files that were not inspected
- silently assume a missing repository state
- replace root-cause reasoning with blind patching

When information is missing, use the available repository/file context first.

If uncertainty remains and the task cannot be safely completed, state the uncertainty clearly and provide the safest partial result.

---

## 19. Default Implementation Bias

Prefer:

- minimal, contract-aligned changes
- explicit data flow
- typed boundaries where the surrounding codebase supports them
- deterministic-friendly behavior
- traceable outcomes
- small, composable functions
- preserving extension boundaries

Avoid:

- hidden side effects
- broad rewrites without need
- convenience-driven architecture drift
- overbuilding future features
- mixing optional product-shell concerns into core engine logic
- creating long-lived duplicate documents

---

## 20. Final Rule

When working on Nexa, optimize for this sequence:

```text
preserve architecture
→ preserve contracts
→ preserve runtime truth
→ make the smallest safe change
→ test the affected behavior
→ document only what changed
→ hand off clearly
```

End of AI Guide.
