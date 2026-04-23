[DESIGN]
[GRAPH_WORKSPACE_VIEW_MODEL_SPEC v0.2]

1. PURPOSE

This document defines the official Graph Workspace View Model
for Nexa UI.

Its purpose is to provide a stable, UI-friendly representation of:

- circuit structure
- node/edge status
- previewed structural changes
- selection state
- graph-level summaries

The Graph Workspace is the primary visual module of the Nexa UI shell.
It is responsible for showing structure.
It is not responsible for owning structural truth.

2. POSITION IN UI ARCHITECTURE

The Graph Workspace consumes data only through the adapter/view-model boundary.

Flow:

Engine truth
→ UI Adapter / View Model Layer
→ GraphWorkspaceViewModel
→ Graph Workspace UI Module

The Graph Workspace must never directly read or mutate raw engine internals.

3. CORE PRINCIPLES

3.1 The Graph Workspace is a view layer, not a truth layer.
3.2 Structural truth remains engine-owned.
3.3 Graph view must expose both current structure and previewed changes.
3.4 Invalid or incomplete drafts must still be renderable.
3.5 Graph status must make blocked/warning/running states visible.
3.6 Selection and layout are UI-state concerns, not engine-truth concerns.
3.7 The model must be stable enough for multiple UI shells.

4. TOP-LEVEL VIEW MODEL

GraphWorkspaceViewModel
- graph_id: string
- graph_title: optional string
- storage_role: enum("working_save", "commit_snapshot", "execution_record", "none")
- graph_status: enum(
    "draft",
    "review_ready",
    "approved",
    "invalid",
    "running",
    "completed",
    "failed",
    "partial",
    "unknown"
  )
- nodes: list[GraphNodeView]
- edges: list[GraphEdgeView]
- groups: list[GraphGroupView]
- selected_node_ids: list[string]
- selected_edge_ids: list[string]
- graph_metrics: GraphMetricsView
- graph_findings_summary: GraphFindingsSummary
- preview_overlay: optional GraphPreviewOverlay
- layout_hints: optional GraphLayoutHints
- explanation: optional string

5. FIELD SEMANTICS

5.1 graph_id
Stable identifier for the current graph view target.

5.2 graph_title
Optional display title for the graph.

5.3 storage_role
Indicates whether the graph is sourced from:
- working_save
- commit_snapshot
- execution_record
- none

This must not be guessed by UI.

5.4 graph_status
Graph-level status summary.

Semantics:
- draft: editable current draft
- review_ready: draft has passed enough checks for review
- approved: commit snapshot style approved state
- invalid: blocking structural/design issues exist
- running: execution currently active
- completed: latest run completed successfully
- failed: latest run failed
- partial: partial run state exists
- unknown: state could not be determined safely

5.5 nodes / edges / groups
Primary structural display elements.

5.6 selected_node_ids / selected_edge_ids
UI selection state projected into the view model.

5.7 graph_metrics
Graph-level counts and summaries.

5.8 graph_findings_summary
Aggregated validation / execution / preview counts.

5.9 preview_overlay
Optional overlay describing proposed changes not yet committed.

5.10 layout_hints
Optional hints that support rendering, not execution.

6. NODE VIEW MODEL

GraphNodeView
- node_id: string
- label: string
- kind: string
- subtype: optional string
- position: optional NodePosition
- size: optional NodeSize
- status: enum(
    "normal",
    "warning",
    "error",
    "blocked",
    "running",
    "completed",
    "failed",
    "preview_added",
    "preview_updated",
    "preview_removed",
    "affected",
    "unknown"
  )
- execution_state: optional enum(
    "idle",
    "queued",
    "running",
    "completed",
    "failed",
    "partial",
    "cancelled"
  )
- validation_state: optional enum(
    "pass",
    "warning",
    "confirmation_required",
    "blocked",
    "unknown"
  )
- title_badge: optional string
- badges: list[NodeBadgeView]
- input_summary: optional string
- output_summary: optional string
- preview_change_state: enum(
    "unchanged",
    "added",
    "updated",
    "removed",
    "affected"
  )
- has_designer_proposal: bool
- has_blocking_findings: bool
- has_warning_findings: bool
- has_execution_events: bool
- child_refs: optional list[string]
- metadata_summary: optional dict

7. NODE POSITION / SIZE

NodePosition
- x: float
- y: float

NodeSize
- width: optional float
- height: optional float

Rules:
- position/size are UI-facing values
- they do not define execution semantics
- absence of position must not make the graph invalid

8. NODE BADGES

NodeBadgeView
- badge_type: enum(
    "validation_warning",
    "validation_blocked",
    "execution_running",
    "execution_failed",
    "execution_completed",
    "preview_added",
    "preview_updated",
    "preview_removed",
    "designer_pending",
    "subgraph",
    "tool_capable",
    "provider",
    "plugin",
    "custom"
  )
- label: string
- severity: optional enum("info", "warning", "error")
- count: optional int

Purpose:
Badges provide compact visual summaries without requiring node expansion.

9. EDGE VIEW MODEL

GraphEdgeView
- edge_id: string
- from_node_id: string
- to_node_id: string
- label: optional string
- status: enum(
    "normal",
    "warning",
    "error",
    "preview_added",
    "preview_removed",
    "affected",
    "unknown"
  )
- edge_type: optional string
- preview_change_state: enum(
    "unchanged",
    "added",
    "removed",
    "affected"
  )
- metadata_summary: optional dict

Rules:
- edge status must not imply execution truth beyond what engine provides
- preview-specific edge states must remain visually distinct

10. GROUP VIEW MODEL

GraphGroupView
- group_id: string
- label: string
- member_node_ids: list[string]
- collapsed: bool
- status: optional enum("normal", "warning", "error", "preview_changed")
- metadata_summary: optional dict

Purpose:
Allows higher-level grouping/folding without changing engine structure.

11. GRAPH METRICS VIEW

GraphMetricsView
- node_count: int
- edge_count: int
- group_count: int
- warning_count: int
- blocking_count: int
- running_node_count: int
- completed_node_count: int
- failed_node_count: int
- preview_added_count: int
- preview_updated_count: int
- preview_removed_count: int

12. FINDINGS SUMMARY VIEW

GraphFindingsSummary
- validation_warning_count: int
- validation_blocking_count: int
- confirmation_required_count: int
- execution_warning_count: int
- execution_error_count: int
- designer_pending_count: int

Purpose:
Provides compact graph-level summary for headers/status bars.

13. PREVIEW OVERLAY

GraphPreviewOverlay
- overlay_id: string
- preview_ref: optional string
- summary: string
- affected_node_ids: list[string]
- affected_edge_ids: list[string]
- added_node_ids: list[string]
- updated_node_ids: list[string]
- removed_node_ids: list[string]
- added_edge_ids: list[string]
- removed_edge_ids: list[string]
- destructive_change_present: bool
- requires_confirmation: bool

Rules:
- preview overlay is explanatory only
- overlay must not be treated as committed structure
- destructive changes must be visible

14. LAYOUT HINTS

GraphLayoutHints
- layout_mode: optional enum("manual", "auto", "hierarchical", "layered", "compact")
- suggested_focus_node_id: optional string
- suggested_zoom_region: optional dict
- minimap_enabled: optional bool

Rules:
- hints assist rendering only
- they do not determine execution order

15. RENDERABILITY RULES

The Graph Workspace must remain renderable even when:

- entry node is missing
- outputs are incomplete
- validation is blocked
- preview is partial
- execution has failed
- some nodes lack layout metadata

This is required because Working Save may be invalid or incomplete but still saveable.

16. STATUS PROJECTION RULES

16.1 Node status is a projection, not raw truth.
The adapter may synthesize node status from:
- validation findings
- execution state
- preview state

16.2 Projection priority
If multiple statuses apply, preferred visual priority is:

1. preview_removed
2. blocked
3. failed
4. running
5. warning
6. preview_updated
7. preview_added
8. completed
9. normal

This is a UI projection rule only.

17. PREVIEW PROJECTION RULES

Previewed changes must be visible without pretending they are committed.

Examples:
- added node → preview_added
- removed node → preview_removed
- changed node → preview_updated
- indirectly impacted node → affected

The underlying engine truth remains unchanged until commit.

18. STORAGE ROLE PROJECTION RULES

18.1 working_save
Graph may be incomplete or invalid.
UI should still show structure.

18.2 commit_snapshot
Graph should represent approved structural state.
Draft clutter should not appear.

18.3 execution_record
Graph may be shown with run-state overlays,
but structural truth still comes from the referenced approved structure.

19. SUBCIRCUIT DISPLAY RULES

If subcircuits exist, GraphNodeView may expose:

- kind = "subcircuit"
- child_refs
- subgraph badge

But:
- expanding/collapsing subcircuits in UI must not collapse engine boundaries
- parent/child execution truth must remain engine-owned
- UI may show hierarchy, but may not invent hidden node semantics

20. GRAPH WORKSPACE ACTION BOUNDARY

The Graph Workspace may emit:

- selection actions
- focus actions
- layout actions
- bounded edit intents

The Graph Workspace must not:

- directly save structure
- directly commit previewed changes
- directly alter validation truth
- directly alter execution truth

21. MINIMUM FIRST IMPLEMENTATION

The first implementation of GraphWorkspaceViewModel should support:

- node rendering
- edge rendering
- graph status
- selection projection
- validation badge projection
- execution badge projection
- preview overlay projection
- basic group/fold support
- storage role projection

22. FINAL DECISION

GraphWorkspaceViewModel is the official UI-facing structural projection
of Nexa graph state.

It is not the source of truth.
It is the stable visual contract through which UI shells/modules
see graph structure, status, and previewed change state.

23. LOCALIZATION ALIGNMENT

23.1 Text ownership in Graph Workspace must be split.

Localization-facing chrome/system fields:
- graph-level empty states
- graph status labels derived from enums
- panel/tool action hints
- warnings that are UI/system messages
- explanation text when it is shell-authored help text

Content-bearing fields:
- graph title when authored by user/import/source artifact
- node labels
- group labels
- input/output summaries
- preview snippets derived from circuit/resource content

23.2 Canonical ids and statuses remain unlocalized values.
Localized labels are derived from them separately.

23.3 The view model should interpret the older `string` shorthand as:
- DisplayTextRef for chrome/system fields
- ContentTextView for content-bearing fields

23.4 Graph layout must tolerate translated status text expansion without changing node semantics.
