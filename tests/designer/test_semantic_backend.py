from __future__ import annotations

import json

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
from src.designer.request_normalizer import DesignerRequestNormalizer
from src.designer.semantic_backend import GenerateTextSemanticBackend
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
            metrics=ProviderMetrics(latency_ms=7),
        )


def _semantic_card() -> DesignerSessionStateCard:
    return DesignerSessionStateCard(
        card_version="0.1",
        session_id="sess-semantic-backend",
        storage_role="working_save",
        current_working_save=WorkingSaveReality(
            mode="existing_draft",
            savefile_ref="ws-semantic-1",
            node_list=("node.answerer", "node.reviewer", "node.final_judge"),
            provider_refs=("openai:gpt-4o-mini", "anthropic:claude-sonnet"),
            plugin_refs=("web.search",),
            prompt_refs=("prompt.strict_review",),
        ),
        current_selection=CurrentSelectionState(selection_mode="none"),
        target_scope=SessionTargetScope(mode="existing_circuit", touch_budget="bounded"),
        available_resources=AvailableResources(
            providers=(
                ResourceAvailability(id="openai:gpt-4o-mini"),
                ResourceAvailability(id="anthropic:claude-sonnet"),
            ),
            plugins=(ResourceAvailability(id="web.search"),),
            prompts=(ResourceAvailability(id="prompt.strict_review"),),
        ),
        objective=ObjectiveSpec(primary_goal="Upgrade reviewer node"),
        constraints=ConstraintSet(),
        conversation_context=ConversationContext(user_request_text="Have the reviewer use Claude and add search."),
    )


def test_generate_text_semantic_backend_parses_json_text_payload() -> None:
    provider = _GenerateTextProvider(
        text=json.dumps(
            {
                "category": "MODIFY_CIRCUIT",
                "confidence_hint": 0.73,
                "action_candidates": [
                    {
                        "action_type": "replace_provider",
                        "target_node_descriptor": {"kind": "node", "label_hint": "reviewer"},
                        "provider_descriptor": {"resource_type": "provider", "family": "claude"},
                    }
                ],
            }
        )
    )
    backend = GenerateTextSemanticBackend(provider=provider, provider_name="fake.semantic")

    payload = backend.generate_semantic_payload(
        request_text="Have the reviewer use Claude instead.",
        effective_request_text="Have the reviewer use Claude instead.",
        context_payload={"available_resources": {"providers": ["anthropic:claude-sonnet"]}},
    )

    assert payload["category"] == "MODIFY_CIRCUIT"
    assert provider.calls
    assert "Never output canonical ids" in provider.calls[0]["prompt"]


def test_generate_text_semantic_backend_parses_fenced_json_payload() -> None:
    provider = _GenerateTextProvider(
        text="""Here is the result:
```json
{
  "category": "MODIFY_CIRCUIT",
  "action_candidates": []
}
```"""
    )
    backend = GenerateTextSemanticBackend(provider=provider, provider_name="fake.semantic")

    payload = backend.generate_semantic_payload(
        request_text="Interpret this.",
        effective_request_text="Interpret this.",
        context_payload={},
    )

    assert payload["category"] == "MODIFY_CIRCUIT"


def test_request_normalizer_uses_generate_text_semantic_backend_end_to_end() -> None:
    provider = _GenerateTextProvider(
        text=json.dumps(
            {
                "category": "MODIFY_CIRCUIT",
                "confidence_hint": 0.81,
                "action_candidates": [
                    {
                        "action_type": "replace_provider",
                        "target_node_descriptor": {"kind": "node", "label_hint": "reviewer", "role_hint": "review"},
                        "provider_descriptor": {"resource_type": "provider", "family": "claude", "raw_reference_text": "Claude"},
                    },
                    {
                        "action_type": "attach_plugin",
                        "target_node_descriptor": {"kind": "node", "label_hint": "reviewer"},
                        "plugin_descriptor": {"resource_type": "plugin", "capability_hint": "search tool", "raw_reference_text": "search"},
                    },
                ],
            }
        )
    )
    backend = GenerateTextSemanticBackend(provider=provider, provider_name="fake.semantic")
    normalizer = DesignerRequestNormalizer(
        semantic_backend=backend,
        use_llm_semantic_interpreter=True,
        llm_backend_required=True,
    )

    intent = normalizer.normalize(
        "Have the reviewer use Claude and add search.",
        context=RequestNormalizationContext(working_save_ref="ws-semantic-1", session_state_card=_semantic_card()),
    )

    action_types = {action.action_type for action in intent.proposed_actions}
    assert action_types == {"replace_provider", "attach_plugin"}
    assert all(action.target_ref == "node.reviewer" for action in intent.proposed_actions)
    provider_action = next(action for action in intent.proposed_actions if action.action_type == "replace_provider")
    plugin_action = next(action for action in intent.proposed_actions if action.action_type == "attach_plugin")
    assert provider_action.parameters["provider_id"] == "anthropic:claude-sonnet"
    assert plugin_action.parameters["plugin_id"] == "web.search"


def test_generate_text_semantic_backend_raises_on_provider_error() -> None:
    provider = _GenerateTextProvider(text=None, error="backend unavailable")
    backend = GenerateTextSemanticBackend(provider=provider, provider_name="fake.semantic")

    with pytest.raises(RuntimeError, match="semantic_backend_provider_error"):
        backend.generate_semantic_payload(
            request_text="Interpret this.",
            effective_request_text="Interpret this.",
            context_payload={},
        )
