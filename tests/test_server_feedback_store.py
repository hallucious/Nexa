from __future__ import annotations

import pytest

from src.server.fastapi_binding_models import FastApiRouteDependencies
from src.server.feedback_store import InMemoryFeedbackStore, bind_feedback_store


def test_feedback_store_writes_and_lists_rows_in_reverse_chronological_order() -> None:
    store = InMemoryFeedbackStore()
    store.write({
        "feedback_id": "fb-001",
        "user_id": "user-owner",
        "workspace_id": "ws-001",
        "workspace_title": "Primary Workflow",
        "category": "friction_note",
        "surface": "circuit_library",
        "message": "The next action was hard to find.",
        "status": "received",
        "created_at": "2026-04-14T08:00:00+00:00",
    })
    store.write({
        "feedback_id": "fb-002",
        "user_id": "user-owner",
        "workspace_id": "ws-001",
        "workspace_title": "Primary Workflow",
        "category": "bug_report",
        "surface": "result_history",
        "message": "This screen failed unexpectedly.",
        "run_id": "run-001",
        "status": "received",
        "created_at": "2026-04-14T08:05:00+00:00",
    })

    rows = store.list_rows()
    assert rows[0]["feedback_id"] == "fb-002"
    assert rows[1]["feedback_id"] == "fb-001"


def test_feedback_store_rejects_invalid_category() -> None:
    store = InMemoryFeedbackStore()
    with pytest.raises(ValueError):
        store.write({
            "feedback_id": "fb-003",
            "user_id": "user-owner",
            "workspace_id": "ws-001",
            "workspace_title": "Primary Workflow",
            "category": "not-valid",
            "surface": "result_history",
            "message": "Invalid category",
            "status": "received",
            "created_at": "2026-04-14T08:00:00+00:00",
        })


def test_bind_feedback_store_updates_dependencies() -> None:
    deps = bind_feedback_store(dependencies=FastApiRouteDependencies(), store=InMemoryFeedbackStore())
    assert deps.feedback_rows_provider() == ()
