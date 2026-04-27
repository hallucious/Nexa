from __future__ import annotations

from src.server.workspace_shell_runtime import build_workspace_shell_runtime_payload
from src.storage.models.shared_sections import CircuitModel, ResourcesModel, StateModel
from src.storage.models.working_save_model import RuntimeModel, UIModel, WorkingSaveMeta, WorkingSaveModel


def _working_save() -> WorkingSaveModel:
    return WorkingSaveModel(
        meta=WorkingSaveMeta(format_version="1.0.0", storage_role="working_save", working_save_id="ws-001", name="Draft"),
        circuit=CircuitModel(nodes=[{"id": "n1"}], edges=[], entry="n1", outputs=[]),
        resources=ResourcesModel(prompts={}, providers={}, plugins={}),
        state=StateModel(input={}, working={}, memory={}),
        runtime=RuntimeModel(status="draft", validation_summary={}, last_run={}, errors=[]),
        ui=UIModel(layout={}, metadata={"app_language": "en-US"}),
    )


def _workspace_row() -> dict[str, str]:
    return {"workspace_id": "ws-001", "title": "Draft"}


def _provider_rows() -> list[dict[str, object]]:
    return [{"workspace_id": "ws-001", "provider_key": "openai", "enabled": True}]


def _run_rows() -> list[dict[str, str]]:
    return [{"workspace_id": "ws-001", "run_id": "run-001", "status": "completed", "status_family": "terminal_success", "updated_at": "2026-04-27T00:00:00Z"}]


def _result_rows() -> dict[str, dict[str, object]]:
    return {"run-001": {"result_state": "ready_success", "final_status": "completed", "result_summary": "Readable result", "final_output": {"value_preview": "ok"}}}


def test_ready_result_preview_completes_server_result_path_without_onboarding_milestone() -> None:
    payload = build_workspace_shell_runtime_payload(
        workspace_row=_workspace_row(),
        artifact_source=_working_save(),
        recent_run_rows=_run_rows(),
        result_rows_by_run_id=_result_rows(),
        provider_binding_rows=_provider_rows(),
    )

    review = payload["server_product_readiness_review"]
    stages = {stage["stage_id"]: stage for stage in review["stages"]}

    assert review["review_state"] == "product_surface_stable"
    assert review["uses_onboarding_state"] is False
    assert stages["first_success_setup"]["stage_state"] == "complete"
    assert stages["first_success_run"]["stage_state"] == "complete"
    assert stages["return_use"]["stage_state"] in {"complete", "return_use_ready"}
    assert stages["return_use"]["return_path_kind"] in {"result_reentry", "workflow_reentry", "feedback_followup"}


def test_explicit_onboarding_first_success_allows_server_stable_surface() -> None:
    payload = build_workspace_shell_runtime_payload(
        workspace_row=_workspace_row(),
        artifact_source=_working_save(),
        recent_run_rows=_run_rows(),
        result_rows_by_run_id=_result_rows(),
        onboarding_rows=[{"workspace_id": "ws-001", "first_success_achieved": True}],
        provider_binding_rows=_provider_rows(),
    )

    review = payload["server_product_readiness_review"]
    stages = {stage["stage_id"]: stage for stage in review["stages"]}

    assert review["review_state"] == "product_surface_stable"
    assert stages["return_use"]["stage_state"] == "complete"
    assert stages["return_use"]["return_path_kind"] in {"result_reentry", "workflow_reentry", "feedback_followup"}


def test_feedback_continuity_does_not_infer_first_success_from_return_path() -> None:
    payload = build_workspace_shell_runtime_payload(
        workspace_row=_workspace_row(),
        artifact_source=_working_save(),
        recent_run_rows=_run_rows(),
        result_rows_by_run_id=_result_rows(),
        provider_binding_rows=_provider_rows(),
    )

    feedback = payload["feedback_continuity_section"]

    assert feedback["feedback_state"] == "blocked_help"
    assert feedback["feedback_path_kind"] == "blocked_help"
    assert feedback["current_step_id"] == "report_confusion"
