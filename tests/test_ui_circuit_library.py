from __future__ import annotations

from src.server.workspace_onboarding_models import (
    ProductActivityContinuitySummary,
    ProductWorkspaceLinks,
    ProductWorkspaceListResponse,
    ProductWorkspaceSummaryView,
)
from src.ui.circuit_library import read_circuit_library_view_model
from src.ui.result_history import read_result_history_view_model
from src.server.run_list_models import ProductWorkspaceRunListResponse, ProductRunListAppliedFilters, ProductRunListItemView, ProductRunListLinks
from src.server.run_read_models import ProductExecutionTargetView, ProductRunResultResponse, ProductResultSummaryView, ProductFinalOutputView


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


def test_circuit_library_projects_expose_result_history_reentry_link() -> None:
    response = ProductWorkspaceListResponse(returned_count=1, workspaces=(_summary("ws-result", title="Results Workflow", last_run_id="run-001", last_result_status="completed", recent_run_count=1),))
    vm = read_circuit_library_view_model(response)
    assert vm.items[0].result_history_href == "/app/workspaces/ws-result/results?run_id=run-001"
    assert vm.items[0].result_history_action_label == "Open results"


def test_result_history_view_model_projects_beginner_reopen_cards() -> None:
    response = ProductWorkspaceRunListResponse(
        workspace_id="ws-001",
        workspace_title="Primary Workspace",
        returned_count=2,
        total_visible_count=2,
        runs=(
            ProductRunListItemView(run_id="run-002", workspace_id="ws-001", execution_target=ProductExecutionTargetView(target_type="commit_snapshot", target_ref="snap-002"), status="completed", status_family="terminal_success", created_at="2026-04-11T12:01:00+00:00", updated_at="2026-04-11T12:01:05+00:00", completed_at="2026-04-11T12:01:05+00:00", result_state="ready_success", result_summary=ProductResultSummaryView(title="Run completed", description="Success."), links=ProductRunListLinks(status="/api/runs/run-002", result="/api/runs/run-002/result", trace="/api/runs/run-002/trace", artifacts="/api/runs/run-002/artifacts")),
            ProductRunListItemView(run_id="run-001", workspace_id="ws-001", execution_target=ProductExecutionTargetView(target_type="commit_snapshot", target_ref="snap-001"), status="failed", status_family="terminal_failure", created_at="2026-04-11T12:00:00+00:00", updated_at="2026-04-11T12:00:05+00:00", completed_at="2026-04-11T12:00:05+00:00", result_state="ready_failure", result_summary=ProductResultSummaryView(title="Run failed", description="The run failed."), links=ProductRunListLinks(status="/api/runs/run-001", result="/api/runs/run-001/result", trace="/api/runs/run-001/trace", artifacts="/api/runs/run-001/artifacts")),
        ),
        applied_filters=ProductRunListAppliedFilters(limit=20),
    )
    vm = read_result_history_view_model(response, result_rows_by_run_id={"run-002": ProductRunResultResponse(run_id="run-002", workspace_id="ws-001", result_state="ready_success", final_status="completed", result_summary=ProductResultSummaryView(title="Last successful result", description="Success."), final_output=ProductFinalOutputView(output_key="answer", value_preview="Hello again", value_type="string"))}, selected_run_id="run-002")
    assert vm.visible is True
    assert vm.history_status == "ready"
    assert vm.selected_run_id == "run-002"
    assert vm.items[0].status_key == "success"
    assert vm.items[0].open_result_href == "/app/workspaces/ws-001/results?run_id=run-002"
    assert vm.items[0].output_preview == "Hello again"
    assert vm.items[1].status_key == "failed"



def test_circuit_library_prioritizes_server_onboarding_resume_target() -> None:
    response = ProductWorkspaceListResponse(
        returned_count=1,
        workspaces=(
            _summary(
                "ws-onboarding",
                title="Onboarding Workflow",
                last_run_id="run-101",
                last_result_status="completed",
                recent_run_count=1,
            ),
        ),
    )

    vm = read_circuit_library_view_model(
        response,
        onboarding_state_by_workspace_id={
            "ws-onboarding": {
                "workspace_id": "ws-onboarding",
                "first_success_achieved": False,
                "advanced_surfaces_unlocked": False,
                "current_step": "read_result",
            }
        },
    )

    assert vm.items[0].status_key == "resume_onboarding"
    assert vm.items[0].onboarding_incomplete is True
    assert vm.items[0].continue_href == "/app/workspaces/ws-onboarding/results?run_id=run-101"
    assert vm.items[0].continue_label == "Resume first result"
    assert any("Server progress saved your place" in line for line in vm.items[0].summary_lines)


def test_result_history_projects_onboarding_banner_when_first_success_is_not_finished() -> None:
    response = ProductWorkspaceRunListResponse(
        workspace_id="ws-001",
        workspace_title="Primary Workflow",
        returned_count=1,
        total_visible_count=1,
        runs=(
            ProductRunListItemView(
                run_id="run-002",
                workspace_id="ws-001",
                execution_target=ProductExecutionTargetView(target_type="approved_snapshot", target_ref="snap-001"),
                status="completed",
                status_family="terminal_success",
                created_at="2026-04-13T09:00:00+00:00",
                updated_at="2026-04-13T09:05:00+00:00",
                completed_at="2026-04-13T09:05:00+00:00",
                result_state="ready_success",
                result_summary=ProductResultSummaryView(title="Last successful result", description="Success."),
                links=ProductRunListLinks(status="/api/runs/run-002", result="/api/runs/run-002/result", trace="/api/runs/run-002/trace", artifacts="/api/runs/run-002/artifacts"),
            ),
        ),
        applied_filters=ProductRunListAppliedFilters(limit=20),
    )
    vm = read_result_history_view_model(
        response,
        result_rows_by_run_id={
            "run-002": ProductRunResultResponse(
                run_id="run-002",
                workspace_id="ws-001",
                result_state="ready_success",
                final_status="completed",
                result_summary=ProductResultSummaryView(title="Last successful result", description="Success."),
                final_output=ProductFinalOutputView(output_key="answer", value_preview="Hello again", value_type="string"),
            )
        },
        selected_run_id="run-002",
        onboarding_state={
            "workspace_id": "ws-001",
            "first_success_achieved": False,
            "advanced_surfaces_unlocked": False,
            "current_step": "read_result",
        },
    )
    assert vm.onboarding_incomplete is True
    assert vm.onboarding_step_id == "read_result"
    assert vm.onboarding_action_href == "/app/workspaces/ws-001/results?run_id=run-002"
    assert vm.onboarding_action_label == "Stay on this result"
