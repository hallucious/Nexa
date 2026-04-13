from __future__ import annotations

from dataclasses import replace

from src.designer.normalization_context import RequestNormalizationContext
from src.designer.proposal_flow import DesignerProposalFlow
from src.designer.request_normalizer import DesignerRequestNormalizer
from src.designer.session_state_card_builder import DesignerSessionStateCardBuilder
from tests.test_phase4_ui_flow_connection import _ws


class _RecordingBackend:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []

    def generate_semantic_payload(self, *, request_text: str, effective_request_text: str, context_payload: dict):
        self.calls.append((request_text, context_payload))
        return {
            "category": "MODIFY_CIRCUIT",
            "confidence": 0.9,
            "notes": ["llm-session-path"],
        }


def test_request_normalizer_uses_session_keys_from_session_state_card_notes(monkeypatch):
    backend = _RecordingBackend()
    captured = {}

    def _fake_build(preset: str, *, session_key: str | None = None, **kwargs):
        captured["preset"] = preset
        captured["session_key"] = session_key
        return backend

    monkeypatch.setattr(
        "src.designer.semantic_interpreter_factory.build_semantic_backend_with_session",
        _fake_build,
    )

    card = DesignerSessionStateCardBuilder().build(
        request_text="Change provider in node answerer to Claude",
        artifact=None,
        target_scope_mode="existing_circuit",
    )
    card = replace(
        card,
        notes={**card.notes, "provider_session_keys": {"claude": "sk-ant-user-session"}},
    )

    normalizer = DesignerRequestNormalizer(semantic_backend_preset="claude")
    intent = normalizer.normalize(
        "Change provider in node answerer to Claude",
        context=RequestNormalizationContext(
            session_state_card=card,
            working_save_ref="ws-001",
        ),
    )

    assert captured == {"preset": "claude", "session_key": "sk-ant-user-session"}
    assert intent.category == "MODIFY_CIRCUIT"
    assert backend.calls


def test_proposal_flow_threads_session_keys_from_session_state_card_notes(monkeypatch):
    backend = _RecordingBackend()
    captured = {}

    def _fake_build(preset: str, *, session_key: str | None = None, **kwargs):
        captured["preset"] = preset
        captured["session_key"] = session_key
        return backend

    monkeypatch.setattr(
        "src.designer.semantic_interpreter_factory.build_semantic_backend_with_session",
        _fake_build,
    )

    card = DesignerSessionStateCardBuilder().build(
        request_text="Change provider in node answerer to Claude",
        artifact=None,
        target_scope_mode="existing_circuit",
    )
    card = replace(
        card,
        notes={**card.notes, "provider_session_keys": {"claude": "sk-ant-flow-session"}},
    )

    flow = DesignerProposalFlow(normalizer=DesignerRequestNormalizer(semantic_backend_preset="claude"))
    bundle = flow.propose(
        "Change provider in node answerer to Claude",
        working_save_ref="ws-001",
        session_state_card=card,
    )

    assert captured == {"preset": "claude", "session_key": "sk-ant-flow-session"}
    assert bundle.intent.category == "MODIFY_CIRCUIT"
    assert backend.calls


def test_session_state_card_builder_carries_provider_session_keys_from_working_save_metadata():
    artifact = _ws(
        metadata={
            "provider_session_keys": {
                "gpt": "sk-gpt-session",
                "claude": "sk-ant-session",
                "ignored": "   ",
            }
        }
    )
    card = DesignerSessionStateCardBuilder().build(
        request_text="Create a workflow",
        artifact=artifact,
    )

    assert card.notes["provider_session_keys"] == {
        "gpt": "sk-gpt-session",
        "claude": "sk-ant-session",
    }
