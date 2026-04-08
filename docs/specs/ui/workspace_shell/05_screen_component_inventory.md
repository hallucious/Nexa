# Screen Component Inventory v1

## Recommended save path
`docs/specs/ui/workspace_shell/05_screen_component_inventory.md`

## 1. Purpose

This document lists the concrete UI components required to realize the Nexa shell.

It is more granular than a wireframe and more practical than abstract shell language.

## 2. Top-level shell

### `WorkspaceShell`
Responsibilities:
- layout orchestration
- mode-aware panel emphasis
- keyboard shortcut boundary
- global shell state projection

Must never own:
- structural truth
- execution truth
- approval truth

## 3. Top Bar family

- `WorkspaceBreadcrumb`
- `StorageRoleBadge`
- `GlobalStatusSummary`
- `PrimaryActionCluster`
- `ModeSwitcher`
- `SearchQuickJump`

These are all global.

## 4. Left Rail family

- `OutlinePane`
- `TemplateLibraryPane`
- `LensSelectorPane`
- `StorageNavigatorPane`
- `ProposalOutlinePane`
- `RunOutlinePane`

These are about navigation and interpretation, not truth mutation.

## 5. Graph region family

- `GraphHeader`
- `GraphToolbar`
- `GraphCanvas`
- `GraphOverlayLayer`
- `GraphSelectionLayer`
- `GraphPreviewLayer`
- `GraphNodeCard`
- `GraphEdgeLine`
- `GraphGroupFrame`
- `GraphMiniMap` (optional early)

## 6. Right Stack family

- `InspectorPanel`
- `DesignerPanel`
- `ExecutionSidePanel`

## 7. Inspector internals

- `SelectedObjectHeader`
- `ObjectStatusSummary`
- `EditableFieldSection`
- `ReadonlyFieldSection`
- `RelatedFindingsSection`
- `RelatedExecutionSection`
- `RelatedArtifactsSection`
- `InspectorActionBar`

## 8. Designer internals

- `DesignerRequestInput`
- `IntentSummaryCard`
- `PatchSummaryCard`
- `PrecheckSummaryCard`
- `AssumptionList`
- `ConfirmationList`
- `DesignerActionBar`

## 9. Execution internals

- `RunHeader`
- `ActiveNodeCard`
- `ProgressCard`
- `RecentEventsList`
- `ExecutionControlBar`
- `LatestOutputSummary`

## 10. Bottom Dock family

- `ValidationTab`
- `ExecutionTab`
- `TraceTab`
- `ArtifactsTab`
- `DiffTab`
- optional `PrecheckTab`

## 11. Bottom Dock internals by tab

### Validation
- `ValidationStatusBanner`
- `FindingFilterBar`
- `BlockingFindingsList`
- `WarningFindingsList`
- `ConfirmationFindingsList`
- `SuggestedActionsRow`

### Execution
- `ExecutionSummaryStrip`
- `NodeProgressTable`
- `RunMetricsPanel`
- `ExecutionWarningsList`

### Trace
- `TraceTimelineList`
- `TraceFilterBar`
- `EventDetailPane`
- `TraceJumpLinks`

### Artifacts
- `ArtifactCategoryTabs`
- `ArtifactList`
- `ArtifactPreviewPane`
- `ArtifactMetadataPane`
- `ArtifactLinkGraph`

### Diff
- `DiffScopeHeader`
- `DiffModeSelector`
- `DiffSummaryCard`
- `StructuralDeltaList`
- `OutputDeltaList`
- `ExecutionDeltaList`
- `DiffJumpLinks`

## 12. Why this inventory exists

This list prevents vague implementation.
A future UI implementation can now ask:
- which component family is missing?
- what is its job?
- what truth boundary must it respect?
