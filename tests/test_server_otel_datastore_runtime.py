from __future__ import annotations

import json

from src.server.edge_observability_runtime import REDACTED_VALUE
from src.server.otel_datastore_runtime import (
    OTEL_DATASTORE_EVENT_TYPE,
    build_otel_database_span_attributes,
    build_otel_datastore_exception_event,
    build_otel_datastore_span_event,
    build_otel_redis_span_attributes,
    emit_otel_datastore_span,
)


def test_build_otel_database_span_attributes_redacts_sql_and_parameters() -> None:
    attributes = build_otel_database_span_attributes(
        operation="select",
        db_system="postgresql",
        table_name="run_submission",
        query_label="load_run_submission_by_id",
        statement="select * from run_submission where api_key = 'sk-sql-secret'",
        parameters={"api_key": "sk-parameter-secret", "run_id": "run-001"},
        row_count=1,
        duration_ms=12.7,
        extra={"safe_family": "run_submission", "worker_token": "sk-worker-secret"},
    )

    serialized = json.dumps(attributes, sort_keys=True)
    assert "select * from run_submission" not in serialized
    assert "sk-sql-secret" not in serialized
    assert "sk-parameter-secret" not in serialized
    assert "sk-worker-secret" not in serialized
    assert attributes["span.kind"] == "client"
    assert attributes["db.system"] == "postgresql"
    assert attributes["db.operation"] == "SELECT"
    assert attributes["db.sql.table"] == "run_submission"
    assert attributes["db.query.label"] == "load_run_submission_by_id"
    assert attributes["db.statement"] == REDACTED_VALUE
    assert attributes["db.query.parameters"] == REDACTED_VALUE
    assert attributes["db.rows_affected"] == 1
    assert attributes["db.duration_ms"] == 12
    assert attributes["safe_family"] == "run_submission"
    assert attributes["worker_token"] == REDACTED_VALUE


def test_build_otel_redis_span_attributes_hashes_raw_keys() -> None:
    attributes = build_otel_redis_span_attributes(
        command="get",
        key="nexa:edge:rate-limit:GET:/api/runs:sk-session-secret",
        key_prefix="nexa:edge:rate-limit",
        database_index=0,
        duration_ms=4.9,
        hit=True,
        extra={"authorization": "Bearer sk-header-secret", "safe_count": 2},
    )

    serialized = json.dumps(attributes, sort_keys=True)
    assert "sk-session-secret" not in serialized
    assert "sk-header-secret" not in serialized
    assert "GET:/api/runs" not in serialized
    assert attributes["span.kind"] == "client"
    assert attributes["db.system"] == "redis"
    assert attributes["db.operation"] == "GET"
    assert attributes["db.redis.key_prefix"] == "nexa:edge:rate-limit"
    assert len(attributes["db.redis.key_hash"]) == 16
    assert attributes["db.redis.database_index"] == 0
    assert attributes["db.duration_ms"] == 4
    assert attributes["db.redis.hit"] is True
    assert attributes["authorization"] == REDACTED_VALUE
    assert attributes["safe_count"] == 2


def test_build_otel_datastore_exception_event_redacts_secret_text() -> None:
    event = build_otel_datastore_exception_event(
        exc=RuntimeError("database failed with sk-db-secret"),
        attributes={
            "db.statement": "select secret from table",
            "safe_label": "run_lookup",
        },
    )

    serialized = json.dumps(event, sort_keys=True)
    assert "sk-db-secret" not in serialized
    assert "select secret" not in serialized
    assert event["name"] == "exception"
    assert event["attributes"]["exception.type"] == "RuntimeError"
    assert event["attributes"]["exception.message"] == REDACTED_VALUE
    assert event["attributes"]["db.statement"] == REDACTED_VALUE
    assert event["attributes"]["safe_label"] == "run_lookup"


def test_build_and_emit_otel_datastore_span_event_is_safe() -> None:
    emitted: list[dict] = []
    attributes = build_otel_database_span_attributes(
        operation="insert",
        table_name="file_upload",
        statement="insert into file_upload values ('raw confidential document')",
        parameters={"document_text": "raw confidential document"},
    )
    event = emit_otel_datastore_span(
        emitted.append,
        name="db.query",
        attributes=attributes,
        events=[{"db.statement": "select * from users", "safe": "value"}],
    )

    serialized = json.dumps(event, sort_keys=True)
    assert "raw confidential document" not in serialized
    assert "select * from users" not in serialized
    assert event["event_type"] == OTEL_DATASTORE_EVENT_TYPE
    assert event["name"] == "db.query"
    assert event["attributes"]["db.statement"] == REDACTED_VALUE
    assert event["events"][0]["db.statement"] == REDACTED_VALUE
    assert emitted == [event]


def test_emit_otel_datastore_span_suppresses_writer_failures() -> None:
    def _failing_writer(_event):
        raise RuntimeError("otel writer unavailable")

    event = emit_otel_datastore_span(
        _failing_writer,
        name="redis.command",
        attributes=build_otel_redis_span_attributes(command="set", key="cache:sk-secret"),
    )

    serialized = json.dumps(event, sort_keys=True)
    assert "sk-secret" not in serialized
    assert event["event_type"] == OTEL_DATASTORE_EVENT_TYPE
    assert event["name"] == "redis.command"
