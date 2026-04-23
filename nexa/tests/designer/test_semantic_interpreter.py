from __future__ import annotations

import pytest

from src.designer.normalization_context import RequestNormalizationContext
from src.designer.semantic_interpreter import (
    LLMBackedStructuredSemanticInterpreter,
    LegacyRuleBasedSemanticInterpreter,
)
from src.designer.models.semantic_intent import SemanticActionCandidate


class _Backend:
    def __init__(self, payload=None, *, exc: Exception | None = None):
        self.payload = payload or {}
        self.exc = exc

    def generate_semantic_payload(self, **kwargs):
        if self.exc is not None:
            raise self.exc
        return self.payload


def test_llm_structured_semantic_interpreter_builds_semantic_intent() -> None:
    backend = _Backend(
        {
            "category": "MODIFY_CIRCUIT",
            "confidence_hint": 0.75,
            "notes": ["semantic-path"],
            "action_candidates": [
                {
                    "action_type": "replace_provider",
                    "target_node_descriptor": {
                        "kind": "node",
                        "label_hint": "reviewer",
                        "role_hint": "review",
                    },
                    "provider_descriptor": {
                        "resource_type": "provider",
                        "family": "claude",
                        "raw_reference_text": "Claude",
                    },
                }
            ],
        }
    )
    interpreter = LLMBackedStructuredSemanticInterpreter(backend=backend)

    semantic_intent = interpreter.interpret(
        "Have the reviewer use Claude instead.",
        context=RequestNormalizationContext(working_save_ref="ws-1"),
    )

    assert semantic_intent.category == "MODIFY_CIRCUIT"
    assert semantic_intent.confidence_hint == pytest.approx(0.75)
    assert semantic_intent.notes == ("semantic-path",)
    assert semantic_intent.action_candidates == (
        SemanticActionCandidate(
            action_type="replace_provider",
            target_node_descriptor=semantic_intent.action_candidates[0].target_node_descriptor,
            provider_descriptor=semantic_intent.action_candidates[0].provider_descriptor,
            notes=(),
        ),
    )
    assert semantic_intent.action_candidates[0].target_node_descriptor.label_hint == "reviewer"
    assert semantic_intent.action_candidates[0].provider_descriptor.family == "claude"


def test_llm_structured_semantic_interpreter_rejects_canonical_ids() -> None:
    backend = _Backend(
        {
            "category": "MODIFY_CIRCUIT",
            "action_candidates": [
                {
                    "action_type": "replace_provider",
                    "provider_descriptor": {
                        "resource_type": "provider",
                        "family": "claude",
                        "provider_id": "anthropic:claude-sonnet",
                    },
                }
            ],
        }
    )
    interpreter = LLMBackedStructuredSemanticInterpreter(backend=backend, allow_fallback=False)

    with pytest.raises(ValueError, match="canonical ids"):
        interpreter.interpret(
            "Have the reviewer use Claude instead.",
            context=RequestNormalizationContext(working_save_ref="ws-1"),
        )


def test_llm_structured_semantic_interpreter_falls_back_on_invalid_payload() -> None:
    backend = _Backend(
        {
            "category": "MODIFY_CIRCUIT",
            "action_candidates": [
                {
                    "action_type": "replace_provider",
                    "provider_descriptor": {
                        "resource_type": "provider",
                        "family": "claude",
                        "provider_id": "anthropic:claude-sonnet",
                    },
                }
            ],
        }
    )
    interpreter = LLMBackedStructuredSemanticInterpreter(
        backend=backend,
        fallback_interpreter=LegacyRuleBasedSemanticInterpreter(),
        allow_fallback=True,
    )

    semantic_intent = interpreter.interpret(
        "Have the reviewer use Claude instead.",
        context=RequestNormalizationContext(working_save_ref="ws-1"),
    )

    assert semantic_intent.category == "MODIFY_CIRCUIT"
    assert any(note.startswith("llm_semantic_fallback:") for note in semantic_intent.notes)


def test_llm_structured_semantic_interpreter_surfaces_clarification_fields() -> None:
    backend = _Backend(
        {
            "category": "MODIFY_CIRCUIT",
            "confidence_hint": 0.41,
            "clarification_required": True,
            "clarification_questions": ["Which reviewer node do you mean?"],
            "semantic_ambiguity_notes": ["Two reviewer-like nodes were mentioned in context."],
            "action_candidates": [
                {
                    "action_type": "replace_provider",
                    "target_node_descriptor": {"kind": "node", "role_hint": "review"},
                    "provider_descriptor": {"resource_type": "provider", "family": "claude"},
                }
            ],
        }
    )
    interpreter = LLMBackedStructuredSemanticInterpreter(backend=backend)

    semantic_intent = interpreter.interpret(
        "Have the reviewer use Claude instead.",
        context=RequestNormalizationContext(working_save_ref="ws-1"),
    )

    assert semantic_intent.clarification_required is True
    assert semantic_intent.clarification_questions == ("Which reviewer node do you mean?",)
    assert semantic_intent.semantic_ambiguity_notes == ("Two reviewer-like nodes were mentioned in context.",)
    assert semantic_intent.confidence_hint == pytest.approx(0.41)
