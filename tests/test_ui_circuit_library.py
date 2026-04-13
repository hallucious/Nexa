from __future__ import annotations

from src.server.workspace_onboarding_models import (
    ProductActivityContinuitySummary,
    ProductWorkspaceLinks,
    ProductWorkspaceListResponse,
    ProductWorkspaceSummaryView,
)
from src.ui.circuit_library import read_circuit_library_view_model


def _summary(
    workspace_id: str,
    *,
    title: str,
    last_run_id: str | None = None,
    last_result_status: str | None = None,
    recent_run_count: int = 0,
    active_run_count: int = 0,
    archived: bool = False,
    recovery_state: str | None = None,
    orphan_review_required: bool = False,
) -> ProductWorkspaceSummaryView:
    return ProductWorkspaceSummaryView(
        workspace_id=workspace_id,
        title=title,
        role="owner",
        updated_at="2026-04-13T10:00:00+00:00",
        last_run_id=last_run_id,
        last_result_status=last_result_status,
        archived=archived,
        recovery_state=recovery_state,
        orphan_review_required=orphan_review_required,
        activity_continuity=ProductActivityContinuitySummary(
            recent_run_count=recent_run_count,
            active_run_count=active_run_count,
            latest_run_id=last_run_id,
        ),
        links=ProductWorkspaceLinks(
            detail=f"/api/workspaces/{workspace_id}",
            runs=f"/api/workspaces/{workspace_id}/runs",
            onboarding=f"/api/users/me/onboarding?workspace_id={workspace_id}",
        ),
    )


def test_circuit_library_projects_return_use_cards_with_continue_affordance_and_history_signal() -> None:
    response = ProductWorkspaceListResponse(
        returned_count=2,
        workspaces=(
            _summary("ws-draft", title="Draft Workflow"),
            _summary(
                "ws-result",
                title="Results Workflow",
                last_run_id="run-001",
                last_result_status="completed",
                recent_run_count=1,
            ),
        ),
    )

    vm = read_circuit_library_view_model(response)

    assert vm.visible is True
    assert vm.library_status == "ready"
    assert vm.returned_count == 2
    assert vm.items[0].continue_href == "/app/workspaces/ws-draft"
    assert vm.items[0].status_key == "draft"
    assert vm.items[0].has_recent_result_history is False
    assert vm.items[1].status_key == "recent_result"
    assert vm.items[1].has_recent_result_history is True
    assert vm.items[1].continue_label == "Continue"
    assert any("Recent result history" in line for line in [vm.items[1].result_history_label or ""])


def test_circuit_library_projects_running_and_review_states() -> None:
    response = ProductWorkspaceListResponse(
        returned_count=2,
        workspaces=(
            _summary("ws-running", title="Running Workflow", last_run_id="run-002", recent_run_count=2, active_run_count=1),
            _summary("ws-review", title="Review Workflow", last_run_id="run-003", recent_run_count=1, recovery_state="manual_review_required", orphan_review_required=True),
        ),
    )

    vm = read_circuit_library_view_model(response)

    assert vm.items[0].status_key == "running"
    assert vm.items[1].status_key == "needs_review"


def test_circuit_library_projects_empty_state_when_no_workspaces_are_visible() -> None:
    vm = read_circuit_library_view_model(ProductWorkspaceListResponse(returned_count=0, workspaces=()))

    assert vm.visible is True
    assert vm.library_status == "empty"
    assert vm.returned_count == 0
    assert vm.items == []
    assert vm.empty_title == "No workflows yet"
