# Designer Governance Contract v0.1

## 1. Purpose

This contract defines the governance boundary between the Designer subsystem
and the UI layer.

Its purpose is to make one rule explicit:
UI MUST NOT own Designer governance decision logic.
UI collects user actions and displays engine-generated governance results.

## 2. Core Principle

The canonical Designer flow remains:

User Request
→ Intent
→ Patch
→ Precheck
→ Preview
→ Approval
→ Commit

The governance decision boundary exists inside the engine-owned stages of this flow.
UI may project those stages, but UI may not recreate them.

## 3. Engine-owned Governance Responsibilities

### 3.1 Preview Generation
Engine implementation:
- `src/designer/preview_builder.py`
- `src/designer/models/circuit_draft_preview.py`

Rules:
- Engine builds `CircuitDraftPreview`
- Engine assigns preview identity
- Engine determines confirmation requirements exposed through the preview artifact
- UI MUST NOT generate preview content locally

### 3.2 Validation Precheck
Engine implementation:
- `src/designer/models/validation_precheck.py`
- `docs/specs/designer/designer_validator_precheck_contract.md`

Rules:
- Engine evaluates the proposed future state
- Engine classifies blocking findings, warnings, and confirmation-required findings
- Engine computes precheck status
- UI MUST NOT rerun or reinterpret precheck logic to produce a different status

### 3.3 Approval Eligibility
Engine implementation:
- `src/designer/models/designer_approval_flow.py`
- `docs/specs/designer/designer_approval_flow_contract.md`

Rules:
- Engine computes `commit_eligible`
- Engine tracks unanswered decisions and confirmation resolution
- Engine determines whether approval may proceed
- UI MUST NOT calculate approval eligibility from findings or preview data

### 3.4 Governance Policy Application
Engine implementation:
- `src/designer/control_governance.py`

Rules:
- Engine applies governance tiering and confirmation pressure
- Engine determines whether ambiguity or scope mismatch blocks or slows approval
- UI MUST NOT reinterpret governance policy to weaken engine decisions

## 4. UI Adapter Responsibilities

The UI adapter MAY:
- read engine-generated preview state
- read engine-generated precheck state
- read engine-generated approval/governance state
- reshape those into `DesignerPanelViewModel`
- expose user-facing action hints that remain consistent with engine-owned state

The UI adapter MUST NOT:
- generate preview content
- run validation precheck
- calculate `commit_eligible`
- downgrade blocked or confirmation-required governance state
- bypass engine-owned approval flow

## 5. Forbidden Patterns

### 5.1 UI-side Preview Generation
Forbidden pattern:
- UI constructs preview content as if it were the authoritative preview artifact

Correct pattern:
- Engine builds preview
- Adapter reads preview
- UI displays preview

### 5.2 UI-side Approval Decision
Forbidden pattern:
- UI decides “approve button enabled” by independently reading blocking/warning counts

Correct pattern:
- Engine computes approval readiness
- Adapter projects `approval_state.commit_eligible`
- UI respects that value

### 5.3 UI-side Governance Reinterpretation
Forbidden pattern:
- UI treats confirmation-required governance as a cosmetic warning

Correct pattern:
- Engine emits confirmation-required state
- Adapter preserves it
- UI displays it without weakening it

## 6. Test Requirements

Minimum verification for this boundary:

1. Adapter boundary tests
- adapter does not generate preview content
- adapter exposes engine-owned approval eligibility unchanged
- adapter exposes engine-owned confirmation requirements unchanged

2. View model contract tests
- adapter-produced view model carries engine-generated preview identity
- adapter-produced view model carries engine-generated precheck status
- adapter-produced view model carries engine-owned approval eligibility / confirmation state

## 7. Related Documents

UI-facing documents:
- `docs/specs/ui/designer_panel_view_model_spec.md`
- `docs/specs/ui/ui_adapter_view_model_contract.md`

Engine/designer documents:
- `docs/specs/designer/designer_approval_flow_contract.md`
- `docs/specs/designer/designer_validator_precheck_contract.md`
- `docs/specs/designer/circuit_draft_preview_contract.md`
