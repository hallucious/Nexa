[DESIGN]
[UI_STATE_OWNERSHIP_AND_PERSISTENCE_SPEC v0.1]

1. PURPOSE

This document defines the official ownership and persistence boundary
for UI state in Nexa.

Its purpose is to provide a stable rule set for:

- what UI state exists
- which state is UI-owned
- which state remains engine-owned
- where UI state may be persisted
- what UI state may be restored
- what UI state must never be confused with structural, approval,
  execution, or storage truth

This specification exists to prevent future UI work from leaking into
engine truth through convenience-driven persistence.

2. POSITION IN ARCHITECTURE

Official structure:

Nexa Engine
→ UI Adapter / View Model Layer
→ UI Module Slots
→ Theme / Layout Layer

Within this structure:

- engine owns structural truth
- engine owns approval truth
- engine owns execution truth
- engine owns storage lifecycle truth
- UI owns only presentation and interaction state

This means UI persistence is not an alternative savefile or execution record system.

3. CORE PRINCIPLES

3.1 UI-owned state is real, but it is not engine truth.
3.2 Persisting UI-owned state must not change execution meaning.
3.3 Restoring UI-owned state must not be interpreted as structural restore.
3.4 UI state and engine state must remain explicitly separable.
3.5 UI persistence must support replaceable shells and modules.
3.6 UI persistence must be safe even when Working Save is invalid.
3.7 UI persistence must never silently cross commit / approval / execution boundaries.

4. TOP-LEVEL MODEL

UIStateOwnershipModel
- ui_state_version: string
- ownership_summary: OwnershipSummaryView
- local_view_state: LocalViewStateView
- workspace_state: WorkspaceStateView
- panel_state: PanelStateView
- theme_layout_state: ThemeLayoutStateView
- filter_sort_state: FilterSortStateView
- selection_state: SelectionStateView
- session_interaction_state: SessionInteractionStateView
- persistence_policy: UIPersistencePolicyView
- diagnostics: UIStateDiagnosticsView
- explanation: optional string

5. OWNERSHIP SUMMARY VIEW

OwnershipSummaryView
- engine_owned_domains: list[string]
- ui_owned_domains: list[string]
- explicitly_forbidden_crossovers: list[string]

Minimum engine-owned domains:
- circuit structure
- resources truth
- validation truth
- approval truth
- execution truth
- trace/history truth
- storage role truth
- commit lineage truth

Minimum UI-owned domains:
- selected object
- active tab/panel
- panel visibility
- zoom level
- scroll position
- node positions used only for visualization
- collapsed/expanded state
- local filters/sorts
- layout preset selection
- theme selection
- temporary highlights

6. LOCAL VIEW STATE VIEW

LocalViewStateView
- zoom_level: optional float
- viewport_center: optional dict
- scroll_offsets: optional dict
- temporary_highlights: list[string]
- hover_target: optional string
- active_tab_id: optional string

Purpose:
Represents ephemeral presentation state.

Rules:
- these values are UI-owned only
- these values may be restored for ergonomics
- these values must not alter graph semantics

7. WORKSPACE STATE VIEW

WorkspaceStateView
- node_positions: dict
- group_collapsed_state: dict
- manual_layout_notes: optional dict
- workspace_focus_mode: optional string

Rules:
- node_positions are visual placement data
- restoring node_positions must not be interpreted as graph mutation
- workspace state may be persisted in UI-oriented sections or user preferences only

8. PANEL STATE VIEW

PanelStateView
- visible_panels: list[string]
- pinned_panels: list[string]
- panel_sizes: dict
- panel_order: list[string]
- floating_panels: list[string]

Rules:
- panel state belongs to UI-owned state
- panel state may affect ergonomics only
- hidden panels must not imply hidden truth resolution

9. THEME / LAYOUT STATE VIEW

ThemeLayoutStateView
- active_theme_id: optional string
- active_layout_id: optional string
- appearance_mode: optional string
- density_mode: optional string
- user_mode: optional string
- accessibility_flags: dict

Rules:
- theme/layout state is UI-owned
- theme/layout persistence must not alter lifecycle semantics
- theme/layout restore must not change permissions

10. FILTER / SORT STATE VIEW

FilterSortStateView
- validation_filters: dict
- execution_filters: dict
- artifact_filters: dict
- diff_filters: dict
- sort_preferences: dict

Purpose:
Represents temporary reading preferences across modules.

Rules:
- filtering must not redefine the underlying truth
- a filtered-out finding still exists
- sorting must not imply priority or severity changes unless explicitly engine-provided

11. SELECTION STATE VIEW

SelectionStateView
- selected_node_ids: list[string]
- selected_edge_ids: list[string]
- selected_artifact_ids: list[string]
- selected_trace_event_ids: list[string]
- selected_storage_ref: optional string
- selected_diff_change_id: optional string

Rules:
- selection state is UI-owned
- selection restore may improve continuity
- selection restore must not trigger mutation by itself

12. SESSION INTERACTION STATE VIEW

SessionInteractionStateView
- unsent_designer_text: optional string
- draft_form_values: dict
- dismissed_hints: list[string]
- last_opened_sections: list[string]
- local_compare_pairs: optional dict

Purpose:
Represents in-progress interaction state that improves continuity.

Rules:
- session interaction state must not be treated as approved intent
- restoring draft form values must not create Designer actions automatically

13. UI PERSISTENCE POLICY VIEW

UIPersistencePolicyView
- persistence_mode: enum(
    "in_memory_only",
    "workspace_local",
    "user_profile",
    "ui_section_only",
    "mixed",
    "unknown"
  )
- allowed_targets: list[string]
- forbidden_targets: list[string]
- restore_behavior: enum(
    "best_effort",
    "strict_ui_only",
    "partial_restore",
    "unknown"
  )
- invalid_draft_behavior: enum(
    "restore_ui_state_allowed",
    "restore_ui_state_limited",
    "no_restore",
    "unknown"
  )

Purpose:
Declares where UI state may be written and how restore should behave.

14. ALLOWED PERSISTENCE TARGETS

UI-owned state may be persisted to one or more of the following:

- in-memory session state
- user preference store
- shell-specific local workspace store
- explicitly UI-scoped savefile section when such storage is allowed by contract

Rules:
- UI persistence target must be explicit
- UI persistence target must not silently become engine truth
- the same UI state may be represented differently across replaceable shells

15. FORBIDDEN PERSISTENCE TARGETS

UI-owned state must not be persisted as if it were:

- approved structural truth
- execution record truth
- validation finding truth
- approval decision truth
- commit lineage truth
- replay/audit evidence

This means the following are forbidden:

- treating panel layout restore as graph restore
- treating theme selection as storage role metadata
- treating selection restore as execution replay state
- treating local designer draft text as approved patch state

16. SAVEFILE RELATIONSHIP RULES

When savefiles contain a `ui` section or similar UI-scoped storage:

- that section remains UI-owned
- that section is not part of execution semantics
- that section is not approval truth
- that section is not replay truth

Implications:
- Working Save may carry UI convenience state for editing continuity
- Commit Snapshot must not be polluted with transient UI clutter
- Execution Record must not be treated as a place for general UI workspace restore

17. WORKING SAVE / COMMIT SNAPSHOT / EXECUTION RECORD RULES

17.1 Working Save
- UI restore support is most acceptable here
- invalid draft status does not block UI restore
- UI clutter must still remain clearly UI-scoped

17.2 Commit Snapshot
- UI state should be minimized or absent
- no transient editor noise should be treated as commit truth

17.3 Execution Record
- run history is engine-owned
- UI viewing preferences may exist externally, but must not be embedded as run truth

18. RESTORE BOUNDARY RULES

Restoring UI state may:
- reopen panels
- restore layout
- restore selected object
- restore filters
- restore local draft text
- restore zoom/position

Restoring UI state must not:
- change node/resource definitions
- change validation outcomes
- change approval outcomes
- change execution results
- create or apply patches
- create commits
- alter storage roles

19. MODULE REPLACEABILITY RULES

Because Nexa UI is shell-replaceable and module-replaceable:

- persisted UI state must be portable enough for shared semantics
  where useful
- but must not assume one fixed shell implementation forever
- module-specific persistence should degrade safely when a module is absent

Example:
- if Trace Viewer is replaced, old trace-panel filter state may be ignored safely
- this is acceptable because UI persistence is best-effort, not truth-critical

20. DIAGNOSTICS VIEW

UIStateDiagnosticsView
- forbidden_crossover_count: int
- unsupported_restore_count: int
- missing_module_restore_count: int
- stale_ui_state_count: int
- load_error_count: int
- last_error_label: optional string

Purpose:
Provides visibility when UI persistence becomes inconsistent or unsafe.

21. MINIMUM FIRST IMPLEMENTATION

The first implementation of UI state ownership/persistence should support:

- explicit engine-owned vs UI-owned boundary
- panel/layout persistence
- theme/layout persistence
- selection persistence
- filter/sort persistence
- safe Working Save UI restore
- diagnostics for forbidden truth crossover

22. FINAL DECISION

UI-owned state in Nexa is valid and useful,
but it remains strictly separate from engine-owned truth.

UI persistence is an ergonomic continuity system,
not a structural, approval, execution, or storage truth system.

Any future UI restore mechanism that blurs that boundary is invalid.
