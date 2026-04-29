from __future__ import annotations

from typing import Any, Mapping

import pytest

from src.server.gdpr_deletion_adapters import GdprPostgresDeletionAdapter
from src.server.gdpr_deletion_schema import GDPR_USER_DELETION_AUDIT_TABLE


class _FakeResult:
    def __init__(self, rowcount: int = 1) -> None:
        self.rowcount = rowcount


class _FakeConnection:
    def __init__(self) -> None:
        self.calls: list[tuple[str, Mapping[str, Any]]] = []

    def execute(self, sql: Any, params: Mapping[str, Any]) -> _FakeResult:
        self.calls.append((str(sql), dict(params)))
        return _FakeResult()

    def __enter__(self) -> "_FakeConnection":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:  # noqa: ANN001
        return None


class _FakeEngine:
    def __init__(self) -> None:
        self.connection = _FakeConnection()

    def begin(self) -> _FakeConnection:
        return self.connection


def test_postgres_audit_writer_populates_append_only_audit_identity(monkeypatch: pytest.MonkeyPatch) -> None:
    from src.server import gdpr_deletion_adapters

    monkeypatch.setattr(gdpr_deletion_adapters, "text", lambda sql: sql)
    engine = _FakeEngine()
    adapter = GdprPostgresDeletionAdapter(engine=engine)

    written = adapter.write_audit(
        {
            "deletion_request_id": "gdpr-001",
            "user_ref": "user_ref_001",
            "requested_by_ref": "actor_ref_001",
            "status": "completed",
            "reason": "user_requested_deletion",
            "api_key": "sk-audit-secret",
        }
    )

    assert written["audit_event_id"].startswith("uda_")
    assert written["recorded_at"]
    assert written["event_type"] == "user_deletion_audit"
    assert written["api_key"] == "<redacted>"
    sql, params = engine.connection.calls[0]
    assert f"INSERT INTO {GDPR_USER_DELETION_AUDIT_TABLE}" in sql
    assert "audit_event_id" in sql
    assert params["audit_event_id"] == written["audit_event_id"]
    assert params["deletion_request_id"] == "gdpr-001"
    assert params["audit_payload"]["api_key"] == "<redacted>"


def test_postgres_audit_writer_supports_denied_route_audit_without_deletion_request(monkeypatch: pytest.MonkeyPatch) -> None:
    from src.server import gdpr_deletion_adapters

    monkeypatch.setattr(gdpr_deletion_adapters, "text", lambda sql: sql)
    engine = _FakeEngine()
    adapter = GdprPostgresDeletionAdapter(engine=engine)

    written = adapter.write_audit(
        {
            "event_type": "gdpr_deletion_denied",
            "actor_ref": "actor_ref_001",
            "reason": "gdpr_deletion_permission_denied",
            "source_lookup_attempted": False,
            "deletion_attempted": False,
        }
    )

    sql, params = engine.connection.calls[0]
    assert f"INSERT INTO {GDPR_USER_DELETION_AUDIT_TABLE}" in sql
    assert written["audit_event_id"].startswith("uda_")
    assert written["event_type"] == "gdpr_deletion_denied"
    assert params["deletion_request_id"] == ""
    assert params["requested_by_ref"] == "actor_ref_001"
    assert params["event_type"] == "gdpr_deletion_denied"
    assert params["audit_payload"]["source_lookup_attempted"] is False
    assert params["audit_payload"]["deletion_attempted"] is False
