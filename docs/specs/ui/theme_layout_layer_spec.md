[DESIGN]
[THEME_LAYOUT_LAYER_SPEC v0.1]

1. PURPOSE

This document defines the official Theme / Layout Layer
for Nexa UI.

Its purpose is to provide a stable, replaceable, UI-only layer for:

- visual theming
- layout presets
- density modes
- beginner / advanced workspace presentation
- panel arrangement presets
- accessibility-oriented presentation options

The Theme / Layout Layer is the outermost visual-and-ergonomic layer
of the Nexa UI shell.

It is responsible for:

- controlling appearance without changing execution meaning
- supporting multiple visual skins over the same UI contract
- supporting layout presets for different user levels and tasks
- preserving UI ergonomics while keeping engine truth untouched

It is not responsible for:

- structural truth
- approval truth
- execution truth
- storage lifecycle truth
- direct mutation of engine-owned artifacts

2. POSITION IN UI ARCHITECTURE

The Theme / Layout Layer sits above UI modules.

Official structure:

Nexa Engine
→ UI Adapter / View Model Layer
→ UI Module Slots
→ Theme / Layout Layer

This means Theme / Layout is not an alternative engine contract.
It is the outer presentation layer only.

3. CORE PRINCIPLES

3.1 Theme / Layout is visual, not semantic.
3.2 Theme / Layout may change presentation, but must not change execution meaning.
3.3 Theme / Layout must be replaceable.
3.4 Layout presets must not redefine storage roles or approval state.
3.5 Beginner / advanced presentation differences must remain UI-only.
3.6 Accessibility adjustments must be supported without changing engine truth.
3.7 Theme / Layout settings belong to UI-owned state.

4. TOP-LEVEL VIEW MODEL

ThemeLayoutViewModel
- active_theme_id: optional string
- active_layout_id: optional string
- appearance_mode: enum(
    "light",
    "dark",
    "system",
    "high_contrast",
    "unknown"
  )
- density_mode: enum(
    "compact",
    "comfortable",
    "expanded",
    "unknown"
  )
- user_mode: enum(
    "beginner",
    "advanced",
    "review",
    "execution_focus",
    "unknown"
  )
- available_themes: list[ThemeOptionView]
- available_layouts: list[LayoutPresetView]
- accessibility_state: AccessibilityStateView
- panel_visibility_state: PanelVisibilityStateView
- workspace_layout_state: WorkspaceLayoutStateView
- action_hints: list[ThemeLayoutActionHint]
- diagnostics: ThemeLayoutDiagnosticsView
- explanation: optional string

5. FIELD SEMANTICS

5.1 active_theme_id
The currently applied visual theme identifier.

5.2 active_layout_id
The currently applied layout preset identifier.

5.3 appearance_mode
High-level appearance mode selection.

5.4 density_mode
Visual spacing and information density mode.

5.5 user_mode
Presentation profile for task/skill alignment.

5.6 available_themes / available_layouts
Selectable UI-only configuration options.

5.7 accessibility_state
Current accessibility-related settings.

5.8 panel_visibility_state
Which UI panels are currently shown or hidden.

5.9 workspace_layout_state
Arrangement data for panel sizes, docking, and orientation.

5.10 action_hints
Bounded UI-facing actions related to theme/layout switching.

5.11 diagnostics
Conflicts, unsupported presets, or restore/load issues.

6. THEME OPTION VIEW

ThemeOptionView
- theme_id: string
- label: string
- category: enum(
    "default",
    "professional",
    "minimal",
    "high_contrast",
    "custom"
  )
- description: optional string
- supports_dark_mode: bool
- supports_high_contrast: bool
- recommended_for: optional list[string]

Purpose:
Represents one selectable visual theme.

7. LAYOUT PRESET VIEW

LayoutPresetView
- layout_id: string
- label: string
- preset_type: enum(
    "beginner",
    "advanced",
    "review",
    "execution_focus",
    "designer_focus",
    "custom"
  )
- description: optional string
- visible_panels: list[string]
- default_panel_positions: dict
- recommended_for: optional list[string]

Purpose:
Represents one selectable panel/layout preset.

Rules:
- preset_type is ergonomic classification only
- it must not redefine module responsibilities or engine state

8. ACCESSIBILITY STATE VIEW

AccessibilityStateView
- high_contrast_enabled: bool
- reduced_motion_enabled: bool
- large_text_enabled: bool
- focus_emphasis_enabled: bool
- color_independent_status_markers: bool

Purpose:
Supports accessibility-oriented presentation.

Rules:
- accessibility settings must not alter underlying truth values
- status distinctions must remain readable without relying on color alone

9. PANEL VISIBILITY STATE VIEW

PanelVisibilityStateView
- graph_workspace_visible: bool
- inspector_visible: bool
- validation_visible: bool
- execution_visible: bool
- designer_visible: bool
- trace_visible: bool
- artifact_visible: bool
- storage_visible: bool
- diff_visible: bool

Rules:
- hiding a panel hides presentation only
- hidden panels do not imply absent truth
- no panel may be hidden in a way that silently suppresses blocking truth

10. WORKSPACE LAYOUT STATE VIEW

WorkspaceLayoutStateView
- left_sidebar_width: optional int
- right_sidebar_width: optional int
- bottom_panel_height: optional int
- center_focus_mode: bool
- dock_mode: enum(
    "multi_panel",
    "single_focus",
    "split_horizontal",
    "split_vertical",
    "unknown"
  )
- panel_order: list[string]
- floating_panels_enabled: bool

Purpose:
Represents UI arrangement and docking state.

Rules:
- workspace layout is UI-owned state
- it must not leak into engine-owned structural or execution truth

11. THEME / LAYOUT ACTION HINT

ThemeLayoutActionHint
- action_type: enum(
    "set_theme",
    "set_layout_preset",
    "toggle_panel_visibility",
    "set_density_mode",
    "set_user_mode",
    "restore_default_layout",
    "toggle_accessibility_option",
    "none"
  )
- label: string
- enabled: bool
- reason_disabled: optional string
- target_ref: optional string

Purpose:
Provides bounded UI actions for the outer presentation layer.

12. THEME / LAYOUT DIAGNOSTICS VIEW

ThemeLayoutDiagnosticsView
- unsupported_theme_count: int
- unsupported_layout_count: int
- restore_conflict_count: int
- hidden_blocking_truth_risk: bool
- load_error_count: int
- last_error_label: optional string

Rules:
- diagnostics must warn when layout settings risk hiding important blocking information
- diagnostics must not invent underlying engine issues

13. BEGINNER / ADVANCED MODE RULES

13.1 beginner mode
- simpler panel visibility defaults
- larger spacing
- more explanatory labels
- fewer simultaneously visible advanced surfaces

13.2 advanced mode
- denser information display
- more simultaneous panels
- faster navigation emphasis
- more direct inspection surfaces

Rules:
- both modes operate over the same engine truth
- beginner mode must not alter or simplify truth itself
- advanced mode must not bypass approval or validation boundaries

14. REVIEW / EXECUTION FOCUS RULES

14.1 review mode
- prioritizes Validation, Diff, Storage, and Designer preview surfaces
- useful before approval/commit

14.2 execution_focus mode
- prioritizes Execution, Trace, Artifact, and Graph visibility
- useful during or after runs

Rules:
- these are presentation presets only
- they must not change lifecycle state or execution permissions

15. CUSTOMIZATION BOUNDARY RULES

Theme / Layout customization may change:
- color palette
- spacing
- panel arrangement
- font scaling
- visible module emphasis

Theme / Layout customization must not change:
- approval state semantics
- storage role semantics
- validation severity semantics
- execution status semantics
- trace/event ordering semantics

16. STORAGE RELATIONSHIP RULES

Theme / Layout settings belong to UI-owned state.
They may be stored in UI-oriented sections or user preferences,
but they are not part of engine-owned structural or execution truth.

This means:
- theme changes do not create commits
- layout changes do not alter Working Save / Commit Snapshot / Execution Record meaning
- UI presentation restore must not be confused with structural restore

17. PANEL ACTION BOUNDARY

The Theme / Layout Layer may emit:
- theme change requests
- layout preset change requests
- panel visibility toggles
- accessibility toggles
- restore-default-layout requests

The Theme / Layout Layer must not:
- change engine-owned truth
- suppress blocking findings as if resolved
- mutate compared artifacts
- alter approval flow
- alter execution permissions

18. MINIMUM FIRST IMPLEMENTATION

The first implementation of ThemeLayoutViewModel should support:

- active theme selection
- active layout preset selection
- appearance mode
- density mode
- beginner / advanced presentation mode
- panel visibility state
- workspace arrangement state
- accessibility toggles
- diagnostics for hidden-blocking-truth risk

19. FINAL DECISION

ThemeLayoutViewModel is the official UI-facing contract
for the outermost visual, ergonomic, and accessibility layer of Nexa UI.

It is the stable visual-and-ergonomic projection layer
for Theme / Layout UI systems.

It is not an engine contract,
and it must never become a path that changes structural,
approval, execution, or storage truth.
