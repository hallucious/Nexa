from __future__ import annotations

from src.ui.feedback_channel import read_feedback_channel_view_model


def test_feedback_channel_projects_structured_options_and_existing_items() -> None:
    vm = read_feedback_channel_view_model(
        workspace_id="ws-001",
        workspace_title="Primary Workflow",
        current_user_id="user-owner",
        feedback_rows=(
            {
                "feedback_id": "fb-002",
                "user_id": "user-owner",
                "workspace_id": "ws-001",
                "workspace_title": "Primary Workflow",
                "category": "bug_report",
                "surface": "result_history",
                "message": "The result screen did not explain the failure clearly.",
                "run_id": "run-002",
                "status": "received",
                "created_at": "2026-04-14T08:05:00+00:00",
            },
        ),
        prefill_category="friction_note",
        prefill_surface="result_history",
        prefill_run_id="run-002",
    )

    assert vm.visible is True
    assert vm.channel_status == "ready"
    assert vm.submit_path == "/api/workspaces/ws-001/feedback"
    assert vm.prefill_category == "friction_note"
    assert vm.prefill_surface == "result_history"
    assert vm.prefill_run_id == "run-002"
    assert {option.category_key for option in vm.options} == {"confusing_screen", "friction_note", "bug_report"}
    assert vm.items[0].category_key == "bug_report"
    assert vm.items[0].surface_key == "result_history"


def test_feedback_channel_localizes_options_for_korean() -> None:
    vm = read_feedback_channel_view_model(
        workspace_id="ws-001",
        workspace_title="주요 워크플로우",
        app_language="ko",
    )
    titles = {option.category_key: option.title for option in vm.options}
    assert titles["confusing_screen"] == "헷갈리는 화면 신고"
    assert titles["friction_note"] == "빠른 불편 메모"
    assert titles["bug_report"] == "버그 신고 바로가기"
