from __future__ import annotations

import pytest

from src.designer.models.designer_session_state_card import (
    AvailableResources,
    ConstraintSet,
    ConversationContext,
    CurrentSelectionState,
    DesignerSessionStateCard,
    ObjectiveSpec,
    ResourceAvailability,
    SessionTargetScope,
    WorkingSaveReality,
)
from src.designer.normalization_context import RequestNormalizationContext
from src.designer.proposal_flow import DesignerProposalFlow
from src.designer.request_normalizer import DesignerRequestNormalizer
from src.designer.semantic_backend_presets import (
    first_available_semantic_backend_preset,
    missing_semantic_backend_preset_env_vars,
    semantic_backend_preset_specs,
    supported_semantic_backend_presets,
)


def _skip_if_live_semantic_runtime_issue(exc: Exception) -> None:
    message = str(exc)
    markers = (
        "semantic_backend_provider_error",
        "semantic_backend_invalid_json_payload",
        "SAFE_MODE failed",
        "HTTPError",
        "invalid format/schema",
    )
    if any(marker in message for marker in markers):
        pytest.skip(f"live semantic runtime issue: {message}")


def _semantic_card() -> DesignerSessionStateCard:
    return DesignerSessionStateCard(
        card_version="0.1",
        session_id="sess-live-semantic",
        storage_role="working_save",
        current_working_save=WorkingSaveReality(
            mode="existing_draft",
            savefile_ref="ws-live-semantic-1",
            node_list=("node.answerer", "node.reviewer", "node.final_judge"),
            edge_list=("node.answerer -> node.reviewer", "node.reviewer -> node.final_judge"),
            prompt_refs=("prompt.default_review", "prompt.strict_review"),
            provider_refs=("openai:gpt-4o-mini", "anthropic:claude-sonnet"),
            plugin_refs=("web.search",),
        ),
        current_selection=CurrentSelectionState(selection_mode="none"),
        target_scope=SessionTargetScope(mode="existing_circuit", touch_budget="bounded"),
        available_resources=AvailableResources(
            prompts=(
                ResourceAvailability(id="prompt.default_review"),
                ResourceAvailability(id="prompt.strict_review"),
            ),
            providers=(
                ResourceAvailability(id="openai:gpt-4o-mini"),
                ResourceAvailability(id="anthropic:claude-sonnet"),
            ),
            plugins=(
                ResourceAvailability(id="web.search"),
            ),
        ),
        objective=ObjectiveSpec(primary_goal="Change reviewer provider"),
        constraints=ConstraintSet(),
        conversation_context=ConversationContext(user_request_text="Have the reviewer use Claude instead."),
    )


def _require_preset_credentials(preset: str) -> None:
    missing = missing_semantic_backend_preset_env_vars(preset)
    if missing:
        joined = ", ".join(missing)
        pytest.skip(f"live semantic provider preset {preset!r} requires one of: {joined}")


@pytest.mark.integration
@pytest.mark.parametrize("preset", supported_semantic_backend_presets())
def test_live_semantic_backend_preset_normalizer_smoke(preset: str) -> None:
    _require_preset_credentials(preset)
    normalizer = DesignerRequestNormalizer(
        semantic_backend_preset=preset,
        semantic_backend_preset_use_env=True,
        use_llm_semantic_interpreter=True,
        llm_backend_required=True,
    )

    try:
        intent = normalizer.normalize(
            "Modify the existing circuit. Change the reviewer provider to Claude. Do exactly one provider change.",
            context=RequestNormalizationContext(
                working_save_ref="ws-live-semantic-1",
                session_state_card=_semantic_card(),
            ),
        )
    except (RuntimeError, ValueError) as exc:
        _skip_if_live_semantic_runtime_issue(exc)
        raise

    assert intent.category == "MODIFY_CIRCUIT"
    assert [action.action_type for action in intent.proposed_actions] == ["replace_provider"]
    assert intent.proposed_actions[0].target_ref == "node.reviewer"
    assert intent.proposed_actions[0].parameters["provider_id"] == "anthropic:claude-sonnet"


@pytest.mark.integration
def test_live_semantic_backend_preset_proposal_flow_smoke() -> None:
    preset = first_available_semantic_backend_preset()
    if preset is None:
        pytest.skip("live semantic provider smoke requires at least one configured preset credential")

    normalizer = DesignerRequestNormalizer(
        semantic_backend_preset=preset,
        semantic_backend_preset_use_env=True,
        use_llm_semantic_interpreter=True,
        llm_backend_required=True,
    )
    flow = DesignerProposalFlow(normalizer=normalizer)

    try:
        bundle = flow.propose(
            "Modify the existing circuit. Change the reviewer provider to Claude. Do exactly one provider change.",
            working_save_ref="ws-live-semantic-1",
            session_state_card=_semantic_card(),
        )
    except (RuntimeError, ValueError) as exc:
        _skip_if_live_semantic_runtime_issue(exc)
        raise

    assert bundle.intent.category == "MODIFY_CIRCUIT"
    assert [action.action_type for action in bundle.intent.proposed_actions] == ["replace_provider"]
    assert [op.op_type for op in bundle.patch.operations] == ["set_node_provider"]
    assert bundle.patch.operations[0].target_ref == "node.reviewer"
    assert bundle.patch.operations[0].payload["provider_id"] == "anthropic:claude-sonnet"


@pytest.mark.integration
def test_live_semantic_backend_preset_metadata_smoke() -> None:
    preset = first_available_semantic_backend_preset()
    if preset is None:
        pytest.skip("live semantic provider smoke requires at least one configured preset credential")

    spec = semantic_backend_preset_specs()[preset]
    normalizer = DesignerRequestNormalizer(
        semantic_backend_preset=preset,
        semantic_backend_preset_use_env=True,
        use_llm_semantic_interpreter=True,
        llm_backend_required=True,
    )
    try:
        intent = normalizer.normalize(
            "Modify the existing circuit. Change the reviewer provider to Claude. Do exactly one provider change.",
            context=RequestNormalizationContext(
                working_save_ref="ws-live-semantic-1",
                session_state_card=_semantic_card(),
            ),
        )
    except (RuntimeError, ValueError) as exc:
        _skip_if_live_semantic_runtime_issue(exc)
        raise

    assert intent.intent_id.startswith("intent-")
    assert spec.provider_name.startswith("designer.semantic.")
    assert not intent.requires_user_confirmation
