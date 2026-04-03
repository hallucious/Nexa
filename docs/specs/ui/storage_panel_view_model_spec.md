[DESIGN]
[STORAGE_PANEL_VIEW_MODEL_SPEC v0.1]

1. PURPOSE

This document defines the official Storage Panel View Model
for Nexa UI.

Its purpose is to provide a stable, UI-friendly representation of:

- current storage role
- Working Save state
- Commit Snapshot state
- Execution Record state
- storage lifecycle transitions
- latest references and relationships between storage artifacts
- storage-scoped warnings and action availability

The Storage Panel is the primary storage-lifecycle-and-artifact-identity module
of the Nexa UI shell.

It is responsible for:

- showing which storage layer the user is looking at
- showing the relationship between draft, approved snapshot, and run history
- showing whether the current draft has uncommitted changes
- showing whether execution is anchored to a commit snapshot
- showing recent commit/run references and summaries
- exposing bounded storage-oriented actions such as save, review, commit, rollback-target selection, and record inspection when allowed

It is not responsible for redefining storage truth,
silently collapsing storage layers,
or directly mutating approved/historical artifacts.

2. POSITION IN UI ARCHITECTURE

The Storage Panel consumes data only through the adapter/view-model boundary.

Flow:

Engine truth
→ UI Adapter / View Model Layer
→ StoragePanelViewModel
→ Storage Panel UI Module

The Storage Panel must never directly read or mutate raw engine internals.

3. CORE PRINCIPLES

3.1 Storage Panel is a lifecycle/provenance view layer, not a truth layer.
3.2 Storage lifecycle truth remains engine-owned.
3.3 Working Save, Commit Snapshot, and Execution Record must remain distinct.
3.4 The panel must not visually collapse “current draft” and “approved structure” into one ambiguous state.
3.5 The panel must keep latest references explicit.
3.6 The panel must support incomplete/invalid Working Save visibility.
3.7 Historical execution records must remain history-oriented, not editable.

4. TOP-LEVEL VIEW MODEL

StoragePanelViewModel
- active_storage_role: enum("working_save", "commit_snapshot", "execution_record", "none")
- panel_mode: enum(
    "draft_focus",
    "commit_focus",
    "execution_focus",
    "lifecycle_overview",
    "unknown"
  )
- lifecycle_summary: StorageLifecycleSummaryView
- working_save_card: optional WorkingSaveCardView
- commit_snapshot_card: optional CommitSnapshotCardView
- execution_record_card: optional ExecutionRecordCardView
- relationship_graph: StorageRelationshipView
- recent_entries: StorageRecentEntriesView
- available_actions: list[StorageActionHint]
- diagnostics: StorageDiagnosticsView
- explanation: optional string

5. FIELD SEMANTICS

5.1 active_storage_role
The currently focused storage truth domain.

5.2 panel_mode
Primary UI emphasis for this panel.

Examples:
- draft_focus
- commit_focus
- execution_focus
- lifecycle_overview

5.3 lifecycle_summary
Compact interpretation of current storage state.

5.4 working_save_card / commit_snapshot_card / execution_record_card
Role-specific summaries.

5.5 relationship_graph
Reference-safe linkage between current draft, latest commit, and latest run.

5.6 recent_entries
Compact recent history list.

5.7 available_actions
UI-facing allowed/disabled lifecycle actions.

5.8 diagnostics
Storage inconsistency, staleness, missing-ref, or load warnings.

6. STORAGE LIFECYCLE SUMMARY VIEW

StorageLifecycleSummaryView
- has_working_save: bool
- has_latest_commit_snapshot: bool
- has_latest_execution_record: bool
- current_stage: enum(
    "editing",
    "review_ready",
    "approved",
    "executing",
    "executed",
    "failed_execution",
    "unknown"
  )
- uncommitted_changes_present: bool
- latest_commit_id: optional string
- latest_run_id: optional string
- summary_label: optional string

Rules:
- current_stage is a UI summary, not a replacement for underlying role truth
- uncommitted_changes_present must remain explicit
- latest_commit_id and latest_run_id must come from engine-owned references

7. WORKING SAVE CARD VIEW

WorkingSaveCardView
- working_save_id: string
- status: enum(
    "draft",
    "validation_failed",
    "ready_for_review",
    "validated",
    "execution_failed",
    "executed",
    "unknown"
  )
- title: optional string
- updated_at: optional string
- validation_summary_label: optional string
- latest_run_summary_label: optional string
- latest_artifact_ref_count: optional int
- designer_state_present: bool
- can_save: bool
- can_submit_for_review: bool
- can_compare_to_latest_commit: bool

Rules:
- Working Save may remain invalid and still saveable
- status describes working condition, not approval truth
- full execution chronology must not be implied here

8. COMMIT SNAPSHOT CARD VIEW

CommitSnapshotCardView
- commit_id: string
- parent_commit_id: optional string
- status: enum(
    "approved",
    "approved_with_warnings",
    "superseded",
    "rollback_candidate",
    "unknown"
  )
- created_at: optional string
- title: optional string
- approval_summary_label: optional string
- validation_summary_label: optional string
- source_working_save_id: optional string
- can_execute: bool
- can_compare: bool
- can_rollback_to: bool

Rules:
- Commit Snapshot is structurally approved state
- blocked/failed validation states must not appear as valid commit snapshot status
- temporary editor clutter must not be represented here as truth

9. EXECUTION RECORD CARD VIEW

ExecutionRecordCardView
- run_id: string
- commit_id: string
- status: enum(
    "running",
    "completed",
    "failed",
    "partial",
    "cancelled",
    "unknown"
  )
- started_at: optional string
- finished_at: optional string
- output_summary_label: optional string
- artifact_count: optional int
- trace_available: bool
- replay_available: bool
- can_open_trace: bool
- can_open_artifacts: bool
- can_compare_runs: bool

Rules:
- Execution Record is run history, not structural truth
- commit_id reference is mandatory when execution record truth is shown
- this card must not imply editability of run history

10. STORAGE RELATIONSHIP VIEW

StorageRelationshipView
- working_save_ref: optional string
- latest_commit_ref: optional string
- latest_run_ref: optional string
- source_to_commit_label: optional string
- commit_to_run_label: optional string
- latest_run_matches_latest_commit: optional bool
- draft_vs_commit_status: optional enum(
    "no_commit",
    "in_sync",
    "has_uncommitted_changes",
    "unknown"
  )

Purpose:
Shows how the three storage layers connect.

11. STORAGE RECENT ENTRIES VIEW

StorageRecentEntriesView
- recent_working_save_refs: list[string]
- recent_commit_refs: list[string]
- recent_run_refs: list[string]
- selected_ref: optional string

Purpose:
Supports compact recent-history navigation.

12. STORAGE ACTION HINT

StorageActionHint
- action_type: enum(
    "save_working_save",
    "submit_for_review",
    "open_validation",
    "approve_and_commit",
    "open_latest_commit",
    "run_from_commit",
    "open_latest_run",
    "compare_draft_to_commit",
    "compare_runs",
    "open_trace",
    "open_artifacts",
    "select_rollback_target",
    "none"
  )
- label: string
- enabled: bool
- reason_disabled: optional string
- target_ref: optional string

Purpose:
Guides the UI toward valid lifecycle actions without bypassing engine rules.

13. STORAGE DIAGNOSTICS VIEW

StorageDiagnosticsView
- stale_reference_count: int
- missing_commit_ref_count: int
- missing_run_ref_count: int
- lifecycle_warning_count: int
- load_error_count: int
- last_error_label: optional string

Rules:
- missing/stale refs must remain visible
- diagnostics must not redefine storage truth

14. WORKING SAVE RULES

When active_storage_role = "working_save":
- the panel must show that the artifact is editable
- invalid or incomplete state must remain visible
- save must remain allowed even when structural execution is not possible
- comparison to latest commit may be shown as “uncommitted changes” view

15. COMMIT SNAPSHOT RULES

When active_storage_role = "commit_snapshot":
- the panel must show approved structural anchor semantics
- commit snapshot must not be presented as a draft
- commit snapshot may be used as execution anchor, diff target, or rollback target
- approval/validation summaries should remain visible

16. EXECUTION RECORD RULES

When active_storage_role = "execution_record":
- the panel must show run-oriented history semantics
- latest output/artifact/trace summaries may be shown
- structural editability must remain unavailable
- comparison to other runs may be offered if engine supports it

17. DESIGNER / APPROVAL FLOW RULES

The Storage Panel may reflect proposal-flow position,
but it must not bypass that flow.

Allowed examples:
- show that Working Save is ready for review
- show that commit creation is blocked by unresolved findings
- show that latest commit was created from an approved proposal

Forbidden examples:
- silently creating a commit from draft state
- showing “approved” without approval truth
- treating Working Save as committed truth once a commit exists

18. PANEL ACTION BOUNDARY

The Storage Panel may emit:
- save requests
- review/approval navigation actions
- commit/open/run navigation actions
- compare/open-trace/open-artifacts actions

The Storage Panel must not:
- redefine storage lifecycle
- silently promote Working Save into Commit Snapshot
- silently convert run history into editable draft state
- bypass validation/precheck/approval boundaries

19. MINIMUM FIRST IMPLEMENTATION

The first implementation of StoragePanelViewModel should support:

- active_storage_role
- lifecycle summary
- Working Save card
- latest Commit Snapshot card
- latest Execution Record card
- storage relationship view
- recent entries
- bounded action hints
- diagnostics for stale/missing refs

20. FINAL DECISION

StoragePanelViewModel is the official UI-facing contract
for presenting storage lifecycle state, artifact identity boundaries,
and cross-layer references in Nexa.

It is the stable storage-lifecycle-and-provenance projection layer
for Storage Panel UI modules.

It is not the storage system itself,
and it must never become a shortcut that collapses
Working Save, Commit Snapshot, and Execution Record into one truth.