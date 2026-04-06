from __future__ import annotations

from src.designer.proposal_flow import DesignerProposalFlow
from src.designer.request_normalizer import DesignerRequestNormalizer, RequestNormalizationContext
from src.designer.models.designer_session_state_card import (
    AvailableResources,
    ConversationContext,
    CurrentSelectionState,
    DesignerSessionStateCard,
    RevisionAttemptSummary,
    RevisionState,
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
                {"commit_id": "commit-latest", "patch_ref": "patch-latest", "touched_node_ids": ["node.reviewer"]},
                {"commit_id": "commit-older", "patch_ref": "patch-older", "touched_node_ids": ["node.answerer"]},
            ],
        },
    )

    intent = normalizer.normalize(
        "Revert the previous change",
        context=RequestNormalizationContext(working_save_ref="ws-001", session_state_card=card),
    )

    assert any("commit-latest" in assumption.text for assumption in intent.assumptions)
    assert any("revert_committed_change" in assumption.text for assumption in intent.assumptions)



def test_request_normalizer_resolves_second_latest_commit_when_explicit() -> None:
    normalizer = DesignerRequestNormalizer()
    card = DesignerSessionStateCard(
        card_version="0.1",
        session_id="sess-second-latest",
        storage_role="working_save",
        current_working_save=WorkingSaveReality(
            mode="existing_draft",
            savefile_ref="ws-001",
            node_list=("node.answerer", "node.reviewer"),
        ),
        current_selection=CurrentSelectionState(selection_mode="none"),
        target_scope=SessionTargetScope(mode="existing_circuit", touch_budget="bounded"),
        available_resources=AvailableResources(),
        objective=ObjectiveSpec(primary_goal="Revert the change before last"),
        constraints=ConstraintSet(),
        conversation_context=ConversationContext(
            user_request_text="Revert the change before last",
        ),
        notes={
            "commit_summary_history": [
                {"commit_id": "commit-latest", "patch_ref": "patch-latest", "touched_node_ids": ["node.reviewer"]},
                {"commit_id": "commit-second", "patch_ref": "patch-second", "touched_node_ids": ["node.answerer"]},
            ],
        },
    )

    intent = normalizer.normalize(
        "Revert the change before last",
        context=RequestNormalizationContext(working_save_ref="ws-001", session_state_card=card),
    )

    assert any("commit-second" in assumption.text for assumption in intent.assumptions)
    assert all(flag.type != "committed_summary_reference_needs_clarification" for flag in intent.ambiguity_flags)


def test_request_normalizer_resolves_exact_commit_reference_without_ambiguity() -> None:
    normalizer = DesignerRequestNormalizer()
    card = DesignerSessionStateCard(
        card_version="0.1",
        session_id="sess-exact-commit",
        storage_role="working_save",
        current_working_save=WorkingSaveReality(
            mode="existing_draft",
            savefile_ref="ws-001",
            node_list=("node.answerer", "node.reviewer"),
        ),
        current_selection=CurrentSelectionState(selection_mode="none"),
        target_scope=SessionTargetScope(mode="existing_circuit", touch_budget="bounded"),
        available_resources=AvailableResources(),
        objective=ObjectiveSpec(primary_goal="Rollback commit abc1234"),
        constraints=ConstraintSet(),
        conversation_context=ConversationContext(
            user_request_text="Rollback commit abc1234",
        ),
        notes={
            "commit_summary_history": [
                {"commit_id": "fff9999", "patch_ref": "patch-latest", "touched_node_ids": ["node.reviewer"]},
                {"commit_id": "abc1234def", "patch_ref": "patch-target", "touched_node_ids": ["node.answerer"]},
            ],
        },
    )

    intent = normalizer.normalize(
        "Rollback commit abc1234",
        context=RequestNormalizationContext(working_save_ref="ws-001", session_state_card=card),
    )

    assert any("abc1234def" in assumption.text for assumption in intent.assumptions)
    assert all(flag.type != "committed_summary_reference_needs_clarification" for flag in intent.ambiguity_flags)
    assert all(flag.type != "committed_summary_reference_history" for flag in intent.ambiguity_flags)


def test_request_normalizer_requires_clarification_for_nonlatest_older_reference() -> None:
    normalizer = DesignerRequestNormalizer()
    card = DesignerSessionStateCard(
        card_version="0.1",
        session_id="sess-older-ambiguous",
        storage_role="working_save",
        current_working_save=WorkingSaveReality(
            mode="existing_draft",
            savefile_ref="ws-001",
            node_list=("node.answerer", "node.reviewer"),
        ),
        current_selection=CurrentSelectionState(selection_mode="none"),
        target_scope=SessionTargetScope(mode="existing_circuit", touch_budget="bounded"),
        available_resources=AvailableResources(),
        objective=ObjectiveSpec(primary_goal="Undo the older change"),
        constraints=ConstraintSet(),
        conversation_context=ConversationContext(
            user_request_text="Undo the older change",
        ),
        notes={
            "commit_summary_history": [
                {"commit_id": "commit-latest", "patch_ref": "patch-latest", "touched_node_ids": ["node.reviewer"]},
                {"commit_id": "commit-second", "patch_ref": "patch-second", "touched_node_ids": ["node.answerer"]},
                {"commit_id": "commit-third", "patch_ref": "patch-third"},
            ],
        },
    )

    intent = normalizer.normalize(
        "Undo the older change",
        context=RequestNormalizationContext(working_save_ref="ws-001", session_state_card=card),
    )

    assert any(flag.type == "committed_summary_reference_needs_clarification" for flag in intent.ambiguity_flags)


def test_request_normalizer_flags_insufficient_history_for_second_latest_reference() -> None:
    normalizer = DesignerRequestNormalizer()
    card = DesignerSessionStateCard(
        card_version="0.1",
        session_id="sess-insufficient-history",
        storage_role="working_save",
        current_working_save=WorkingSaveReality(
            mode="existing_draft",
            savefile_ref="ws-001",
            node_list=("node.answerer",),
        ),
        current_selection=CurrentSelectionState(selection_mode="none"),
        target_scope=SessionTargetScope(mode="existing_circuit", touch_budget="bounded"),
        available_resources=AvailableResources(),
        objective=ObjectiveSpec(primary_goal="Revert the change before last"),
        constraints=ConstraintSet(),
        conversation_context=ConversationContext(
            user_request_text="Revert the change before last",
        ),
        notes={
            "commit_summary_history": [
                {"commit_id": "commit-latest", "patch_ref": "patch-latest", "touched_node_ids": ["node.reviewer"]},
            ],
        },
    )

    intent = normalizer.normalize(
        "Revert the change before last",
        context=RequestNormalizationContext(working_save_ref="ws-001", session_state_card=card),
    )

    assert any(flag.type == "committed_summary_insufficient_history" for flag in intent.ambiguity_flags)



def test_request_normalizer_auto_targets_single_touched_node_for_latest_reference() -> None:
    normalizer = DesignerRequestNormalizer()
    card = DesignerSessionStateCard(
        card_version="0.1",
        session_id="sess-target-auto",
        storage_role="working_save",
        current_working_save=WorkingSaveReality(
            mode="existing_draft",
            savefile_ref="ws-001",
            node_list=("node.answerer", "node.reviewer"),
        ),
        current_selection=CurrentSelectionState(selection_mode="none"),
        target_scope=SessionTargetScope(mode="existing_circuit", touch_budget="bounded"),
        available_resources=AvailableResources(),
        objective=ObjectiveSpec(primary_goal="Undo the last change"),
        constraints=ConstraintSet(),
        conversation_context=ConversationContext(user_request_text="Undo the last change"),
        notes={
            "commit_summary_history": [
                {"commit_id": "commit-latest", "patch_ref": "patch-latest", "touched_node_ids": ["node.reviewer"]},
            ],
        },
    )

    intent = normalizer.normalize(
        "Undo the last change",
        context=RequestNormalizationContext(working_save_ref="ws-001", session_state_card=card),
    )

    assert intent.target_scope.mode == "node_only"
    assert intent.target_scope.node_refs == ("node.reviewer",)
    assert any("auto-resolved to node.reviewer" in assumption.text for assumption in intent.assumptions)
    assert all(flag.type != "committed_summary_target_needs_clarification" for flag in intent.ambiguity_flags)


def test_request_normalizer_requires_clarification_for_multi_target_summary_without_explicit_target() -> None:
    normalizer = DesignerRequestNormalizer()
    card = DesignerSessionStateCard(
        card_version="0.1",
        session_id="sess-target-clarify",
        storage_role="working_save",
        current_working_save=WorkingSaveReality(
            mode="existing_draft",
            savefile_ref="ws-001",
            node_list=("node.answerer", "node.reviewer"),
        ),
        current_selection=CurrentSelectionState(selection_mode="none"),
        target_scope=SessionTargetScope(mode="existing_circuit", touch_budget="bounded"),
        available_resources=AvailableResources(),
        objective=ObjectiveSpec(primary_goal="Undo the last change"),
        constraints=ConstraintSet(),
        conversation_context=ConversationContext(user_request_text="Undo the last change"),
        notes={
            "commit_summary_history": [
                {"commit_id": "commit-latest", "patch_ref": "patch-latest", "touched_node_ids": ["node.reviewer", "node.answerer"]},
            ],
        },
    )

    intent = normalizer.normalize(
        "Undo the last change",
        context=RequestNormalizationContext(working_save_ref="ws-001", session_state_card=card),
    )

    assert intent.target_scope.mode == "existing_circuit"
    assert intent.target_scope.node_refs == ()
    assert any(flag.type == "committed_summary_target_needs_clarification" for flag in intent.ambiguity_flags)


def test_request_normalizer_flags_conflicting_explicit_target_against_referenced_summary() -> None:
    normalizer = DesignerRequestNormalizer()
    card = DesignerSessionStateCard(
        card_version="0.1",
        session_id="sess-target-conflict",
        storage_role="working_save",
        current_working_save=WorkingSaveReality(
            mode="existing_draft",
            savefile_ref="ws-001",
            node_list=("node.answerer", "node.reviewer"),
        ),
        current_selection=CurrentSelectionState(selection_mode="none"),
        target_scope=SessionTargetScope(mode="existing_circuit", touch_budget="bounded"),
        available_resources=AvailableResources(),
        objective=ObjectiveSpec(primary_goal="Undo the last change on node answerer"),
        constraints=ConstraintSet(),
        conversation_context=ConversationContext(user_request_text="Undo the last change on node answerer"),
        notes={
            "commit_summary_history": [
                {"commit_id": "commit-latest", "patch_ref": "patch-latest", "touched_node_ids": ["node.reviewer"]},
            ],
        },
    )

    intent = normalizer.normalize(
        "Undo the last change on node answerer",
        context=RequestNormalizationContext(working_save_ref="ws-001", session_state_card=card),
    )

    assert intent.target_scope.node_refs == ("node.answerer",)
    assert any(flag.type == "committed_summary_target_conflict" for flag in intent.ambiguity_flags)


def test_request_normalizer_auto_resolves_safe_revert_action_for_latest_summary() -> None:
    normalizer = DesignerRequestNormalizer()
    card = DesignerSessionStateCard(
        card_version="0.1",
        session_id="sess-action-auto",
        storage_role="working_save",
        current_working_save=WorkingSaveReality(
            mode="existing_draft",
            savefile_ref="ws-001",
            node_list=("node.answerer", "node.reviewer"),
        ),
        current_selection=CurrentSelectionState(selection_mode="none"),
        target_scope=SessionTargetScope(mode="existing_circuit", touch_budget="bounded"),
        available_resources=AvailableResources(),
        objective=ObjectiveSpec(primary_goal="Undo the last change"),
        constraints=ConstraintSet(),
        conversation_context=ConversationContext(user_request_text="Undo the last change"),
        notes={
            "commit_summary_history": [
                {"commit_id": "commit-latest", "patch_ref": "patch-latest", "touched_node_ids": ["node.reviewer"]},
            ],
        },
    )

    intent = normalizer.normalize(
        "Undo the last change",
        context=RequestNormalizationContext(working_save_ref="ws-001", session_state_card=card),
    )

    assert intent.proposed_actions[0].action_type == "update_node"
    assert intent.proposed_actions[0].target_ref == "node.reviewer"
    assert intent.proposed_actions[0].parameters["operation_mode"] == "revert_committed_change"
    assert intent.proposed_actions[0].parameters["commit_id"] == "commit-latest"
    assert intent.proposed_actions[0].parameters["patch_ref"] == "patch-latest"
    assert any("revert_committed_change" in assumption.text for assumption in intent.assumptions)


def test_request_normalizer_requires_clarification_for_mixed_revert_and_provider_change() -> None:
    normalizer = DesignerRequestNormalizer()
    card = DesignerSessionStateCard(
        card_version="0.1",
        session_id="sess-action-mixed",
        storage_role="working_save",
        current_working_save=WorkingSaveReality(
            mode="existing_draft",
            savefile_ref="ws-001",
            node_list=("node.answerer", "node.reviewer"),
        ),
        current_selection=CurrentSelectionState(selection_mode="none"),
        target_scope=SessionTargetScope(mode="existing_circuit", touch_budget="bounded"),
        available_resources=AvailableResources(),
        objective=ObjectiveSpec(primary_goal="Undo the last change and switch provider"),
        constraints=ConstraintSet(),
        conversation_context=ConversationContext(user_request_text="Undo the last change and switch provider in node reviewer to Claude"),
        notes={
            "commit_summary_history": [
                {"commit_id": "commit-latest", "patch_ref": "patch-latest", "touched_node_ids": ["node.reviewer"]},
            ],
        },
    )

    intent = normalizer.normalize(
        "Undo the last change and switch provider in node reviewer to Claude",
        context=RequestNormalizationContext(working_save_ref="ws-001", session_state_card=card),
    )

    assert any(flag.type == "committed_summary_action_needs_clarification" for flag in intent.ambiguity_flags)
    assert any(flag.type == "mixed_referential_provider_change" for flag in intent.ambiguity_flags)
    assert all(
        action.parameters.get("operation_mode") != "revert_committed_change"
        for action in intent.proposed_actions
    )
    assert not intent.proposed_actions
    assert any("reason_code=MIXED_REFERENTIAL_PROVIDER_CHANGE" in assumption.text for assumption in intent.assumptions)



def test_request_normalizer_requires_clarification_for_mixed_revert_and_plugin_add() -> None:
    normalizer = DesignerRequestNormalizer()
    card = DesignerSessionStateCard(
        card_version="0.1",
        session_id="sess-action-plugin-mixed",
        storage_role="working_save",
        current_working_save=WorkingSaveReality(
            mode="existing_draft",
            savefile_ref="ws-001",
            node_list=("node.answerer", "node.reviewer"),
        ),
        current_selection=CurrentSelectionState(selection_mode="none"),
        target_scope=SessionTargetScope(mode="existing_circuit", touch_budget="bounded"),
        available_resources=AvailableResources(),
        objective=ObjectiveSpec(primary_goal="Rollback the last change and add plugin"),
        constraints=ConstraintSet(),
        conversation_context=ConversationContext(user_request_text="Rollback the last change and add plugin search in node reviewer"),
        notes={
            "commit_summary_history": [
                {"commit_id": "commit-latest", "patch_ref": "patch-latest", "touched_node_ids": ["node.reviewer"]},
            ],
        },
    )

    intent = normalizer.normalize(
        "Rollback the last change and add plugin search in node reviewer",
        context=RequestNormalizationContext(working_save_ref="ws-001", session_state_card=card),
    )

    assert any(flag.type == "committed_summary_action_needs_clarification" for flag in intent.ambiguity_flags)
    assert any(flag.type == "mixed_referential_plugin_attach" for flag in intent.ambiguity_flags)
    assert not intent.proposed_actions
    assert any("reason_code=MIXED_REFERENTIAL_PLUGIN_ATTACH" in assumption.text for assumption in intent.assumptions)


def test_proposal_flow_surfaces_mixed_referential_provider_change_in_precheck_and_preview() -> None:
    flow = DesignerProposalFlow()
    card = DesignerSessionStateCard(
        card_version="0.1",
        session_id="sess-mixed-precheck-preview",
        storage_role="working_save",
        current_working_save=WorkingSaveReality(
            mode="existing_draft",
            savefile_ref="ws-001",
            node_list=("node.answerer", "node.reviewer"),
        ),
        current_selection=CurrentSelectionState(selection_mode="none"),
        target_scope=SessionTargetScope(mode="existing_circuit", touch_budget="bounded"),
        available_resources=AvailableResources(),
        objective=ObjectiveSpec(primary_goal="Undo the last change and switch provider"),
        constraints=ConstraintSet(),
        conversation_context=ConversationContext(
            user_request_text="Undo the last change and switch provider in node reviewer to Claude"
        ),
        notes={
            "commit_summary_history": [
                {"commit_id": "commit-latest", "patch_ref": "patch-latest", "touched_node_ids": ["node.reviewer"]},
            ],
        },
    )

    bundle = flow.propose(
        "Undo the last change and switch provider in node reviewer to Claude",
        working_save_ref="ws-001",
        session_state_card=card,
    )

    assert bundle.precheck.overall_status == "confirmation_required"
    assert any(
        finding.issue_code == "MIXED_REFERENTIAL_PROVIDER_CHANGE"
        for finding in bundle.precheck.confirmation_findings
    )
    assert any(
        "reason_code=MIXED_REFERENTIAL_PROVIDER_CHANGE" in item
        for item in bundle.preview.confirmation_preview.required_confirmations
    )
    assert "reason_code=MIXED_REFERENTIAL_PROVIDER_CHANGE" in bundle.rendered_preview


def test_request_normalizer_requires_explicit_anchor_after_repeated_confirmation_cycles() -> None:
    normalizer = DesignerRequestNormalizer()
    card = DesignerSessionStateCard(
        card_version="0.1",
        session_id="sess-repeat-anchor",
        storage_role="working_save",
        current_working_save=WorkingSaveReality(
            mode="existing_draft",
            savefile_ref="ws-001",
            node_list=("node.answerer", "node.reviewer"),
        ),
        current_selection=CurrentSelectionState(selection_mode="none"),
        target_scope=SessionTargetScope(mode="existing_circuit", touch_budget="bounded"),
        available_resources=AvailableResources(),
        objective=ObjectiveSpec(primary_goal="Undo the last change"),
        constraints=ConstraintSet(),
        revision_state=RevisionState(
            revision_index=2,
            attempt_history=(
                RevisionAttemptSummary(
                    attempt_index=1,
                    stage="precheck",
                    outcome="confirmation_required",
                    reason_code="DESIGNER-CONFIRMATION-REQUIRED",
                    message="The proposal may proceed to preview, but explicit approval or clarification is required before commit.",
                ),
                RevisionAttemptSummary(
                    attempt_index=2,
                    stage="precheck",
                    outcome="confirmation_required",
                    reason_code="DESIGNER-CONFIRMATION-REQUIRED",
                    message="The proposal may proceed to preview, but explicit approval or clarification is required before commit.",
                ),
            ),
        ),
        conversation_context=ConversationContext(user_request_text="Undo the last change"),
        notes={
            "commit_summary_history": [
                {"commit_id": "commit-latest", "patch_ref": "patch-latest", "touched_node_ids": ["node.reviewer"]},
            ],
            "control_governance_requires_explicit_referential_anchor": True,
        },
    )

    intent = normalizer.normalize(
        "Undo the last change",
        context=RequestNormalizationContext(working_save_ref="ws-001", session_state_card=card),
    )

    assert any(flag.type == "committed_summary_repeat_cycle_anchor_required" for flag in intent.ambiguity_flags)
    assert all(
        action.parameters.get("operation_mode") != "revert_committed_change"
        for action in intent.proposed_actions
    )
    assert any("Repeated confirmation cycles are active for referential interpretation" in assumption.text for assumption in intent.assumptions)


def test_repeated_confirmation_governance_surfaces_policy_in_precheck_and_preview() -> None:
    flow = DesignerProposalFlow()
    card = DesignerSessionStateCard(
        card_version="0.1",
        session_id="sess-governance-precheck",
        storage_role="working_save",
        current_working_save=WorkingSaveReality(
            mode="existing_draft",
            savefile_ref="ws-001",
            node_list=("node.answerer", "node.reviewer"),
        ),
        current_selection=CurrentSelectionState(selection_mode="none"),
        target_scope=SessionTargetScope(mode="existing_circuit", touch_budget="bounded"),
        available_resources=AvailableResources(),
        objective=ObjectiveSpec(primary_goal="Undo the last change"),
        constraints=ConstraintSet(),
        revision_state=RevisionState(
            revision_index=3,
            attempt_history=(
                RevisionAttemptSummary(
                    attempt_index=1,
                    stage="precheck",
                    outcome="confirmation_required",
                    reason_code="DESIGNER-CONFIRMATION-REQUIRED",
                    message="The proposal may proceed to preview, but explicit approval or clarification is required before commit.",
                ),
                RevisionAttemptSummary(
                    attempt_index=2,
                    stage="precheck",
                    outcome="confirmation_required",
                    reason_code="DESIGNER-CONFIRMATION-REQUIRED",
                    message="The proposal may proceed to preview, but explicit approval or clarification is required before commit.",
                ),
                RevisionAttemptSummary(
                    attempt_index=3,
                    stage="precheck",
                    outcome="confirmation_required",
                    reason_code="DESIGNER-CONFIRMATION-REQUIRED",
                    message="The proposal may proceed to preview, but explicit approval or clarification is required before commit.",
                ),
            ),
        ),
        conversation_context=ConversationContext(user_request_text="Undo the last change"),
        notes={
            "commit_summary_history": [
                {"commit_id": "commit-latest", "patch_ref": "patch-latest", "touched_node_ids": ["node.reviewer"]},
            ],
            "control_governance_policy_tier": "strict",
            "control_governance_requires_explicit_referential_anchor": True,
            "control_governance_precheck_message": "Repeated referential ambiguity has triggered strict governance mode. Provide an explicit commit anchor, explicit node target, or explicit non-latest selector before approval can continue safely.",
            "control_governance_preview_hint": "Strict referential governance is active. The next safe step is to restate the request with a stronger anchor instead of relying on 'last change' style language.",
            "control_governance_policy_reason": "Three or more closely related confirmation cycles were observed, so referential auto-resolution has moved into strict governance mode.",
            "control_governance_ambiguity_pressure_score": 5,
            "control_governance_ambiguity_pressure_band": "strict",
            "control_governance_pressure_transition": "escalating_or_sustained_repeat_pressure",
            "control_governance_pressure_summary": "Ambiguity pressure is high and still building (5/5, strict band).",
        },
    )

    bundle = flow.propose(
        "Undo the last change",
        working_save_ref="ws-001",
        session_state_card=card,
    )

    assert bundle.precheck.overall_status == "confirmation_required"
    assert any(finding.issue_code == "REFERENTIAL_GOVERNANCE_STRICT" for finding in bundle.precheck.confirmation_findings)
    assert any("strict governance mode" in finding.message for finding in bundle.precheck.confirmation_findings)
    assert bundle.preview.summary_card.user_action_hint == "Provide a stronger referential anchor before approving the proposal."
    assert any("Strict referential governance is active." in item for item in bundle.preview.confirmation_preview.required_confirmations)
    assert any("Ambiguity pressure is high and still building (5/5, strict band)." in item for item in bundle.preview.confirmation_preview.required_confirmations)
    assert "strict governance mode" in bundle.preview.explanation
    assert "5/5 (strict)" in bundle.rendered_preview
    assert "strict governance mode" in bundle.rendered_preview


def test_request_normalizer_allows_explicit_node_anchor_after_repeated_confirmation_cycles() -> None:
    normalizer = DesignerRequestNormalizer()
    card = DesignerSessionStateCard(
        card_version="0.1",
        session_id="sess-repeat-node-anchor",
        storage_role="working_save",
        current_working_save=WorkingSaveReality(
            mode="existing_draft",
            savefile_ref="ws-001",
            node_list=("node.answerer", "node.reviewer"),
        ),
        current_selection=CurrentSelectionState(selection_mode="none"),
        target_scope=SessionTargetScope(mode="existing_circuit", touch_budget="bounded"),
        available_resources=AvailableResources(),
        objective=ObjectiveSpec(primary_goal="Undo the last change on node reviewer"),
        constraints=ConstraintSet(),
        revision_state=RevisionState(
            revision_index=2,
            attempt_history=(
                RevisionAttemptSummary(
                    attempt_index=1,
                    stage="precheck",
                    outcome="confirmation_required",
                    reason_code="DESIGNER-CONFIRMATION-REQUIRED",
                    message="The proposal may proceed to preview, but explicit approval or clarification is required before commit.",
                ),
                RevisionAttemptSummary(
                    attempt_index=2,
                    stage="precheck",
                    outcome="confirmation_required",
                    reason_code="DESIGNER-CONFIRMATION-REQUIRED",
                    message="The proposal may proceed to preview, but explicit approval or clarification is required before commit.",
                ),
            ),
        ),
        conversation_context=ConversationContext(user_request_text="Undo the last change on node reviewer"),
        notes={
            "commit_summary_history": [
                {"commit_id": "commit-latest", "patch_ref": "patch-latest", "touched_node_ids": ["node.reviewer"]},
            ],
            "control_governance_requires_explicit_referential_anchor": True,
        },
    )

    intent = normalizer.normalize(
        "Undo the last change on node reviewer",
        context=RequestNormalizationContext(working_save_ref="ws-001", session_state_card=card),
    )

    assert all(flag.type != "committed_summary_repeat_cycle_anchor_required" for flag in intent.ambiguity_flags)
    assert any(
        action.parameters.get("operation_mode") == "revert_committed_change"
        for action in intent.proposed_actions
    )


def test_proposal_flow_surfaces_anchored_governance_as_warning_not_confirmation() -> None:
    flow = DesignerProposalFlow()
    card = DesignerSessionStateCard(
        card_version="0.1",
        session_id="sess-anchored-strict",
        storage_role="working_save",
        current_working_save=WorkingSaveReality(
            mode="existing_draft",
            savefile_ref="ws-001",
            node_list=("node.answerer", "node.reviewer"),
        ),
        current_selection=CurrentSelectionState(selection_mode="none"),
        target_scope=SessionTargetScope(mode="existing_circuit", touch_budget="bounded"),
        available_resources=AvailableResources(),
        objective=ObjectiveSpec(primary_goal="Undo the last change on node reviewer"),
        constraints=ConstraintSet(),
        revision_state=RevisionState(
            revision_index=3,
            attempt_history=(
                RevisionAttemptSummary(1, "precheck", "confirmation_required", "DESIGNER-CONFIRMATION-REQUIRED", "confirm"),
                RevisionAttemptSummary(2, "precheck", "confirmation_required", "DESIGNER-CONFIRMATION-REQUIRED", "confirm"),
                RevisionAttemptSummary(3, "precheck", "confirmation_required", "DESIGNER-CONFIRMATION-REQUIRED", "confirm"),
            ),
        ),
        conversation_context=ConversationContext(user_request_text="Undo the last change on node reviewer"),
        notes={
            "commit_summary_history": [
                {"commit_id": "commit-latest", "patch_ref": "patch-latest", "touched_node_ids": ["node.reviewer"]},
            ],
            "control_governance_policy_tier": "strict",
            "control_governance_requires_explicit_referential_anchor": True,
            "control_governance_policy_reason": "Three or more closely related confirmation cycles were observed, so referential auto-resolution has moved into strict governance mode.",
            "control_governance_preview_hint": "Strict referential governance is active. The next safe step is to restate the request with a stronger anchor instead of relying on 'last change' style language.",
            "control_governance_ambiguity_pressure_score": 4,
            "control_governance_ambiguity_pressure_band": "strict",
            "control_governance_pressure_transition": "held_until_resolution",
            "control_governance_pressure_summary": "Ambiguity pressure remains held (4/5, strict band).",
        },
    )

    bundle = flow.propose(
        "Undo the last change on node reviewer",
        working_save_ref="ws-001",
        session_state_card=card,
    )

    assert bundle.precheck.overall_status == "confirmation_required"
    assert not any(f.issue_code == "REFERENTIAL_GOVERNANCE_STRICT" for f in bundle.precheck.confirmation_findings)
    assert any(f.issue_code == "REFERENTIAL_GOVERNANCE_STRICT_ANCHORED" for f in bundle.precheck.warning_findings)
    assert "strong enough anchor" in bundle.preview.explanation
    assert "4/5 (strict band)" in bundle.preview.explanation
    assert not any(f.issue_code == "REFERENTIAL_GOVERNANCE_STRICT" for f in bundle.precheck.confirmation_findings)
    assert any(f.issue_code == "REFERENTIAL_GOVERNANCE_STRICT_ANCHORED" for f in bundle.precheck.warning_findings)
    assert "strong enough anchor" in bundle.preview.explanation


def test_proposal_flow_does_not_surface_governance_for_unrelated_nonreferential_request() -> None:
    flow = DesignerProposalFlow()
    card = DesignerSessionStateCard(
        card_version="0.1",
        session_id="sess-nonreferential-strict",
        storage_role="working_save",
        current_working_save=WorkingSaveReality(
            mode="existing_draft",
            savefile_ref="ws-001",
            node_list=("node.answerer", "node.reviewer"),
        ),
        current_selection=CurrentSelectionState(selection_mode="none"),
        target_scope=SessionTargetScope(mode="existing_circuit", touch_budget="bounded"),
        available_resources=AvailableResources(),
        objective=ObjectiveSpec(primary_goal="Change provider in node reviewer to Claude"),
        constraints=ConstraintSet(),
        conversation_context=ConversationContext(user_request_text="Change provider in node reviewer to Claude"),
        notes={
            "control_governance_policy_tier": "strict",
            "control_governance_requires_explicit_referential_anchor": True,
            "control_governance_policy_reason": "Three or more closely related confirmation cycles were observed, so referential auto-resolution has moved into strict governance mode.",
            "control_governance_preview_hint": "Strict referential governance is active. The next safe step is to restate the request with a stronger anchor instead of relying on 'last change' style language.",
        },
    )

    bundle = flow.propose(
        "Change provider in node reviewer to Claude",
        working_save_ref="ws-001",
        session_state_card=card,
    )

    assert not any(f.issue_code.startswith("REFERENTIAL_GOVERNANCE_") for f in bundle.precheck.confirmation_findings)
    assert not any(f.issue_code.startswith("REFERENTIAL_GOVERNANCE_") for f in bundle.precheck.warning_findings)
    assert "strict governance mode" not in bundle.preview.explanation



def test_request_normalizer_reuses_pending_governance_revision_guidance_for_referential_retry() -> None:
    normalizer = DesignerRequestNormalizer()
    card = DesignerSessionStateCard(
        card_version="0.1",
        session_id="sess-pending-anchor-reuse",
        storage_role="working_save",
        current_working_save=WorkingSaveReality(
            mode="existing_draft",
            savefile_ref="ws-001",
            node_list=("node.answerer", "node.reviewer"),
        ),
        current_selection=CurrentSelectionState(selection_mode="none"),
        target_scope=SessionTargetScope(mode="existing_circuit", touch_budget="bounded"),
        available_resources=AvailableResources(),
        objective=ObjectiveSpec(primary_goal="Undo the last change"),
        constraints=ConstraintSet(),
        conversation_context=ConversationContext(user_request_text="Undo the last change"),
        notes={
            "commit_summary_history": [
                {"commit_id": "commit-latest", "patch_ref": "patch-latest", "touched_node_ids": ["node.reviewer"]},
            ],
            "control_governance_pending_anchor_requirement": True,
            "control_governance_pending_anchor_requirement_mode": "required",
            "control_governance_last_revision_guidance": "Provide an explicit commit anchor before the next revision attempt.",
            "control_governance_last_revision_pressure_summary": "Ambiguity pressure remains 5/5 (strict band), so do not fall back to loose selectors.",
            "control_governance_last_revision_pressure_score": 5,
            "control_governance_last_revision_pressure_band": "strict",
            "control_governance_last_revision_next_actions": [
                "provide_explicit_anchor",
                "restate_request_with_stronger_selector",
            ],
            "control_governance_requires_explicit_referential_anchor": True,
        },
    )

    intent = normalizer.normalize(
        "Undo the last change",
        context=RequestNormalizationContext(working_save_ref="ws-001", session_state_card=card),
    )

    assert any(flag.type == "governance_pressure_carryover" for flag in intent.risk_flags)
    assert any("5/5 (strict band)" in flag.description for flag in intent.risk_flags if flag.type == "governance_pressure_carryover")
    assert any("persisted revision guidance" in assumption.text for assumption in intent.assumptions)
    anchor_flag = next(flag for flag in intent.ambiguity_flags if flag.type == "committed_summary_repeat_cycle_anchor_required")
    assert "5/5 (strict band)" in anchor_flag.description


def test_request_normalizer_does_not_apply_pending_governance_revision_guidance_to_nonreferential_request() -> None:
    normalizer = DesignerRequestNormalizer()
    card = DesignerSessionStateCard(
        card_version="0.1",
        session_id="sess-pending-anchor-ignore",
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
        conversation_context=ConversationContext(user_request_text="Change provider in node reviewer to Claude"),
        notes={
            "control_governance_pending_anchor_requirement": True,
            "control_governance_pending_anchor_requirement_mode": "required",
            "control_governance_last_revision_guidance": "Provide an explicit commit anchor before the next revision attempt.",
            "control_governance_last_revision_pressure_summary": "Ambiguity pressure remains 5/5 (strict band), so do not fall back to loose selectors.",
            "control_governance_last_revision_pressure_score": 5,
            "control_governance_last_revision_pressure_band": "strict",
            "control_governance_last_revision_next_actions": ["provide_explicit_anchor"],
        },
    )

    intent = normalizer.normalize(
        "Change provider in node reviewer to Claude",
        context=RequestNormalizationContext(working_save_ref="ws-001", session_state_card=card),
    )

    assert all(flag.type != "governance_pressure_carryover" for flag in intent.risk_flags)
    assert all("persisted revision guidance" not in assumption.text for assumption in intent.assumptions)


def test_request_normalizer_does_not_carry_governance_pressure_for_nonreferential_followup() -> None:
    normalizer = DesignerRequestNormalizer()
    card = DesignerSessionStateCard(
        card_version="0.1",
        session_id="sess-nonreferential-followup",
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
        conversation_context=ConversationContext(user_request_text="Undo the last change"),
        notes={
            "control_governance_pending_anchor_requirement": True,
            "control_governance_pending_anchor_requirement_mode": "required",
            "control_governance_last_revision_guidance": "Provide an explicit commit anchor before the next revision attempt.",
            "control_governance_last_revision_pressure_summary": "Ambiguity pressure remains 5/5 (strict band), so do not fall back to loose selectors.",
            "control_governance_last_revision_pressure_score": 5,
            "control_governance_last_revision_pressure_band": "strict",
            "control_governance_last_revision_next_actions": [
                "provide_explicit_anchor",
                "restate_request_with_stronger_selector",
            ],
        },
    )

    intent = normalizer.normalize(
        "Change provider in node reviewer to Claude",
        context=RequestNormalizationContext(working_save_ref="ws-001", session_state_card=card),
    )

    assert all(flag.type != "governance_pressure_carryover" for flag in intent.risk_flags)
    assert all("explicit commit anchor" not in assumption.text for assumption in intent.assumptions)


def test_request_normalizer_does_not_carry_unsatisfied_governance_pressure_for_anchored_referential_retry() -> None:
    normalizer = DesignerRequestNormalizer()
    card = DesignerSessionStateCard(
        card_version="0.1",
        session_id="sess-anchored-followup",
        storage_role="working_save",
        current_working_save=WorkingSaveReality(
            mode="existing_draft",
            savefile_ref="ws-001",
            node_list=("node.answerer", "node.reviewer"),
        ),
        current_selection=CurrentSelectionState(selection_mode="none"),
        target_scope=SessionTargetScope(mode="existing_circuit", touch_budget="bounded"),
        available_resources=AvailableResources(),
        objective=ObjectiveSpec(primary_goal="Undo anchored change"),
        constraints=ConstraintSet(),
        conversation_context=ConversationContext(user_request_text="Undo the last change"),
        notes={
            "commit_summary_history": [
                {"commit_id": "fff9999", "patch_ref": "patch-latest", "touched_node_ids": ["node.reviewer"]},
                {"commit_id": "abc1234def", "patch_ref": "patch-target", "touched_node_ids": ["node.answerer"]},
            ],
            "control_governance_pending_anchor_requirement": True,
            "control_governance_pending_anchor_requirement_mode": "required",
            "control_governance_last_revision_guidance": "Provide an explicit commit anchor before the next revision attempt.",
            "control_governance_last_revision_pressure_summary": "Ambiguity pressure remains 5/5 (strict band), so do not fall back to loose selectors.",
            "control_governance_last_revision_pressure_score": 5,
            "control_governance_last_revision_pressure_band": "strict",
            "control_governance_last_revision_next_actions": [
                "provide_explicit_anchor",
                "restate_request_with_stronger_selector",
            ],
        },
    )

    intent = normalizer.normalize(
        "Undo the last change on node reviewer",
        context=RequestNormalizationContext(working_save_ref="ws-001", session_state_card=card),
    )

    assert all(flag.type != "governance_pressure_carryover" for flag in intent.risk_flags)
    assert all(flag.type != "committed_summary_repeat_cycle_anchor_required" for flag in intent.ambiguity_flags)



def test_request_normalizer_reuses_recent_cleared_governance_resolution_for_referential_followup() -> None:
    normalizer = DesignerRequestNormalizer()
    card = DesignerSessionStateCard(
        card_version="0.1",
        session_id="sess-cleared-resolution-followup",
        storage_role="working_save",
        current_working_save=WorkingSaveReality(
            mode="existing_draft",
            savefile_ref="ws-001",
            node_list=("node.answerer", "node.reviewer"),
        ),
        current_selection=CurrentSelectionState(selection_mode="none"),
        target_scope=SessionTargetScope(mode="existing_circuit", touch_budget="bounded"),
        available_resources=AvailableResources(),
        objective=ObjectiveSpec(primary_goal="Undo anchored change"),
        constraints=ConstraintSet(),
        conversation_context=ConversationContext(user_request_text="Undo the last change on node reviewer"),
        notes={
            "commit_summary_history": [
                {"commit_id": "fff9999", "patch_ref": "patch-latest", "touched_node_ids": ["node.reviewer"]},
            ],
            "control_governance_last_pending_anchor_resolution_status": "cleared_by_anchored_retry",
            "control_governance_last_pending_anchor_resolution_summary": "Pending governance carryover was cleared because the stronger referential anchor was satisfied in the last cycle.",
            "control_governance_last_pending_anchor_resolution_request_text": "Undo the last change on node reviewer",
        },
    )

    intent = normalizer.normalize(
        "Undo the last change on node reviewer",
        context=RequestNormalizationContext(working_save_ref="ws-001", session_state_card=card),
    )

    assert all(flag.type != "governance_pressure_carryover" for flag in intent.risk_flags)
    assert any("already satisfied by an anchored retry" in assumption.text for assumption in intent.assumptions)


def test_request_normalizer_ignores_expired_recent_cleared_governance_resolution() -> None:
    normalizer = DesignerRequestNormalizer()
    card = DesignerSessionStateCard(
        card_version="0.1",
        session_id="sess-cleared-resolution-expired",
        storage_role="working_save",
        current_working_save=WorkingSaveReality(
            mode="existing_draft",
            savefile_ref="ws-001",
            node_list=("node.answerer", "node.reviewer"),
        ),
        current_selection=CurrentSelectionState(selection_mode="none"),
        target_scope=SessionTargetScope(mode="existing_circuit", touch_budget="bounded"),
        available_resources=AvailableResources(),
        objective=ObjectiveSpec(primary_goal="Undo anchored change"),
        constraints=ConstraintSet(),
        conversation_context=ConversationContext(user_request_text="Undo the last change on node reviewer"),
        notes={
            "commit_summary_history": [
                {"commit_id": "fff9999", "patch_ref": "patch-latest", "touched_node_ids": ["node.reviewer"]},
            ],
            "control_governance_last_pending_anchor_resolution_status": "cleared_by_anchored_retry",
            "control_governance_last_pending_anchor_resolution_summary": "Pending governance carryover was cleared because the stronger referential anchor was satisfied in the last cycle.",
            "control_governance_last_pending_anchor_resolution_request_text": "Undo the last change on node reviewer",
            "control_governance_last_pending_anchor_resolution_age": 1,
        },
    )

    intent = normalizer.normalize(
        "Undo the last change on node reviewer",
        context=RequestNormalizationContext(working_save_ref="ws-001", session_state_card=card),
    )

    assert all("already satisfied by an anchored retry" not in assumption.text for assumption in intent.assumptions)


def test_request_normalizer_hides_recent_cleared_governance_resolution_for_nonreferential_followup() -> None:
    normalizer = DesignerRequestNormalizer()
    card = DesignerSessionStateCard(
        card_version="0.1",
        session_id="sess-cleared-resolution-ignore",
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
        conversation_context=ConversationContext(user_request_text="Change provider in node reviewer to Claude"),
        notes={
            "control_governance_last_pending_anchor_resolution_status": "cleared_by_anchored_retry",
            "control_governance_last_pending_anchor_resolution_summary": "Pending governance carryover was cleared because the stronger referential anchor was satisfied in the last cycle.",
            "control_governance_last_pending_anchor_resolution_request_text": "Undo the last change on node reviewer",
        },
    )

    intent = normalizer.normalize(
        "Change provider in node reviewer to Claude",
        context=RequestNormalizationContext(working_save_ref="ws-001", session_state_card=card),
    )

    assert all("already satisfied by an anchored retry" not in assumption.text for assumption in intent.assumptions)


def test_request_normalizer_reuses_recent_multi_step_revision_history_for_mutation_request() -> None:
    normalizer = DesignerRequestNormalizer()
    card = DesignerSessionStateCard(
        card_version="0.1",
        session_id="sess-recent-revision-history",
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
        conversation_context=ConversationContext(user_request_text="Change provider in node reviewer to Claude", clarified_interpretation="Only modify node.reviewer."),
        notes={
            "approval_revision_recent_history": [
                {"continuation_modes": ["choose_interpretation"], "selected_interpretation": "Only modify node.reviewer."},
                {"continuation_modes": ["request_revision"], "selected_interpretation": "Only modify node.reviewer."},
            ],
            "approval_revision_recent_history_count": 2,
            "approval_revision_recent_history_summary": "Recent approval/revision continuity includes 2 step(s). Latest continuation mode: request revision. Latest clarified interpretation remains: Only modify node.reviewer.",
        },
    )

    intent = normalizer.normalize(
        "Change provider in node reviewer to Claude",
        context=RequestNormalizationContext(working_save_ref="ws-001", session_state_card=card),
    )

    assert any("multi-step revision thread" in assumption.text for assumption in intent.assumptions)


def test_request_normalizer_hides_recent_multi_step_revision_history_for_read_only_request() -> None:
    normalizer = DesignerRequestNormalizer()
    card = DesignerSessionStateCard(
        card_version="0.1",
        session_id="sess-recent-revision-history-readonly",
        storage_role="working_save",
        current_working_save=WorkingSaveReality(
            mode="existing_draft",
            savefile_ref="ws-001",
            node_list=("node.answerer", "node.reviewer"),
        ),
        current_selection=CurrentSelectionState(selection_mode="none"),
        target_scope=SessionTargetScope(mode="existing_circuit", touch_budget="bounded"),
        available_resources=AvailableResources(),
        objective=ObjectiveSpec(primary_goal="Explain changes"),
        constraints=ConstraintSet(),
        conversation_context=ConversationContext(user_request_text="Explain what changed", clarified_interpretation="Only modify node.reviewer."),
        notes={
            "approval_revision_recent_history": [
                {"continuation_modes": ["choose_interpretation"], "selected_interpretation": "Only modify node.reviewer."},
                {"continuation_modes": ["request_revision"], "selected_interpretation": "Only modify node.reviewer."},
            ],
            "approval_revision_recent_history_count": 2,
            "approval_revision_recent_history_summary": "Recent approval/revision continuity includes 2 step(s). Latest continuation mode: request revision. Latest clarified interpretation remains: Only modify node.reviewer.",
        },
    )

    intent = normalizer.normalize(
        "Explain what changed in node reviewer",
        context=RequestNormalizationContext(working_save_ref="ws-001", session_state_card=card),
    )

    assert all("multi-step revision thread" not in assumption.text for assumption in intent.assumptions)
