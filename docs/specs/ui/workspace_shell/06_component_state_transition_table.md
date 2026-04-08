# Component State Transition Table v1

## Recommended save path
`docs/specs/ui/workspace_shell/06_component_state_transition_table.md`

## 1. Purpose

This document fixes which components are:

- primary
- visible
- collapsed
- hidden
- disabled

across the main shell states.

## 2. Meaning of states

### `primary`
Center of attention.
Gets default focus and the strongest space claim.

### `visible`
Open and usable, but not the main foreground.

### `collapsed`
Present but minimized.

### `hidden`
Not shown by default in this state.

### `disabled`
Shown but unavailable for action.

## 3. High-level table

### Top Bar
Always visible across Build / Review / Run.

### StorageRoleBadge
Always visible.

### GlobalStatusSummary
Visible in Build/Review, primary in Run.

### Left Rail
Always present, but internal tabs change priority.

### GraphWorkspace
Primary in all three states.

### InspectorPanel
Primary in Build, visible in Review/Run.

### DesignerPanel
Collapsed in Build, primary in Review, hidden in Run.

### ExecutionSidePanel
Hidden in Build, collapsed in Review, primary in Run.

### ValidationTab
Primary in Build, visible in Review, collapsed in Run.

### DiffTab
Collapsed in Build, primary in Review, collapsed in Run.

### TraceTab
Hidden in Build, collapsed in Review, primary in Run.

## 4. Build-specific emphasis

Build foreground:
- Graph
- Inspector
- Validation

Build background:
- Designer
- Diff
- Trace
- Artifacts

## 5. Review-specific emphasis

Review foreground:
- Graph preview layer
- Designer
- Diff
- Validation / Precheck

Review background:
- direct structure-edit tooling
- live execution controls

## 6. Run-specific emphasis

Run foreground:
- Graph execution overlays
- Execution side panel
- Trace
- Execution tab
- Artifacts

Run background:
- edit tools
- proposal controls

## 7. Why this table matters

Without fixed visibility rules, implementations drift toward "show everything all the time."
That destroys the shell.
This table enforces emphasis.
