from __future__ import annotations

from dataclasses import dataclass, field

from src.storage.models.commit_snapshot_model import CommitSnapshotModel
from src.storage.models.execution_record_model import ExecutionRecordModel
from src.storage.models.loaded_nex_artifact import LoadedNexArtifact
from src.storage.models.working_save_model import WorkingSaveModel
from src.ui.action_schema import BuilderActionSchemaView, BuilderActionView, read_builder_action_schema
from src.ui.builder_workflow_hub import BuilderWorkflowHubViewModel
from src.ui.panel_coordination import BuilderPanelCoordinationStateView


@dataclass(frozen=True)
class BuilderCommandRouteView:
    route_id: str
    action_id: str
    label: str
    command_type: str
    target_domain: str
    workflow_id: str | None
    preferred_workspace_id: str
    preferred_panel_id: str
    engine_boundary: str
    enabled: bool
    reason_disabled: str | None = None
    destructive: bool = False
    requires_confirmation: bool = False


@dataclass(frozen=True)
class BuilderCommandRoutingViewModel:
    routing_status: str = "ready"
    source_role: str = "none"
    routes: list[BuilderCommandRouteView] = field(default_factory=list)
    enabled_route_count: int = 0
    disabled_route_count: int = 0
    explanation: str | None = None


SourceLike = WorkingSaveModel | CommitSnapshotModel | ExecutionRecordModel | LoadedNexArtifact | None


def _unwrap(source: SourceLike):
    if isinstance(source, LoadedNexArtifact):
        return source.parsed_model
    return source


def _storage_role(source) -> str:
    if isinstance(source, WorkingSaveModel):
        return "working_save"
    if isinstance(source, CommitSnapshotModel):
        return "commit_snapshot"
    if isinstance(source, ExecutionRecordModel):
        return "execution_record"
    return "none"


def _route_template(action_id: str) -> tuple[str, str, str | None, str, str, str]:
    mapping = {
        "save_working_save": ("storage.save_working_save", "storage", None, "visual_editor", "storage", "working_save_api"),
        "open_visual_editor": ("ui.open_visual_editor", "ui", None, "visual_editor", "graph", "ui_boundary"),
        "open_node_configuration": ("ui.open_node_configuration", "ui", None, "node_configuration", "inspector", "ui_boundary"),
        "open_runtime_monitoring": ("ui.open_runtime_monitoring", "ui", None, "runtime_monitoring", "execution", "ui_boundary"),
        "review_draft": ("designer.review_draft", "designer", "proposal_commit", "node_configuration", "validation", "designer_flow"),
        "commit_snapshot": ("storage.commit_snapshot", "storage", "proposal_commit", "node_configuration", "designer", "commit_gateway"),
        "open_latest_commit": ("storage.open_latest_commit", "storage", None, "visual_editor", "storage", "ui_boundary"),
        "select_rollback_target": ("storage.select_rollback_target", "storage", None, "visual_editor", "storage", "ui_boundary"),
        "run_current": ("execution.run_current", "execution", "execution_launch", "runtime_monitoring", "execution", "execution_runner"),
        "run_from_commit": ("execution.run_from_commit", "execution", "execution_launch", "runtime_monitoring", "execution", "execution_runner"),
        "cancel_run": ("execution.cancel_run", "execution", "execution_launch", "runtime_monitoring", "execution", "execution_runner"),
        "replay_latest": ("execution.replay_latest", "execution", "execution_launch", "runtime_monitoring", "trace_timeline", "execution_replay"),
        "open_latest_run": ("execution.open_latest_run", "execution", "execution_launch", "runtime_monitoring", "execution", "execution_replay"),
        "open_trace": ("execution.open_trace", "execution", "execution_launch", "runtime_monitoring", "trace_timeline", "execution_replay"),
        "open_artifacts": ("execution.open_artifacts", "execution", "execution_launch", "runtime_monitoring", "artifact", "execution_replay"),
        "open_diff": ("comparison.open_diff", "comparison", None, "visual_editor", "diff", "diff_engine"),
        "compare_runs": ("comparison.compare_runs", "comparison", "execution_launch", "visual_editor", "diff", "diff_engine"),
        "approve_for_commit": ("designer.approve_for_commit", "designer", "proposal_commit", "node_configuration", "designer", "approval_flow"),
        "request_revision": ("designer.request_revision", "designer", "proposal_commit", "node_configuration", "designer", "designer_flow"),
        "open_provider_setup": ("ui.open_provider_setup", "ui", "proposal_commit", "node_configuration", "designer", "ui_boundary"),
        "create_circuit_from_template": ("ui.open_template_gallery", "ui", "proposal_commit", "node_configuration", "designer", "ui_boundary"),
        "open_file_input": ("ui.open_file_input", "ui", "proposal_commit", "node_configuration", "designer", "ui_boundary"),
        "enter_url_input": ("ui.enter_url_input", "ui", "proposal_commit", "node_configuration", "designer", "ui_boundary"),
        "review_run_cost": ("ui.review_run_cost", "ui", "execution_launch", "runtime_monitoring", "execution", "ui_boundary"),
        "watch_run_progress": ("ui.watch_run_progress", "ui", "execution_launch", "runtime_monitoring", "execution", "ui_boundary"),
        "open_circuit_library": ("ui.open_circuit_library", "ui", None, "library", "circuit_library", "ui_boundary"),
        "open_result_history": ("ui.open_result_history", "ui", None, "runtime_monitoring", "result_history", "ui_boundary"),
        "open_feedback_channel": ("ui.open_feedback_channel", "ui", None, "library", "feedback_channel", "ui_boundary"),
    }
    return mapping.get(action_id, (f"builder.{action_id}", "builder", None, "visual_editor", "graph", "ui_boundary"))


def _prioritize_workspace(
    workspace_id: str,
    panel_id: str,
    *,
    workflow_hub: BuilderWorkflowHubViewModel | None,
    coordination_state: BuilderPanelCoordinationStateView | None,
) -> tuple[str, str]:
    if workflow_hub is not None and workflow_hub.recommended_workflow_id == "execution_launch":
        if workspace_id == "runtime_monitoring":
            return workspace_id, panel_id
    if coordination_state is not None and coordination_state.active_panel == "diff" and workspace_id == "visual_editor":
        return workspace_id, "diff"
    return workspace_id, panel_id


def read_builder_command_routing_view_model(
    source: SourceLike,
    *,
    action_schema: BuilderActionSchemaView | None = None,
    workflow_hub: BuilderWorkflowHubViewModel | None = None,
    coordination_state: BuilderPanelCoordinationStateView | None = None,
    explanation: str | None = None,
) -> BuilderCommandRoutingViewModel:
    source_unwrapped = _unwrap(source)
    source_role = _storage_role(source_unwrapped)
    action_schema = action_schema or read_builder_action_schema(source_unwrapped)

    routes: list[BuilderCommandRouteView] = []
    for action in [*action_schema.primary_actions, *action_schema.secondary_actions, *action_schema.contextual_actions]:
        command_type, target_domain, workflow_id, workspace_id, panel_id, engine_boundary = _route_template(action.action_id)
        workspace_id, panel_id = _prioritize_workspace(
            workspace_id,
            panel_id,
            workflow_hub=workflow_hub,
            coordination_state=coordination_state,
        )
        routes.append(
            BuilderCommandRouteView(
                route_id=f"route:{action.action_id}",
                action_id=action.action_id,
                label=action.label,
                command_type=command_type,
                target_domain=target_domain,
                workflow_id=workflow_id,
                preferred_workspace_id=workspace_id,
                preferred_panel_id=panel_id,
                engine_boundary=engine_boundary,
                enabled=action.enabled,
                reason_disabled=action.reason_disabled,
                destructive=action.destructive,
                requires_confirmation=action.requires_confirmation,
            )
        )

    enabled_route_count = sum(1 for route in routes if route.enabled)
    disabled_route_count = len(routes) - enabled_route_count
    if not routes:
        routing_status = "empty"
    elif enabled_route_count == 0:
        routing_status = "blocked"
    elif any(route.requires_confirmation for route in routes if route.enabled) or disabled_route_count:
        routing_status = "attention"
    else:
        routing_status = "ready"
    return BuilderCommandRoutingViewModel(
        routing_status=routing_status,
        source_role=source_role,
        routes=routes,
        enabled_route_count=enabled_route_count,
        disabled_route_count=disabled_route_count,
        explanation=explanation,
    )


__all__ = [
    "BuilderCommandRouteView",
    "BuilderCommandRoutingViewModel",
    "read_builder_command_routing_view_model",
]
