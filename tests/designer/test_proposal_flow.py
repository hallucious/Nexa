from __future__ import annotations

from src.designer.proposal_flow import DesignerProposalFlow
from src.designer.request_normalizer import DesignerRequestNormalizer, RequestNormalizationContext
from src.designer.models.designer_session_state_card import (
    AvailableResources,
    ConversationContext,
    CurrentSelectionState,
    DesignerSessionStateCard,
    SessionTargetScope,
    WorkingSaveReality,
)
from src.designer.models.designer_intent import ConstraintSet, ObjectiveSpec


def test_request_normalizer_creates_new_circuit_intent() -> None:
    normalizer = DesignerRequestNormalizer()
    intent = normalizer.normalize("Create a document summarization workflow")
    assert intent.category == "CREATE_CIRCUIT"
    assert intent.target_scope.mode == "new_circuit"
    assert intent.proposed_actions


def test_proposal_flow_builds_non_committing_bundle_for_modify_request() -> None:
    flow = DesignerProposalFlow()
    bundle = flow.propose("Add a review node before final output in node judge", working_save_ref="ws-001")
    assert bundle.intent.category == "MODIFY_CIRCUIT"
    assert bundle.patch.patch_mode == "modify_existing"
    assert bundle.precheck.overall_status == "confirmation_required"
    assert bundle.preview.preview_mode == "patch_modify"
    assert "Risk + Confirmation" in bundle.rendered_preview
    assert bundle.preview.confirmation_preview.auto_commit_allowed is False


def test_proposal_flow_marks_missing_target_as_confirmation_required() -> None:
    flow = DesignerProposalFlow()
    bundle = flow.propose("Change provider in node answerer to Claude")
    assert bundle.intent.requires_user_confirmation is True
    assert bundle.precheck.overall_status == "confirmation_required"
    assert bundle.precheck.confirmation_findings


def test_proposal_flow_blocks_explain_requests_in_step2() -> None:
    flow = DesignerProposalFlow()
    try:
        flow.propose("Explain what this circuit does", working_save_ref="ws-001")
    except ValueError as exc:
        assert "mutation-oriented" in str(exc)
    else:
        raise AssertionError("Expected Step 2 flow to reject explain-only requests")


def test_proposal_flow_builds_repair_bundle() -> None:
    flow = DesignerProposalFlow()
    bundle = flow.propose("Repair the broken connection in node reviewer", working_save_ref="ws-002")
    assert bundle.intent.category == "REPAIR_CIRCUIT"
    assert bundle.patch.patch_mode == "repair_existing"
    assert bundle.precheck.can_proceed_to_preview is True


def test_proposal_flow_builds_optimize_bundle() -> None:
    flow = DesignerProposalFlow()
    bundle = flow.propose("Optimize node scorer to reduce cost", working_save_ref="ws-003")
    assert bundle.intent.category == "OPTIMIZE_CIRCUIT"
    assert bundle.patch.patch_mode == "optimize_existing"
    assert bundle.preview.summary_card.proposal_type == "optimize"


def test_request_normalizer_creates_target_ambiguity_flag_without_working_save_ref() -> None:
    normalizer = DesignerRequestNormalizer()
    intent = normalizer.normalize(
        "Modify node answerer to add a review step",
        context=RequestNormalizationContext(working_save_ref=None),
    )
    assert intent.ambiguity_flags
    assert intent.requires_user_confirmation is True



def test_request_normalizer_uses_clarified_interpretation_to_bound_scope() -> None:
    normalizer = DesignerRequestNormalizer()
    card = DesignerSessionStateCard(
        card_version="0.1",
        session_id="sess-clarified",
        storage_role="working_save",
        current_working_save=WorkingSaveReality(
            mode="existing_draft",
            savefile_ref="ws-001",
            node_list=("node.answerer", "node.reviewer"),
        ),
        current_selection=CurrentSelectionState(selection_mode="none"),
        target_scope=SessionTargetScope(mode="existing_circuit", touch_budget="bounded"),
        available_resources=AvailableResources(),
        objective=ObjectiveSpec(primary_goal="Change provider"),
        constraints=ConstraintSet(),
        conversation_context=ConversationContext(
            user_request_text="Change provider across the whole circuit",
            clarified_interpretation="Only change provider in node reviewer",
        ),
    )

    intent = normalizer.normalize(
        "Change provider across the whole circuit",
        context=RequestNormalizationContext(working_save_ref="ws-001", session_state_card=card),
    )

    assert all(flag.type != "broad_scope" for flag in intent.ambiguity_flags)
    assert intent.target_scope.node_refs == ("node.reviewer",)


def test_request_normalizer_uses_latest_committed_summary_priority_for_referential_request() -> None:
    normalizer = DesignerRequestNormalizer()
    card = DesignerSessionStateCard(
        card_version="0.1",
        session_id="sess-commit-summary",
        storage_role="working_save",
        current_working_save=WorkingSaveReality(
            mode="existing_draft",
            savefile_ref="ws-001",
            node_list=("node.answerer", "node.reviewer"),
        ),
        current_selection=CurrentSelectionState(selection_mode="none"),
        target_scope=SessionTargetScope(mode="existing_circuit", touch_budget="bounded"),
        available_resources=AvailableResources(),
        objective=ObjectiveSpec(primary_goal="Revert the previous change"),
        constraints=ConstraintSet(),
        conversation_context=ConversationContext(
            user_request_text="Revert the previous change",
        ),
        notes={
            "committed_summary_primary": {
                "commit_id": "commit-latest",
                "patch_ref": "patch-latest",
            },
            "commit_summary_history": [
                {"commit_id": "commit-latest", "patch_ref": "patch-latest"},
                {"commit_id": "commit-older", "patch_ref": "patch-older"},
            ],
        },
    )

    intent = normalizer.normalize(
        "Revert the previous change",
        context=RequestNormalizationContext(working_save_ref="ws-001", session_state_card=card),
    )

    assert any("commit-latest" in assumption.text for assumption in intent.assumptions)
    assert any(flag.type == "committed_summary_reference_history" for flag in intent.ambiguity_flags)

