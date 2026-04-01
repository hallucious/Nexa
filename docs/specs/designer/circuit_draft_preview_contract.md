# Circuit Draft Preview Contract v0.1

## 1. Purpose

This contract defines the canonical preview boundary for Designer AI proposals.

The preview must answer:
1. What will change?
2. What will stay the same?
3. What will the circuit look like after the change?
4. What outputs, risks, and costs will change?
5. What requires explicit approval?

## 2. Core Principles

1. Preview is mandatory for create/modify/repair/optimize.
2. Preview must be human-readable before machine-detailed.
3. Preview must separate structural, behavioral, output, and risk/cost changes.
4. Preview must not hide destructive edits.
5. Preview must expose assumptions and safe defaults.

## 3. CircuitDraftPreview Schema

```text
CircuitDraftPreview
- preview_id
- intent_ref
- patch_ref
- precheck_ref
- preview_mode
- summary_card
- structural_preview
- node_change_preview
- edge_change_preview
- output_change_preview
- behavior_change_preview
- risk_preview
- cost_preview
- assumption_preview
- confirmation_preview
- graph_view_model
- explanation
```

## 4. Required Preview Areas

- summary card
- structural delta
- node change cards
- edge change cards
- output change preview
- behavior change preview
- risk preview
- cost preview
- assumption preview
- confirmation preview

## 5. Rendering Order

A conforming preview must be understandable in this order:
1. summary
2. structural delta
3. node/edge changes
4. output change
5. risk + confirmation
6. cost + behavior
7. assumptions/defaults
8. optional graph

## 6. Invariants

- no hidden deletion
- no hidden output change
- no hidden assumptions
- no preview/patch mismatch
- no UI-only invented semantics

## 7. Decision

Designer AI must not only propose safely.
It must preview clearly before commit.
