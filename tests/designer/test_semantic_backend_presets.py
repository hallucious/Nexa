from __future__ import annotations

import json

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
from src.designer.proposal_flow import DesignerProposalFlow
from src.designer.request_normalizer import DesignerRequestNormalizer
from src.designer.semantic_backend_presets import (
    available_semantic_backend_presets,
    build_semantic_backend_from_preset,
    normalize_semantic_backend_preset,
)
from src.providers.provider_contract import ProviderMetrics, ProviderResult


class _GenerateTextProvider:
    def __init__(self, *, text: str | None = None, raw: dict | None = None, error: str | None = None):
        self.text = text
        self.raw = raw or {}
        self.error = error
        self.calls: list[dict] = []

    def generate_text(self, **kwargs):
        self.calls.append(kwargs)
        return ProviderResult(
            success=self.error is None,
            text=self.text,
            raw=dict(self.raw),
            error=self.error,
            reason_code=None if self.error is None else "AI.provider_error",
            metrics=ProviderMetrics(latency_ms=11),
        )


def _semantic_card() -> DesignerSessionStateCard:
    return DesignerSessionStateCard(
        card_version="0.1",
        session_id="sess-semantic-preset",
        storage_role="working_save",
        current_working_save=WorkingSaveReality(
            mode="existing_draft",
            savefile_ref="ws-semantic-preset-1",
            node_list=("node.answerer", "node.reviewer", "node.final_judge"),
            provider_refs=("openai:gpt-4o-mini", "anthropic:claude-sonnet"),
        ),
        current_selection=CurrentSelectionState(selection_mode="none"),
        target_scope=SessionTargetScope(mode="existing_circuit", touch_budget="bounded"),
        available_resources=AvailableResources(
            providers=(
                ResourceAvailability(id="openai:gpt-4o-mini"),
                ResourceAvailability(id="anthropic:claude-sonnet"),
            )
        ),
        objective=ObjectiveSpec(primary_goal="Change reviewer provider"),
        constraints=ConstraintSet(),
        conversation_context=ConversationContext(user_request_text="Have the reviewer use Claude instead."),
    )


def test_normalize_semantic_backend_preset_supports_aliases() -> None:
    assert normalize_semantic_backend_preset("openai") == "gpt"
    assert normalize_semantic_backend_preset("anthropic") == "claude"
    assert normalize_semantic_backend_preset("pplx") == "perplexity"


def test_available_semantic_backend_presets_detects_env_keys() -> None:
    available = available_semantic_backend_presets(
        env={
            "OPENAI_API_KEY": "sk-test",
            "ANTHROPIC_API_KEY": "ak-test",
            "UNRELATED": "1",
        }
    )
    assert available == ("gpt", "claude")


def test_build_semantic_backend_from_preset_uses_alias_mapping() -> None:
    provider = _GenerateTextProvider(text=json.dumps({"category": "MODIFY_CIRCUIT", "action_candidates": []}))
    backend = build_semantic_backend_from_preset("anthropic", providers={"claude": provider})
    assert backend.provider is provider
    assert backend.provider_name == "designer.semantic.claude"


def test_request_normalizer_accepts_semantic_backend_preset() -> None:
    provider = _GenerateTextProvider(
        text=json.dumps(
            {
                "category": "MODIFY_CIRCUIT",
                "confidence_hint": 0.82,
                "action_candidates": [
                    {
                        "action_type": "replace_provider",
                        "target_node_descriptor": {"kind": "node", "label_hint": "reviewer", "role_hint": "review"},
                        "provider_descriptor": {"resource_type": "provider", "family": "claude", "raw_reference_text": "Claude"},
                    }
                ],
            }
        )
    )
    normalizer = DesignerRequestNormalizer(
        semantic_backend_preset="anthropic",
        semantic_backend_preset_providers={"claude": provider},
        use_llm_semantic_interpreter=True,
        llm_backend_required=True,
    )

    intent = normalizer.normalize(
        "Have the reviewer use Claude instead.",
        context=__import__('src.designer.normalization_context', fromlist=['RequestNormalizationContext']).RequestNormalizationContext(
            working_save_ref="ws-semantic-preset-1",
            session_state_card=_semantic_card(),
        ),
    )

    assert [action.action_type for action in intent.proposed_actions] == ["replace_provider"]
    assert intent.proposed_actions[0].target_ref == "node.reviewer"
    assert intent.proposed_actions[0].parameters["provider_id"] == "anthropic:claude-sonnet"


def test_semantic_backend_preset_proposal_flow_e2e() -> None:
    provider = _GenerateTextProvider(
        text=json.dumps(
            {
                "category": "MODIFY_CIRCUIT",
                "confidence_hint": 0.84,
                "action_candidates": [
                    {
                        "action_type": "replace_provider",
                        "target_node_descriptor": {"kind": "node", "label_hint": "reviewer", "role_hint": "review"},
                        "provider_descriptor": {"resource_type": "provider", "family": "claude", "raw_reference_text": "Claude"},
                    }
                ],
            }
        )
    )
    normalizer = DesignerRequestNormalizer(
        semantic_backend_preset="anthropic",
        semantic_backend_preset_providers={"anthropic": provider},
        use_llm_semantic_interpreter=True,
        llm_backend_required=True,
    )
    flow = DesignerProposalFlow(normalizer=normalizer)

    bundle = flow.propose(
        "Have the reviewer use Claude instead.",
        working_save_ref="ws-semantic-preset-1",
        session_state_card=_semantic_card(),
    )

    assert bundle.intent.proposed_actions[0].action_type == "replace_provider"
    assert bundle.patch.operations[0].op_type == "set_node_provider"
    assert bundle.patch.operations[0].target_ref == "node.reviewer"
