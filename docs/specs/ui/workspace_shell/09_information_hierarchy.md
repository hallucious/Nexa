# Information Hierarchy / Screen Priority Table v1

## Recommended save path
`docs/specs/ui/workspace_shell/09_information_hierarchy.md`

## 1. Purpose

This document fixes what must be visible first and what may be delayed.

Without hierarchy, the UI collapses into a noisy toolshed.

## 2. Priority levels

### Level 1 — always visible
Identity and next action information.

### Level 2 — usually visible
Frequently needed but not always foreground.

### Level 3 — expandable
Dense information available on demand.

### Level 4 — expert / deep inspection
Advanced-only or deeply nested inspection surfaces.

## 3. Level 1 items

- current workspace name
- current storage role
- current mode
- global status summary
- graph anchor
- primary actions

## 4. Level 2 items

- current selection detail
- validation summary
- designer summary in review flow
- execution summary in run flow
- template / outline entry points
- lens selector access

## 5. Level 3 items

- trace slices
- artifact metadata depth
- diff details
- advanced filters
- grouped findings
- metrics panels

## 6. Level 4 items

- provenance and deep causal drill-down
- advanced storage comparison
- dense observability surfaces
- expert keyboard overlays
- multi-focus analysis views

## 7. Why hierarchy matters

The UI must answer, in order:
1. where am I?
2. what state am I in?
3. what do I do next?
4. what is wrong?
5. where do I drill deeper?

If the UI answers 4 and 5 before 1 and 2, it is badly ordered.
