from __future__ import annotations

from dataclasses import dataclass, field

from src.designer.models.circuit_draft_preview import CircuitDraftPreview
from src.designer.models.circuit_patch_plan import CircuitPatchPlan
from src.designer.models.designer_approval_flow import DesignerApprovalFlowState
from src.designer.models.designer_intent import DesignerIntent
from src.designer.models.designer_session_state_card import DesignerSessionStateCard
from src.designer.models.validation_precheck import ValidationPrecheck
from src.storage.models.loaded_nex_artifact import LoadedNexArtifact
from src.storage.models.commit_snapshot_model import CommitSnapshotModel
from src.storage.models.execution_record_model import ExecutionRecordModel
from src.storage.models.working_save_model import WorkingSaveModel
from src.ui.i18n import ui_language_from_sources, ui_text
from src.ui.template_gallery import TemplateGalleryViewModel, read_template_gallery_view_model


@dataclass(frozen=True)
class DesignerRequestStateView:
    current_request_text: str | None = None
    request_status: str = "unknown"
    last_submitted_at: str | None = None
    input_placeholder: str | None = None
    can_submit: bool = False
    submit_reason_disabled: str | None = None


@dataclass(frozen=True)
class DesignerIntentStateView:
    intent_id: str | None = None
    category: str | None = None
    target_scope_summary: str | None = None
    objective_summary: str | None = None
    constraints_summary: str | None = None
    assumption_count: int = 0
    ambiguity_count: int = 0
    risk_flag_count: int = 0
    confidence: float | None = None
    explanation: str | None = None


@dataclass(frozen=True)
class DesignerPatchStateView:
    patch_id: str | None = None
    patch_mode: str | None = None
    summary: str | None = None
    operation_count: int = 0
    scope_level: str | None = None
    touch_mode: str | None = None
    touched_node_count: int = 0
    touched_edge_count: int = 0
    touched_output_count: int = 0
    destructive_change_present: bool = False
    reversibility_summary: str | None = None


@dataclass(frozen=True)
class DesignerPrecheckStateView:
    precheck_id: str | None = None
    overall_status: str = "unknown"
    blocking_count: int = 0
    warning_count: int = 0
    confirmation_count: int = 0
    top_issue_label: str | None = None
    can_proceed_to_preview: bool = False
    can_proceed_to_approval: bool = False
    recommended_next_step: str | None = None


@dataclass(frozen=True)
class DesignerPreviewStateView:
    preview_id: str | None = None
    preview_status: str = "unknown"
    one_sentence_summary: str | None = None
    proposal_type: str | None = None
    change_scope: str | None = None
    touched_node_count: int = 0
    touched_edge_count: int = 0
    touched_output_count: int = 0
    requires_confirmation: bool = False
    auto_commit_allowed: bool = False


@dataclass(frozen=True)
class DesignerApprovalStateView:
    approval_id: str | None = None
    approval_status: str = "not_started"
    current_stage: str | None = None
    final_outcome: str | None = None
    decision_count: int = 0
    unanswered_decision_count: int = 0
    commit_eligible: bool = False
    auto_commit_allowed: bool = False


@dataclass(frozen=True)
class DesignerRevisionStateView:
    revision_index: int = 0
    retry_reason: str | None = None
    prior_rejection_count: int = 0
    user_correction_count: int = 0
    last_control_action: str | None = None
    last_terminal_status: str | None = None
    attempt_count: int = 0


@dataclass(frozen=True)
class DesignerActionHint:
    action_type: str
    label: str
    enabled: bool
    reason_disabled: str | None = None


@dataclass(frozen=True)
class DesignerTargetRefView:
    target_ref: str
    target_type: str
    label: str


@dataclass(frozen=True)
class DesignerPanelViewModel:
    session_mode: str
    storage_role: str
    request_state: DesignerRequestStateView = field(default_factory=DesignerRequestStateView)
    intent_state: DesignerIntentStateView = field(default_factory=DesignerIntentStateView)
    patch_state: DesignerPatchStateView = field(default_factory=DesignerPatchStateView)
    precheck_state: DesignerPrecheckStateView = field(default_factory=DesignerPrecheckStateView)
    preview_state: DesignerPreviewStateView = field(default_factory=DesignerPreviewStateView)
    approval_state: DesignerApprovalStateView = field(default_factory=DesignerApprovalStateView)
    revision_state: DesignerRevisionStateView = field(default_factory=DesignerRevisionStateView)
    suggested_actions: list[DesignerActionHint] = field(default_factory=list)
    related_targets: list[DesignerTargetRefView] = field(default_factory=list)
    template_gallery: TemplateGalleryViewModel = field(default_factory=TemplateGalleryViewModel)
    explanation: str | None = None


def _storage_role(source) -> str:
    if source is None:
        return "none"
    if isinstance(source, WorkingSaveModel):
        return "working_save"
    if isinstance(source, CommitSnapshotModel):
        return "commit_snapshot"
    if isinstance(source, ExecutionRecordModel):
        return "execution_record"
    if isinstance(source, LoadedNexArtifact):
        return _storage_role(source.parsed_model)
    return "none"


def _working_save_metadata(source) -> dict[str, object]:
    if isinstance(source, WorkingSaveModel):
        return dict(source.ui.metadata or {})
    if isinstance(source, LoadedNexArtifact):
        return _working_save_metadata(source.parsed_model)
    return {}


def _is_beginner_empty_workspace(source) -> bool:
    if not isinstance(source, WorkingSaveModel):
        return False
    metadata = _working_save_metadata(source)
    if bool(metadata.get("advanced_mode_requested")) or str(metadata.get("user_mode") or "").lower() == "advanced":
        return False
    if bool(metadata.get("beginner_first_success_achieved")):
        return False
    return not source.circuit.nodes and not source.circuit.edges


def _session_mode_from_card(card: DesignerSessionStateCard | None) -> str:
    if card is None:
        return "idle"
    mapping = {
        "new_circuit": "create_circuit",
        "existing_circuit": "modify_circuit",
        "subgraph_only": "modify_circuit",
        "node_only": "modify_circuit",
        "read_only": "analyze_circuit",
    }
    return mapping.get(card.target_scope.mode, "unknown")


def read_designer_panel_view_model(
    source: WorkingSaveModel | CommitSnapshotModel | ExecutionRecordModel | LoadedNexArtifact | None,
    *,
    session_state_card: DesignerSessionStateCard | None = None,
    intent: DesignerIntent | None = None,
    patch_plan: CircuitPatchPlan | None = None,
    precheck: ValidationPrecheck | None = None,
    preview: CircuitDraftPreview | None = None,
    approval_flow: DesignerApprovalFlowState | None = None,
    explanation: str | None = None,
) -> DesignerPanelViewModel:
    storage_role = _storage_role(source)
    session_mode = _session_mode_from_card(session_state_card)

    app_language = ui_language_from_sources(source)

    placeholder_key = "designer.request.input_placeholder.beginner" if _is_beginner_empty_workspace(source) else "designer.request.input_placeholder"
    template_gallery_vm = read_template_gallery_view_model(source)

    request_state = DesignerRequestStateView(
        current_request_text=session_state_card.conversation_context.user_request_text if session_state_card is not None else None,
        request_status=("submitted" if session_state_card is not None else "empty"),
        input_placeholder=ui_text(placeholder_key, app_language=app_language),
        can_submit=storage_role in {"working_save", "none"},
        submit_reason_disabled=None if storage_role in {"working_save", "none"} else ui_text("designer.request.read_only_disabled", app_language=app_language),
    )
    intent_state = DesignerIntentStateView(
        intent_id=intent.intent_id if intent is not None else None,
        category=intent.category if intent is not None else None,
        target_scope_summary=(f"{intent.target_scope.mode} / {intent.target_scope.max_change_scope}" if intent is not None else None),
        objective_summary=(intent.objective.primary_goal if intent is not None else None),
        constraints_summary=("; ".join(filter(None, [intent.constraints.output_requirements, intent.constraints.safety_level])) if intent is not None else None),
        assumption_count=len(intent.assumptions) if intent is not None else 0,
        ambiguity_count=len(intent.ambiguity_flags) if intent is not None else 0,
        risk_flag_count=len(intent.risk_flags) if intent is not None else 0,
        confidence=intent.confidence if intent is not None else None,
        explanation=intent.explanation if intent is not None else None,
    )
    patch_state = DesignerPatchStateView(
        patch_id=patch_plan.patch_id if patch_plan is not None else None,
        patch_mode=patch_plan.patch_mode if patch_plan is not None else None,
        summary=patch_plan.summary if patch_plan is not None else None,
        operation_count=len(patch_plan.operations) if patch_plan is not None else 0,
        scope_level=patch_plan.change_scope.scope_level if patch_plan is not None else None,
        touch_mode=patch_plan.change_scope.touch_mode if patch_plan is not None else None,
        touched_node_count=len(patch_plan.change_scope.touched_nodes) if patch_plan is not None else 0,
        touched_edge_count=len(patch_plan.change_scope.touched_edges) if patch_plan is not None else 0,
        touched_output_count=len(patch_plan.change_scope.touched_outputs) if patch_plan is not None else 0,
        destructive_change_present=(patch_plan.reversibility.destructive_ops_present if patch_plan is not None else False),
        reversibility_summary=((patch_plan.reversibility.rollback_strategy or ("reversible" if patch_plan.reversibility.reversible else None)) if patch_plan is not None else None),
    )
    precheck_state = DesignerPrecheckStateView(
        precheck_id=precheck.precheck_id if precheck is not None else None,
        overall_status=("not_run" if precheck is None else precheck.overall_status),
        blocking_count=(len(precheck.blocking_findings) if precheck is not None else 0),
        warning_count=(len(precheck.warning_findings) if precheck is not None else 0),
        confirmation_count=(len(precheck.confirmation_findings) if precheck is not None else 0),
        top_issue_label=((precheck.blocking_findings or precheck.warning_findings or precheck.confirmation_findings)[0].message if precheck and (precheck.blocking_findings or precheck.warning_findings or precheck.confirmation_findings) else None),
        can_proceed_to_preview=(precheck.can_proceed_to_preview if precheck is not None else False),
        can_proceed_to_approval=(precheck.overall_status in {"pass", "pass_with_warnings", "confirmation_required"} if precheck is not None else False),
        recommended_next_step=(precheck.recommended_next_actions[0] if precheck and precheck.recommended_next_actions else None),
    )
    preview_state = DesignerPreviewStateView(
        preview_id=preview.preview_id if preview is not None else None,
        preview_status=("ready" if preview is not None else "not_ready"),
        one_sentence_summary=(preview.summary_card.one_sentence_summary if preview is not None else None),
        proposal_type=(preview.summary_card.proposal_type if preview is not None else None),
        change_scope=(preview.summary_card.change_scope if preview is not None else None),
        touched_node_count=(preview.summary_card.touched_node_count if preview is not None else 0),
        touched_edge_count=(preview.summary_card.touched_edge_count if preview is not None else 0),
        touched_output_count=(preview.summary_card.touched_output_count if preview is not None else 0),
        requires_confirmation=(preview.confirmation_preview.required_confirmations != () if preview is not None else False),
        auto_commit_allowed=(preview.confirmation_preview.auto_commit_allowed if preview is not None else False),
    )
    approval_state = DesignerApprovalStateView(
        approval_id=approval_flow.approval_id if approval_flow is not None else None,
        approval_status=(approval_flow.final_outcome if approval_flow is not None else "not_started"),
        current_stage=(approval_flow.current_stage if approval_flow is not None else None),
        final_outcome=(approval_flow.final_outcome if approval_flow is not None else None),
        decision_count=(len(approval_flow.user_decisions) if approval_flow is not None else 0),
        unanswered_decision_count=(len(approval_flow.unanswered_required_decision_points) if approval_flow is not None else 0),
        commit_eligible=(approval_flow.commit_eligible if approval_flow is not None else False),
        auto_commit_allowed=(approval_flow.auto_commit_allowed if approval_flow is not None else False),
    )
    revision_state = DesignerRevisionStateView(
        revision_index=(session_state_card.revision_state.revision_index if session_state_card is not None else 0),
        retry_reason=(session_state_card.revision_state.retry_reason if session_state_card is not None else None),
        prior_rejection_count=(len(session_state_card.revision_state.prior_rejection_reasons) if session_state_card is not None else 0),
        user_correction_count=(len(session_state_card.revision_state.user_corrections) if session_state_card is not None else 0),
        last_control_action=(session_state_card.revision_state.last_control_action if session_state_card is not None else None),
        last_terminal_status=(session_state_card.revision_state.last_terminal_status if session_state_card is not None else None),
        attempt_count=(len(session_state_card.revision_state.attempt_history) if session_state_card is not None else 0),
    )
    suggested_actions = [
        DesignerActionHint("submit_request", ui_text("designer.action.submit_request", app_language=app_language), request_state.can_submit, request_state.submit_reason_disabled),
        DesignerActionHint(
            "preview_patch",
            ui_text("designer.action.preview_patch", app_language=app_language),
            precheck_state.can_proceed_to_preview and patch_state.patch_id is not None,
            None if precheck_state.can_proceed_to_preview and patch_state.patch_id is not None else ui_text("designer.action.preview_patch_disabled", app_language=app_language),
        ),
        DesignerActionHint(
            "approve_for_commit",
            ui_text("designer.action.approve_for_commit", app_language=app_language),
            preview_state.preview_status == "ready" and precheck_state.overall_status in {"pass", "pass_with_warnings", "confirmation_required"},
            None if preview_state.preview_status == "ready" and precheck_state.overall_status in {"pass", "pass_with_warnings", "confirmation_required"} else ui_text("designer.action.approve_for_commit_disabled", app_language=app_language),
        ),
    ]
    related_targets: list[DesignerTargetRefView] = []
    if patch_plan is not None:
        related_targets.extend(DesignerTargetRefView(f"node:{node}", "node", node) for node in patch_plan.change_scope.touched_nodes)
        related_targets.extend(DesignerTargetRefView(f"edge:{edge}", "edge", edge) for edge in patch_plan.change_scope.touched_edges)
        related_targets.extend(DesignerTargetRefView(f"output:{output}", "output", output) for output in patch_plan.change_scope.touched_outputs)
    return DesignerPanelViewModel(
        session_mode=session_mode,
        storage_role=storage_role,
        request_state=request_state,
        intent_state=intent_state,
        patch_state=patch_state,
        precheck_state=precheck_state,
        preview_state=preview_state,
        approval_state=approval_state,
        revision_state=revision_state,
        suggested_actions=suggested_actions,
        related_targets=related_targets,
        template_gallery=template_gallery_vm,
        explanation=explanation,
    )


__all__ = [
    "DesignerActionHint",
    "DesignerApprovalStateView",
    "DesignerIntentStateView",
    "DesignerPanelViewModel",
    "DesignerPatchStateView",
    "DesignerPrecheckStateView",
    "DesignerPreviewStateView",
    "DesignerRequestStateView",
    "DesignerRevisionStateView",
    "DesignerTargetRefView",
    "read_designer_panel_view_model",
]
