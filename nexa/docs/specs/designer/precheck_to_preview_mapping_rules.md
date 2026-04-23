# Precheck to Preview Mapping Rules v0.1

## Recommended save path
`docs/specs/designer/precheck_to_preview_mapping_rules.md`

## 1. Purpose

This document defines the canonical mapping rules from:

- `ValidationPrecheck`
to
- `CircuitDraftPreview`

Its purpose is to ensure that preview is built from explicit precheck results
and patch-aware structural deltas, not from hidden interpretation.

## 2. Core Decision

Preview must be derived from:
- patch intent and structure
- precheck findings
- evaluated future-state consequences

Preview is explanatory.
It must not mutate the savefile or silently reclassify findings.

## 3. Mapping Principles

1. preview must make future-state change understandable
2. preview must separate structure, behavior, output, risk, and cost
3. blocking issues must remain visible
4. destructive changes must never be hidden
5. assumptions and ambiguity must remain visible

## 4. Source and Target Objects

### Source
`ValidationPrecheck`

### Target
`CircuitDraftPreview`

Canonical preview fields:

- `preview_id`
- `intent_ref`
- `patch_ref`
- `precheck_ref`
- `preview_mode`
- `summary_card`
- `structural_preview`
- `node_change_preview`
- `edge_change_preview`
- `output_change_preview`
- `behavior_change_preview`
- `risk_preview`
- `cost_preview`
- `assumption_preview`
- `confirmation_preview`
- `graph_view_model`
- `explanation`

## 5. Top-Level Mapping Rules

### 5.1 `overall_status` -> preview emphasis
- `pass` -> preview may emphasize clean proposal summary
- `pass_with_warnings` -> preview must surface warning areas
- `confirmation_required` -> preview must highlight decision points
- `blocked` -> preview must clearly show why commit cannot proceed

### 5.2 Findings -> visible preview sections
- blocking findings -> blocking banner and structural explanation
- warning findings -> warning panel / highlighted hotspots
- confirmation findings -> explicit decision prompts

### 5.3 `evaluated_scope` -> structural preview bounds
Preview must show exactly the touched area and its relationship to the larger graph.

### 5.4 `preview_requirements` -> preview completeness rules
All required preview elements must be represented.
Precheck may strengthen preview, not weaken it.

## 6. Structural Preview Rules

`structural_preview` must show:
- what nodes are added, changed, or removed
- what edges are added, changed, or removed
- what touched outputs are affected
- whether the patch is append-only, structural-edit, or destructive-edit

## 7. Behavior Preview Rules

`behavior_change_preview` must explain likely change in:
- execution path
- review depth
- branching
- provider/plugin usage behavior
- safety or cost profile

Preview must stay explanatory, not claim certainty beyond evidence.

## 8. Risk and Cost Preview Rules

`risk_preview` must be derived from:
- `risk_report`
- blocking/warning/confirmation findings
- safety review

`cost_preview` must be derived from:
- `cost_assessment`

## 9. Confirmation Preview Rules

If status is `confirmation_required`,
preview must explicitly show:
- what the user is being asked to accept
- why confirmation is required
- what tradeoff is involved

## 10. Blocked Preview Rules

If status is `blocked`,
preview must not pretend that the proposal is ready.
It must explain:
- what is blocked
- why
- what revision is needed next

## 11. Decision

The canonical path from `ValidationPrecheck` to `CircuitDraftPreview`
must remain explicit, user-readable, and status-faithful.
