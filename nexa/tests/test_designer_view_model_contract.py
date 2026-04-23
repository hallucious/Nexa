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


def _source() -> LoadedNexArtifact:
    working_save = WorkingSaveModel(
        meta=WorkingSaveMeta(format_version="1.0.0", storage_role="working_save", working_save_id="ws-designer-contract", name="Designer VM contract"),
        circuit=CircuitModel(nodes=[{"id": "node-a"}, {"id": "node-b"}], edges=[], entry="node-a", outputs=[]),
        resources=ResourcesModel(prompts={}, providers={}, plugins={}),
        state=StateModel(input={}, working={}, memory={}),
        runtime=RuntimeModel(status="draft", validation_summary={}, last_run={}, errors=[]),
        ui=UIModel(layout={}, metadata={"app_language": "ko"}),
    )
    return LoadedNexArtifact(
        storage_role="working_save",
        raw_data={},
        parsed_model=working_save,
        findings=[],
        load_status="loaded",
    )


def _preview() -> CircuitDraftPreview:
    return CircuitDraftPreview(
        preview_id="preview-abc123",
        intent_ref="intent-001",
        patch_ref="patch-001",
        precheck_ref="precheck-001",
        preview_mode="patch_modify",
        summary_card=SummaryCard(
            title="Modify proposal",
            one_sentence_summary="Engine generated preview.",
            proposal_type="modify",
            change_scope="bounded",
            touched_node_count=2,
            touched_edge_count=1,
            touched_output_count=0,
        ),
        structural_preview=StructuralPreview(
            before_exists=True,
            before_node_count=2,
            after_node_count=2,
            before_edge_count=1,
            after_edge_count=1,
            modified_nodes=("node-a", "node-b"),
        ),
        confirmation_preview=ConfirmationPreview(
            required_confirmations=("Resolve ambiguity before commit",),
            auto_commit_allowed=False,
        ),
        graph_view_model=GraphViewModel(node_count=2, edge_count=1),
    )


def _precheck() -> ValidationPrecheck:
    return ValidationPrecheck(
        precheck_id="precheck-001",
        patch_ref="patch-001",
        intent_ref="intent-001",
        evaluated_scope=EvaluatedScope(mode="existing_circuit_patch"),
        overall_status="confirmation_required",
        structural_validity=ValidityReport(status="valid"),
        dependency_validity=ValidityReport(status="valid"),
        input_output_validity=ValidityReport(status="valid"),
        provider_resolution=ResolutionReport(status="resolved"),
        plugin_resolution=ResolutionReport(status="resolved"),
        safety_review=ValidityReport(status="valid"),
        cost_assessment=CostAssessmentReport(status="acceptable"),
        ambiguity_assessment=AmbiguityAssessmentReport(status="clear"),
        confirmation_findings=(
            PrecheckFinding(issue_code="DESIGNER_CONFIRMATION", message="Resolve ambiguity before commit."),
        ),
    )


def _approval() -> DesignerApprovalFlowState:
    return DesignerApprovalFlowState(
        approval_id="approval-001",
        intent_ref="intent-001",
        patch_ref="patch-001",
        precheck_ref="precheck-001",
        preview_ref="preview-abc123",
        current_stage="awaiting_decision",
        final_outcome="pending",
        precheck_status="confirmation_required",
        confirmation_finding_count=1,
        confirmation_resolved=False,
    )


def test_adapter_produced_view_model_exposes_engine_generated_preview_identity() -> None:
    source = _source()
    adapter = NexaUIViewAdapter(latest_working_save=source.parsed_model)

    vm = adapter.read_designer_panel_view_model(
        source,
        preview=_preview(),
        precheck=_precheck(),
        approval_flow=_approval(),
    )

    assert vm.preview_state.preview_id == "preview-abc123"
    assert vm.preview_state.preview_status == "ready"


def test_adapter_produced_view_model_exposes_engine_precheck_status() -> None:
    source = _source()
    adapter = NexaUIViewAdapter(latest_working_save=source.parsed_model)

    vm = adapter.read_designer_panel_view_model(
        source,
        preview=_preview(),
        precheck=_precheck(),
        approval_flow=_approval(),
    )

    assert vm.precheck_state.overall_status == "confirmation_required"
    assert vm.precheck_state.confirmation_count == 1


def test_adapter_produced_view_model_exposes_engine_governance_state() -> None:
    source = _source()
    adapter = NexaUIViewAdapter(latest_working_save=source.parsed_model)

    vm = adapter.read_designer_panel_view_model(
        source,
        preview=_preview(),
        precheck=_precheck(),
        approval_flow=_approval(),
    )

    assert vm.preview_state.requires_confirmation is True
    assert vm.approval_state.commit_eligible is False
