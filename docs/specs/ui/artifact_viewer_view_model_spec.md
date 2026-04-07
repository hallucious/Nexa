[DESIGN]
[ARTIFACT_VIEWER_VIEW_MODEL_SPEC v0.2]

1. PURPOSE

This document defines the official Artifact Viewer View Model
for Nexa UI.

Its purpose is to provide a stable, UI-friendly representation of:

- execution artifacts
- artifact summaries and previews
- artifact lineage/context linkage
- artifact-to-node / artifact-to-event / artifact-to-output linkage
- artifact inspection state
- artifact integrity metadata

The Artifact Viewer is the primary artifact-inspection module
of the Nexa UI shell.

It is responsible for:

- showing what artifacts were produced
- showing concise previews and metadata
- distinguishing final artifacts from intermediate artifacts
- linking artifacts back to their producing execution context
- allowing focused artifact inspection without exposing raw engine internals directly

It is not responsible for mutating artifacts,
rewriting artifact history,
or inventing artifact lineage.

2. POSITION IN UI ARCHITECTURE

The Artifact Viewer consumes data only through the adapter/view-model boundary.

Flow:

Engine truth
→ UI Adapter / View Model Layer
→ ArtifactViewerViewModel
→ Artifact Viewer UI Module

The Artifact Viewer must never directly read or mutate raw engine internals.

3. CORE PRINCIPLES

3.1 Artifact Viewer is an inspection layer, not a truth layer.
3.2 Artifact truth and lineage remain engine-owned.
3.3 Artifacts must remain append-only in meaning.
3.4 Intermediate artifacts and final artifacts must remain distinguishable.
3.5 Missing artifact bodies/previews must remain visible as unavailable, not silently synthesized.
3.6 Artifact linkage to trace/execution context must preserve provenance.
3.7 Large artifacts must be representable through preview/slice metadata without requiring full body load.

4. TOP-LEVEL VIEW MODEL

ArtifactViewerViewModel
- source_mode: enum(
    "live_execution_artifacts",
    "execution_record_artifacts",
    "replay_artifacts",
    "working_save_artifact_refs",
    "unknown"
  )
- storage_role: enum("working_save", "commit_snapshot", "execution_record", "none")
- viewer_status: enum(
    "idle",
    "loading",
    "ready",
    "partial",
    "failed",
    "unknown"
  )
- artifact_summary: ArtifactSummaryView
- artifact_list: list[ArtifactItemView]
- selected_artifact: optional ArtifactDetailView
- related_links: ArtifactRelatedLinksView
- filter_state: ArtifactFilterStateView
- diagnostics: ArtifactDiagnosticsView
- explanation: optional string

5. FIELD SEMANTICS

5.1 source_mode
Indicates what artifact surface is being shown.

Examples:
- live_execution_artifacts
- execution_record_artifacts
- replay_artifacts
- working_save_artifact_refs

5.2 storage_role
Indicates which storage layer anchors the shown artifact references.

5.3 viewer_status
Top-level artifact viewer state.

Semantics:
- idle: no artifact surface loaded
- loading: artifact summaries or details are being loaded
- ready: artifact surface is available
- partial: only partial metadata/previews are available
- failed: artifact loading failed
- unknown: cannot determine safely

5.4 artifact_summary
Compact aggregate summary.

5.5 artifact_list
Visible artifact entries for browsing/searching/filtering.

5.6 selected_artifact
Detailed representation of the currently focused artifact.

5.7 related_links
Cross-links to graph, trace, execution, and outputs.

5.8 filter_state
Projected viewer filter/search state.

5.9 diagnostics
Missing bodies, unavailable previews, integrity/load warnings.

6. ARTIFACT SUMMARY VIEW

ArtifactSummaryView
- total_artifact_count: int
- visible_artifact_count: int
- final_artifact_count: int
- intermediate_artifact_count: int
- warning_count: int
- integrity_issue_count: int
- top_summary_label: optional string

Purpose:
Compact overview for headers/status areas.

7. ARTIFACT ITEM VIEW

ArtifactItemView
- artifact_id: string
- title: string
- artifact_type: optional string
- category: enum(
    "output",
    "intermediate",
    "debug",
    "report",
    "file",
    "trace_linked",
    "unknown"
  )
- producer_node_id: optional string
- producer_resource_type: optional enum(
    "prompt",
    "provider",
    "plugin",
    "subcircuit",
    "runtime",
    "unknown"
  )
- producer_resource_id: optional string
- created_at: optional string
- size_label: optional string
- preview_text: optional string
- is_final: bool
- is_partial: bool
- integrity_status: enum(
    "ok",
    "missing_body",
    "hash_unavailable",
    "mismatch",
    "unknown"
  )

Rules:
- preview_text is a preview only, not the canonical body
- integrity_status must reflect actual engine-provided integrity metadata
- is_partial must remain visible

8. ARTIFACT DETAIL VIEW

ArtifactDetailView
- artifact_id: string
- title: string
- artifact_type: optional string
- body_mode: enum(
    "text",
    "json",
    "table",
    "binary_ref",
    "unavailable",
    "unknown"
  )
- body_preview: optional string
- structured_preview: optional dict
- metadata: ArtifactMetadataView
- integrity: ArtifactIntegrityView
- lineage: ArtifactLineageView
- related_output_names: list[string]
- related_event_ids: list[string]

Purpose:
Provides focused inspection for one artifact.

Rules:
- unavailable body must remain explicit
- structured_preview is optional and must not imply full-body access
- binary or large artifact bodies may be represented as references

9. ARTIFACT METADATA VIEW

ArtifactMetadataView
- mime_type: optional string
- encoding: optional string
- size_bytes: optional int
- created_at: optional string
- source_label: optional string
- tags: list[string]

10. ARTIFACT INTEGRITY VIEW

ArtifactIntegrityView
- hash_value: optional string
- hash_algorithm: optional string
- integrity_status: enum(
    "ok",
    "not_checked",
    "missing_hash",
    "mismatch",
    "unknown"
  )
- integrity_message: optional string

Rules:
- the viewer must not fabricate integrity results
- mismatch must remain visually distinct

11. ARTIFACT LINEAGE VIEW

ArtifactLineageView
- producer_node_id: optional string
- producer_event_id: optional string
- producer_run_id: optional string
- source_artifact_ids: list[string]
- derived_artifact_ids: list[string]
- lineage_summary: optional string

Purpose:
Shows where the artifact came from and what it led to.

12. ARTIFACT RELATED LINKS VIEW

ArtifactRelatedLinksView
- related_graph_target_ids: list[string]
- related_trace_event_ids: list[string]
- related_validation_finding_ids: list[string]
- related_output_names: list[string]
- related_execution_run_id: optional string

Purpose:
Allows the viewer to coordinate with other modules.

13. ARTIFACT FILTER STATE VIEW

ArtifactFilterStateView
- show_final: bool
- show_intermediate: bool
- show_debug: bool
- only_integrity_issues: bool
- search_query: optional string
- group_by: enum("none", "producer", "category", "type")

14. ARTIFACT DIAGNOSTICS VIEW

ArtifactDiagnosticsView
- missing_body_count: int
- unavailable_preview_count: int
- integrity_warning_count: int
- load_error_count: int
- last_error_label: optional string

Rules:
- unavailable artifact content must be surfaced, not hidden
- diagnostics must remain separate from artifact truth

15. LIVE EXECUTION RULES

When source_mode = "live_execution_artifacts":
- artifact_list may grow over time
- previews may appear before final bodies
- intermediate artifacts may later be followed by final artifacts

The viewer must not pretend the list is finalized during active execution.

16. EXECUTION RECORD RULES

When source_mode = "execution_record_artifacts":
- artifacts are historical
- lineage and producer context should come from recorded execution truth
- artifact mutability controls must remain unavailable

17. WORKING SAVE RULES

When source_mode = "working_save_artifact_refs":
- only recent/local artifact references may be present
- this is not a substitute for full execution history
- stale or missing refs must remain visible as refs, not converted into fake history

18. LARGE / BINARY ARTIFACT RULES

The viewer must support artifacts whose full bodies are not practical to inline.

Examples:
- binary files
- large JSON outputs
- reports
- debug bundles

Rules:
- references/previews are acceptable
- the UI must distinguish reference-only artifacts from fully loaded artifacts

19. PANEL ACTION BOUNDARY

The Artifact Viewer may emit:
- select-artifact actions
- open-related-trace actions
- focus-producer-node actions
- focus-related-output actions

The Artifact Viewer must not:
- mutate artifacts
- rewrite artifact lineage
- fabricate previews as truth
- collapse append-only history into editable state

20. MINIMUM FIRST IMPLEMENTATION

The first implementation of ArtifactViewerViewModel should support:

- source_mode
- viewer_status
- artifact summary counts
- artifact list
- selected artifact detail
- integrity metadata
- lineage summary
- related links
- filter/search state
- diagnostics for missing/unavailable artifacts

21. FINAL DECISION

ArtifactViewerViewModel is the official UI-facing contract
for presenting artifact summaries, previews, integrity metadata,
and artifact provenance in Nexa.

It is the stable artifact-inspection projection layer
for Artifact Viewer UI modules.

It is not the artifact store itself,
and it must never become a mutation surface for artifact truth.

22. LOCALIZATION ALIGNMENT

22.1 Artifact Viewer must distinguish artifact content from UI chrome.

Localization-facing chrome/system fields:
- viewer controls
- section labels
- unsupported-preview messages
- integrity-warning text
- empty-state text

Content-bearing fields:
- artifact title when authored/imported/generated
- artifact preview body
- metadata values that originate from run content

22.2 Artifact ids, hashes, provenance refs, and integrity states remain canonical values.
Localized labels are derived separately.
