# Designer AI Input Exposure Rules v0.1

## Recommended save path
`docs/specs/designer/designer_ai_input_exposure_rules.md`

## 1. Purpose

This document defines the canonical rules for which information from Nexa
may be exposed to Designer AI for circuit-generation work.

Its purpose is to ensure that Designer AI receives:
- enough information to generate bounded proposals
- no unnecessary or over-privileged information
- a stable and explainable input surface

This document is about **input exposure**, not about later intent/patch/precheck logic.

## 2. Core Decision

Designer AI must not receive the whole internal system by default.

Official rule:

- expose only the information needed for the current design task
- prefer structured exposure over raw dump exposure
- expose authoritative design-state fields explicitly
- mark reference-only fields as reference-only
- keep authority outside the exposed payload unless explicitly represented as forbidden

In short:

Designer AI receives a bounded design-facing projection of Nexa state.

## 3. Exposure Principles

### 3.1 Need-to-design principle
A field may be exposed only if it can materially help:
- category selection
- scope-bounded proposal generation
- resource-aware design
- risk-aware design
- constraint-aware design

### 3.2 Structured over raw
Prefer:
- normalized summaries
- ids and references
- scoped lists
- status flags

Avoid raw transcript or raw internal object dumps unless unavoidable.

### 3.3 Current reality first
Expose the current Working Save reality before speculative or historical context.

### 3.4 Scope-first exposure
If the allowed scope is narrow, expose narrow context first.

### 3.5 Reference-only separation
Some fields may be visible only as context, not as permission.

## 4. Canonical Exposure Categories

Designer AI input may expose information from the following categories:

1. current structural reality
2. current user focus
3. permitted modification boundary
4. available design resources
5. design objective
6. hard and soft constraints
7. current findings
8. current risks
9. revision/approval flow state
10. conversation summary
11. output expectations
12. forbidden authority

## 5. Always-Expose Fields

The following should normally always be exposed for real design work.

### 5.1 Current Working Save summary
Expose:
- savefile reference
- revision id
- mode
- circuit summary
- touched validity status
- node ids
- edge ids
- output ids
- prompt/provider/plugin refs used by the draft

Reason:
Designer AI must know what currently exists.

### 5.2 Target scope
Expose:
- mode
- touch budget
- allowed node refs
- allowed edge refs
- allowed output refs
- destructive allowance

Reason:
Designer AI must know where it is allowed to act.

### 5.3 Objective
Expose:
- primary goal
- secondary goals
- success criteria
- preferred behavior

Reason:
Without objective, design becomes under-specified.

### 5.4 Constraints
Expose:
- hard constraints
- soft preferences
- safety level
- human review requirement
- output requirements
- forbidden patterns

Reason:
Constraints directly shape valid proposal space.

### 5.5 Findings and risks
Expose:
- blocking findings
- warning findings
- confirmation findings
- unresolved high risks
- severity summary

Reason:
Designer AI must know what is already wrong or dangerous.

### 5.6 Available resources
Expose:
- available prompt ids
- available provider ids
- available plugin ids
- availability status
- restrictions or notes

Reason:
Designer AI must not propose unavailable components as if they are ready.

### 5.7 Forbidden authority
Expose:
- may_commit_directly = false
- may_redefine_engine_contracts = false
- may_bypass_precheck = false
- may_bypass_preview = false
- may_bypass_approval = false
- may_mutate_committed_truth_directly = false

Reason:
The boundary must be explicit, not implicit.

## 6. Conditionally Exposed Fields

These fields may be exposed depending on task mode.

### 6.1 Current selection
Expose when:
- selection exists
- the task is bounded by current focus
- narrow patching is preferred

### 6.2 Commit Snapshot context
Expose when:
- read-only comparison matters
- the user asks to align draft with approved state
- the task involves rollback / divergence analysis

Expose as reference-only, not editable truth.

### 6.3 Execution Record summary
Expose when:
- design must respond to past run failures
- repair proposals depend on run history
- performance/cost optimization depends on observed execution

### 6.4 Conversation context
Expose as summary, not raw transcript, unless a more detailed trace is essential.

## 7. Exposure Granularity Rules

### 7.1 Full-circuit exposure
Use when:
- creating a new circuit
- broad modification is allowed
- graph-wide reasoning is required

### 7.2 Selection-scoped exposure
Use when:
- scope is node_only or subgraph_only
- prior proposals were too broad
- user correction narrowed the target

### 7.3 Summary-first exposure
Use by default for:
- large circuits
- long histories
- many findings
- many resources

### 7.4 Expand-on-demand exposure
If the design task cannot be completed safely from summary-first exposure,
expand only the needed slice.

## 8. Canonical Exposure Shape

Recommended top-level exposure blocks:

- design_reality
- focus_scope
- available_resources
- objective
- constraints
- findings
- risks
- revision_flow
- conversation_summary
- output_contract
- forbidden_authority

## 9. Reference-Only Fields

The following may be exposed as context but must be clearly marked as non-authoritative for mutation:

- commit snapshot summaries
- historical execution summaries
- UI state hints
- non-selected graph areas when scope is narrow
- archived rejected proposals

## 10. Exposure Safety Rules

### 10.1 Do not expose hidden authority
Never expose:
- fake approval
- silent commit permission
- engine contract rewrite authority
- hidden override channels

### 10.2 Do not expose secrets as design context
Secret or environment values must not be exposed unless the design task explicitly requires a safe placeholder representation.

### 10.3 Do not expose raw internal noise by default
Avoid:
- raw internal debug payloads
- giant validator internals
- non-material UI layout data
- irrelevant runtime traces

## 11. Minimal Exposure Set

The minimal safe real-design exposure set is:

- current_working_save summary
- target_scope
- objective
- constraints
- findings
- risks
- available_resources
- output_contract
- forbidden_authority

Anything smaller is usually too weak for safe proposal generation.

## 12. Decision

Designer AI input exposure must be:
- bounded
- structured
- scope-aware
- resource-aware
- constraint-bound
- authority-safe

The canonical rule is not “show everything”.
It is “show only what safe bounded design requires”.
