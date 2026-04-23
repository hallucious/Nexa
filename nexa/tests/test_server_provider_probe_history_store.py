from __future__ import annotations

import pytest

from src.server.fastapi_binding_models import FastApiRouteDependencies
from src.server.provider_probe_history_store import InMemoryProviderProbeHistoryStore, bind_probe_history_store


def _row(*, probe_event_id: str, workspace_id: str = "ws-001", occurred_at: str = "2026-04-11T12:00:00+00:00") -> dict[str, object]:
    return {
        "probe_event_id": probe_event_id,
        "workspace_id": workspace_id,
        "provider_key": "openai",
        "provider_family": "openai",
        "display_name": "OpenAI GPT",
        "probe_status": "reachable",
        "connectivity_state": "ok",
        "secret_resolution_status": "resolved",
        "requested_model_ref": "gpt-4.1",
        "effective_model_ref": "gpt-4.1",
        "occurred_at": occurred_at,
        "requested_by_user_id": "user-owner",
        "message": "Probe completed.",
    }


def test_provider_probe_history_store_normalizes_and_sorts_rows() -> None:
    store = InMemoryProviderProbeHistoryStore.from_rows((_row(probe_event_id="probe-1", occurred_at="2026-04-11T12:01:00+00:00"),))
    store.write(_row(probe_event_id="probe-2", occurred_at="2026-04-11T12:02:00+00:00"))

    workspace_rows = store.list_workspace_rows("ws-001")
    assert [row["probe_event_id"] for row in workspace_rows] == ["probe-2", "probe-1"]

    recent_rows = store.list_recent_rows(limit=1)
    assert len(recent_rows) == 1
    assert recent_rows[0]["probe_event_id"] == "probe-2"


def test_provider_probe_history_store_rejects_invalid_rows() -> None:
    store = InMemoryProviderProbeHistoryStore()

    with pytest.raises(ValueError):
        store.write({"workspace_id": "ws-001"})


def test_bind_probe_history_store_wires_read_and_write_dependencies() -> None:
    store = InMemoryProviderProbeHistoryStore.from_rows((_row(probe_event_id="probe-1"),))
    deps = bind_probe_history_store(dependencies=FastApiRouteDependencies(), store=store)

    deps.provider_probe_history_writer(_row(probe_event_id="probe-2", occurred_at="2026-04-11T12:03:00+00:00"))

    workspace_rows = deps.workspace_provider_probe_rows_provider("ws-001")
    assert [row["probe_event_id"] for row in workspace_rows] == ["probe-2", "probe-1"]

    recent_rows = deps.recent_provider_probe_rows_provider()
    assert recent_rows[0]["probe_event_id"] == "probe-2"
