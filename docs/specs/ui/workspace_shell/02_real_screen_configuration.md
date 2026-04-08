# Real Screen Configuration v1

## Recommended save path
`docs/specs/ui/workspace_shell/02_real_screen_configuration.md`

## 1. Purpose

This document fixes the first concrete, product-level screen composition for Nexa.

The goal is not to draw a pretty screen.
The goal is to define a **working shell** that can support:
- graph construction
- inspection
- validation
- execution
- designer proposal flow
- future observability expansion

## 2. Core screen philosophy

The screen must satisfy three rules at once:

1. the graph stays central
2. detail is read through side and dock panels
3. hidden system state becomes visible through overlays, lenses, and dedicated panes

This means Nexa should not become:
- a modal wizard product
- a linear form-based builder
- a dashboard that hides structure
- a review tool without a real graph workspace

## 3. Canonical shell layout

The v1 shell is:

- Top Bar
- Left Rail / Left Panel
- Center Graph Workspace
- Right Stack
- Bottom Dock

In text form:

Top Bar  
Left Rail | Graph Workspace | Right Stack  
Bottom Dock

This is the most rational layout for a graph-centered tool that must also expose validation, execution, trace, artifacts, and diff without constantly navigating away.

## 4. Top Bar

Top Bar is for **global state and global actions only**.

It should contain:
- workspace name
- current storage role
- global status summary
- primary actions
- mode switcher
- search / quick jump

It must not become:
- a crowded toolbar
- a deep feature shelf
- an inspector replacement

## 5. Left Rail / Left Panel

The left side is for deciding **what to look at**, not for editing truth directly.

It should hold:
- outline
- template library
- lens selector
- storage navigator
- proposal outline in review mode
- run outline in run mode

This makes the left side the exploration and interpretation zone.

## 6. Center Graph Workspace

The center is always the structural anchor.

It must show:
- nodes
- edges
- groups / zones / subcircuit boundaries
- graph overlays
- preview overlays
- execution overlays
- selection and jump highlights

The graph remains central across Build, Review, and Run.
State changes only alter what is emphasized on top of the same graph-centered shell.

## 7. Right Stack

The right side is the detail-and-intent side.

It should host:
- Inspector
- Designer
- Execution side detail

The right side is where the selected thing becomes meaningful.

Graph tells you **what exists**.
Right Stack tells you **what it means now**.

## 8. Bottom Dock

Bottom Dock is the time/risk/evidence/comparison zone.

It should contain tabs for:
- Validation
- Execution
- Trace
- Artifacts
- Diff
- optionally Precheck

The bottom area is where dense lists, logs, event timelines, artifact previews, and comparison data can live without stealing the graph's central role.

## 9. Why this configuration is the best v1

This layout is strongest because:
- the center always keeps structure visible
- the right side holds object-specific context
- the bottom holds dense diagnostics and evidence
- the left side stays navigational rather than overloaded
- the shell can survive beginner and advanced modes without becoming a different product

## 10. Wrong alternatives

### 10.1 Bottom-heavy dashboard
Wrong because it demotes the graph and turns Nexa into a monitoring console.

### 10.2 Full-screen graph with floating popups only
Wrong because serious diagnostics and review data need dense panes, not endless popovers.

### 10.3 Wizard-only designer flow
Wrong because it would hide structural truth behind sequential forms.

### 10.4 Dedicated separate apps for Build / Review / Run
Wrong because the shell should remain one workspace with state emphasis shifts, not three disconnected products.

## 11. Initial v1 default

The most rational initial default is:

- Top Bar visible
- Left Rail visible but compact
- Graph dominant
- Right Stack open
- Bottom Dock present but medium or collapsed until needed

This supports both first-run users and experts without throwing all density at once.
