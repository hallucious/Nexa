from __future__ import annotations

from dataclasses import dataclass, field, replace

from src.contracts.nex_contract import ValidationReport
from src.designer.models.circuit_draft_preview import CircuitDraftPreview
from src.designer.models.circuit_patch_plan import CircuitPatchPlan
from src.designer.models.designer_approval_flow import DesignerApprovalFlowState
from src.designer.models.designer_intent import DesignerIntent
from src.designer.models.designer_session_state_card import DesignerSessionStateCard
from src.designer.models.validation_precheck import ValidationPrecheck
from src.storage.models.commit_snapshot_model import CommitSnapshotModel
from src.storage.models.execution_record_model import ExecutionRecordModel
from src.storage.models.loaded_nex_artifact import LoadedNexArtifact
from src.storage.models.working_save_model import WorkingSaveModel
from src.ui.builder_end_user_flow_hub import BuilderEndUserFlowHubViewModel, read_builder_end_user_flow_hub_view_model
from src.ui.builder_workflow_hub import BuilderWorkflowHubViewModel, read_builder_workflow_hub_view_model
from src.ui.i18n import ui_language_from_sources, ui_text
from src.ui.product_flow_closure import ProductFlowClosureStageView, ProductFlowClosureViewModel, read_product_flow_closure_view_model
from src.ui.product_flow_e2e_path import ProductFlowE2ECheckpointView, ProductFlowE2EPathViewModel, read_product_flow_e2e_path_view_model
from src.ui.product_flow_handoff import ProductFlowHandoffViewModel, read_product_flow_handoff_view_model
from src.ui.product_flow_readiness import ProductFlowReadinessViewModel, read_product_flow_readiness_view_model
from src.ui.product_flow_runbook import ProductFlowRunbookEntryView, ProductFlowRunbookViewModel, read_product_flow_runbook_view_model


@dataclass(frozen=True)
class ProductFlowTransitionView:
    transition_id: str
    label: str
    transition_status: str
    transition_status_label: str
    from_stage_id: str
    to_stage_id: str
    crossed: bool = False
    crossable: bool = False
    live: bool = False
    required_action_id: str | None = None
    required_action_label: str | None = None
    recommended_flow_id: str | None = None
    workspace_id: str | None = None
    panel_id: str | None = None
    target_ref: str | None = None
    open_requirement_id: str | None = None
    open_requirement_label: str | None = None


@dataclass(frozen=True)
class ProductFlowTransitionViewModel:
    transition_status: str = "empty"
    transition_status_label: str | None = None
    source_role: str = "none"
    current_transition_id: str | None = None
    recommended_transition_id: str | None = None
    live_transition_id: str | None = None
    next_action_id: str | None = None
    next_action_label: str | None = None
    terminal_transition_ready: bool = False
    crossed_transition_count: int = 0
    crossable_transition_count: int = 0
    blocked_transition_count: int = 0
    transitions: list[ProductFlowTransitionView] = field(default_factory=list)
    explanation: str | None = None


SourceLike = WorkingSaveModel | CommitSnapshotModel | ExecutionRecordModel | LoadedNexArtifact | None
_TRANSITIONS: tuple[tuple[str, str, str], ...] = (
    ("review_to_approval", "review", "approval"),
    ("approval_to_commit", "approval", "commit"),
    ("commit_to_run", "commit", "run"),
    ("run_to_followthrough", "run", "followthrough"),
)
_CHECKPOINT_BY_STAGE = {
    "review": "review",
    "approval": "approval",
    "commit": "commit",
    "run": "run",
}
_RUNBOOK_BY_STAGE = {
    "review": "review_proposal",
    "approval": "approval_decision",
    "commit": "commit_snapshot",
    "run": "run_current",
}
_FOLLOWTHROUGH_CHECKPOINTS = ("trace", "artifact", "diff")


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


def _closure_map(closure: ProductFlowClosureViewModel | None) -> dict[str, ProductFlowClosureStageView]:
    if closure is None:
        return {}
    return {item.stage_id: item for item in closure.stages}


def _checkpoint_map(e2e_path: ProductFlowE2EPathViewModel | None) -> dict[str, ProductFlowE2ECheckpointView]:
    if e2e_path is None:
        return {}
    return {item.checkpoint_id: item for item in e2e_path.checkpoints}


def _runbook_map(runbook: ProductFlowRunbookViewModel | None) -> dict[str, ProductFlowRunbookEntryView]:
    if runbook is None:
        return {}
    return {item.entry_id: item for item in runbook.entries}


def _label(key: str, *, app_language: str, fallback: str) -> str:
    return ui_text(key, app_language=app_language, fallback_text=fallback)


def _action_label(action_id: str | None, *, app_language: str) -> str | None:
    if action_id is None:
        return None
    return ui_text(f"builder.action.{action_id}", app_language=app_language, fallback_text=action_id.replace("_", " ").title())


def _followthrough_checkpoint(checkpoint_map: dict[str, ProductFlowE2ECheckpointView]) -> ProductFlowE2ECheckpointView | None:
    complete = next((checkpoint_map[item] for item in _FOLLOWTHROUGH_CHECKPOINTS if item in checkpoint_map and checkpoint_map[item].complete), None)
    if complete is not None:
        return complete
    actionable = next((checkpoint_map[item] for item in _FOLLOWTHROUGH_CHECKPOINTS if item in checkpoint_map and checkpoint_map[item].actionable), None)
    if actionable is not None:
        return actionable
    blocked = next((checkpoint_map[item] for item in _FOLLOWTHROUGH_CHECKPOINTS if item in checkpoint_map and checkpoint_map[item].checkpoint_status == "blocked"), None)
    if blocked is not None:
        return blocked
    return next((checkpoint_map[item] for item in _FOLLOWTHROUGH_CHECKPOINTS if item in checkpoint_map), None)


def _build_transition(
    transition_id: str,
    from_stage_id: str,
    to_stage_id: str,
    *,
    closure_map: dict[str, ProductFlowClosureStageView],
    checkpoint_map: dict[str, ProductFlowE2ECheckpointView],
    runbook_map: dict[str, ProductFlowRunbookEntryView],
    handoff: ProductFlowHandoffViewModel | None,
    app_language: str,
) -> ProductFlowTransitionView:
    from_stage = closure_map.get(from_stage_id)
    to_stage = closure_map.get(to_stage_id)
    checkpoint = _followthrough_checkpoint(checkpoint_map) if to_stage_id == "followthrough" else checkpoint_map.get(_CHECKPOINT_BY_STAGE.get(to_stage_id, ""))
    runbook_entry = runbook_map.get(_RUNBOOK_BY_STAGE.get(to_stage_id, ""))

    crossed = bool(to_stage is not None and to_stage.closed)
    live = bool(to_stage_id == "run" and checkpoint is not None and checkpoint.checkpoint_status == "active")
    blocked = bool(to_stage is not None and to_stage.stage_status == "blocked")
    crossable = bool(not crossed and not live and not blocked and to_stage is not None and to_stage.closeable and (from_stage is None or from_stage.closed))

    if crossed:
        transition_status = "crossed"
    elif live:
        transition_status = "live"
    elif blocked:
        transition_status = "blocked"
    elif crossable:
        transition_status = "crossable"
    else:
        transition_status = "waiting"

    required_action_id = None
    recommended_flow_id = None
    workspace_id = None
    panel_id = None
    target_ref = None
    open_requirement_id = None

    if to_stage_id == "followthrough" and handoff is not None:
        followthrough_action_map = {
            "inspect_trace": "open_diff",
            "inspect_artifacts": "open_diff",
            "compare_results": "open_diff",
        }
        followthrough_flow_map = {
            "inspect_trace": "flow:open_diff",
            "inspect_artifacts": "flow:open_diff",
            "compare_results": "flow:open_diff",
        }
        required_action_id = followthrough_action_map.get(handoff.followthrough_entry_id) or handoff.primary_action_id
        recommended_flow_id = followthrough_flow_map.get(handoff.followthrough_entry_id)
        workspace_id = handoff.followthrough_workspace_id or handoff.primary_workspace_id
        panel_id = handoff.followthrough_panel_id or handoff.primary_panel_id
        target_ref = handoff.followthrough_target_ref or handoff.primary_target_ref
    if required_action_id is None and checkpoint is not None:
        required_action_id = checkpoint.action_id
        workspace_id = workspace_id or checkpoint.workspace_id
        panel_id = panel_id or checkpoint.panel_id
        target_ref = target_ref or checkpoint.target_ref
    if required_action_id is None and runbook_entry is not None:
        required_action_id = runbook_entry.action_id
        recommended_flow_id = recommended_flow_id or (f"flow:{runbook_entry.action_id}" if runbook_entry.action_id is not None else None)
        workspace_id = workspace_id or runbook_entry.preferred_workspace_id
        panel_id = panel_id or runbook_entry.preferred_panel_id
        target_ref = target_ref or runbook_entry.target_ref
    if required_action_id is None and to_stage is not None:
        required_action_id = to_stage.required_action_id
        recommended_flow_id = recommended_flow_id or to_stage.recommended_flow_id
        workspace_id = workspace_id or to_stage.workspace_id
        panel_id = panel_id or to_stage.panel_id
        target_ref = target_ref or to_stage.target_ref
    if recommended_flow_id is None and to_stage is not None:
        recommended_flow_id = to_stage.recommended_flow_id

    if transition_status in {"waiting", "blocked"}:
        open_requirement_id = (to_stage.open_requirement if to_stage is not None else None) or required_action_id

    return ProductFlowTransitionView(
        transition_id=transition_id,
        label=_label(f"transition.flow.{transition_id}", app_language=app_language, fallback=transition_id.replace("_", " ").title()),
        transition_status=transition_status,
        transition_status_label=_label(f"transition.flow_status.{transition_status}", app_language=app_language, fallback=transition_status.replace("_", " ").title()),
        from_stage_id=from_stage_id,
        to_stage_id=to_stage_id,
        crossed=crossed,
        crossable=crossable,
        live=live,
        required_action_id=required_action_id,
        required_action_label=_action_label(required_action_id, app_language=app_language),
        recommended_flow_id=recommended_flow_id,
        workspace_id=workspace_id,
        panel_id=panel_id,
        target_ref=target_ref,
        open_requirement_id=open_requirement_id if not crossable and not crossed and not live else None,
        open_requirement_label=_action_label(open_requirement_id, app_language=app_language) if open_requirement_id is not None and not crossable and not crossed and not live else None,
    )


def read_product_flow_transition_view_model(
    source: SourceLike,
    *,
    validation_report: ValidationReport | None = None,
    execution_record: ExecutionRecordModel | None = None,
    session_state_card: DesignerSessionStateCard | None = None,
    intent: DesignerIntent | None = None,
    patch_plan: CircuitPatchPlan | None = None,
    precheck: ValidationPrecheck | None = None,
    preview: CircuitDraftPreview | None = None,
    approval_flow: DesignerApprovalFlowState | None = None,
    workflow_hub: BuilderWorkflowHubViewModel | None = None,
    runbook: ProductFlowRunbookViewModel | None = None,
    handoff: ProductFlowHandoffViewModel | None = None,
    readiness: ProductFlowReadinessViewModel | None = None,
    e2e_path: ProductFlowE2EPathViewModel | None = None,
    closure: ProductFlowClosureViewModel | None = None,
    end_user_flow_hub: BuilderEndUserFlowHubViewModel | None = None,
    explanation: str | None = None,
) -> ProductFlowTransitionViewModel:
    source_unwrapped = _unwrap(source)
    source_role = _storage_role(source_unwrapped)
    app_language = ui_language_from_sources(source_unwrapped, execution_record)

    if source_unwrapped is None and execution_record is None:
        return ProductFlowTransitionViewModel()

    base_source = source_unwrapped if source_unwrapped is not None else execution_record
    workflow_hub = workflow_hub or read_builder_workflow_hub_view_model(
        base_source,
        validation_report=validation_report,
        execution_record=execution_record,
        session_state_card=session_state_card,
        intent=intent,
        patch_plan=patch_plan,
        precheck=precheck,
        preview=preview,
        approval_flow=approval_flow,
    )
    runbook = runbook or read_product_flow_runbook_view_model(
        base_source,
        validation_report=validation_report,
        execution_record=execution_record,
        session_state_card=session_state_card,
        intent=intent,
        patch_plan=patch_plan,
        precheck=precheck,
        preview=preview,
        approval_flow=approval_flow,
        workflow_hub=workflow_hub,
    )
    handoff = handoff or read_product_flow_handoff_view_model(
        base_source,
        validation_report=validation_report,
        execution_record=execution_record,
        session_state_card=session_state_card,
        intent=intent,
        patch_plan=patch_plan,
        precheck=precheck,
        preview=preview,
        approval_flow=approval_flow,
        workflow_hub=workflow_hub,
        runbook=runbook,
    )
    end_user_flow_hub = end_user_flow_hub or read_builder_end_user_flow_hub_view_model(base_source)
    readiness = readiness or read_product_flow_readiness_view_model(
        base_source,
        validation_report=validation_report,
        execution_record=execution_record,
        session_state_card=session_state_card,
        intent=intent,
        patch_plan=patch_plan,
        precheck=precheck,
        preview=preview,
        approval_flow=approval_flow,
        workflow_hub=workflow_hub,
        runbook=runbook,
        handoff=handoff,
        end_user_flow_hub=end_user_flow_hub,
    )
    e2e_path = e2e_path or read_product_flow_e2e_path_view_model(
        base_source,
        validation_report=validation_report,
        execution_record=execution_record,
        session_state_card=session_state_card,
        intent=intent,
        patch_plan=patch_plan,
        precheck=precheck,
        preview=preview,
        approval_flow=approval_flow,
        workflow_hub=workflow_hub,
        runbook=runbook,
        handoff=handoff,
        readiness=readiness,
        end_user_flow_hub=end_user_flow_hub,
    )
    closure = closure or read_product_flow_closure_view_model(
        base_source,
        validation_report=validation_report,
        execution_record=execution_record,
        session_state_card=session_state_card,
        intent=intent,
        patch_plan=patch_plan,
        precheck=precheck,
        preview=preview,
        approval_flow=approval_flow,
        workflow_hub=workflow_hub,
        runbook=runbook,
        handoff=handoff,
        readiness=readiness,
        e2e_path=e2e_path,
        end_user_flow_hub=end_user_flow_hub,
    )

    closure_map = _closure_map(closure)
    checkpoint_map = _checkpoint_map(e2e_path)
    runbook_map = _runbook_map(runbook)
    transitions = [
        _build_transition(
            transition_id,
            from_stage_id,
            to_stage_id,
            closure_map=closure_map,
            checkpoint_map=checkpoint_map,
            runbook_map=runbook_map,
            handoff=handoff,
            app_language=app_language,
        )
        for transition_id, from_stage_id, to_stage_id in _TRANSITIONS
    ]

    active_review_chain = source_role == "working_save" and any(item is not None for item in (session_state_card, intent, patch_plan, precheck, preview, approval_flow))
    if active_review_chain:
        transition_by_id = {item.transition_id: item for item in transitions}
        commit_stage = closure_map.get("commit")
        run_stage = closure_map.get("run")
        follow_stage = closure_map.get("followthrough")
        patched: list[ProductFlowTransitionView] = []
        for item in transitions:
            if item.transition_id == "approval_to_commit" and commit_stage is not None:
                if commit_stage.stage_status == "blocked":
                    item = replace(item, transition_status="blocked", transition_status_label=_label("transition.flow_status.blocked", app_language=app_language, fallback="Blocked"), crossed=False, crossable=False, live=False, open_requirement_id=(commit_stage.open_requirement or item.required_action_id), open_requirement_label=_action_label(commit_stage.open_requirement or item.required_action_id, app_language=app_language))
                else:
                    item = replace(item, transition_status="crossable", transition_status_label=_label("transition.flow_status.crossable", app_language=app_language, fallback="Crossable"), crossed=False, crossable=True, live=False, open_requirement_id=None, open_requirement_label=None)
            elif item.transition_id == "commit_to_run" and run_stage is not None:
                if run_stage.stage_status == "blocked":
                    item = replace(item, transition_status="blocked", transition_status_label=_label("transition.flow_status.blocked", app_language=app_language, fallback="Blocked"), crossed=False, crossable=False, live=False, open_requirement_id=(run_stage.open_requirement or item.required_action_id), open_requirement_label=_action_label(run_stage.open_requirement or item.required_action_id, app_language=app_language))
                else:
                    item = replace(item, transition_status="waiting", transition_status_label=_label("transition.flow_status.waiting", app_language=app_language, fallback="Waiting"), crossed=False, crossable=False, live=False, open_requirement_id=(item.required_action_id), open_requirement_label=_action_label(item.required_action_id, app_language=app_language))
            elif item.transition_id == "run_to_followthrough" and follow_stage is not None:
                item = replace(item, transition_status="waiting", transition_status_label=_label("transition.flow_status.waiting", app_language=app_language, fallback="Waiting"), crossed=False, crossable=False, live=False, open_requirement_id=(item.required_action_id), open_requirement_label=_action_label(item.required_action_id, app_language=app_language))
            patched.append(item)
        transitions = patched

    crossed_transition_count = sum(1 for item in transitions if item.crossed)
    crossable_transition_count = sum(1 for item in transitions if item.crossable)
    blocked_transition_count = sum(1 for item in transitions if item.transition_status == "blocked")
    live_transition = next((item for item in transitions if item.live), None)
    transition_by_id = {item.transition_id: item for item in transitions}

    recommended_transition = None
    if live_transition is not None:
        recommended_transition = live_transition
    elif source_role == "working_save" and transition_by_id.get("approval_to_commit") is not None and not transition_by_id["approval_to_commit"].crossed and (transition_by_id["approval_to_commit"].transition_status in {"crossable", "blocked"} or (closure is not None and closure.current_stage_id == "commit")):
        recommended_transition = transition_by_id["approval_to_commit"]
    elif source_role == "working_save" and transition_by_id.get("commit_to_run") is not None and transition_by_id["commit_to_run"].transition_status in {"crossable", "blocked", "live"}:
        recommended_transition = transition_by_id["commit_to_run"]
    elif execution_record is not None and transition_by_id.get("run_to_followthrough") is not None and transition_by_id["run_to_followthrough"].transition_status in {"crossable", "crossed", "live"}:
        recommended_transition = transition_by_id["run_to_followthrough"]
    else:
        recommended_transition = next((item for item in transitions if item.crossable), None) or next((item for item in transitions if item.transition_status == "blocked"), None) or next((item for item in transitions if not item.crossed), None)

    current_transition = recommended_transition or next((item for item in transitions if not item.crossed), None)
    terminal_transition_ready = all(item.crossed for item in transitions)

    if not transitions:
        overall_status = "empty"
    elif live_transition is not None:
        overall_status = "live"
    elif recommended_transition is not None and recommended_transition.transition_status == "blocked":
        overall_status = "blocked"
    elif terminal_transition_ready and recommended_transition is None:
        overall_status = "terminal"
    elif terminal_transition_ready and recommended_transition is not None:
        overall_status = "terminal"
    elif recommended_transition is not None and recommended_transition.transition_status in {"crossable", "crossed"}:
        overall_status = "actionable"
    elif crossable_transition_count:
        overall_status = "actionable"
    elif blocked_transition_count:
        overall_status = "blocked"
    else:
        overall_status = "ready"

    next_action_id = recommended_transition.required_action_id if recommended_transition is not None else None
    return ProductFlowTransitionViewModel(
        transition_status=overall_status,
        transition_status_label=_label(f"transition.flow_status_group.{overall_status}", app_language=app_language, fallback=overall_status.replace("_", " ").title()),
        source_role=source_role,
        current_transition_id=current_transition.transition_id if current_transition is not None else None,
        recommended_transition_id=recommended_transition.transition_id if recommended_transition is not None else None,
        live_transition_id=live_transition.transition_id if live_transition is not None else None,
        next_action_id=next_action_id,
        next_action_label=_action_label(next_action_id, app_language=app_language),
        terminal_transition_ready=terminal_transition_ready,
        crossed_transition_count=crossed_transition_count,
        crossable_transition_count=crossable_transition_count,
        blocked_transition_count=blocked_transition_count,
        transitions=transitions,
        explanation=explanation,
    )


__all__ = [
    "ProductFlowTransitionView",
    "ProductFlowTransitionViewModel",
    "read_product_flow_transition_view_model",
]
