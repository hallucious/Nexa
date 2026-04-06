from __future__ import annotations

from src.designer.models import DesignerSessionStateCard
from src.designer.models.designer_intent import ConstraintSet, ObjectiveSpec
from src.designer.models.designer_session_state_card import (
    AvailableResources,
    ConversationContext,
    CurrentSelectionState,
    SessionTargetScope,
    WorkingSaveReality,
)
from src.designer.proposal_flow import DesignerProposalFlow
from src.designer.session_state_card_builder import DesignerSessionStateCardBuilder
from src.storage.models.shared_sections import CircuitModel, MetaBase, ResourcesModel, StateModel
from src.storage.models.working_save_model import RuntimeModel, UIModel, WorkingSaveMeta, WorkingSaveModel


def make_working_save() -> WorkingSaveModel:
    return WorkingSaveModel(
        meta=WorkingSaveMeta(format_version="1.0.0", storage_role="working_save", working_save_id="ws-001", name="demo"),
        circuit=CircuitModel(
            nodes=[{"id": "node.answerer", "kind": "provider"}, {"id": "node.reviewer", "kind": "provider"}],
            edges=[{"from": "node.answerer", "to": "node.reviewer"}],
            outputs=[{"name": "final_answer", "source": "node.reviewer.output.result"}],
        ),
        resources=ResourcesModel(
            prompts={"prompt.review": {}},
            providers={"provider.gpt": {}, "provider.claude": {}},
            plugins={"plugin.search": {}},
        ),
        state=StateModel(),
        runtime=RuntimeModel(status="draft"),
        ui=UIModel(),
    )


def test_session_state_card_builder_builds_from_working_save() -> None:
    builder = DesignerSessionStateCardBuilder()
    card = builder.build(request_text="Add a review node before final output", artifact=make_working_save())
    assert card.storage_role == "working_save"
    assert card.current_working_save.savefile_ref == "ws-001"
    assert "node.answerer" in card.current_working_save.node_list
    assert any(item.id == "provider.claude" for item in card.available_resources.providers)
    assert card.target_scope.mode == "existing_circuit"


def test_proposal_flow_accepts_session_state_card_and_narrows_scope() -> None:
    flow = DesignerProposalFlow()
    card = DesignerSessionStateCard(
        card_version="0.1",
        session_id="sess-1",
        storage_role="working_save",
        current_working_save=WorkingSaveReality(
            mode="existing_draft",
            savefile_ref="ws-001",
            circuit_summary="2 nodes",
            node_list=("node.answerer", "node.reviewer"),
            edge_list=("node.answerer->node.reviewer",),
            output_list=("final_answer",),
            provider_refs=("provider.gpt",),
        ),
        current_selection=CurrentSelectionState(selection_mode="node", selected_refs=("node.answerer",)),
        target_scope=SessionTargetScope(mode="node_only", touch_budget="minimal", allowed_node_refs=("node.answerer",)),
        available_resources=AvailableResources(),
        objective=ObjectiveSpec(primary_goal="Add review"),
        constraints=ConstraintSet(provider_restrictions=("provider.legacy",)),
        conversation_context=ConversationContext(user_request_text="Change provider in node answerer to Claude"),
    )
    bundle = flow.propose(
        "Change provider in node answerer to Claude",
        working_save_ref="ws-001",
        session_state_card=card,
    )
    assert bundle.session_state_card.session_id == "sess-1"
    assert bundle.intent.target_scope.mode == "node_only"
    assert bundle.intent.target_scope.node_refs == ("node.answerer",)
    assert bundle.intent.constraints.provider_restrictions == ("provider.legacy",)



def test_session_state_card_builder_surfaces_pending_governance_anchor_carryover() -> None:
    from src.designer.session_state_persistence import persist_designer_session_state

    builder = DesignerSessionStateCardBuilder()
    base = builder.build(request_text="Undo the last change", artifact=make_working_save())
    carried = base.__class__(**{
        **base.__dict__,
        "notes": {
            **base.notes,
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
    })
    persisted = persist_designer_session_state(make_working_save(), session_state_card=carried)

    rebuilt = builder.build(request_text="Undo the last change", artifact=persisted)

    assert rebuilt.notes["control_governance_revision_guidance_carryover_applied"] is True
    assert any("Provide an explicit commit anchor" in item for item in rebuilt.current_findings.warning_findings)
    assert any("Next safe step:" in item for item in rebuilt.current_findings.warning_findings)
    assert any("Pending referential-anchor requirement remains" in item for item in rebuilt.current_risks.risk_flags)
    assert any("5/5 (strict band)" in item for item in rebuilt.current_risks.unresolved_high_risks)


def test_session_state_card_builder_hides_pending_governance_carryover_for_nonreferential_request() -> None:
    from src.designer.session_state_persistence import persist_designer_session_state

    builder = DesignerSessionStateCardBuilder()
    base = builder.build(request_text="Undo the last change", artifact=make_working_save())
    carried = base.__class__(**{
        **base.__dict__,
        "notes": {
            **base.notes,
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
    })
    persisted = persist_designer_session_state(make_working_save(), session_state_card=carried)

    rebuilt = builder.build(request_text="Change provider in node reviewer to Claude", artifact=persisted)

    assert rebuilt.notes["control_governance_revision_guidance_carryover_status"] == "hidden_nonreferential"
    assert rebuilt.notes["control_governance_revision_guidance_carryover_applied"] is False
    assert all("Provide an explicit commit anchor" not in item for item in rebuilt.current_findings.warning_findings)
    assert all("Pending referential-anchor requirement remains" not in item for item in rebuilt.current_risks.risk_flags)


def test_session_state_card_builder_downgrades_pending_governance_carryover_for_anchored_request() -> None:
    from src.designer.session_state_persistence import persist_designer_session_state

    builder = DesignerSessionStateCardBuilder()
    base = builder.build(request_text="Undo the last change", artifact=make_working_save())
    carried = base.__class__(**{
        **base.__dict__,
        "notes": {
            **base.notes,
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
    })
    persisted = persist_designer_session_state(make_working_save(), session_state_card=carried)

    rebuilt = builder.build(request_text="Undo the last change on node reviewer", artifact=persisted)

    assert rebuilt.notes["control_governance_revision_guidance_carryover_status"] == "anchored_satisfied"
    assert rebuilt.notes["control_governance_revision_guidance_carryover_applied"] is True
    assert any("already provides a stronger referential anchor" in item for item in rebuilt.current_findings.warning_findings)
    assert all("Pending referential-anchor requirement remains" not in item for item in rebuilt.current_risks.risk_flags)
    assert rebuilt.current_risks.unresolved_high_risks == ()



def test_session_state_card_builder_surfaces_recent_cleared_governance_resolution_for_referential_followup() -> None:
    from src.designer.session_state_persistence import persist_designer_session_state

    builder = DesignerSessionStateCardBuilder()
    base = builder.build(request_text="Undo the last change on node reviewer", artifact=make_working_save())
    carried = base.__class__(**{
        **base.__dict__,
        "notes": {
            **base.notes,
            "control_governance_last_pending_anchor_resolution_status": "cleared_by_anchored_retry",
            "control_governance_last_pending_anchor_resolution_summary": "Pending governance carryover was cleared because the stronger referential anchor was satisfied in the last cycle.",
            "control_governance_last_pending_anchor_resolution_request_text": "Undo the last change on node reviewer",
        },
    })
    persisted = persist_designer_session_state(make_working_save(), session_state_card=carried)

    rebuilt = builder.build(request_text="Undo the last change on node reviewer", artifact=persisted)

    assert rebuilt.notes["control_governance_recent_resolution_status"] == "visible_referential"
    assert rebuilt.notes["control_governance_recent_resolution_applied"] is True
    assert any("recently cleared by an explicit anchored retry" in item for item in rebuilt.current_findings.warning_findings)
    assert all("Pending referential-anchor requirement remains" not in item for item in rebuilt.current_risks.risk_flags)


def test_session_state_card_builder_hides_expired_recent_governance_resolution() -> None:
    from src.designer.session_state_persistence import persist_designer_session_state

    builder = DesignerSessionStateCardBuilder()
    base = builder.build(request_text="Undo the last change on node reviewer", artifact=make_working_save())
    carried = base.__class__(**{
        **base.__dict__,
        "notes": {
            **base.notes,
            "control_governance_last_pending_anchor_resolution_status": "cleared_by_anchored_retry",
            "control_governance_last_pending_anchor_resolution_summary": "Pending governance carryover was cleared because the stronger referential anchor was satisfied in the last cycle.",
            "control_governance_last_pending_anchor_resolution_request_text": "Undo the last change on node reviewer",
            "control_governance_last_pending_anchor_resolution_age": 1,
        },
    })
    persisted = persist_designer_session_state(make_working_save(), session_state_card=carried)

    rebuilt = builder.build(request_text="Undo the last change on node reviewer", artifact=persisted)

    assert rebuilt.notes["control_governance_recent_resolution_status"] == "expired_recent_followup"
    assert rebuilt.notes["control_governance_recent_resolution_applied"] is False
    assert all("recently cleared by an explicit anchored retry" not in item for item in rebuilt.current_findings.warning_findings)


def test_session_state_card_builder_hides_recent_cleared_governance_resolution_for_nonreferential_followup() -> None:
    from src.designer.session_state_persistence import persist_designer_session_state

    builder = DesignerSessionStateCardBuilder()
    base = builder.build(request_text="Undo the last change on node reviewer", artifact=make_working_save())
    carried = base.__class__(**{
        **base.__dict__,
        "notes": {
            **base.notes,
            "control_governance_last_pending_anchor_resolution_status": "cleared_by_anchored_retry",
            "control_governance_last_pending_anchor_resolution_summary": "Pending governance carryover was cleared because the stronger referential anchor was satisfied in the last cycle.",
            "control_governance_last_pending_anchor_resolution_request_text": "Undo the last change on node reviewer",
        },
    })
    persisted = persist_designer_session_state(make_working_save(), session_state_card=carried)

    rebuilt = builder.build(request_text="Change provider in node reviewer to Claude", artifact=persisted)

    assert rebuilt.notes["control_governance_recent_resolution_status"] == "hidden_nonreferential"
    assert rebuilt.notes["control_governance_recent_resolution_applied"] is False
    assert all("recently cleared by an explicit anchored retry" not in item for item in rebuilt.current_findings.warning_findings)


def test_session_state_card_builder_surfaces_recent_multi_step_revision_history_for_mutation_request() -> None:
    from src.designer.session_state_persistence import persist_designer_session_state

    builder = DesignerSessionStateCardBuilder()
    base = builder.build(request_text="Change provider", artifact=make_working_save())
    carried = base.__class__(**{
        **base.__dict__,
        "notes": {
            **base.notes,
            "approval_revision_recent_history": [
                {"continuation_modes": ["choose_interpretation"], "selected_interpretation": "Only modify node.reviewer."},
                {"continuation_modes": ["request_revision"], "selected_interpretation": "Only modify node.reviewer."},
            ],
            "approval_revision_recent_history_count": 2,
            "approval_revision_recent_history_summary": "Recent approval/revision continuity includes 2 step(s). Latest continuation mode: request revision. Latest clarified interpretation remains: Only modify node.reviewer.",
        },
    })
    persisted = persist_designer_session_state(make_working_save(), session_state_card=carried)

    rebuilt = builder.build(request_text="Change provider in node reviewer to Claude", artifact=persisted)

    assert rebuilt.notes["approval_revision_recent_history_applied"] is True
    assert any("multi-step revision thread" in item or "Recent approval/revision continuity" in item for item in rebuilt.current_findings.warning_findings)


def test_session_state_card_builder_hides_recent_multi_step_revision_history_for_read_only_request() -> None:
    from src.designer.session_state_persistence import persist_designer_session_state

    builder = DesignerSessionStateCardBuilder()
    base = builder.build(request_text="Change provider", artifact=make_working_save())
    carried = base.__class__(**{
        **base.__dict__,
        "notes": {
            **base.notes,
            "approval_revision_recent_history": [
                {"continuation_modes": ["choose_interpretation"], "selected_interpretation": "Only modify node.reviewer."},
                {"continuation_modes": ["request_revision"], "selected_interpretation": "Only modify node.reviewer."},
            ],
            "approval_revision_recent_history_count": 2,
            "approval_revision_recent_history_summary": "Recent approval/revision continuity includes 2 step(s). Latest continuation mode: request revision. Latest clarified interpretation remains: Only modify node.reviewer.",
        },
    })
    persisted = persist_designer_session_state(make_working_save(), session_state_card=carried)

    rebuilt = builder.build(request_text="Explain what changed in node reviewer", artifact=persisted)

    assert rebuilt.notes["approval_revision_recent_history_status"] == "hidden_read_only"
    assert not any("Recent approval/revision continuity" in item for item in rebuilt.current_findings.warning_findings)




def test_session_state_card_builder_hides_expired_recent_revision_history() -> None:
    from src.designer.session_state_persistence import persist_designer_session_state

    builder = DesignerSessionStateCardBuilder()
    artifact = make_working_save()
    base = builder.build(request_text="Change provider", artifact=artifact)
    carried = base.__class__(**{
        **base.__dict__,
        "notes": {
            **base.notes,
            "approval_revision_recent_history": [
                {"continuation_modes": ["choose_interpretation"], "selected_interpretation": "Only modify node.reviewer."},
                {"continuation_modes": ["request_revision"], "selected_interpretation": "Only modify node.reviewer."},
            ],
            "approval_revision_recent_history_count": 2,
            "approval_revision_recent_history_summary": "Recent approval/revision continuity includes 2 step(s). Latest continuation mode: request revision. Latest clarified interpretation remains: Only modify node.reviewer.",
            "approval_revision_recent_history_age": 2,
        },
    })
    persisted = persist_designer_session_state(artifact, session_state_card=carried)

    rebuilt = builder.build(request_text="Change provider in node reviewer to Claude", artifact=persisted)

    assert rebuilt.notes["approval_revision_recent_history_status"] == "expired_recent_followup"
    assert rebuilt.notes["approval_revision_recent_history_applied"] is False
    assert all("multi-step revision thread" not in item for item in rebuilt.current_findings.warning_findings)

def test_builder_hides_recent_revision_history_when_scope_redirects() -> None:
    from src.designer.session_state_persistence import persist_designer_session_state

    builder = DesignerSessionStateCardBuilder()
    artifact = make_working_save()
    base = builder.build(request_text="Change provider", artifact=artifact)
    carried = base.__class__(**{
        **base.__dict__,
        "notes": {
            **base.notes,
            "approval_revision_recent_history": [
                {"continuation_modes": ["choose_interpretation"], "selected_interpretation": "Only modify node.reviewer."},
                {"continuation_modes": ["request_revision"], "selected_interpretation": "Only modify node.reviewer."},
            ],
            "approval_revision_recent_history_count": 2,
            "approval_revision_recent_history_summary": "Recent approval/revision continuity includes 2 step(s). Latest continuation mode: request revision. Latest clarified interpretation remains: Only modify node.reviewer.",
        },
    })
    persisted = persist_designer_session_state(artifact, session_state_card=carried)

    rebuilt = builder.build(request_text="Instead, change node.final_judge provider.", artifact=persisted)

    assert rebuilt.notes["approval_revision_recent_history_status"] == "redirect_scope"
    assert rebuilt.notes["approval_revision_recent_history_applied"] is False
    assert "approval_revision_recent_history" not in rebuilt.notes
    assert rebuilt.notes["approval_revision_redirect_archived_status"] == "visible_mutation"
    assert "background history" in rebuilt.notes["approval_revision_redirect_archived_summary"]
    assert rebuilt.notes["approval_revision_redirect_archived_applied"] is True
    assert any("background history" in item for item in rebuilt.current_findings.warning_findings)
    assert all("multi-step revision thread" not in item for item in rebuilt.current_findings.warning_findings)


def test_builder_reopens_redirect_archive_into_active_recent_history() -> None:
    from src.designer.session_state_persistence import persist_designer_session_state

    builder = DesignerSessionStateCardBuilder()
    artifact = make_working_save()
    base = builder.build(request_text="Change provider", artifact=artifact)
    carried = base.__class__(**{
        **base.__dict__,
        "notes": {
            **base.notes,
            "approval_revision_redirect_archived_status": "archived_background",
            "approval_revision_redirect_archived_summary": "A previous revision thread was explicitly redirected away from its older scope and now remains only as short-lived background history.",
            "approval_revision_redirect_archived_history": [
                {"continuation_modes": ["choose_interpretation"], "selected_interpretation": "Only modify node.reviewer."},
                {"continuation_modes": ["request_revision"], "selected_interpretation": "Only modify node.reviewer."},
            ],
            "approval_revision_redirect_archived_count": 2,
        },
    })
    persisted = persist_designer_session_state(artifact, session_state_card=carried)

    rebuilt = builder.build(request_text="Change provider in node.reviewer to Claude.", artifact=persisted)

    assert rebuilt.notes["approval_revision_recent_history_status"] == "visible_mutation"
    assert rebuilt.notes["approval_revision_recent_history_applied"] is True
    assert rebuilt.notes["approval_revision_recent_history_count"] == 2
    assert rebuilt.notes["approval_revision_recent_history_reopened_status"] == "restored_from_redirect_archive"
    assert rebuilt.notes["approval_revision_recent_history_reopened_applied"] is True
    assert "reopens that older redirected scope" in rebuilt.notes["approval_revision_recent_history_summary"]
    assert "approval_revision_redirect_archived_status" not in rebuilt.notes
    assert any("restored as active continuity again" in item for item in rebuilt.current_findings.warning_findings)
    assert all("background history" not in item for item in rebuilt.current_findings.warning_findings)
