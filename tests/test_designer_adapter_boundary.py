from __future__ import annotations

from src.designer.models.circuit_draft_preview import (
    CircuitDraftPreview,
    ConfirmationPreview,
    GraphViewModel,
    StructuralPreview,
    SummaryCard,
)
from src.designer.models.designer_approval_flow import DesignerApprovalFlowState
from src.designer.models.validation_precheck import (
    AmbiguityAssessmentReport,
    CostAssessmentReport,
    EvaluatedScope,
    PrecheckFinding,
    ResolutionReport,
    ValidityReport,
    ValidationPrecheck,
)
from src.storage.models.loaded_nex_artifact import LoadedNexArtifact
from src.storage.models.shared_sections import CircuitModel, ResourcesModel, StateModel
from src.storage.models.working_save_model import RuntimeModel, UIModel, WorkingSaveMeta, WorkingSaveModel
from src.ui.adapter import NexaUIViewAdapter


def _working_save() -> WorkingSaveModel:
    return WorkingSaveModel(
        meta=WorkingSaveMeta(format_version="1.0.0", storage_role="working_save", working_save_id="ws-designer-boundary", name="Designer boundary"),
        circuit=CircuitModel(nodes=[{"id": "review_node"}], edges=[], entry="review_node", outputs=[]),
        resources=ResourcesModel(prompts={}, providers={}, plugins={}),
        state=StateModel(input={}, working={}, memory={}),
        runtime=RuntimeModel(status="draft", validation_summary={}, last_run={}, errors=[]),
        ui=UIModel(layout={}, metadata={"app_language": "en"}),
    )


def _preview(*, requires_confirmation: bool = False) -> CircuitDraftPreview:
    confirmations = ("Confirm provider replacement",) if requires_confirmation else ()
    return CircuitDraftPreview(
        preview_id="preview-001",
        intent_ref="intent-001",
        patch_ref="patch-001",
        precheck_ref="precheck-001",
        preview_mode="patch_modify",
        summary_card=SummaryCard(
            title="Modify circuit proposal",
            one_sentence_summary="Update the current circuit proposal.",
            proposal_type="modify",
            change_scope="bounded",
            touched_node_count=1,
            touched_edge_count=0,
            touched_output_count=0,
        ),
        structural_preview=StructuralPreview(
            before_exists=True,
            before_node_count=1,
            after_node_count=1,
            before_edge_count=0,
            after_edge_count=0,
            modified_nodes=("review_node",),
        ),
        confirmation_preview=ConfirmationPreview(
            required_confirmations=confirmations,
            auto_commit_allowed=False,
        ),
        graph_view_model=GraphViewModel(node_count=1, edge_count=0),
    )


def _approval(*, final_outcome: str = "approved_for_commit", confirmation_resolved: bool = True) -> DesignerApprovalFlowState:
    return DesignerApprovalFlowState(
        approval_id="approval-001",
        intent_ref="intent-001",
        patch_ref="patch-001",
        precheck_ref="precheck-001",
        preview_ref="preview-001",
        current_stage="awaiting_decision",
        final_outcome=final_outcome,
        precheck_status="pass",
        confirmation_finding_count=1 if not confirmation_resolved else 0,
        confirmation_resolved=confirmation_resolved,
    )


def _precheck(*, overall_status: str = "confirmation_required") -> ValidationPrecheck:
    confirmation_findings = ()
    if overall_status == "confirmation_required":
        confirmation_findings = (
            PrecheckFinding(issue_code="DESIGNER_CONFIRMATION", message="Confirmation required."),
        )
    return ValidationPrecheck(
        precheck_id="precheck-001",
        patch_ref="patch-001",
        intent_ref="intent-001",
        evaluated_scope=EvaluatedScope(mode="existing_circuit_patch"),
        overall_status=overall_status,
        structural_validity=ValidityReport(status="valid"),
        dependency_validity=ValidityReport(status="valid"),
        input_output_validity=ValidityReport(status="valid"),
        provider_resolution=ResolutionReport(status="resolved"),
        plugin_resolution=ResolutionReport(status="resolved"),
        safety_review=ValidityReport(status="valid"),
        cost_assessment=CostAssessmentReport(status="acceptable"),
        ambiguity_assessment=AmbiguityAssessmentReport(status="clear"),
        confirmation_findings=confirmation_findings,
    )


def test_adapter_does_not_generate_preview(monkeypatch) -> None:
    adapter = NexaUIViewAdapter(latest_working_save=_working_save())

    def _forbidden_build(*args, **kwargs):
        raise AssertionError("Adapter must not generate preview content")

    monkeypatch.setattr("src.designer.preview_builder.DesignerPreviewBuilder.build", _forbidden_build)

    engine_preview = _preview()
    vm = adapter.read_designer_panel_view_model(
        _working_save(),
        preview=engine_preview,
        approval_flow=_approval(),
    )

    assert vm.preview_state.preview_id == engine_preview.preview_id
    assert vm.preview_state.one_sentence_summary == engine_preview.summary_card.one_sentence_summary


def test_adapter_exposes_engine_approval_decision_unchanged() -> None:
    adapter = NexaUIViewAdapter(latest_working_save=_working_save())
    engine_approval = _approval(final_outcome="approved_for_commit")

    vm = adapter.read_designer_panel_view_model(
        _working_save(),
        preview=_preview(),
        approval_flow=engine_approval,
    )

    assert engine_approval.commit_eligible is True
    assert vm.approval_state.commit_eligible == engine_approval.commit_eligible
    assert vm.approval_state.final_outcome == engine_approval.final_outcome


def test_adapter_exposes_engine_confirmation_requirements_unchanged() -> None:
    adapter = NexaUIViewAdapter(latest_working_save=_working_save())
    engine_preview = _preview(requires_confirmation=True)
    engine_precheck = _precheck(overall_status="confirmation_required")

    vm = adapter.read_designer_panel_view_model(
        LoadedNexArtifact(
            storage_role="working_save",
            raw_data={},
            parsed_model=_working_save(),
            findings=[],
            load_status="loaded",
        ),
        precheck=engine_precheck,
        preview=engine_preview,
        approval_flow=_approval(final_outcome="pending"),
    )

    assert vm.precheck_state.overall_status == engine_precheck.overall_status
    assert vm.preview_state.requires_confirmation is True
