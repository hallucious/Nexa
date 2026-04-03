[DESIGN]
[UI_SECTION_SCHEMA_SPEC v0.1]

1. PURPOSE

This document defines the official `.nex.ui` section schema for Nexa.

Its purpose is to provide a stable, explicit, UI-scoped storage structure for:

- workspace continuity
- visual layout restore
- panel state restore
- selection continuity
- theme/layout continuity
- safe editor ergonomics

This specification exists to connect:

- UI State Ownership & Persistence rules
- `.nex` unified top-level schema
- Working Save / Commit Snapshot storage-role separation

The `.nex.ui` section is UI-owned.
It is not structural truth, approval truth, execution truth, or storage-lifecycle truth.

2. POSITION IN STORAGE SYSTEM

Official `.nex` family structure already distinguishes:

- Working Save
- Commit Snapshot

and the broader storage lifecycle already distinguishes:

- Working Save
- Commit Snapshot
- Execution Record

Within that system, the `ui` section is allowed only as a UI-scoped section
and must remain clearly separate from engine-owned meaning.

3. CORE PRINCIPLES

3.1 The `ui` section is UI-owned only.
3.2 The `ui` section must never affect execution semantics.
3.3 The `ui` section must never redefine approval/commit truth.
3.4 The `ui` section is primarily for Working Save continuity.
3.5 The `ui` section must be portable enough for replaceable UI shells,
    but must not force one shell forever.
3.6 Missing or unsupported `ui` state must fail softly.
3.7 `ui` section restore is best-effort ergonomics, not truth restoration.

4. ROLE-SPECIFIC RULES

4.1 Working Save
- `ui` section is allowed
- `ui` section is recommended when editor continuity matters
- invalid or incomplete draft status does not block `ui` restore

4.2 Commit Snapshot
- `ui` section should be absent by default
- if ever allowed later, it must be strictly minimal and clearly non-authoritative
- transient editor clutter must not enter approved structural artifacts

4.3 Execution Record
- general `.nex.ui` schema does not apply here as workspace restore truth
- run-view preferences belong outside execution truth

5. TOP-LEVEL UI SECTION MODEL

UISection
- schema_version: string
- shell_compatibility: UIShellCompatibilityView
- workspace: UIWorkspaceSection
- panels: UIPanelsSection
- selection: UISelectionSection
- filters: UIFiltersSection
- appearance: UIAppearanceSection
- session: UISessionSection
- diagnostics: optional UIDiagnosticsSection

Rules:
- all subsections are UI-scoped
- unsupported subsections may be ignored safely
- unknown future fields may be preserved when possible, but must not change truth semantics

6. SCHEMA VERSION

schema_version
- identifies the `ui` section schema version
- is independent from engine format version
- allows UI schema migration without redefining structural schema

Example:
"schema_version": "1.0.0"

7. SHELL COMPATIBILITY VIEW

UIShellCompatibilityView
- preferred_shell_id: optional string
- preferred_shell_version: optional string
- module_state_versions: dict
- portability_mode: enum(
    "portable_preferred",
    "shell_specific_allowed",
    "mixed",
    "unknown"
  )

Purpose:
Declares compatibility hints for restoring UI state across shells/modules.

Rules:
- this is advisory only
- failure to match a shell must not invalidate the `.nex` artifact
- shell mismatch must degrade gracefully

8. WORKSPACE SECTION

UIWorkspaceSection
- viewport: UIViewportState
- layout: UILayoutState
- graph_presentation: UIGraphPresentationState

8.1 UIViewportState
- zoom_level: optional float
- center_x: optional float
- center_y: optional float
- scroll_x: optional float
- scroll_y: optional float

Rules:
- viewport state affects presentation only
- restore must not change node semantics

8.2 UILayoutState
- node_positions: dict
- group_positions: dict
- collapsed_groups: list[string]
- manual_notes: optional dict
- focus_mode: optional string

Rules:
- node_positions are visual placement hints only
- layout restore must not be interpreted as structural graph mutation

8.3 UIGraphPresentationState
- visible_overlays: list[string]
- edge_label_visibility: optional bool
- node_detail_density: optional string
- preview_overlay_enabled: optional bool

Rules:
- graph presentation state is UI-only
- hiding an overlay does not change the underlying truth

9. PANELS SECTION

UIPanelsSection
- visible_panels: list[string]
- pinned_panels: list[string]
- active_panel: optional string
- panel_order: list[string]
- panel_sizes: dict
- floating_panels: list[string]
- dock_mode: optional string

Rules:
- panel state is UI ergonomics only
- hidden panel state must not imply hidden truth resolution

10. SELECTION SECTION

UISelectionSection
- selected_node_ids: list[string]
- selected_edge_ids: list[string]
- selected_output_ids: list[string]
- selected_artifact_ids: list[string]
- selected_trace_event_ids: list[string]
- selected_storage_ref: optional string
- selected_diff_change_id: optional string

Rules:
- restoring selection must not trigger engine mutation
- empty selection is valid
- stale selection references may be dropped safely

11. FILTERS SECTION

UIFiltersSection
- validation_filters: dict
- execution_filters: dict
- trace_filters: dict
- artifact_filters: dict
- diff_filters: dict
- sort_preferences: dict

Rules:
- filters alter reading, not truth
- filtered-out items still exist
- sort order must not redefine severity or priority unless engine-provided

12. APPEARANCE SECTION

UIAppearanceSection
- active_theme_id: optional string
- active_layout_id: optional string
- appearance_mode: optional string
- density_mode: optional string
- user_mode: optional string
- accessibility_flags: dict

Rules:
- appearance restore is UI-only
- accessibility state must remain non-semantic
- theme/layout restore must not change permissions, commit state, or execution state

13. SESSION SECTION

UISessionSection
- unsent_designer_text: optional string
- draft_form_values: dict
- dismissed_hints: list[string]
- recent_compare_pairs: optional dict
- last_opened_sections: list[string]

Rules:
- session data is in-progress interaction state only
- restoring unsent text must not create intent/patch/approval actions automatically
- session state should remain lightweight

14. DIAGNOSTICS SECTION

UIDiagnosticsSection
- stale_reference_count: int
- unsupported_module_state_count: int
- shell_mismatch_count: int
- load_warning_count: int
- last_warning_label: optional string

Purpose:
Allows the shell to record non-truth-critical restore issues.

Rules:
- diagnostics must never be treated as validation truth
- diagnostics may be discarded safely

15. MINIMUM FIRST SCHEMA

The first practical schema should support at least:

- schema_version
- workspace.viewport
- workspace.layout.node_positions
- panels.visible_panels
- panels.panel_sizes
- selection.selected_node_ids
- filters.validation_filters
- appearance.active_theme_id
- appearance.active_layout_id
- session.unsent_designer_text

16. EXAMPLE

{
  "ui": {
    "schema_version": "1.0.0",
    "shell_compatibility": {
      "preferred_shell_id": "nexa-default-shell",
      "preferred_shell_version": "0.1.0",
      "module_state_versions": {
        "graph_workspace": "1.0.0",
        "inspector_panel": "1.0.0"
      },
      "portability_mode": "portable_preferred"
    },
    "workspace": {
      "viewport": {
        "zoom_level": 0.9,
        "center_x": 1200,
        "center_y": 640
      },
      "layout": {
        "node_positions": {
          "node_a": {"x": 100, "y": 120},
          "node_b": {"x": 360, "y": 120}
        },
        "group_positions": {},
        "collapsed_groups": [],
        "focus_mode": "normal"
      },
      "graph_presentation": {
        "visible_overlays": ["validation", "preview"],
        "preview_overlay_enabled": true
      }
    },
    "panels": {
      "visible_panels": ["graph", "inspector", "validation", "designer"],
      "pinned_panels": ["inspector"],
      "active_panel": "designer",
      "panel_order": ["graph", "inspector", "validation", "designer"],
      "panel_sizes": {
        "left_sidebar_width": 280,
        "right_sidebar_width": 340,
        "bottom_panel_height": 220
      },
      "floating_panels": [],
      "dock_mode": "multi_panel"
    },
    "selection": {
      "selected_node_ids": ["node_b"],
      "selected_edge_ids": [],
      "selected_output_ids": [],
      "selected_artifact_ids": [],
      "selected_trace_event_ids": []
    },
    "filters": {
      "validation_filters": {
        "show_warnings": true,
        "show_blocking": true
      },
      "execution_filters": {},
      "trace_filters": {},
      "artifact_filters": {},
      "diff_filters": {},
      "sort_preferences": {}
    },
    "appearance": {
      "active_theme_id": "default-light",
      "active_layout_id": "beginner-review",
      "appearance_mode": "light",
      "density_mode": "comfortable",
      "user_mode": "beginner",
      "accessibility_flags": {
        "high_contrast_enabled": false,
        "reduced_motion_enabled": false
      }
    },
    "session": {
      "unsent_designer_text": "Add a review node before final output",
      "draft_form_values": {},
      "dismissed_hints": [],
      "last_opened_sections": ["designer_intent", "validation_findings"]
    }
  }
}

17. PARSER / LOADER RULES

17.1 Missing `ui`
- valid for Working Save
- shell uses defaults

17.2 Invalid `ui` subsection
- should produce UI-scoped warnings, not structural invalidity by default
- unless a future contract explicitly tightens this

17.3 Unknown `ui` fields
- may be ignored or preserved best-effort
- must not be reinterpreted as structural data

17.4 Stale references
- may be dropped safely during restore
- must not fail the whole `.nex` artifact load by default

18. FORBIDDEN CONTENT

The `ui` section must not contain authoritative copies of:

- approved commit status
- validation blocking truth
- execution outputs truth
- trace history truth
- artifact lineage truth
- storage role truth

Examples of forbidden misuse:
- `ui.commit_is_approved = true`
- `ui.last_execution_output = ...` as source of truth
- `ui.validation_blocking_count = 0` replacing real validation
- `ui.storage_role = "commit_snapshot"`

19. RELATIONSHIP TO DESIGNER FLOW

The `ui` section may store ergonomic continuity for Designer interaction such as:

- unsent designer text
- local open/closed sections
- local compare pair selection

But it must not store authoritative Designer pipeline truth such as:

- approved patch state
- authoritative precheck result
- authoritative commit approval result

Those remain engine-owned and must be reconstructed from the real pipeline objects.

20. FINAL DECISION

The `.nex.ui` section is the official UI-scoped continuity container for Nexa Working Save artifacts.

It exists to restore workspace ergonomics safely.
It is not a secondary truth system.

Any future use of `.nex.ui` that changes structural, approval, execution, or storage meaning is invalid.
