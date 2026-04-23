from __future__ import annotations

import pytest

from src.server.fastapi_binding_models import FastApiRouteDependencies
from src.server.provider_binding_store import InMemoryProviderBindingStore, bind_provider_binding_store


def _row(**overrides):
    row = {
        "binding_id": "binding-001",
        "workspace_id": "ws-001",
        "provider_key": "openai",
        "provider_family": "openai",
        "display_name": "OpenAI GPT",
        "credential_source": "managed",
        "secret_ref": "secret://ws-001/openai",
        "secret_version_ref": "v1",
        "enabled": True,
        "default_model_ref": "gpt-4.1",
        "allowed_model_refs": ("gpt-4.1",),
        "created_at": "2026-04-11T12:00:00+00:00",
        "updated_at": "2026-04-11T12:05:00+00:00",
        "last_rotated_at": "2026-04-11T12:05:00+00:00",
        "updated_by_user_id": "user-owner",
    }
    row.update(overrides)
    return row


def test_provider_binding_store_normalizes_and_reads_rows() -> None:
    store = InMemoryProviderBindingStore.from_rows((
        _row(provider_key="OpenAI"),
        _row(
            binding_id="binding-002",
            provider_key="anthropic",
            provider_family="anthropic",
            display_name="Anthropic Claude",
            updated_at="2026-04-11T12:06:00+00:00",
        ),
    ))

    rows = store.list_workspace_rows("ws-001")
    assert [row["provider_key"] for row in rows] == ["anthropic", "openai"]
    all_rows = store.list_all_rows()
    assert [row["provider_key"] for row in all_rows] == ["anthropic", "openai"]
    assert store.get_workspace_provider_row("ws-001", "OPENAI")["provider_key"] == "openai"


def test_provider_binding_store_rejects_invalid_rows() -> None:
    store = InMemoryProviderBindingStore()
    with pytest.raises(ValueError):
        store.write({"workspace_id": "ws-001", "provider_key": "openai"})


def test_bind_provider_binding_store_wires_read_and_write_dependencies() -> None:
    store = InMemoryProviderBindingStore()
    deps = bind_provider_binding_store(dependencies=FastApiRouteDependencies(), store=store)
    deps.provider_binding_writer(
        _row(
            binding_id="binding-003",
            provider_key="gemini",
            provider_family="google",
            display_name="Google Gemini",
        )
    )

    listed = deps.workspace_provider_binding_rows_provider("ws-001")
    assert listed[0]["binding_id"] == "binding-003"
    selected = deps.workspace_provider_binding_row_provider("ws-001", "gemini")
    assert selected is not None
    assert selected["provider_key"] == "gemini"
    recent_rows = deps.recent_provider_binding_rows_provider()
    assert recent_rows[0]["binding_id"] == "binding-003"
