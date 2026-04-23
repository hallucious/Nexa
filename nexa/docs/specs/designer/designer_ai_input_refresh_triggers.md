# Designer AI Input Refresh Triggers v0.1

## Recommended save path
`docs/specs/designer/designer_ai_input_refresh_triggers.md`

## 1. Purpose

This document defines when the exposed input state for Designer AI
must be recomputed, refreshed, or invalidated.

Its purpose is to ensure that Designer AI does not keep reasoning from stale design context.

## 2. Core Decision

Designer AI input is not static.

Official rule:

- refresh the input projection whenever a materially relevant design signal changes
- do not rely on old session-card content after state-changing events
- distinguish hard refresh triggers from soft refresh triggers

In short:

Stale input is a design risk and must be managed explicitly.

## 3. Trigger Classes

There are two trigger classes:

1. hard refresh triggers
2. soft refresh triggers

### 3.1 Hard refresh trigger
A change that can materially invalidate prior design interpretation,
scope, or operation feasibility.

### 3.2 Soft refresh trigger
A change that should update presentation or confidence,
but may not fully invalidate prior bounded reasoning.

## 4. Hard Refresh Triggers

### 4.1 Working Save structure changed
Examples:
- node added
- node removed
- edge changed
- output binding changed
- provider/plugin attachment changed

Reason:
Current design reality changed.

### 4.2 Target scope changed
Examples:
- whole circuit -> node_only
- destructive allowed -> destructive forbidden
- touched refs changed

Reason:
Proposal boundaries changed.

### 4.3 Available resource status changed
Examples:
- provider becomes unavailable
- plugin becomes available
- restriction list changes

Reason:
Feasible proposal space changed.

### 4.4 Findings changed materially
Examples:
- new blocking finding
- broken path resolved
- confirmation requirement added

Reason:
Repair vs modify vs optimize pressure may change.

### 4.5 High-risk status changed
Examples:
- risk escalated
- high risk resolved
- safety review requirement changed

Reason:
Proposal safety posture changed.

### 4.6 User correction changed interpretation
Examples:
- "only modify reviewer node"
- "do not touch outputs"
- "make it cheaper instead"

Reason:
Interpretation basis changed.

### 4.7 Approval boundary changed
Examples:
- approval requested
- approval rejected
- confirmation required
- review policy changed

Reason:
Proposal path changed.

## 5. Soft Refresh Triggers

### 5.1 Selection changed
If scope is still broad, this may be soft.
If scope is selection-bound, selection change becomes hard.

### 5.2 Conversation summary updated without structural meaning shift
Examples:
- wording clarified but scope/objective unchanged

### 5.3 UI note or explanation preference changed
Usually soft unless it affects effective boundedness.

### 5.4 Non-material historical context appended
Examples:
- additional archival note
- duplicate old rejection message

## 6. Invalidation Rules

### 6.1 Hard trigger invalidates prior design-state projection
A new session-card projection must be generated.

### 6.2 Hard trigger may invalidate prior intent confidence
Earlier generated interpretations may need downgrade or regeneration.

### 6.3 Soft trigger updates context but may preserve prior bounded proposal
Only if no authority/scope/constraint/finding/resource change occurred.

## 7. Regeneration Rules

When a hard refresh trigger occurs, recompute at least:

- current_working_save summary
- target_scope
- available_resources
- current_findings
- current_risks
- revision_state
- approval_state
- conversation_context summary if changed

## 8. Revision Loop Rule

Every revision cycle should check whether any hard refresh trigger occurred
before reusing the prior session-state projection.

## 9. Cache Safety Rule

Cached Designer AI input must not be reused if:
- revision id changed
- touched refs changed
- findings changed materially
- resource availability changed
- approval state changed
- latest user correction changed interpretation

## 10. Example Trigger Cases

### Case 1
User says:
"Only modify the reviewer node."

Effect:
- hard refresh

### Case 2
A plugin becomes unavailable.

Effect:
- hard refresh

### Case 3
The user selects a different node, but scope is still whole-circuit.

Effect:
- usually soft refresh

### Case 4
Validator adds a new blocking finding for output path.

Effect:
- hard refresh

## 11. Decision

Designer AI input must refresh whenever design-relevant state changes materially.

The canonical rule is:
refresh on structure, scope, resource, finding, risk, approval, or interpretation changes.
