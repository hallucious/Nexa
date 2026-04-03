from __future__ import annotations

from src.designer.approval_flow import DesignerApprovalCoordinator
from src.designer.commit_gateway import DesignerCommitGateway
from src.designer.models.circuit_patch_plan import (
    ChangeScope,
    CircuitPatchPlan,
    PatchOperation,
    ReversibilitySpec,
)
from src.designer.patch_applier import DesignerPatchApplier
from src.designer.proposal_flow import DesignerProposalFlow
from src.designer.models.designer_approval_flow import UserDecision
from src.storage.models.shared_sections import CircuitModel, ResourcesModel, StateModel
from src.storage.models.working_save_model import RuntimeModel, UIModel, WorkingSaveMeta, WorkingSaveModel


def make_base_working_save(*, working_save_id: str = "ws-100") -> WorkingSaveModel:
    return WorkingSaveModel(
        meta=WorkingSaveMeta(
            format_version="1.0.0",
            storage_role="working_save",
            name="Designer Base",
            working_save_id=working_save_id,
        ),
        circuit=CircuitModel(
            nodes=[
                {
                    "id": "node.start",
                    "type": "ai",
                    "resource_ref": {"prompt": "prompt.start", "provider": "openai:gpt"},
                },
                {
                    "id": "judge",
                    "type": "ai",
                    "resource_ref": {"prompt": "prompt.judge", "provider": "openai:gpt"},
                },
            ],
            edges=[{"from": "node.start", "to": "judge"}],
            entry="node.start",
            outputs=[{"name": "final_answer", "source": "judge.output"}],
        ),
        resources=ResourcesModel(
            prompts={"prompt.start": {}, "prompt.judge": {}},
            providers={"openai:gpt": {}, "anthropic:claude": {}},
            plugins={"web.search": {}, "tool.generic": {}},
        ),
        state=StateModel(input={"question": "What is AI?"}, working={}, memory={}),
        runtime=RuntimeModel(status="validated", validation_summary={"blocking_count": 0}),
        ui=UIModel(layout={}, metadata={}),
    )


def test_patch_applier_builds_review_gate_candidate_from_bundle() -> None:
    flow = DesignerProposalFlow()
    bundle = flow.propose("Add a review node before final output in node judge", working_save_ref="ws-100")
    applier = DesignerPatchApplier()

    result = applier.apply_bundle(make_base_working_save(), bundle)

    candidate = result.candidate_working_save
    node_ids = [node["id"] for node in candidate.circuit.nodes]
    assert "judge__review_gate" in node_ids
    assert {"from": "judge", "to": "judge__review_gate"} in candidate.circuit.edges
    assert candidate.circuit.outputs[0]["source"] == "judge__review_gate.output"
    assert candidate.runtime.status == "ready_for_review"
    assert candidate.designer is not None
    assert candidate.designer.data["last_applied_patch_ref"] == bundle.patch.patch_id


def test_patch_applier_updates_provider_reference_for_replace_provider_patch() -> None:
    flow = DesignerProposalFlow()
    bundle = flow.propose("Change provider in node judge to Claude", working_save_ref="ws-100")
    applier = DesignerPatchApplier()

    result = applier.apply_bundle(make_base_working_save(), bundle)

    judge = next(node for node in result.candidate_working_save.circuit.nodes if node["id"] == "judge")
    assert judge["resource_ref"]["provider"] == "anthropic:claude"
    assert judge["execution"]["provider"]["provider_id"] == "anthropic:claude"


def test_patch_applier_renames_node_and_rewrites_edges_outputs_and_entry() -> None:
    patch = CircuitPatchPlan(
        patch_id="patch-rename",
        patch_mode="modify_existing",
        summary="Rename judge to reviewer.",
        intent_ref="intent-rename",
        change_scope=ChangeScope(
            scope_level="minimal",
            touch_mode="structural_edit",
            touched_nodes=("judge",),
        ),
        operations=(
            PatchOperation(
                op_id="op-1",
                op_type="rename_node",
                target_ref="judge",
                payload={"new_name": "reviewer"},
                rationale="Make the node role clearer.",
            ),
        ),
        reversibility=ReversibilitySpec(reversible=True),
    )
    applier = DesignerPatchApplier()
    base = make_base_working_save()

    result = applier.apply_patch(base, patch)

    node_ids = [node["id"] for node in result.candidate_working_save.circuit.nodes]
    assert "reviewer" in node_ids
    assert "judge" not in node_ids
    assert result.candidate_working_save.circuit.edges == [{"from": "node.start", "to": "reviewer"}]
    assert result.candidate_working_save.circuit.outputs[0]["source"] == "reviewer.output"


def test_patch_applier_closes_designer_path_through_commit_gateway() -> None:
    flow = DesignerProposalFlow()
    bundle = flow.propose("Add a review node before final output in node judge", working_save_ref="ws-100")
    coordinator = DesignerApprovalCoordinator()
    state = coordinator.create_state(bundle)
    approved = coordinator.resolve(
        state,
        tuple(UserDecision(decision_point_id=point.decision_id, outcome="approve") for point in state.required_decision_points),
    )
    applier = DesignerPatchApplier()
    application = applier.apply_bundle(make_base_working_save(), bundle)
    gateway = DesignerCommitGateway(coordinator=coordinator)

    commit_result = gateway.commit_candidate(application.candidate_working_save, approved, commit_id="commit-designer-1")

    committed_node_ids = [node["id"] for node in commit_result.commit_snapshot.circuit.nodes]
    assert "judge__review_gate" in committed_node_ids
    assert commit_result.approval_state.current_stage == "committed"
    assert commit_result.commit_snapshot.meta.commit_id == "commit-designer-1"
