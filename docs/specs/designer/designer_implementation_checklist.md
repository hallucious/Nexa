# Designer Implementation Checklist v0.1

## Recommended save path
`docs/specs/designer/designer_implementation_checklist.md`

## 1. Purpose

This document defines the implementation-time checklist for connecting the Designer specification bundle to code.

Its purpose is to prevent partial integration where the contracts exist on paper but the runtime, storage, UI, and tests do not actually respect them.

## 2. Scope

This checklist applies when implementing or refactoring any of the following:
- session-state construction
- intent generation
- grounding
- patch planning
- precheck
- preview
- approval flow
- commit gateway

## 3. Checklist

### 3.1 Session-state boundary
- build `DesignerSessionStateCard` explicitly from current Working Save reality
- do not let the Designer layer infer hidden scope or hidden authority
- ensure selection, available resources, constraints, findings, and approval/revision state are projected explicitly

### 3.2 Intent / grounding boundary
- keep semantic interpretation and symbolic grounding distinct
- ensure grounded references are deterministic and reproducible
- never let semantic output mutate savefile truth directly

### 3.3 Patch / precheck / preview chain
- patch plans must remain explicit and previewable
- precheck must evaluate future-state proposal validity before commit
- preview must remain derived from patch + precheck, not from UI-side guesswork

### 3.4 Approval / commit boundary
- approval must remain explicit
- blocked previews must not cross commit
- commit must verify approval truth and base-revision consistency

### 3.5 Storage alignment
- Working Save remains draft/editable state
- Commit Snapshot remains approved structural truth
- Designer flow must not collapse these roles together

### 3.6 UI alignment
- UI may display and route Designer state
- UI must not generate preview/precheck/approval truth locally
- Designer panel must respect engine-owned governance state

### 3.7 Test coverage
- contract-level model tests
- proposal-flow tests
- storage-role boundary tests
- UI adapter projection tests
- approval/commit gateway tests

## 4. Minimum Done Criteria

Designer implementation is not done until all are true:
1. session-state input boundary is explicit
2. semantic vs grounded intent split is preserved
3. patch / precheck / preview chain is explicit
4. approval / commit boundary is guarded
5. storage/UI/tests are synchronized

## 5. Decision

Designer implementation must be treated as a multi-boundary integration problem, not a single prompt or single UI task.
