[DESIGN]
[DIFF_VIEWER_VIEW_MODEL_SPEC v0.1]

1. PURPOSE

This document defines the official Diff Viewer View Model
for Nexa UI.

Its purpose is to provide a stable, UI-friendly representation of:

- structural differences between Working Save and Commit Snapshot
- differences between two Commit Snapshots
- differences between two Execution Records
- previewed proposal deltas before commit
- normalized change signals derived from raw diff operations
- diff-scoped navigation and inspection state

The Diff Viewer is the primary change-inspection-and-comparison module
of the Nexa UI shell.

It is responsible for:

- showing what changed
- distinguishing structural diff, execution diff, and preview diff
- showing change scope and severity
- linking diffs back to graph objects, outputs, artifacts, and runs
- exposing normalized change summaries rather than only raw textual deltas
- allowing focused comparison views without collapsing source/target truth

It is not responsible for mutating compared artifacts,
inventing differences,
or redefining source/target truth.

2. POSITION IN UI ARCHITECTURE

The Diff Viewer consumes data only through the adapter/view-model boundary.

Flow:

Engine truth
→ UI Adapter / View Model Layer
→ DiffViewerViewModel
→ Diff Viewer UI Module

The Diff Viewer must never directly read or mutate raw engine internals.

3. CORE PRINCIPLES

3.1 Diff Viewer is a comparison layer, not a truth layer.
3.2 Diff meaning must remain anchored to explicit source and target references.
3.3 Structural diff, execution diff, and preview diff must remain distinguishable.
3.4 Raw diff operations may be transformed into higher-level change signals,
    but the viewer must not fabricate semantic certainty beyond supported evidence.
3.5 Destructive changes must remain visually obvious.
3.6 Missing or partial comparison data must remain explicit.
3.7 Source and target artifacts must not be collapsed into one ambiguous merged truth.

4. TOP-LEVEL VIEW MODEL

DiffViewerViewModel
- diff_mode: enum(
    "draft_vs_commit",
    "commit_vs_commit",
    "run_vs_run",
    "preview_vs_current",
    "artifact_vs_artifact",
    "unknown"
  )
- viewer_status: enum(
    "idle",
    "loading",
    "ready",
    "partial",
    "failed",
    "unknown"
  )
- source_ref: DiffEndpointRefView
- target_ref: DiffEndpointRefView
- summary: DiffSummaryView
- grouped_changes: list[DiffGroupView]
- selected_change: optional DiffChangeDetailView
- filter_state: DiffFilterStateView
- related_links: DiffRelatedLinksView
- diagnostics: DiffDiagnosticsView
- explanation: optional string

5. FIELD SEMANTICS

5.1 diff_mode
Indicates what comparison class is being shown.

Examples:
- draft_vs_commit
- commit_vs_commit
- run_vs_run
- preview_vs_current
- artifact_vs_artifact

5.2 viewer_status
Top-level diff viewer state.

Semantics:
- idle: no diff target loaded
- loading: comparison is being prepared
- ready: comparison is available
- partial: comparison is available but incomplete
- failed: diff generation/loading failed
- unknown: cannot determine safely

5.3 source_ref / target_ref
Explicit comparison endpoints.

5.4 summary
Compact counts and high-level interpretation of the comparison.

5.5 grouped_changes
Grouped diff entries by target, category, severity, or scope.

5.6 selected_change
Detailed representation of the currently focused diff item.

5.7 filter_state
Projected filter/search/grouping state for diff browsing.

5.8 related_links
Cross-links to graph, inspector, validation, execution, trace, and artifacts.

5.9 diagnostics
Missing endpoints, incomplete diff, unsupported comparison warnings.

6. DIFF ENDPOINT REF VIEW

DiffEndpointRefView
- endpoint_type: enum(
    "working_save",
    "commit_snapshot",
    "execution_record",
    "preview",
    "artifact",
    "unknown"
  )
- ref_id: optional string
- title: optional string
- created_at: optional string
- status_label: optional string

Rules:
- endpoint identity must be explicit
- the UI must never guess endpoint type only from payload shape

7. DIFF SUMMARY VIEW

DiffSummaryView
- total_change_count: int
- added_count: int
- removed_count: int
- updated_count: int
- moved_count: int
- destructive_change_count: int
- structural_change_count: int
- execution_change_count: int
- artifact_change_count: int
- top_summary_label: optional string

Purpose:
Compact overview for headers/status bars.

8. DIFF GROUP VIEW

DiffGroupView
- group_id: string
- group_label: string
- group_type: enum(
    "target",
    "category",
    "severity",
    "change_scope",
    "custom"
  )
- changes: list[DiffChangeItemView]
- count: int
- collapsed_by_default: bool

Purpose:
Supports grouped rendering such as:
- all changes on node X
- all destructive changes
- all output-related changes

9. DIFF CHANGE ITEM VIEW

DiffChangeItemView
- change_id: string
- change_type: enum(
    "added",
    "removed",
    "updated",
    "moved",
    "replaced",
    "affected",
    "unknown"
  )
- category: enum(
    "node",
    "edge",
    "output",
    "resource",
    "parameter",
    "artifact",
    "execution_result",
    "validation_state",
    "metadata",
    "unknown"
  )
- target_type: enum(
    "node",
    "edge",
    "output",
    "artifact",
    "run",
    "storage",
    "preview",
    "unknown"
  )
- target_id: optional string
- short_label: string
- before_preview: optional string
- after_preview: optional string
- destructive: bool
- severity: optional enum("info", "warning", "error")
- signal_type: optional enum(
    "ADD",
    "REMOVE",
    "REPLACE",
    "MODIFY",
    "MOVE",
    "AFFECT"
  )

Rules:
- before_preview and after_preview are summaries, not authoritative full values
- signal_type is optional because not all raw diffs can be safely normalized that far
- destructive must remain explicit

10. DIFF CHANGE DETAIL VIEW

DiffChangeDetailView
- change_id: string
- title: string
- description: optional string
- category: string
- before_value_preview: optional string
- after_value_preview: optional string
- raw_diff_ops: list[RawDiffOpView]
- normalized_signals: list[DiffSignalView]
- affected_refs: list[string]
- related_finding_ids: list[string]
- related_event_ids: list[string]
- explanation: optional string

Purpose:
Provides focused detail for one selected change.

11. RAW DIFF OP VIEW

RawDiffOpView
- op_type: enum("equal", "insert", "delete", "replace", "unknown")
- text_preview: string

Purpose:
Allows the UI to preserve lower-level diff evidence when available.

12. DIFF SIGNAL VIEW

DiffSignalView
- signal_type: enum("ADD", "REMOVE", "REPLACE", "MODIFY", "MOVE", "AFFECT")
- before: optional string
- after: optional string
- confidence: optional float
- explanation: optional string

Rules:
- normalized signals are higher-level derived comparison signals
- confidence must not be presented as certainty when heuristic
- if no reliable signal is derivable, raw ops may remain the primary evidence

13. DIFF FILTER STATE VIEW

DiffFilterStateView
- show_added: bool
- show_removed: bool
- show_updated: bool
- show_destructive_only: bool
- show_structural_only: bool
- show_execution_only: bool
- search_query: optional string
- group_by: enum("target", "category", "severity", "none")

14. DIFF RELATED LINKS VIEW

DiffRelatedLinksView
- related_graph_target_ids: list[string]
- related_inspector_target_ids: list[string]
- related_validation_finding_ids: list[string]
- related_run_ids: list[string]
- related_artifact_ids: list[string]

Purpose:
Lets the viewer coordinate with the rest of the UI shell.

15. DIFF DIAGNOSTICS VIEW

DiffDiagnosticsView
- incomplete_diff: bool
- missing_source_ref: bool
- missing_target_ref: bool
- unsupported_section_count: int
- load_error_count: int
- last_error_label: optional string

Rules:
- incomplete comparison must remain visible
- unsupported diff surfaces must not be hidden or silently omitted as if unchanged

16. DIFF MODE RULES

16.1 draft_vs_commit
- compares current Working Save to latest or selected Commit Snapshot
- useful for uncommitted changes view
- structural and parameter/resource changes should dominate

16.2 commit_vs_commit
- compares two approved structural snapshots
- useful for history, rollback, and release comparison

16.3 run_vs_run
- compares two Execution Records
- useful for outcome/regression comparison
- structural diff must not be implied unless separately available from their commit anchors

16.4 preview_vs_current
- compares proposed preview state against current Working Save or selected structural baseline
- must not imply committed truth

16.5 artifact_vs_artifact
- compares two artifact summaries/bodies/previews
- must remain clearly artifact-scoped

17. NORMALIZED SIGNAL RULES

The viewer may present higher-level change signals when supported.

Examples:
- delete X + insert Y → REPLACE
- insert only → ADD
- delete only → REMOVE
- same target, changed value → MODIFY

Rules:
- normalized signal extraction must remain evidence-based
- when ambiguity exists, raw diff ops must remain available
- the viewer must not overstate semantic certainty beyond actual comparison support

18. EXECUTION DIFF RULES

For run_vs_run mode:
- differences in final outputs, node results, warnings, or artifacts may be shown
- run history comparisons must not be reinterpreted as structural source-of-truth changes
- the compared runs' commit anchors should remain visible if available

19. PREVIEW DIFF RULES

For preview_vs_current mode:
- preview changes must remain visibly non-committed
- destructive proposal deltas must remain obvious
- approval/precheck linkage may be shown via related links

20. PANEL ACTION BOUNDARY

The Diff Viewer may emit:
- focus-target actions
- open-graph actions
- open-inspector actions
- open-validation actions
- open-run actions
- open-artifact actions

The Diff Viewer must not:
- mutate compared artifacts
- silently merge source and target truth
- fabricate changes
- commit previewed changes
- redefine execution or storage truth

21. MINIMUM FIRST IMPLEMENTATION

The first implementation of DiffViewerViewModel should support:

- explicit source/target endpoint refs
- diff summary counts
- grouped changes
- selected change detail
- raw diff ops
- normalized signals where safely available
- draft_vs_commit mode
- run_vs_run mode
- preview_vs_current mode
- diagnostics for incomplete comparison

22. FINAL DECISION

DiffViewerViewModel is the official UI-facing contract
for presenting structural, execution, preview, and artifact comparisons in Nexa.

It is the stable change-inspection-and-comparison projection layer
for Diff Viewer UI modules.

It is not the diff engine itself,
and it must never become a shortcut that rewrites source or target truth.
