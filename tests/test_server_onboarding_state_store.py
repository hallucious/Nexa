from __future__ import annotations

import pytest

from src.server.fastapi_binding_models import FastApiRouteDependencies
from src.server.onboarding_state_store import InMemoryOnboardingStateStore, bind_onboarding_state_store


def test_onboarding_state_store_write_and_list_rows() -> None:
    store = InMemoryOnboardingStateStore()
    store.write(
        {
            "onboarding_state_id": "onboard-100",
            "user_id": "user-owner",
            "workspace_id": "ws-100",
            "first_success_achieved": True,
            "advanced_surfaces_unlocked": True,
            "dismissed_guidance_state": {"designer": True},
            "current_step": "workspace-ready",
            "updated_at": "2026-04-12T10:10:00+00:00",
        }
    )

    rows = store.list_rows()
    assert rows[0]["onboarding_state_id"] == "onboard-100"
    assert rows[0]["workspace_id"] == "ws-100"


def test_onboarding_state_store_rejects_invalid_row() -> None:
    store = InMemoryOnboardingStateStore()
    with pytest.raises(ValueError):
        store.write({"user_id": "user-owner", "updated_at": "2026-04-12T10:10:00+00:00"})


def test_bind_onboarding_state_store_wires_rows_and_writer() -> None:
    deps = bind_onboarding_state_store(
        dependencies=FastApiRouteDependencies(),
        store=InMemoryOnboardingStateStore(),
    )
    deps.onboarding_state_writer(
        {
            "onboarding_state_id": "onboard-200",
            "user_id": "user-owner",
            "workspace_id": None,
            "first_success_achieved": False,
            "advanced_surfaces_unlocked": False,
            "dismissed_guidance_state": {},
            "current_step": "start",
            "updated_at": "2026-04-12T10:20:00+00:00",
        }
    )
    assert deps.onboarding_rows_provider()[0]["onboarding_state_id"] == "onboard-200"
