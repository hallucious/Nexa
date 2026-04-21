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
from src.designer.normalization_context import RequestNormalizationContext
from src.designer.proposal_flow import DesignerProposalFlow
from src.designer.request_normalizer import DesignerRequestNormalizer
from src.designer.semantic_backend_presets import (
    available_semantic_backend_presets,
    build_live_semantic_provider_from_preset,
    build_semantic_backend_from_preset,
    first_available_semantic_backend_preset,
    missing_semantic_backend_preset_env_vars,
    normalize_semantic_backend_preset,
    semantic_backend_preset_is_available,
)
from src.providers.provider_adapter_contract import ProviderMetrics, ProviderResult
import src.providers.claude_provider as claude_provider_module


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
        context=RequestNormalizationContext(
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



def test_semantic_backend_preset_supports_mixed_semantic_outputs_e2e() -> None:
    provider = _GenerateTextProvider(
        text=json.dumps(
            {
                "category": "MODIFY_CIRCUIT",
                "confidence_hint": 0.79,
                "action_candidates": [
                    {
                        "action_type": "replace_provider",
                        "target_node_descriptor": {"kind": "node", "label_hint": "reviewer", "role_hint": "review"},
                        "provider_descriptor": {"resource_type": "provider", "family": "claude", "raw_reference_text": "Claude"},
                    },
                    {
                        "action_type": "attach_plugin",
                        "target_node_descriptor": {"kind": "node", "label_hint": "reviewer"},
                        "plugin_descriptor": {"resource_type": "plugin", "family": "search", "capability_hint": "web search"},
                    },
                    {
                        "action_type": "set_prompt",
                        "target_node_descriptor": {"kind": "node", "label_hint": "reviewer"},
                        "prompt_descriptor": {"resource_type": "prompt", "label_hint": "strict review", "raw_reference_text": "strict review prompt"},
                    },
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
    flow = DesignerProposalFlow(normalizer=normalizer)

    bundle = flow.propose(
        "Have the reviewer use Claude, add web search, and use the strict review prompt.",
        working_save_ref="ws-semantic-preset-1",
        session_state_card=_semantic_card(),
    )

    assert [action.action_type for action in bundle.intent.proposed_actions] == [
        "replace_provider",
        "attach_plugin",
        "set_prompt",
    ]
    assert [op.op_type for op in bundle.patch.operations] == [
        "set_node_provider",
        "attach_node_plugin",
        "set_node_prompt",
    ]
    assert bundle.patch.operations[0].target_ref == "node.reviewer"
    assert bundle.patch.operations[1].payload["plugin_id"] == "web.search"
    assert bundle.patch.operations[2].payload["prompt_id"] == "prompt.strict_review"



def test_semantic_backend_preset_surfaces_clarification_loop_state() -> None:
    provider = _GenerateTextProvider(
        text=json.dumps(
            {
                "category": "MODIFY_CIRCUIT",
                "confidence_hint": 0.31,
                "clarification_required": True,
                "clarification_questions": ["Do you mean the reviewer or the final judge?"],
                "semantic_ambiguity_notes": ["Multiple review-related nodes remain plausible."],
                "action_candidates": [],
            }
        )
    )
    card = _semantic_card()
    card = DesignerSessionStateCard(
        card_version=card.card_version,
        session_id="sess-semantic-preset-loop",
        storage_role=card.storage_role,
        current_working_save=card.current_working_save,
        current_selection=card.current_selection,
        target_scope=card.target_scope,
        available_resources=card.available_resources,
        objective=card.objective,
        constraints=card.constraints,
        current_findings=card.current_findings,
        current_risks=card.current_risks,
        revision_state=card.revision_state.__class__(
            revision_index=1,
            user_corrections=("I mean the middle review step.",),
        ),
        approval_state=card.approval_state,
        conversation_context=ConversationContext(
            user_request_text="Use Claude on the reviewer.",
            clarified_interpretation="Use Claude on the middle reviewer step.",
        ),
        output_contract=card.output_contract,
        forbidden_authority=card.forbidden_authority,
        notes=card.notes,
    )
    normalizer = DesignerRequestNormalizer(
        semantic_backend_preset="claude",
        semantic_backend_preset_providers={"claude": provider},
        use_llm_semantic_interpreter=True,
        llm_backend_required=True,
    )

    intent = normalizer.normalize(
        "Use Claude on the reviewer.",
        context=RequestNormalizationContext(
            working_save_ref="ws-semantic-preset-1",
            session_state_card=card,
        ),
    )

    assert any(flag.type == "semantic_interpretation_requires_clarification" for flag in intent.ambiguity_flags)
    assert any(flag.type == "semantic_clarification_loop_persisting" for flag in intent.ambiguity_flags)
    assert intent.requires_user_confirmation is True



def test_semantic_backend_preset_surfaces_full_recovery_after_prior_clarification() -> None:
    provider = _GenerateTextProvider(
        text=json.dumps(
            {
                "category": "MODIFY_CIRCUIT",
                "confidence_hint": 0.87,
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
    card = _semantic_card()
    card = DesignerSessionStateCard(
        card_version=card.card_version,
        session_id="sess-semantic-preset-recovery",
        storage_role=card.storage_role,
        current_working_save=card.current_working_save,
        current_selection=card.current_selection,
        target_scope=card.target_scope,
        available_resources=card.available_resources,
        objective=card.objective,
        constraints=card.constraints,
        current_findings=card.current_findings,
        current_risks=card.current_risks,
        revision_state=card.revision_state,
        approval_state=card.approval_state,
        conversation_context=ConversationContext(
            user_request_text="Use Claude on the reviewer.",
            clarified_interpretation="The reviewer means node.reviewer, not the final judge.",
        ),
        output_contract=card.output_contract,
        forbidden_authority=card.forbidden_authority,
        notes=card.notes,
    )
    normalizer = DesignerRequestNormalizer(
        semantic_backend_preset="anthropic",
        semantic_backend_preset_providers={"anthropic": provider},
        use_llm_semantic_interpreter=True,
        llm_backend_required=True,
    )

    intent = normalizer.normalize(
        "Use Claude on the reviewer.",
        context=RequestNormalizationContext(
            working_save_ref="ws-semantic-preset-1",
            session_state_card=card,
        ),
    )

    assert [action.action_type for action in intent.proposed_actions] == ["replace_provider"]
    assert not any(flag.type == "semantic_interpretation_requires_clarification" for flag in intent.ambiguity_flags)
    assert "A prior clarification resolved the request into concrete grounded actions." in intent.explanation


def test_build_live_semantic_provider_from_preset_uses_provider_from_env(monkeypatch) -> None:
    provider = _GenerateTextProvider()

    def _fake_from_env(cls):
        return provider

    monkeypatch.setattr(claude_provider_module.ClaudeProvider, "from_env", classmethod(_fake_from_env))
    assert build_live_semantic_provider_from_preset("anthropic") is provider


def test_build_semantic_backend_from_preset_supports_env_provider(monkeypatch) -> None:
    provider = _GenerateTextProvider()

    def _fake_from_env(cls):
        return provider

    monkeypatch.setattr(claude_provider_module.ClaudeProvider, "from_env", classmethod(_fake_from_env))
    backend = build_semantic_backend_from_preset("claude", use_env_provider=True)
    assert backend.provider is provider
    assert backend.provider_name == "designer.semantic.claude"


def test_request_normalizer_accepts_env_backed_semantic_backend_preset(monkeypatch) -> None:
    provider = _GenerateTextProvider(
        text=json.dumps(
            {
                "category": "MODIFY_CIRCUIT",
                "confidence_hint": 0.8,
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

    def _fake_from_env(cls):
        return provider

    monkeypatch.setattr(claude_provider_module.ClaudeProvider, "from_env", classmethod(_fake_from_env))
    normalizer = DesignerRequestNormalizer(
        semantic_backend_preset="claude",
        semantic_backend_preset_use_env=True,
        use_llm_semantic_interpreter=True,
        llm_backend_required=True,
    )

    intent = normalizer.normalize(
        "Have the reviewer use Claude instead.",
        context=RequestNormalizationContext(
            working_save_ref="ws-semantic-preset-1",
            session_state_card=_semantic_card(),
        ),
    )

    assert [action.action_type for action in intent.proposed_actions] == ["replace_provider"]
    assert intent.proposed_actions[0].parameters["provider_id"] == "anthropic:claude-sonnet"


def test_missing_semantic_backend_preset_env_vars_reports_missing_alias_group() -> None:
    assert missing_semantic_backend_preset_env_vars(
        "gemini",
        env={},
    ) == ("GEMINI_API_KEY", "GOOGLE_API_KEY")


def test_semantic_backend_preset_is_available_accepts_alias_env_group() -> None:
    assert semantic_backend_preset_is_available(
        "gemini",
        env={"GOOGLE_API_KEY": "x"},
    ) is True


def test_first_available_semantic_backend_preset_returns_first_available() -> None:
    assert first_available_semantic_backend_preset(
        env={"PERPLEXITY_API_KEY": "pplx-key"},
    ) == "perplexity"
