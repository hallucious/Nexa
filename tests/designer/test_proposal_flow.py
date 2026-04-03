from __future__ import annotations

from src.designer.proposal_flow import DesignerProposalFlow
from src.designer.request_normalizer import DesignerRequestNormalizer, RequestNormalizationContext


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
