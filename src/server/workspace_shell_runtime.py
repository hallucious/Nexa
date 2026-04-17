from __future__ import annotations

from dataclasses import asdict
from html import escape
import json
from typing import Any, Mapping, Sequence

from src.storage.models.commit_snapshot_model import CommitSnapshotModel
from src.storage.models.execution_record_model import ExecutionRecordModel
from src.storage.models.loaded_nex_artifact import LoadedNexArtifact
from src.storage.models.shared_sections import CircuitModel, ResourcesModel, StateModel
from src.storage.models.working_save_model import RuntimeModel, UIModel, WorkingSaveMeta, WorkingSaveModel
from src.storage.validators.shared_validator import load_nex
from src.ui.builder_shell import read_builder_shell_view_model
from src.ui.i18n import normalize_ui_language, ui_language_from_sources, ui_text
from src.ui.template_gallery import read_template_gallery_view_model
from src.server.workspace_shell_sections import build_shell_section
from src.storage.share_api import describe_public_nex_link_share

_WORKSPACE_ARTIFACT_KEYS: tuple[str, ...] = (
    "working_save_source",
    "working_save_artifact",
    "working_save",
    "artifact_source",
    "artifact_json",
    "artifact",
)


def _default_working_save(workspace_row: Mapping[str, Any] | None) -> WorkingSaveModel:
    workspace_id = str((workspace_row or {}).get("workspace_id") or "workspace").strip() or "workspace"
    title = str((workspace_row or {}).get("title") or "Untitled Workspace").strip() or "Untitled Workspace"
    description = str((workspace_row or {}).get("description") or "").strip() or None
    return WorkingSaveModel(
        meta=WorkingSaveMeta(
            format_version="1.0.0",
            storage_role="working_save",
            working_save_id=f"{workspace_id}-draft",
            name=title,
            description=description,
        ),
        circuit=CircuitModel(nodes=[], edges=[], entry=None, outputs=[]),
        resources=ResourcesModel(prompts={}, providers={}, plugins={}),
        state=StateModel(input={}, working={}, memory={}),
        runtime=RuntimeModel(status="draft", validation_summary={}, last_run={}, errors=[]),
        ui=UIModel(layout={}, metadata={"app_language": "en-US"}),
    )


def resolve_workspace_artifact_source(
    workspace_row: Mapping[str, Any] | None,
    explicit_source: Any | None,
) -> Any | None:
    if explicit_source is not None:
        return explicit_source
    row = workspace_row or {}
    for key in _WORKSPACE_ARTIFACT_KEYS:
        if key in row and row.get(key) is not None:
            return row.get(key)
    return None


def _load_workspace_model(source: Any | None, workspace_row: Mapping[str, Any] | None):
    if source is None:
        return _default_working_save(workspace_row), None
    loaded = load_nex(source)
    if isinstance(loaded, LoadedNexArtifact) and loaded.parsed_model is not None:
        return loaded.parsed_model, loaded
    return _default_working_save(workspace_row), loaded if isinstance(loaded, LoadedNexArtifact) else None


def _storage_role(model: Any) -> str:
    if isinstance(model, WorkingSaveModel):
        return "working_save"
    if isinstance(model, CommitSnapshotModel):
        return "commit_snapshot"
    if isinstance(model, ExecutionRecordModel):
        return "execution_record"
    return "none"


def _execution_target_for(model: Any) -> dict[str, Any] | None:
    if isinstance(model, WorkingSaveModel):
        return {
            "target_type": "working_save",
            "target_ref": model.meta.working_save_id,
        }
    if isinstance(model, CommitSnapshotModel):
        return {
            "target_type": "commit_snapshot",
            "target_ref": model.meta.commit_id,
        }
    return None


def _workspace_shell_action_availability(model: Any) -> dict[str, dict[str, Any]]:
    storage_role = _storage_role(model)
    if isinstance(model, WorkingSaveModel):
        return {
            "draft_write": {"allowed": True, "reason_code": None},
            "commit": {"allowed": True, "reason_code": None},
            "checkout": {"allowed": False, "reason_code": "workspace_shell.checkout_requires_commit_snapshot"},
            "launch": {"allowed": True, "reason_code": None},
        }
    if isinstance(model, CommitSnapshotModel):
        return {
            "draft_write": {"allowed": False, "reason_code": "workspace_shell.draft_requires_working_save"},
            "commit": {"allowed": False, "reason_code": "workspace_shell.already_commit_snapshot"},
            "checkout": {"allowed": True, "reason_code": None},
            "launch": {"allowed": True, "reason_code": None},
        }
    return {
        "draft_write": {"allowed": False, "reason_code": f"workspace_shell.unsupported_source_role:{storage_role}"},
        "commit": {"allowed": False, "reason_code": f"workspace_shell.unsupported_source_role:{storage_role}"},
        "checkout": {"allowed": False, "reason_code": f"workspace_shell.unsupported_source_role:{storage_role}"},
        "launch": {"allowed": False, "reason_code": f"workspace_shell.unsupported_source_role:{storage_role}"},
    }


def _last_run_id(recent_run_rows: Sequence[Mapping[str, Any]], workspace_id: str) -> str | None:
    for row in recent_run_rows:
        if str(row.get("workspace_id") or "").strip() == workspace_id:
            value = str(row.get("run_id") or "").strip()
            if value:
                return value
    return None


def _latest_run_row(recent_run_rows: Sequence[Mapping[str, Any]], workspace_id: str) -> Mapping[str, Any] | None:
    candidates = [
        dict(row)
        for row in recent_run_rows
        if str(row.get("workspace_id") or "").strip() == workspace_id
    ]
    if not candidates:
        return None
    candidates.sort(
        key=lambda row: (
            str(row.get("updated_at") or ""),
            str(row.get("created_at") or ""),
            str(row.get("run_id") or ""),
        ),
        reverse=True,
    )
    return candidates[0]


def _latest_run_status_preview(latest_run_row: Mapping[str, Any] | None) -> dict[str, Any] | None:
    if latest_run_row is None:
        return None
    run_id = str(latest_run_row.get("run_id") or "").strip()
    if not run_id:
        return None
    status = str(latest_run_row.get("status") or "unknown").strip() or "unknown"
    summary = str(latest_run_row.get("status_family") or "").strip() or status
    started_at = str(latest_run_row.get("started_at") or "").strip() or None
    updated_at = str(latest_run_row.get("updated_at") or "").strip() or None
    return {
        "run_id": run_id,
        "status": status,
        "summary": summary,
        "started_at": started_at,
        "updated_at": updated_at,
    }


def _latest_run_result_preview(
    latest_run_row: Mapping[str, Any] | None,
    result_rows_by_run_id: Mapping[str, Mapping[str, Any]] | None,
) -> dict[str, Any] | None:
    if latest_run_row is None or not result_rows_by_run_id:
        return None
    run_id = str(latest_run_row.get("run_id") or "").strip()
    if not run_id:
        return None
    result_row = result_rows_by_run_id.get(run_id)
    if result_row is None:
        return None
    summary = str(result_row.get("result_summary") or "").strip() or None
    result_state = str(result_row.get("result_state") or "").strip() or None
    final_status = str(result_row.get("final_status") or "").strip() or None
    if not any((summary, result_state, final_status)):
        return None
    return {
        "run_id": run_id,
        "result_state": result_state,
        "final_status": final_status,
        "summary": summary,
    }


def _latest_run_artifacts_preview(
    latest_run_row: Mapping[str, Any] | None,
    artifact_rows_lookup: Any | None,
) -> dict[str, Any] | None:
    if latest_run_row is None or artifact_rows_lookup is None:
        return None
    run_id = str(latest_run_row.get("run_id") or "").strip()
    if not run_id:
        return None
    artifact_rows = tuple(artifact_rows_lookup(run_id) or ())
    if not artifact_rows:
        return None
    first = artifact_rows[0]
    return {
        "run_id": run_id,
        "artifact_count": len(artifact_rows),
        "first_artifact_id": str(first.get("artifact_id") or "").strip() or None,
        "first_label": str(first.get("label") or first.get("payload_preview") or "").strip() or None,
    }


def _latest_run_trace_preview(
    latest_run_row: Mapping[str, Any] | None,
    trace_rows_lookup: Any | None,
) -> dict[str, Any] | None:
    if latest_run_row is None or trace_rows_lookup is None:
        return None
    run_id = str(latest_run_row.get("run_id") or "").strip()
    if not run_id:
        return None
    trace_rows = tuple(trace_rows_lookup(run_id) or ())
    if not trace_rows:
        return None
    ordered = sorted(
        trace_rows,
        key=lambda row: (int(row.get("sequence_number") or 0), str(row.get("occurred_at") or "")),
    )
    latest = ordered[-1]
    return {
        "run_id": run_id,
        "event_count": len(ordered),
        "latest_event_type": str(latest.get("event_type") or "").strip() or None,
        "latest_node_id": str(latest.get("node_id") or "").strip() or None,
        "latest_message": str(latest.get("message_preview") or "").strip() or None,
    }

def _normalized_onboarding_current_step(onboarding_state: Mapping[str, Any] | None) -> str | None:
    if not isinstance(onboarding_state, Mapping):
        return None
    step = str(onboarding_state.get("current_step") or "").strip().lower()
    allowed = {"enter_goal", "review_preview", "approve", "run", "read_result"}
    return step if step in allowed else None


def _summary_lines(*values: str | None) -> list[str]:
    return [value for value in values if isinstance(value, str) and value.strip()]


def _localize_shell_payload(payload: dict[str, Any], app_language: str) -> dict[str, Any]:
    if app_language != "ko":
        return payload

    exact = {
        "Run draft": ui_text("server.shell.run_draft_action", app_language=app_language, fallback_text="Run draft"),
        "Open latest result": ui_text("server.shell.result_history_open_latest", app_language=app_language, fallback_text="Open latest result"),
        "Open latest trace": ui_text("server.shell.trace_history_open_latest", app_language=app_language, fallback_text="Open latest trace"),
        "Open latest artifacts": ui_text("server.shell.artifacts_history_open_latest", app_language=app_language, fallback_text="Open latest artifacts"),
        "Refresh latest status": ui_text("server.shell.status_history_refresh_latest", app_language=app_language, fallback_text="Refresh latest status"),
        "Open Designer detail": ui_text("server.shell.open_designer_detail", app_language=app_language, fallback_text="Open Designer detail"),
        "Open starter templates": ui_text("server.shell.open_starter_templates", app_language=app_language, fallback_text="Open starter templates"),
        "Open Validation detail": ui_text("server.shell.open_validation_detail", app_language=app_language, fallback_text="Open Validation detail"),
        "Open contextual help": ui_text("server.shell.open_contextual_help", app_language=app_language, fallback_text="Open contextual help"),
        "Open Designer": ui_text("server.shell.open_designer", app_language=app_language, fallback_text="Open Designer"),
        "Open Status": ui_text("server.shell.open_status", app_language=app_language, fallback_text="Open Status"),
        "Open Result": ui_text("server.shell.open_result", app_language=app_language, fallback_text="Open Result"),
        "Open Trace": ui_text("server.shell.open_trace", app_language=app_language, fallback_text="Open Trace"),
        "Open Artifacts": ui_text("server.shell.open_artifacts", app_language=app_language, fallback_text="Open Artifacts"),
        "Review Validation": ui_text("server.shell.banner.review_validation", app_language=app_language, fallback_text="Review Validation"),
        "Review preview": ui_text("server.shell.review_preview_action", app_language=app_language, fallback_text="Review preview"),
        "Status history": ui_text("server.shell.run_status_history", app_language=app_language, fallback_text="Status history"),
        "Result history": ui_text("server.shell.run_result_history", app_language=app_language, fallback_text="Result history"),
        "Trace history": ui_text("server.shell.trace_history", app_language=app_language, fallback_text="Trace history"),
        "Artifacts history": ui_text("server.shell.artifacts_history", app_language=app_language, fallback_text="Artifacts history"),
        "Status detail": ui_text("server.shell.status_detail_title", app_language=app_language, fallback_text="Status detail"),
        "Result detail": ui_text("server.shell.result_detail_title", app_language=app_language, fallback_text="Result detail"),
        "Trace detail": ui_text("server.shell.trace_detail_title", app_language=app_language, fallback_text="Trace detail"),
        "Artifacts detail": ui_text("server.shell.artifacts_detail_title", app_language=app_language, fallback_text="Artifacts detail"),
        "Designer workspace": ui_text("server.shell.designer_workspace", app_language=app_language, fallback_text="Designer workspace"),
        "Designer detail": ui_text("server.shell.designer_detail_layer", app_language=app_language, fallback_text="Designer detail"),
        "Validation detail": ui_text("server.shell.validation_detail_title", app_language=app_language, fallback_text="Validation detail"),
        "Use Designer to draft or review the workflow before running.": ui_text("server.shell.designer_detail_default", app_language=app_language, fallback_text="Use Designer to draft or review the workflow before running."),
        "Validation details will appear here as findings accumulate.": ui_text("server.shell.validation_detail_default", app_language=app_language, fallback_text="Validation details will appear here as findings accumulate."),
        "Review validation before the next step.": ui_text("server.shell.validation_default_summary", app_language=app_language, fallback_text="Review validation before the next step."),
        "No recent status history is available yet.": ui_text("server.shell.no_recent_status_history", app_language=app_language, fallback_text="No recent status history is available yet."),
        "No recent result history is available yet.": ui_text("server.shell.no_recent_result_history", app_language=app_language, fallback_text="No recent result history is available yet."),
        "No recent trace history is available yet.": ui_text("server.shell.no_recent_trace_history", app_language=app_language, fallback_text="No recent trace history is available yet."),
        "No recent artifacts history is available yet.": ui_text("server.shell.no_recent_artifacts_history", app_language=app_language, fallback_text="No recent artifacts history is available yet."),
        "Status history entries will appear here as runs accumulate.": ui_text("server.shell.status_history_entries_pending", app_language=app_language, fallback_text="Status history entries will appear here as runs accumulate."),
        "Result history entries will appear here as runs complete.": ui_text("server.shell.result_history_entries_pending", app_language=app_language, fallback_text="Result history entries will appear here as runs complete."),
        "Trace history entries will appear here as runs accumulate.": ui_text("server.shell.trace_history_entries_pending", app_language=app_language, fallback_text="Trace history entries will appear here as runs accumulate."),
        "Artifacts history entries will appear here as runs accumulate.": ui_text("server.shell.artifacts_history_entries_pending", app_language=app_language, fallback_text="Artifacts history entries will appear here as runs accumulate."),
        "Start from Designer to describe your goal or choose a starter template.": ui_text("server.shell.designer_open_default", app_language=app_language, fallback_text="Start from Designer to describe your goal or choose a starter template."),
    }
    prefix = [
        ("Status: ", ui_text("server.shell.validation_prefix", app_language=app_language, fallback_text="Status: ").replace("검증", "상태") if False else ui_text("server.shell.status", app_language=app_language, fallback_text="Status") + ": "),
        ("Run id: ", ui_text("server.shell.run_id_prefix", app_language=app_language, fallback_text="Run id: ")),
        ("Started: ", ui_text("server.shell.started_prefix", app_language=app_language, fallback_text="Started: ")),
        ("Updated: ", ui_text("server.shell.updated_prefix", app_language=app_language, fallback_text="Updated: ")),
        ("Result state: ", ui_text("server.shell.result_state_prefix", app_language=app_language, fallback_text="Result state: ")),
        ("Final status: ", ui_text("server.shell.final_status_prefix", app_language=app_language, fallback_text="Final status: ")),
        ("Summary: ", ui_text("server.shell.summary_prefix", app_language=app_language, fallback_text="Summary: ")),
        ("Preview: ", ui_text("server.shell.preview_prefix", app_language=app_language, fallback_text="Preview: ")),
        ("Trace events: ", ui_text("server.shell.trace_events_prefix", app_language=app_language, fallback_text="Trace events: ")),
        ("Latest event: ", ui_text("server.shell.latest_event_prefix", app_language=app_language, fallback_text="Latest event: ")),
        ("Latest event type: ", ui_text("server.shell.latest_event_type_prefix", app_language=app_language, fallback_text="Latest event type: ")),
        ("Latest node: ", ui_text("server.shell.latest_node_prefix", app_language=app_language, fallback_text="Latest node: ")),
        ("Latest node id: ", ui_text("server.shell.latest_node_id_prefix", app_language=app_language, fallback_text="Latest node id: ")),
        ("Latest message: ", ui_text("server.shell.latest_message_prefix", app_language=app_language, fallback_text="Latest message: ")),
        ("Artifacts: ", ui_text("server.shell.artifacts_prefix", app_language=app_language, fallback_text="Artifacts: ")),
        ("Event count: ", ui_text("server.shell.event_count_prefix", app_language=app_language, fallback_text="Event count: ")),
        ("Artifact count: ", ui_text("server.shell.artifact_count_prefix", app_language=app_language, fallback_text="Artifact count: ")),
        ("First artifact id: ", ui_text("server.shell.first_artifact_id_prefix", app_language=app_language, fallback_text="First artifact id: ")),
        ("First artifact preview: ", ui_text("server.shell.first_artifact_preview_prefix", app_language=app_language, fallback_text="First artifact preview: ")),
        ("Recent runs: ", ui_text("server.shell.recent_runs_prefix", app_language=app_language, fallback_text="Recent runs: ")),
        ("Recent results: ", ui_text("server.shell.recent_results_prefix", app_language=app_language, fallback_text="Recent results: ")),
        ("Recent traces: ", ui_text("server.shell.recent_traces_prefix", app_language=app_language, fallback_text="Recent traces: ")),
        ("Recent artifact sets: ", ui_text("server.shell.recent_artifact_sets_prefix", app_language=app_language, fallback_text="Recent artifact sets: ")),
        ("Latest: ", ui_text("server.shell.latest_prefix", app_language=app_language, fallback_text="Latest: ")),
        ("Request status: ", ui_text("server.shell.request_status_prefix", app_language=app_language, fallback_text="Request status: ")),
        ("Preview status: ", ui_text("server.shell.preview_status_prefix", app_language=app_language, fallback_text="Preview status: ")),
        ("Approval status: ", ui_text("server.shell.approval_status_prefix", app_language=app_language, fallback_text="Approval status: ")),
        ("Templates available: ", ui_text("server.shell.templates_available_prefix", app_language=app_language, fallback_text="Templates available: ")),
        ("Connected providers: ", ui_text("server.shell.connected_providers_prefix", app_language=app_language, fallback_text="Connected providers: ")),
        ("Persisted template: ", ui_text("server.shell.persisted_template_prefix", app_language=app_language, fallback_text="Persisted template: ")),
        ("Submit enabled: ", ui_text("server.shell.submit_enabled_prefix", app_language=app_language, fallback_text="Submit enabled: ")),
        ("Persisted request: ", ui_text("server.shell.persisted_request_prefix", app_language=app_language, fallback_text="Persisted request: ")),
        ("Last designer action: ", ui_text("server.shell.last_designer_action_prefix", app_language=app_language, fallback_text="Last designer action: ")),
        ("Provider setup summary: ", ui_text("server.shell.provider_setup_summary_prefix", app_language=app_language, fallback_text="Provider setup summary: ")),
        ("Suggested action: ", ui_text("server.shell.suggested_action_prefix", app_language=app_language, fallback_text="Suggested action: ")),
        ("Blocking findings: ", ui_text("server.shell.blocking_findings_prefix", app_language=app_language, fallback_text="Blocking findings: ")),
        ("Warnings: ", ui_text("server.shell.warnings_prefix", app_language=app_language, fallback_text="Warnings: ")),
        ("Next action: ", ui_text("server.shell.next_action_prefix", app_language=app_language, fallback_text="Next action: ")),
        ("Persisted validation action: ", ui_text("server.shell.persisted_validation_action_prefix", app_language=app_language, fallback_text="Persisted validation action: ")),
        ("Requires confirmation: ", ui_text("server.shell.requires_confirmation_prefix", app_language=app_language, fallback_text="Requires confirmation: ")),
        ("Can execute: ", ui_text("server.shell.can_execute_prefix", app_language=app_language, fallback_text="Can execute: ")),
        ("Top issue: ", ui_text("server.shell.top_issue_prefix", app_language=app_language, fallback_text="Top issue: ")),
        ("Persisted validation status: ", ui_text("server.shell.persisted_validation_status_prefix", app_language=app_language, fallback_text="Persisted validation status: ")),
        ("Persisted validation message: ", ui_text("server.shell.persisted_validation_message_prefix", app_language=app_language, fallback_text="Persisted validation message: ")),
        ("Designer request: ", ui_text("server.shell.designer_request", app_language=app_language, fallback_text="Designer request: {request}", request="").replace("", "")),
        ("Opened status for ", ui_text("server.shell.opened_status_prefix", app_language=app_language, fallback_text="Opened status for ")),
        ("Opened result for ", ui_text("server.shell.opened_result_prefix", app_language=app_language, fallback_text="Opened result for ")),
        ("Opened trace for ", ui_text("server.shell.opened_trace_prefix", app_language=app_language, fallback_text="Opened trace for ")),
        ("Opened artifacts for ", ui_text("server.shell.opened_artifacts_prefix", app_language=app_language, fallback_text="Opened artifacts for ")),
    ]

    def transform(value: Any) -> Any:
        if isinstance(value, str):
            if value in exact:
                return exact[value]
            if value.startswith("Recommended next: "):
                tail = value[len("Recommended next: "):]
                tail_map = {"Status": ui_text("server.shell.status", app_language=app_language, fallback_text="Status"), "Validation": ui_text("server.shell.section.validation", app_language=app_language, fallback_text="Validation"), "Result": ui_text("server.shell.section.result", app_language=app_language, fallback_text="Result"), "Trace": ui_text("server.shell.section.trace", app_language=app_language, fallback_text="Trace"), "Artifacts": ui_text("server.shell.section.artifacts", app_language=app_language, fallback_text="Artifacts"), "Designer": ui_text("server.shell.section.designer", app_language=app_language, fallback_text="Designer")}
                return ui_text("server.shell.recommended_next_prefix", app_language=app_language, fallback_text="Recommended next: ") + tail_map.get(tail, tail)
            if value.startswith("Step ") and " — " in value:
                number, label = value.split(" — ", 1)
                label_map = {"Enter goal": ui_text("server.shell.step.enter_goal", app_language=app_language, fallback_text="Step 1 of 5 — Enter goal").split(" — ",1)[1], "Review preview": ui_text("server.shell.step.review_preview", app_language=app_language, fallback_text="Step 2 of 5 — Review preview").split(" — ",1)[1], "Approve": ui_text("server.shell.step.approve", app_language=app_language, fallback_text="Step 3 of 5 — Approve").split(" — ",1)[1], "Run": ui_text("server.shell.step.run", app_language=app_language, fallback_text="Step 4 of 5 — Run").split(" — ",1)[1], "Read result": ui_text("server.shell.step.read_result", app_language=app_language, fallback_text="Step 5 of 5 — Read result").split(" — ",1)[1]}
                num_map={"Step 1 of 5": "5단계 중 1단계", "Step 2 of 5": "5단계 중 2단계", "Step 3 of 5": "5단계 중 3단계", "Step 4 of 5": "5단계 중 4단계", "Step 5 of 5": "5단계 중 5단계"}
                return f"{num_map.get(number, number)} — {label_map.get(label, label)}"
            for old, new in prefix:
                if value.startswith(old):
                    if old == "Designer request: ":
                        return ui_text("server.shell.designer_request", app_language=app_language, fallback_text="Designer request: {request}", request=value[len(old):])
                    return new + value[len(old):]
            return value
        if isinstance(value, list):
            return [transform(item) for item in value]
        if isinstance(value, dict):
            return {key: transform(item) for key, item in value.items()}
        return value

    keys = [
        "latest_run_status_summary", "latest_run_result_summary", "latest_run_artifacts_summary", "latest_run_trace_summary",
        "latest_run_status_detail", "latest_run_result_detail", "latest_run_artifacts_detail", "latest_run_trace_detail",
        "status_history_section", "result_history_section", "trace_history_section", "artifacts_history_section",
        "designer_section", "validation_section", "navigation", "step_state_banner",
    ]
    for key in keys:
        if key in payload and payload[key] is not None:
            payload[key] = transform(payload[key])
    return payload


def _latest_run_status_summary(preview: Mapping[str, Any] | None) -> dict[str, Any] | None:
    if not preview:
        return None
    status = str(preview.get("status") or "unknown").strip() or "unknown"
    summary = str(preview.get("summary") or status).strip() or status
    run_id = str(preview.get("run_id") or "").strip() or None
    headline = f"Status: {summary}"
    lines = _summary_lines(
        f"Run id: {run_id}" if run_id else None,
        f"Started: {preview.get('started_at')}" if preview.get('started_at') else None,
        f"Updated: {preview.get('updated_at')}" if preview.get('updated_at') else None,
    )
    return {"headline": headline, "lines": lines}


def _latest_run_result_summary(preview: Mapping[str, Any] | None) -> dict[str, Any] | None:
    if not preview:
        return None
    summary = str(preview.get("summary") or "Result available.").strip() or "Result available."
    result_state = str(preview.get("result_state") or "").strip() or None
    final_status = str(preview.get("final_status") or "").strip() or None
    lines = _summary_lines(
        f"Result state: {result_state}" if result_state else None,
        f"Final status: {final_status}" if final_status else None,
    )
    return {"headline": summary, "lines": lines}


def _latest_run_status_detail(preview: Mapping[str, Any] | None) -> dict[str, Any] | None:
    if not preview:
        return None
    return {
        "title": "Status detail",
        "items": _summary_lines(
            f"Run id: {preview.get('run_id')}" if preview.get("run_id") else None,
            f"Status: {preview.get('status')}" if preview.get("status") else None,
            f"Summary: {preview.get('summary')}" if preview.get("summary") else None,
            f"Started: {preview.get('started_at')}" if preview.get("started_at") else None,
            f"Updated: {preview.get('updated_at')}" if preview.get("updated_at") else None,
        ),
    }


def _latest_run_result_detail(preview: Mapping[str, Any] | None) -> dict[str, Any] | None:
    if not preview:
        return None
    return {
        "title": "Result detail",
        "items": _summary_lines(
            f"Run id: {preview.get('run_id')}" if preview.get("run_id") else None,
            f"Result state: {preview.get('result_state')}" if preview.get("result_state") else None,
            f"Final status: {preview.get('final_status')}" if preview.get("final_status") else None,
            f"Summary: {preview.get('summary')}" if preview.get("summary") else None,
        ),
    }


def _latest_run_artifacts_summary(preview: Mapping[str, Any] | None) -> dict[str, Any] | None:
    if not preview:
        return None
    count = int(preview.get("artifact_count") or 0)
    headline = f"Artifacts: {count}"
    first_artifact_id = str(preview.get("first_artifact_id") or "").strip() or None
    first_label = str(preview.get("first_label") or "").strip() or None
    lines = _summary_lines(
        f"First artifact id: {first_artifact_id}" if first_artifact_id else None,
        f"Preview: {first_label}" if first_label else None,
    )
    return {"headline": headline, "lines": lines}


def _latest_run_trace_summary(preview: Mapping[str, Any] | None) -> dict[str, Any] | None:
    if not preview:
        return None
    count = int(preview.get("event_count") or 0)
    latest_event_type = str(preview.get("latest_event_type") or "").strip() or None
    latest_node_id = str(preview.get("latest_node_id") or "").strip() or None
    latest_message = str(preview.get("latest_message") or "").strip() or None
    headline = f"Trace events: {count}"
    lines = _summary_lines(
        f"Latest event: {latest_event_type}" if latest_event_type else None,
        f"Latest node: {latest_node_id}" if latest_node_id else None,
        f"Latest message: {latest_message}" if latest_message else None,
    )
    return {"headline": headline, "lines": lines}


def _latest_run_trace_detail(preview: Mapping[str, Any] | None) -> dict[str, Any] | None:
    if not preview:
        return None
    count = int(preview.get("event_count") or 0)
    return {
        "title": "Trace detail",
        "items": _summary_lines(
            f"Event count: {count}",
            f"Latest event type: {preview.get('latest_event_type')}" if preview.get("latest_event_type") else None,
            f"Latest node id: {preview.get('latest_node_id')}" if preview.get("latest_node_id") else None,
            f"Latest message: {preview.get('latest_message')}" if preview.get("latest_message") else None,
        ),
    }


def _latest_run_artifacts_detail(preview: Mapping[str, Any] | None) -> dict[str, Any] | None:
    if not preview:
        return None
    count = int(preview.get("artifact_count") or 0)
    return {
        "title": "Artifacts detail",
        "items": _summary_lines(
            f"Artifact count: {count}",
            f"First artifact id: {preview.get('first_artifact_id')}" if preview.get("first_artifact_id") else None,
            f"First artifact preview: {preview.get('first_label')}" if preview.get("first_label") else None,
        ),
    }


def _recent_run_rows_for_workspace(recent_run_rows: Sequence[Mapping[str, Any]], workspace_id: str, *, limit: int = 5) -> tuple[Mapping[str, Any], ...]:
    candidates = [
        dict(row)
        for row in recent_run_rows
        if str(row.get("workspace_id") or "").strip() == workspace_id
    ]
    candidates.sort(
        key=lambda row: (
            str(row.get("updated_at") or ""),
            str(row.get("created_at") or ""),
            str(row.get("run_id") or ""),
        ),
        reverse=True,
    )
    return tuple(candidates[:limit])


def _recent_onboarding_rows_for_workspace(onboarding_rows: Sequence[Mapping[str, Any]], workspace_id: str, *, limit: int = 5) -> tuple[Mapping[str, Any], ...]:
    candidates = [
        dict(row)
        for row in onboarding_rows
        if str(row.get("workspace_id") or "").strip() == workspace_id
    ]
    candidates.sort(
        key=lambda row: (
            str(row.get("updated_at") or ""),
            str(row.get("created_at") or ""),
            str(row.get("onboarding_state_id") or ""),
        ),
        reverse=True,
    )
    return tuple(candidates[:limit])


def _status_history_section(recent_run_rows: Sequence[Mapping[str, Any]], workspace_id: str) -> dict[str, Any]:
    entries: list[dict[str, Any]] = []
    for row in _recent_run_rows_for_workspace(recent_run_rows, workspace_id):
        run_id = str(row.get("run_id") or "").strip()
        if not run_id:
            continue
        status = str(row.get("status") or "unknown").strip() or "unknown"
        summary = str(row.get("status_family") or status).strip() or status
        entries.append({
            "run_id": run_id,
            "status": status,
            "summary": summary,
            "updated_at": str(row.get("updated_at") or "").strip() or None,
        })
    latest = entries[0] if entries else None
    controls: list[dict[str, Any]] = [
        {
            "control_id": "status-history-refresh-latest",
            "label": "Refresh latest status",
            "action_kind": "focus_section",
            "action_target": "runtime.status",
        }
    ]
    if len(entries) > 1:
        previous = entries[1]
        controls.append(
            {
                "control_id": f"status-history-open-{previous['run_id']}",
                "label": f"Open {previous['run_id']} status",
                "action_kind": "open_run_status",
                "action_target": previous["run_id"],
            }
        )
    return build_shell_section(
        headline="Status history",
        lines=_summary_lines(
            f"Recent runs: {len(entries)}" if entries else "No recent status history is available yet.",
            f"Latest: {latest['run_id']} — {latest['summary']}" if latest else None,
        ),
        detail_title="Status history detail",
        detail_items=[f"{index + 1}. {entry['run_id']} — {entry['summary']}" for index, entry in enumerate(entries[:3])],
        detail_empty="Status history entries will appear here as runs accumulate.",
        controls=controls,
        history=entries[:3],
    )




def _localized_runtime_section_label(section_id: str, *, app_language: str = "en") -> str:
    normalized = str(section_id or "").strip().lower()
    key_map = {
        "designer": "server.shell.section.designer",
        "validation": "server.shell.section.validation",
        "status": "server.shell.section.status",
        "result": "server.shell.section.result",
        "trace": "server.shell.section.trace",
        "artifacts": "server.shell.section.artifacts",
    }
    fallback_map = {
        "designer": "Designer",
        "validation": "Validation",
        "status": "Status",
        "result": "Result",
        "trace": "Trace",
        "artifacts": "Artifacts",
    }
    key = key_map.get(normalized)
    if key is None:
        return normalized.title() or "Status"
    return ui_text(key, app_language=app_language, fallback_text=fallback_map[normalized])


def _localized_runtime_action_target_label(action_target: str | None, *, app_language: str = "en") -> str | None:
    target = str(action_target or "").strip()
    if not target:
        return None
    if target.startswith("runtime."):
        section_id = target.split(".", 1)[1]
        return _localized_runtime_section_label(section_id, app_language=app_language)
    if target == "designer":
        return _localized_runtime_section_label("designer", app_language=app_language)
    if target == "validation":
        return _localized_runtime_section_label("validation", app_language=app_language)
    return target

def _result_history_section(
    recent_run_rows: Sequence[Mapping[str, Any]],
    workspace_id: str,
    result_rows_by_run_id: Mapping[str, Mapping[str, Any]] | None,
) -> dict[str, Any]:
    result_rows_by_run_id = result_rows_by_run_id or {}
    entries: list[dict[str, Any]] = []
    for row in _recent_run_rows_for_workspace(recent_run_rows, workspace_id):
        run_id = str(row.get("run_id") or "").strip()
        if not run_id:
            continue
        result_row = result_rows_by_run_id.get(run_id) or {}
        result_state = str(result_row.get("result_state") or "missing").strip() or "missing"
        summary = str(result_row.get("result_summary") or result_row.get("final_status") or "No result summary.").strip() or "No result summary."
        entries.append({
            "run_id": run_id,
            "result_state": result_state,
            "summary": summary,
        })
    latest = entries[0] if entries else None
    controls: list[dict[str, Any]] = [
        {
            "control_id": "result-history-open-latest",
            "label": "Open latest result",
            "action_kind": "focus_section",
            "action_target": "runtime.result",
        }
    ]
    if len(entries) > 1:
        previous = entries[1]
        controls.append(
            {
                "control_id": f"result-history-open-{previous['run_id']}",
                "label": f"Open {previous['run_id']} result",
                "action_kind": "open_run_result",
                "action_target": previous["run_id"],
            }
        )
    return build_shell_section(
        headline="Result history",
        lines=_summary_lines(
            f"Recent results: {len(entries)}" if entries else "No recent result history is available yet.",
            f"Latest: {latest['run_id']} — {latest['result_state']}" if latest else None,
        ),
        detail_title="Result history detail",
        detail_items=[f"{index + 1}. {entry['run_id']} — {entry['result_state']} — {entry['summary']}" for index, entry in enumerate(entries[:3])],
        detail_empty="Result history entries will appear here as runs complete.",
        controls=controls,
        history=entries[:3],
    )



def _recent_activity_entries(
    recent_run_rows: Sequence[Mapping[str, Any]],
    onboarding_rows: Sequence[Mapping[str, Any]],
    workspace_id: str,
) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for row in _recent_run_rows_for_workspace(recent_run_rows, workspace_id):
        run_id = str(row.get("run_id") or "").strip()
        if not run_id:
            continue
        status_family = str(row.get("status_family") or row.get("status") or "unknown").strip() or "unknown"
        occurred_at = str(row.get("updated_at") or row.get("created_at") or "").strip() or None
        entries.append({
            "activity_id": f"run:{run_id}:{occurred_at or ''}",
            "activity_type": "run",
            "label": run_id,
            "status": status_family,
            "occurred_at": occurred_at,
            "summary": f"Run {run_id} reached {status_family}.",
        })
    for row in _recent_onboarding_rows_for_workspace(onboarding_rows, workspace_id):
        onboarding_state_id = str(row.get("onboarding_state_id") or "").strip() or "onboarding"
        current_step = str(row.get("current_step") or "updated").strip() or "updated"
        occurred_at = str(row.get("updated_at") or row.get("created_at") or "").strip() or None
        entries.append({
            "activity_id": f"onboarding:{onboarding_state_id}:{occurred_at or ''}",
            "activity_type": "onboarding",
            "label": onboarding_state_id,
            "status": current_step,
            "occurred_at": occurred_at,
            "summary": f"Onboarding moved to {current_step}.",
        })
    entries.sort(key=lambda item: (str(item.get("occurred_at") or ""), str(item.get("activity_id") or "")), reverse=True)
    return entries[:5]


def _recent_activity_section(
    recent_run_rows: Sequence[Mapping[str, Any]],
    onboarding_rows: Sequence[Mapping[str, Any]],
    workspace_id: str,
    *,
    app_language: str = "en",
) -> dict[str, Any]:
    entries = _recent_activity_entries(recent_run_rows, onboarding_rows, workspace_id)
    latest = entries[0] if entries else None
    return build_shell_section(
        headline=ui_text("server.shell.recent_activity", app_language=app_language, fallback_text="Recent activity"),
        lines=_summary_lines(
            ui_text("server.shell.activity_items_prefix", app_language=app_language, fallback_text="Activity items: ") + str(len(entries)) if entries else ui_text("server.shell.no_recent_activity", app_language=app_language, fallback_text="No recent activity is available yet."),
            ui_text("server.shell.latest_prefix", app_language=app_language, fallback_text="Latest: ") + f"{latest['activity_type']} — {latest['label']}" if latest else None,
        ),
        detail_title=ui_text("server.shell.recent_activity_detail", app_language=app_language, fallback_text="Recent activity detail"),
        detail_items=[
            f"{index + 1}. {entry['activity_type']} — {entry['label']} — {entry['status']}"
            for index, entry in enumerate(entries[:3])
        ],
        detail_empty=ui_text("server.shell.recent_activity_pending", app_language=app_language, fallback_text="Recent activity entries will appear here as work continues."),
        controls=[
            {
                "control_id": "recent-activity-open-route",
                "label": ui_text("server.shell.open_recent_activity", app_language=app_language, fallback_text="Open recent activity"),
                "action_kind": "open_route",
                "action_target": f"/api/users/me/activity?workspace_id={workspace_id}",
            }
        ],
        history=entries[:3],
    )


def _matching_share_history_entries(
    share_payload_rows: Sequence[Mapping[str, Any]],
    model: Any,
) -> list[dict[str, Any]]:
    canonical_ref = _artifact_canonical_ref_for_model(model)
    if not canonical_ref:
        return []
    entries: list[dict[str, Any]] = []
    for row in share_payload_rows:
        try:
            descriptor = describe_public_nex_link_share(dict(row))
        except Exception:
            continue
        if str(descriptor.canonical_ref or "").strip() != canonical_ref:
            continue
        entries.append({
            "share_id": descriptor.share_id,
            "state": descriptor.lifecycle_state,
            "title": descriptor.title,
            "updated_at": descriptor.updated_at,
        })
    entries.sort(key=lambda item: (str(item.get("updated_at") or ""), str(item.get("share_id") or "")), reverse=True)
    return entries


def _history_summary_section(
    recent_run_rows: Sequence[Mapping[str, Any]],
    onboarding_rows: Sequence[Mapping[str, Any]],
    share_payload_rows: Sequence[Mapping[str, Any]],
    model: Any,
    workspace_id: str,
    *,
    app_language: str = "en",
) -> dict[str, Any]:
    run_entries = list(_recent_run_rows_for_workspace(recent_run_rows, workspace_id, limit=50))
    onboarding_entries = list(_recent_onboarding_rows_for_workspace(onboarding_rows, workspace_id, limit=50))
    share_entries = _matching_share_history_entries(share_payload_rows, model)
    pending_runs = sum(1 for row in run_entries if str(row.get("status_family") or "").strip() == "pending")
    active_runs = sum(1 for row in run_entries if str(row.get("status_family") or "").strip() == "active")
    success_runs = sum(1 for row in run_entries if str(row.get("status_family") or "").strip() == "terminal_success")
    failure_runs = sum(1 for row in run_entries if str(row.get("status_family") or "").strip() == "terminal_failure")
    latest_values = [
        str(row.get("updated_at") or row.get("created_at") or "").strip()
        for row in run_entries
    ] + [
        str(row.get("updated_at") or row.get("created_at") or "").strip()
        for row in onboarding_entries
    ] + [
        str(entry.get("updated_at") or "").strip()
        for entry in share_entries
    ]
    latest_activity_at = max([value for value in latest_values if value], default=None)
    return build_shell_section(
        headline=ui_text("server.shell.history_summary", app_language=app_language, fallback_text="History summary"),
        lines=_summary_lines(
            ui_text("server.shell.total_runs_prefix", app_language=app_language, fallback_text="Total runs: ") + str(len(run_entries)),
            ui_text("server.shell.successful_runs_prefix", app_language=app_language, fallback_text="Successful runs: ") + str(success_runs),
            ui_text("server.shell.latest_activity_at_prefix", app_language=app_language, fallback_text="Latest activity at: ") + latest_activity_at if latest_activity_at else None,
        ),
        detail_title=ui_text("server.shell.history_summary_detail", app_language=app_language, fallback_text="History summary detail"),
        detail_items=[
            ui_text("server.shell.pending_runs_prefix", app_language=app_language, fallback_text="Pending runs: ") + str(pending_runs),
            ui_text("server.shell.active_runs_prefix", app_language=app_language, fallback_text="Active runs: ") + str(active_runs),
            ui_text("server.shell.failed_runs_prefix", app_language=app_language, fallback_text="Failed runs: ") + str(failure_runs),
            ui_text("server.shell.onboarding_updates_prefix", app_language=app_language, fallback_text="Onboarding updates: ") + str(len(onboarding_entries)),
            ui_text("server.shell.share_history_entries_prefix", app_language=app_language, fallback_text="Share history entries: ") + str(len(share_entries)),
        ],
        controls=[
            {
                "control_id": "history-summary-open-route",
                "label": ui_text("server.shell.open_history_summary", app_language=app_language, fallback_text="Open history summary"),
                "action_kind": "open_route",
                "action_target": f"/api/users/me/history-summary?workspace_id={workspace_id}",
            },
            {
                "control_id": "history-summary-open-activity",
                "label": ui_text("server.shell.open_recent_activity", app_language=app_language, fallback_text="Open recent activity"),
                "action_kind": "open_route",
                "action_target": f"/api/users/me/activity?workspace_id={workspace_id}",
            },
        ],
        history=[{
            "total_runs": len(run_entries),
            "successful_runs": success_runs,
            "failed_runs": failure_runs,
            "onboarding_updates": len(onboarding_entries),
            "share_history_entries": len(share_entries),
            "latest_activity_at": latest_activity_at,
        }],
    )


def _artifact_mapping_from_source(source: Any | None, model: Any) -> dict[str, Any]:
    if isinstance(source, Mapping):
        return json.loads(json.dumps(source))
    if isinstance(model, WorkingSaveModel):
        return {
            "meta": {
                "format_version": model.meta.format_version,
                "storage_role": "working_save",
                "working_save_id": model.meta.working_save_id,
                "name": model.meta.name,
                "description": model.meta.description,
                "created_at": model.meta.created_at,
                "updated_at": model.meta.updated_at,
            },
            "circuit": {
                "nodes": list(model.circuit.nodes),
                "edges": list(model.circuit.edges),
                "entry": model.circuit.entry,
                "outputs": list(model.circuit.outputs),
                "subcircuits": dict(model.circuit.subcircuits),
            },
            "resources": {
                "prompts": dict(model.resources.prompts),
                "providers": dict(model.resources.providers),
                "plugins": dict(model.resources.plugins),
            },
            "state": {
                "input": dict(model.state.input),
                "working": dict(model.state.working),
                "memory": dict(model.state.memory),
            },
            "runtime": {
                "status": model.runtime.status,
                "validation_summary": dict(model.runtime.validation_summary),
                "last_run": dict(model.runtime.last_run),
                "errors": list(model.runtime.errors),
            },
            "ui": {"layout": dict(model.ui.layout), "metadata": dict(model.ui.metadata)},
            "designer": dict(model.designer.data) if model.designer is not None else {},
        }
    return {}


def _trace_history_section(
    recent_run_rows: Sequence[Mapping[str, Any]],
    workspace_id: str,
    trace_rows_lookup: Any | None,
    *,
    app_language: str = "en",
) -> dict[str, Any]:
    entries: list[dict[str, Any]] = []
    for row in _recent_run_rows_for_workspace(recent_run_rows, workspace_id):
        run_id = str(row.get("run_id") or "").strip()
        if not run_id:
            continue
        trace_rows = tuple(trace_rows_lookup(run_id) or ()) if trace_rows_lookup is not None else ()
        if not trace_rows:
            continue
        ordered = sorted(
            trace_rows,
            key=lambda item: (int(item.get("sequence_number") or 0), str(item.get("occurred_at") or "")),
        )
        latest = ordered[-1]
        entries.append(
            {
                "run_id": run_id,
                "event_count": len(ordered),
                "latest_event_type": str(latest.get("event_type") or "").strip() or None,
                "latest_node_id": str(latest.get("node_id") or "").strip() or None,
            }
        )
    latest = entries[0] if entries else None
    controls: list[dict[str, Any]] = [
        {
            "control_id": "trace-history-open-latest",
            "label": ui_text("server.shell.trace_history_open_latest", app_language=app_language, fallback_text="Open latest trace"),
            "action_kind": "focus_section",
            "action_target": "runtime.trace",
        }
    ]
    if len(entries) > 1:
        previous = entries[1]
        controls.append(
            {
                "control_id": f"trace-history-open-{previous['run_id']}",
                "label": ui_text("server.shell.trace_history_open_for", app_language=app_language, fallback_text="Open {run_id} trace", run_id=str(previous["run_id"])),
                "action_kind": "open_run_trace",
                "action_target": previous["run_id"],
            }
        )
    return build_shell_section(
        headline=ui_text("server.shell.trace_history", app_language=app_language, fallback_text="Trace history"),
        lines=_summary_lines(
            ui_text("server.shell.recent_traces_prefix", app_language=app_language, fallback_text="Recent traces: ") + str(len(entries)) if entries else ui_text("server.shell.no_recent_trace_history", app_language=app_language, fallback_text="No recent trace history is available yet."),
            ui_text("server.shell.latest_prefix", app_language=app_language, fallback_text="Latest: ") + f"{latest['run_id']} — {latest['event_count']} {ui_text('server.shell.events_suffix', app_language=app_language, fallback_text='events')}" if latest else None,
        ),
        detail_title=ui_text("server.shell.trace_detail_title", app_language=app_language, fallback_text="Trace detail"),
        detail_items=[
            f"{index + 1}. {entry['run_id']} — {entry['event_count']} {ui_text('server.shell.events_suffix', app_language=app_language, fallback_text='events')}"
            + (f" — latest: {entry['latest_event_type']}" if entry.get("latest_event_type") else "")
            for index, entry in enumerate(entries[:3])
        ],
        detail_empty=ui_text("server.shell.trace_history_entries_pending", app_language=app_language, fallback_text="Trace history entries will appear here as runs accumulate."),
        controls=controls,
        history=entries[:3],
    )


def _artifacts_history_section(
    recent_run_rows: Sequence[Mapping[str, Any]],
    workspace_id: str,
    artifact_rows_lookup: Any | None,
) -> dict[str, Any]:
    entries: list[dict[str, Any]] = []
    for row in _recent_run_rows_for_workspace(recent_run_rows, workspace_id):
        run_id = str(row.get("run_id") or "").strip()
        if not run_id:
            continue
        artifact_rows = tuple(artifact_rows_lookup(run_id) or ()) if artifact_rows_lookup is not None else ()
        if not artifact_rows:
            continue
        first = artifact_rows[0]
        entries.append(
            {
                "run_id": run_id,
                "artifact_count": len(artifact_rows),
                "first_artifact_id": str(first.get("artifact_id") or "").strip() or None,
                "first_label": str(first.get("label") or first.get("payload_preview") or "").strip() or None,
            }
        )
    latest = entries[0] if entries else None
    controls: list[dict[str, Any]] = [
        {
            "control_id": "artifacts-history-open-latest",
            "label": "Open latest artifacts",
            "action_kind": "focus_section",
            "action_target": "runtime.artifacts",
        }
    ]
    if len(entries) > 1:
        previous = entries[1]
        controls.append(
            {
                "control_id": f"artifacts-history-open-{previous['run_id']}",
                "label": f"Open {previous['run_id']} artifacts",
                "action_kind": "open_run_artifacts",
                "action_target": previous["run_id"],
            }
        )
    return build_shell_section(
        headline="Artifacts history",
        lines=_summary_lines(
            f"Recent artifact sets: {len(entries)}" if entries else "No recent artifacts history is available yet.",
            f"Latest: {latest['run_id']} — {latest['artifact_count']} artifacts" if latest else None,
        ),
        detail_title="Artifacts history detail",
        detail_items=[
            f"{index + 1}. {entry['run_id']} — {entry['artifact_count']} artifacts"
            + (f" — first: {entry['first_artifact_id']}" if entry.get("first_artifact_id") else "")
            for index, entry in enumerate(entries[:3])
        ],
        detail_empty="Artifacts history entries will appear here as runs accumulate.",
        controls=controls,
        history=entries[:3],
    )


def _server_backed_shell_state(source: Any | None, model: Any) -> dict[str, Mapping[str, Any]]:
    mapping = _artifact_mapping_from_source(source, model)
    designer_state = {}
    validation_state = {}
    designer = mapping.get("designer") if isinstance(mapping, Mapping) else None
    if isinstance(designer, Mapping):
        raw = designer.get("server_backed_shell_state")
        if isinstance(raw, Mapping):
            designer_state = dict(raw)
    ui = mapping.get("ui") if isinstance(mapping, Mapping) else None
    if isinstance(ui, Mapping):
        metadata = ui.get("metadata")
        if isinstance(metadata, Mapping):
            raw = metadata.get("runtime_shell_server_state")
            if isinstance(raw, Mapping):
                validation_state = dict(raw)
    return {"designer": designer_state, "validation": validation_state}

def _designer_section(
    shell: Mapping[str, Any] | None,
    template_gallery: Mapping[str, Any] | None,
    persisted_state: Mapping[str, Any] | None = None,
    *,
    app_language: str = "en",
) -> dict[str, Any]:
    shell_map = shell or {}
    designer = shell_map.get("designer") or {}
    request_state = designer.get("request_state") or {}
    preview_state = designer.get("preview_state") or {}
    approval_state = designer.get("approval_state") or {}
    provider_inline = designer.get("provider_inline_key_entry") or {}
    provider_guidance = designer.get("provider_setup_guidance") or {}
    gallery = template_gallery or designer.get("template_gallery") or {}
    templates = tuple(gallery.get("templates") or ())
    template_count = len(templates)
    connected_count = int(provider_inline.get("connected_count") or 0)
    summary_text = (
        str(preview_state.get("one_sentence_summary") or "").strip()
        or str(request_state.get("input_placeholder") or "").strip()
        or "Start from Designer to describe your goal or choose a starter template."
    )
    persisted = dict(persisted_state or {})
    persisted_template_display = persisted.get("selected_template_display_name") or persisted.get("selected_template_id")
    persisted_lookup_aliases = persisted.get("selected_template_lookup_aliases") or ()
    if isinstance(persisted_lookup_aliases, str):
        persisted_lookup_aliases = (persisted_lookup_aliases,)
    persisted_lookup_aliases = tuple(
        str(item).strip() for item in persisted_lookup_aliases if str(item).strip()
    )
    lines = _summary_lines(
        f"Request status: {request_state.get('request_status')}" if request_state.get("request_status") else None,
        f"Preview status: {preview_state.get('preview_status')}" if preview_state.get("preview_status") else None,
        f"Approval status: {approval_state.get('approval_status')}" if approval_state.get("approval_status") else None,
        f"Templates available: {template_count}",
        f"Connected providers: {connected_count}",
        f"Persisted template: {persisted_template_display}" if persisted_template_display else None,
    )
    detail_items = _summary_lines(
        f"Submit enabled: {request_state.get('can_submit')}" if request_state.get("can_submit") is not None else None,
        f"Current request: {request_state.get('current_request_text')}" if request_state.get("current_request_text") else None,
        f"Persisted request: {persisted.get('request_text')}" if persisted.get("request_text") else None,
        ui_text(
            "server.shell.template_ref",
            app_language=app_language,
            fallback_text="Template ref: {template_ref}",
            template_ref=str(persisted.get("selected_template_ref") or "").strip(),
        ) if persisted.get("selected_template_ref") else None,
        ui_text(
            "server.shell.template_lookup_aliases",
            app_language=app_language,
            fallback_text="Lookup aliases: {aliases}",
            aliases=", ".join(persisted_lookup_aliases),
        ) if persisted_lookup_aliases else None,
        ui_text(
            "server.shell.template_provenance",
            app_language=app_language,
            fallback_text="Provenance: {source} / {family}",
            source=str(persisted.get("selected_template_provenance_source") or "").strip(),
            family=str(persisted.get("selected_template_provenance_family") or "").strip(),
        ) if persisted.get("selected_template_provenance_source") or persisted.get("selected_template_provenance_family") else None,
        ui_text(
            "server.shell.template_compatibility",
            app_language=app_language,
            fallback_text="Compatibility: {family} / {behavior}",
            family=str(persisted.get("selected_template_compatibility_family") or "").strip(),
            behavior=str(persisted.get("selected_template_apply_behavior") or "").strip(),
        ) if persisted.get("selected_template_compatibility_family") or persisted.get("selected_template_apply_behavior") else None,
        f"Last designer action: {persisted.get('last_action')}" if persisted.get("last_action") else None,
        f"Provider setup summary: {provider_guidance.get('summary')}" if provider_guidance.get("summary") else None,
        *[
            f"Suggested action: {action.get('label')}"
            for action in (designer.get("suggested_actions") or [])
            if isinstance(action, Mapping) and action.get("label")
        ][:3],
    )
    controls: list[dict[str, Any]] = [
        {
            "control_id": "designer-open-detail",
            "label": "Open Designer detail",
            "action_kind": "focus_section",
            "action_target": "designer.detail",
        },
        {
            "control_id": "designer-open-templates",
            "label": "Open starter templates",
            "action_kind": "focus_auxiliary",
            "action_target": "templates",
        },
    ]
    if templates:
        first_template = templates[0]
        lookup_aliases = tuple(
            str(item).strip() for item in (first_template.get("lookup_aliases") or ()) if str(item).strip()
        )
        controls.insert(
            0,
            {
                "control_id": f"designer-template-{first_template.get('template_id') or 'primary'}",
                "label": f"Use {str(first_template.get('display_name') or ui_text('server.shell.starter_template_fallback', app_language=app_language, fallback_text='starter template')).strip()}",
                "action_kind": "apply_template",
                "action_target": str(first_template.get("template_ref") or first_template.get("template_id") or "").strip() or "template",
                "request_text": str(first_template.get("designer_request_text") or "").strip() or None,
                "template_id": str(first_template.get("template_id") or "").strip() or None,
                "template_ref": str(first_template.get("template_ref") or "").strip() or None,
                "template_display_name": str(first_template.get("display_name") or "").strip() or None,
                "template_summary": str(first_template.get("summary") or "").strip() or None,
                "template_category": str(first_template.get("category") or "").strip() or None,
                "template_lookup_aliases": list(lookup_aliases),
                "template_identity": dict(first_template.get("identity") or {}),
                "template_provenance": dict(first_template.get("provenance") or {}),
                "template_compatibility": dict(first_template.get("compatibility") or {}),
            },
        )
    return {
        "summary": {"headline": "Designer workspace", "lines": [summary_text, *lines]},
        "detail": {"title": "Designer detail", "items": detail_items or ["Use Designer to draft or review the workflow before running."]},
        "controls": controls,
    }


def _validation_section(shell: Mapping[str, Any] | None, *, runnable: bool = False, persisted_state: Mapping[str, Any] | None = None) -> dict[str, Any]:
    shell_map = shell or {}
    validation = shell_map.get("validation") or {}
    summary_block = validation.get("summary") or {}
    beginner_summary = validation.get("beginner_summary") or {}
    overall_status = str(validation.get("overall_status") or "unknown").strip() or "unknown"
    headline = f"Validation: {overall_status}"
    primary_line = str(beginner_summary.get("cause") or beginner_summary.get("status_signal") or "Review validation before the next step.").strip() or "Review validation before the next step."
    persisted = dict(persisted_state or {})
    lines = _summary_lines(
        primary_line,
        f"Blocking findings: {summary_block.get('blocking_count')}" if summary_block.get("blocking_count") is not None else None,
        f"Warnings: {summary_block.get('warning_count')}" if summary_block.get("warning_count") is not None else None,
        f"Next action: {beginner_summary.get('next_action_label')}" if beginner_summary.get("next_action_label") else None,
        f"Persisted validation action: {persisted.get('validation_action')}" if persisted.get("validation_action") else None,
    )
    detail_items = _summary_lines(
        f"Requires confirmation: {summary_block.get('requires_user_confirmation')}" if summary_block.get("requires_user_confirmation") is not None else None,
        f"Can execute: {summary_block.get('can_execute')}" if summary_block.get("can_execute") is not None else None,
        f"Top issue: {summary_block.get('top_issue_label')}" if summary_block.get("top_issue_label") else None,
        f"Persisted validation status: {persisted.get('validation_status')}" if persisted.get("validation_status") else None,
        f"Persisted validation message: {persisted.get('validation_message')}" if persisted.get("validation_message") else None,
        *[
            f"Suggested action: {action.get('label')}"
            for action in (validation.get("suggested_actions") or [])
            if isinstance(action, Mapping) and action.get("label")
        ][:3],
    )
    controls: list[dict[str, Any]] = [
        {
            "control_id": "validation-open-detail",
            "label": "Open Validation detail",
            "action_kind": "focus_section",
            "action_target": "validation.detail",
        },
        {
            "control_id": "validation-open-help",
            "label": "Open contextual help",
            "action_kind": "focus_auxiliary",
            "action_target": "help",
        },
    ]
    can_execute = bool(summary_block.get("can_execute"))
    if runnable and can_execute:
        controls.insert(
            0,
            {
                "control_id": "validation-run-draft",
                "label": "Run draft",
                "action_kind": "run_draft",
                "action_target": "execution",
            },
        )
    elif overall_status == "blocked" or summary_block.get("blocking_count"):
        controls.insert(
            0,
            {
                "control_id": "validation-open-designer",
                "label": "Open Designer",
                "action_kind": "focus_section",
                "action_target": "designer.detail",
            },
        )
    return {
        "summary": {"headline": headline, "lines": lines},
        "detail": {"title": "Validation detail", "items": detail_items or ["Validation details will appear here as findings accumulate."]},
        "controls": controls,
    }



def _navigation_model(
    shell: Mapping[str, Any] | None,
    *,
    app_language: str = "en",
    latest_run_status_preview: Mapping[str, Any] | None,
    latest_run_result_preview: Mapping[str, Any] | None,
    latest_run_trace_preview: Mapping[str, Any] | None,
    latest_run_artifacts_preview: Mapping[str, Any] | None,
    onboarding_state: Mapping[str, Any] | None,
) -> dict[str, Any]:
    sections = (
        {"section_id": "designer", "label": _localized_runtime_section_label("designer", app_language=app_language), "target_id": "designer-summary-card", "detail_target_id": "designer-detail-card"},
        {"section_id": "validation", "label": _localized_runtime_section_label("validation", app_language=app_language), "target_id": "validation-summary-card", "detail_target_id": "validation-detail-card"},
        {"section_id": "status", "label": _localized_runtime_section_label("status", app_language=app_language), "target_id": "latest-run-status-card", "detail_target_id": "latest-run-status-detail-card"},
        {"section_id": "result", "label": _localized_runtime_section_label("result", app_language=app_language), "target_id": "latest-run-result-card", "detail_target_id": "latest-run-result-detail-card"},
        {"section_id": "trace", "label": _localized_runtime_section_label("trace", app_language=app_language), "target_id": "latest-run-trace-card", "detail_target_id": "latest-run-trace-detail-card"},
        {"section_id": "artifacts", "label": _localized_runtime_section_label("artifacts", app_language=app_language), "target_id": "latest-run-artifacts-card", "detail_target_id": "latest-run-artifacts-detail-card"},
    )
    shell_map = shell or {}
    mobile = shell_map.get("mobile_first_run") or {}
    contextual_help = shell_map.get("contextual_help") or {}
    beginner_onboarding = shell_map.get("beginner_onboarding") or {}
    validation = shell_map.get("validation") or {}
    mobile_visible = bool(mobile.get("visible"))
    primary_action_target = str(mobile.get("primary_action_target") or "").strip()
    onboarding_target = str(beginner_onboarding.get("primary_action_target") or "").strip()
    help_stage = str(contextual_help.get("stage") or "").strip().lower()
    shell_status = str(shell_map.get("shell_status") or "").strip().lower()
    validation_status = str(validation.get("overall_status") or "").strip().lower()
    latest_status = str((latest_run_status_preview or {}).get("status") or "").strip().lower()
    latest_result_state = str((latest_run_result_preview or {}).get("result_state") or "").strip().lower()
    latest_trace_count = int((latest_run_trace_preview or {}).get("event_count") or 0)
    latest_artifact_count = int((latest_run_artifacts_preview or {}).get("artifact_count") or 0)
    onboarding_step = _normalized_onboarding_current_step(onboarding_state)

    default_section = "status"
    default_level = "summary"
    guidance_label = ui_text("server.shell.recommended_next", app_language=app_language, fallback_text="Recommended next: {section}", section=_localized_runtime_section_label("status", app_language=app_language))
    guidance_summary = "Open status first to follow the current runtime state."

    if mobile_visible:
        if shell_status == "blocked" or validation_status == "blocked" or onboarding_target == "validation":
            default_section = "validation"
            default_level = "detail"
            guidance_label = ui_text("server.shell.recommended_next", app_language=app_language, fallback_text="Recommended next: {section}", section=_localized_runtime_section_label("validation", app_language=app_language))
            guidance_summary = "Resolve the blocking validation issue before continuing the first-run path."
        elif latest_result_state.startswith("ready") or primary_action_target == "execution.output" or help_stage == "result":
            default_section = "result"
            default_level = "detail"
            guidance_label = ui_text("server.shell.recommended_next", app_language=app_language, fallback_text="Recommended next: {section}", section=_localized_runtime_section_label("result", app_language=app_language))
            guidance_summary = "A readable result is ready, so the mobile first-run path should move to Result next."
        elif latest_status in {"failed", "partial"} and latest_trace_count > 0:
            default_section = "trace"
            default_level = "detail"
            guidance_label = ui_text("server.shell.recommended_next", app_language=app_language, fallback_text="Recommended next: {section}", section=_localized_runtime_section_label("trace", app_language=app_language))
            guidance_summary = "The latest run needs explanation, so open Trace next in the first-run path."
        elif latest_artifact_count > 0 and latest_result_state.startswith("missing"):
            default_section = "artifacts"
            default_level = "detail"
            guidance_label = ui_text("server.shell.recommended_next", app_language=app_language, fallback_text="Recommended next: {section}", section=_localized_runtime_section_label("artifacts", app_language=app_language))
            guidance_summary = "Artifacts are available before a readable result summary, so open Artifacts next."
        elif latest_status in {"running", "queued"} or primary_action_target == "execution" or help_stage == "wait":
            default_section = "status"
            default_level = "summary"
            guidance_label = ui_text("server.shell.recommended_next", app_language=app_language, fallback_text="Recommended next: {section}", section=_localized_runtime_section_label("status", app_language=app_language))
            guidance_summary = "The mobile first-run path is still in progress, so follow Status first."
        elif onboarding_step == "read_result":
            default_section = "result"
            default_level = "detail"
            guidance_label = ui_text("server.shell.recommended_next", app_language=app_language, fallback_text="Recommended next: {section}", section=_localized_runtime_section_label("result", app_language=app_language))
            guidance_summary = "Server-backed workspace progression points to Result as the next first-run step."
        elif onboarding_step == "run":
            default_section = "status"
            default_level = "summary"
            guidance_label = ui_text("server.shell.recommended_next", app_language=app_language, fallback_text="Recommended next: {section}", section=_localized_runtime_section_label("status", app_language=app_language))
            guidance_summary = "Server-backed workspace progression points to Status while the run step is active."
        elif onboarding_step in {"review_preview", "approve"}:
            default_section = "validation"
            default_level = "detail"
            guidance_label = ui_text("server.shell.recommended_next", app_language=app_language, fallback_text="Recommended next: {section}", section=_localized_runtime_section_label("validation", app_language=app_language))
            guidance_summary = "Server-backed workspace progression points to Validation before the run step."
        elif onboarding_target == "designer" or onboarding_step == "enter_goal" or help_stage in {"start", "review"} or primary_action_target == "designer":
            default_section = "designer"
            default_level = "detail"
            guidance_label = ui_text("server.shell.recommended_next", app_language=app_language, fallback_text="Recommended next: {section}", section=_localized_runtime_section_label("designer", app_language=app_language))
            guidance_summary = "Use Designer first to describe or review the workflow before running."
        else:
            default_section = "designer"
            default_level = "detail"
            guidance_label = ui_text("server.shell.recommended_next", app_language=app_language, fallback_text="Recommended next: {section}", section=_localized_runtime_section_label("designer", app_language=app_language))
            guidance_summary = "Start with Designer, then move to Validation and Run when the workflow is ready."

    return {
        "default_section": default_section,
        "default_level": default_level,
        "guidance_label": guidance_label,
        "guidance_summary": guidance_summary,
        "sections": [dict(item) for item in sections],
    }


def _step_state_banner(
    shell: Mapping[str, Any] | None,
    *,
    app_language: str = "en",
    latest_run_status_preview: Mapping[str, Any] | None,
    latest_run_result_preview: Mapping[str, Any] | None,
    latest_run_trace_preview: Mapping[str, Any] | None,
    latest_run_artifacts_preview: Mapping[str, Any] | None,
    navigation: Mapping[str, Any] | None,
    onboarding_state: Mapping[str, Any] | None,
) -> dict[str, Any] | None:
    shell_map = shell or {}
    mobile = shell_map.get("mobile_first_run") or {}
    beginner_onboarding = shell_map.get("beginner_onboarding") or {}
    contextual_help = shell_map.get("contextual_help") or {}
    steps = tuple(mobile.get("steps") or ())
    if not steps:
        return None

    current_step_id = "enter_goal"
    step_index: dict[str, int] = {}
    step_label: dict[str, str] = {}
    fallback_step: Mapping[str, Any] | None = None
    active_step: Mapping[str, Any] | None = None
    for index, step in enumerate(steps, start=1):
        if not isinstance(step, Mapping):
            continue
        step_id = str(step.get("step_id") or "").strip()
        if not step_id:
            continue
        step_index[step_id] = index
        step_label[step_id] = str(step.get("label") or step_id).strip() or step_id
        if fallback_step is None:
            fallback_step = step
        if str(step.get("status") or "") == "active" and active_step is None:
            active_step = step
            current_step_id = step_id
    fallback_step = active_step or fallback_step

    latest_status = str((latest_run_status_preview or {}).get("status") or "").strip().lower()
    latest_result_state = str((latest_run_result_preview or {}).get("result_state") or "").strip().lower()
    latest_trace_count = int((latest_run_trace_preview or {}).get("event_count") or 0)
    latest_artifact_count = int((latest_run_artifacts_preview or {}).get("artifact_count") or 0)
    recommended_section = str((navigation or {}).get("default_section") or "status").strip() or "status"
    onboarding_step = _normalized_onboarding_current_step(onboarding_state)
    action_label: str | None = None
    action_target: str | None = None
    phase = "pre_run"

    if latest_result_state.startswith("ready"):
        current_step_id = "read_result"
        severity = "success"
        summary = ui_text("server.shell.result_ready_summary", app_language=app_language, fallback_text="Result is ready. Open Result next to finish the first-run path.")
        action_label = ui_text("server.shell.open_result", app_language=app_language, fallback_text="Open Result")
        action_target = "runtime.result"
        phase = "post_run"
    elif latest_status in {"failed", "partial"} and latest_trace_count > 0:
        current_step_id = "run"
        severity = "warning"
        summary = ui_text("server.shell.run_needs_diagnosis_summary", app_language=app_language, fallback_text="Run needs diagnosis. Open Trace next to understand what happened.")
        action_label = ui_text("server.shell.open_trace", app_language=app_language, fallback_text="Open Trace")
        action_target = "runtime.trace"
        phase = "post_run"
    elif latest_artifact_count > 0 and not latest_result_state.startswith("ready"):
        current_step_id = "read_result"
        severity = "info"
        summary = ui_text("server.shell.artifacts_ready_summary", app_language=app_language, fallback_text="A readable result is not ready yet, but artifacts are available. Open Artifacts next.")
        action_label = ui_text("server.shell.open_artifacts", app_language=app_language, fallback_text="Open Artifacts")
        action_target = "runtime.artifacts"
        phase = "post_run"
    elif latest_status in {"running", "queued", "accepted"}:
        current_step_id = "run"
        severity = "info"
        summary = ui_text("server.shell.run_in_progress_summary", app_language=app_language, fallback_text="Run is in progress. Watch Status while Nexa prepares the result.")
        action_label = ui_text("server.shell.open_status", app_language=app_language, fallback_text="Open Status")
        action_target = "runtime.status"
        phase = "running"
    else:
        severity = "info"
        summary_by_step = {
            "enter_goal": "Describe your goal to start the first-run path.",
            "review_preview": "Review the proposed workflow preview before approving.",
            "approve": "Approve the proposed workflow so Nexa can prepare it for running.",
            "run": "Run the workflow to generate your first result.",
            "read_result": "Read the result to finish the first-run path.",
        }
        summary = summary_by_step.get(current_step_id, "Follow the guided first-run path one step at a time.")
        shell_status = str(shell_map.get("shell_status") or "").strip().lower()
        onboarding_target = str(beginner_onboarding.get("primary_action_target") or "").strip()
        help_stage = str(contextual_help.get("stage") or "").strip().lower()
        if onboarding_step in {"review_preview", "approve"}:
            current_step_id = onboarding_step
            summary = "Server-backed workspace progression says review and validation come next before the run step."
            action_label = ui_text("server.shell.review_validation_action", app_language=app_language, fallback_text="Review Validation")
            action_target = "validation.detail"
        elif onboarding_step == "enter_goal":
            current_step_id = "enter_goal"
            summary = "Server-backed workspace progression says start in Designer by describing your goal."
            action_label = ui_text("server.shell.open_designer", app_language=app_language, fallback_text="Open Designer")
            action_target = "designer"
        elif onboarding_step == "run":
            current_step_id = "run"
            summary = "Server-backed workspace progression says the run step is next. Open Status to follow it."
            action_label = ui_text("server.shell.open_status", app_language=app_language, fallback_text="Open Status")
            action_target = "runtime.status"
        elif onboarding_step == "read_result":
            current_step_id = "read_result"
            summary = "Server-backed workspace progression says read the latest result next."
            action_label = ui_text("server.shell.open_result", app_language=app_language, fallback_text="Open Result")
            action_target = "runtime.result"
            phase = "post_run"
        elif shell_status == "blocked":
            severity = "warning"
            current_step_id = "review_preview"
            summary = str(beginner_onboarding.get("summary") or contextual_help.get("summary") or "Resolve the blocking review issue before you run.")
            action_label = str(beginner_onboarding.get("primary_action_label") or "Open Validation").strip() or "Open Validation"
            action_target = onboarding_target or "validation"
        elif onboarding_target == "designer":
            summary = str(beginner_onboarding.get("summary") or contextual_help.get("summary") or summary)
            action_label = str(beginner_onboarding.get("primary_action_label") or "Open Designer").strip() or "Open Designer"
            action_target = "designer"
        elif help_stage == "review":
            current_step_id = "review_preview"
            summary = str(contextual_help.get("summary") or summary)
            action_label = "Review preview"
            action_target = "designer"
        elif help_stage == "wait":
            current_step_id = "run"
            summary = str(contextual_help.get("summary") or summary)
            action_label = ui_text("server.shell.open_status", app_language=app_language, fallback_text="Open Status")
            action_target = "runtime.status"
        elif current_step_id == "run":
            action_label = ui_text("server.shell.run_draft_action", app_language=app_language, fallback_text="Run draft")
            action_target = "execution"
        elif current_step_id == "read_result":
            action_label = ui_text("server.shell.open_result", app_language=app_language, fallback_text="Open Result")
            action_target = "runtime.result"

    total_steps = max(len(step_index), 1)
    fallback_step_id = str((fallback_step or {}).get("step_id") or "enter_goal").strip() or "enter_goal"
    current_index = step_index.get(current_step_id) or step_index.get(fallback_step_id) or 1
    current_label = step_label.get(current_step_id) or step_label.get(fallback_step_id) or "Step"
    next_section_label = _localized_runtime_section_label(recommended_section, app_language=app_language)
    if action_target and (str(action_target).startswith("runtime.") or action_target in {"designer", "validation"}):
        action_kind = "focus_section"
    elif action_target == "execution":
        action_kind = "run_draft"
    elif action_target in {"designer.templates", "validation.review"}:
        action_kind = "focus_auxiliary"
    else:
        action_kind = "none"

    return {
        "visible": True,
        "banner_id": current_step_id,
        "severity": severity,
        "phase": phase,
        "title": f"Step {current_index} of {total_steps} — {current_label}",
        "summary": summary,
        "action_label": action_label,
        "action_target": action_target,
        "action_kind": action_kind,
        "current_step_id": current_step_id,
        "current_step_label": current_label,
        "current_step_index": current_index,
        "total_steps": total_steps,
        "recommended_section": recommended_section,
        "recommended_section_label": next_section_label,
    }

def _artifact_canonical_ref_for_model(model: Any) -> str | None:
    if isinstance(model, WorkingSaveModel):
        return str(model.meta.working_save_id or "").strip() or None
    if isinstance(model, CommitSnapshotModel):
        return str(model.meta.commit_id or "").strip() or None
    if isinstance(model, ExecutionRecordModel):
        return str(model.meta.run_id or "").strip() or None
    return None


def _share_history_section(
    share_payload_rows: Sequence[Mapping[str, Any]],
    model: Any,
    workspace_id: str,
    *,
    app_language: str = "en",
) -> dict[str, Any]:
    canonical_ref = _artifact_canonical_ref_for_model(model)
    if not canonical_ref:
        return build_shell_section(
            headline=ui_text("server.shell.share_history", app_language=app_language, fallback_text="Share history"),
            lines=_summary_lines(ui_text("server.shell.no_recent_share_history", app_language=app_language, fallback_text="No public share history is available yet.")),
            detail_title=ui_text("server.shell.share_history_detail", app_language=app_language, fallback_text="Share history detail"),
            detail_empty=ui_text("server.shell.share_history_entries_pending", app_language=app_language, fallback_text="Share history entries will appear here after you publish a share."),
            controls=[{
                "control_id": "share-history-create",
                "label": ui_text("server.shell.create_share", app_language=app_language, fallback_text="Create share"),
                "action_kind": "open_workspace_share_create",
                "action_target": workspace_id,
            }],
            history=[],
        )
    entries: list[dict[str, Any]] = []
    for row in share_payload_rows:
        try:
            descriptor = describe_public_nex_link_share(dict(row))
        except Exception:
            continue
        if str(descriptor.canonical_ref or "").strip() != canonical_ref:
            continue
        entries.append({
            "share_id": descriptor.share_id,
            "title": descriptor.title,
            "state": descriptor.lifecycle_state,
            "share_path": descriptor.share_path,
            "updated_at": descriptor.updated_at,
            "archived": descriptor.archived,
            "audit_event_count": descriptor.audit_event_count,
        })
    entries.sort(key=lambda item: (str(item.get("updated_at") or ""), str(item.get("share_id") or "")), reverse=True)
    latest = entries[0] if entries else None
    controls: list[dict[str, Any]] = [{
        "control_id": "share-history-create",
        "label": ui_text("server.shell.create_share", app_language=app_language, fallback_text="Create share"),
        "action_kind": "open_workspace_share_create",
        "action_target": workspace_id,
    }]
    if latest is not None:
        controls.append({
            "control_id": f"share-history-open-{latest['share_id']}",
            "label": ui_text("server.shell.open_latest_share", app_language=app_language, fallback_text="Open latest share"),
            "action_kind": "open_public_share",
            "action_target": latest["share_id"],
        })
    return build_shell_section(
        headline=ui_text("server.shell.share_history", app_language=app_language, fallback_text="Share history"),
        lines=_summary_lines(
            ui_text("server.shell.recent_shares_prefix", app_language=app_language, fallback_text="Recent shares: ") + str(len(entries)) if entries else ui_text("server.shell.no_recent_share_history", app_language=app_language, fallback_text="No public share history is available yet."),
            ui_text("server.shell.latest_prefix", app_language=app_language, fallback_text="Latest: ") + f"{latest['share_id']} — {latest['state']}" if latest else None,
        ),
        detail_title=ui_text("server.shell.share_history_detail", app_language=app_language, fallback_text="Share history detail"),
        detail_items=[
            f"{index + 1}. {entry['share_id']} — {entry['state']}"
            + (f" — {entry['title']}" if entry.get("title") else "")
            + (f" — {entry['share_path']}" if entry.get("share_path") else "")
            for index, entry in enumerate(entries[:3])
        ],
        detail_empty=ui_text("server.shell.share_history_entries_pending", app_language=app_language, fallback_text="Share history entries will appear here after you publish a share."),
        controls=controls,
        history=entries[:3],
    )


def build_workspace_shell_runtime_payload(
    *,
    workspace_row: Mapping[str, Any] | None,
    artifact_source: Any | None = None,
    recent_run_rows: Sequence[Mapping[str, Any]] = (),
    result_rows_by_run_id: Mapping[str, Mapping[str, Any]] | None = None,
    onboarding_rows: Sequence[Mapping[str, Any]] = (),
    artifact_rows_lookup: Any | None = None,
    trace_rows_lookup: Any | None = None,
    share_payload_rows: Sequence[Mapping[str, Any]] = (),
    app_language_override: str | None = None,
) -> dict[str, Any]:
    source = resolve_workspace_artifact_source(workspace_row, artifact_source)
    model, loaded = _load_workspace_model(source, workspace_row)
    app_language = normalize_ui_language(app_language_override or ui_language_from_sources(model))
    shell_vm = read_builder_shell_view_model(model, app_language=app_language)
    server_backed_state = _server_backed_shell_state(source, model)
    template_gallery = read_template_gallery_view_model(model, app_language=app_language) if isinstance(model, WorkingSaveModel) else None
    workspace_id = str((workspace_row or {}).get("workspace_id") or getattr(getattr(model, "meta", None), "working_save_id", "workspace")).strip() or "workspace"
    workspace_title = str((workspace_row or {}).get("title") or getattr(getattr(model, "meta", None), "name", "Workspace")).strip() or "Workspace"
    target = _execution_target_for(model)
    latest_run_row = _latest_run_row(recent_run_rows, workspace_id)
    latest_run_id = str((latest_run_row or {}).get("run_id") or "").strip() or _last_run_id(recent_run_rows, workspace_id)
    launch_request_template = None
    if target is not None:
        launch_request_template = {
            "workspace_id": workspace_id,
            "execution_target": target,
            "input_payload": {},
            "launch_options": {"allow_working_save_execution": target["target_type"] == "working_save"},
            "client_context": {"surface": "phase6_browser_runtime"},
        }

    onboarding_state = None
    for row in onboarding_rows:
        if str(row.get("workspace_id") or "").strip() == workspace_id:
            onboarding_state = dict(row)
            break

    latest_run_status_preview = _latest_run_status_preview(latest_run_row)
    latest_run_result_preview = _latest_run_result_preview(latest_run_row, result_rows_by_run_id)
    latest_run_artifacts_preview = _latest_run_artifacts_preview(latest_run_row, artifact_rows_lookup)
    latest_run_trace_preview = _latest_run_trace_preview(latest_run_row, trace_rows_lookup)

    navigation = _navigation_model(
        asdict(shell_vm),
        app_language=app_language,
        latest_run_status_preview=latest_run_status_preview,
        latest_run_result_preview=latest_run_result_preview,
        latest_run_trace_preview=latest_run_trace_preview,
        latest_run_artifacts_preview=latest_run_artifacts_preview,
        onboarding_state=onboarding_state,
    )

    payload = {
        "workspace_id": workspace_id,
        "workspace_title": workspace_title,
        "app_language": app_language,
        "storage_role": _storage_role(model),
        "action_availability": _workspace_shell_action_availability(model),
        "click_test_ready": launch_request_template is not None,
        "working_save_id": getattr(getattr(model, "meta", None), "working_save_id", None),
        "commit_id": getattr(getattr(model, "meta", None), "commit_id", None),
        "shell": asdict(shell_vm),
        "template_gallery": asdict(template_gallery) if template_gallery is not None else None,
        "launch_request_template": launch_request_template,
        "routes": {
            "workspace_shell": f"/api/workspaces/{workspace_id}/shell",
            "workspace_page": f"/app/workspaces/{workspace_id}",
            "launch_run": "/api/runs",
            "latest_run_status": (f"/api/runs/{latest_run_id}" if latest_run_id else None),
            "latest_run_result": (f"/api/runs/{latest_run_id}/result" if latest_run_id else None),
            "latest_run_artifacts": (f"/api/runs/{latest_run_id}/artifacts" if latest_run_id else None),
            "latest_run_trace": (f"/api/runs/{latest_run_id}/trace?limit=20" if latest_run_id else None),
            "workspace_runs": f"/api/workspaces/{workspace_id}/runs",
            "onboarding": f"/api/users/me/onboarding?workspace_id={workspace_id}",
            "onboarding_write": "/api/users/me/onboarding",
            "workspace_shell_draft_write": f"/api/workspaces/{workspace_id}/shell/draft",
            "workspace_shell_commit": f"/api/workspaces/{workspace_id}/shell/commit",
            "workspace_shell_checkout": f"/api/workspaces/{workspace_id}/shell/checkout",
            "workspace_shell_launch": f"/api/workspaces/{workspace_id}/shell/launch",
            "workspace_shell_share": f"/api/workspaces/{workspace_id}/shell/share",
            "workspace_recent_activity": f"/api/users/me/activity?workspace_id={workspace_id}",
            "workspace_history_summary": f"/api/users/me/history-summary?workspace_id={workspace_id}",
        },
        "latest_run_status_preview": latest_run_status_preview,
        "latest_run_result_preview": latest_run_result_preview,
        "latest_run_artifacts_preview": latest_run_artifacts_preview,
        "latest_run_trace_preview": latest_run_trace_preview,
        "latest_run_status_summary": _latest_run_status_summary(latest_run_status_preview),
        "latest_run_result_summary": _latest_run_result_summary(latest_run_result_preview),
        "latest_run_artifacts_summary": _latest_run_artifacts_summary(latest_run_artifacts_preview),
        "latest_run_trace_summary": _latest_run_trace_summary(latest_run_trace_preview),
        "latest_run_status_detail": _latest_run_status_detail(latest_run_status_preview),
        "latest_run_result_detail": _latest_run_result_detail(latest_run_result_preview),
        "latest_run_artifacts_detail": _latest_run_artifacts_detail(latest_run_artifacts_preview),
        "latest_run_trace_detail": _latest_run_trace_detail(latest_run_trace_preview),
        "status_history_section": _status_history_section(recent_run_rows, workspace_id),
        "result_history_section": _result_history_section(recent_run_rows, workspace_id, result_rows_by_run_id),
        "trace_history_section": _trace_history_section(recent_run_rows, workspace_id, trace_rows_lookup, app_language=app_language),
        "artifacts_history_section": _artifacts_history_section(recent_run_rows, workspace_id, artifact_rows_lookup),
        "recent_activity_section": _recent_activity_section(recent_run_rows, onboarding_rows, workspace_id, app_language=app_language),
        "history_summary_section": _history_summary_section(recent_run_rows, onboarding_rows, share_payload_rows, model, workspace_id, app_language=app_language),
        "share_history_section": _share_history_section(share_payload_rows, model, workspace_id, app_language=app_language),
        "designer_section": _designer_section(asdict(shell_vm), asdict(template_gallery) if template_gallery is not None else None, persisted_state=server_backed_state.get("designer"), app_language=app_language),
        "validation_section": _validation_section(asdict(shell_vm), runnable=launch_request_template is not None, persisted_state=server_backed_state.get("validation")),
        "navigation": navigation,
        "step_state_banner": _step_state_banner(
            asdict(shell_vm),
            app_language=app_language,
            latest_run_status_preview=latest_run_status_preview,
            latest_run_result_preview=latest_run_result_preview,
            latest_run_trace_preview=latest_run_trace_preview,
            latest_run_artifacts_preview=latest_run_artifacts_preview,
            navigation=navigation,
            onboarding_state=onboarding_state,
        ),
        "continuity": {
            "onboarding_state": onboarding_state,
            "load_status": getattr(loaded, "load_status", "generated_default") if loaded is not None else "generated_default",
            "load_finding_count": len(getattr(loaded, "findings", ()) or ()) if loaded is not None else 0,
        },
        "client_continuity": {
            "enabled": True,
            "storage_key": f"nexa.runtime_shell.{workspace_id}",
            "version": "phase6-batch15",
        },
    }
    payload = _localize_shell_payload(payload, app_language)
    return payload


def render_workspace_shell_runtime_html(payload: Mapping[str, Any]) -> str:
    app_language = normalize_ui_language(payload.get("app_language") or "en")
    workspace_id = escape(str(payload.get("workspace_id") or "workspace"))
    workspace_title = escape(str(payload.get("workspace_title") or "Workspace"))
    shell = payload.get("shell") or {}
    contextual_help = shell.get("contextual_help") or {}
    privacy = shell.get("privacy_transparency") or {}
    mobile = shell.get("mobile_first_run") or {}
    template_gallery = payload.get("template_gallery") or {}
    routes = payload.get("routes") or {}
    launch_template_json = json.dumps(payload.get("launch_request_template"), ensure_ascii=False)
    payload_json = json.dumps(payload, ensure_ascii=False)
    latest_run_status_preview_json = json.dumps(payload.get("latest_run_status_preview"), ensure_ascii=False)
    latest_run_result_preview_json = json.dumps(payload.get("latest_run_result_preview"), ensure_ascii=False)
    latest_run_artifacts_preview_json = json.dumps(payload.get("latest_run_artifacts_preview"), ensure_ascii=False)
    latest_run_trace_preview_json = json.dumps(payload.get("latest_run_trace_preview"), ensure_ascii=False)
    latest_run_status_summary_json = json.dumps(payload.get("latest_run_status_summary"), ensure_ascii=False)
    latest_run_result_summary_json = json.dumps(payload.get("latest_run_result_summary"), ensure_ascii=False)
    latest_run_artifacts_summary_json = json.dumps(payload.get("latest_run_artifacts_summary"), ensure_ascii=False)
    latest_run_trace_summary_json = json.dumps(payload.get("latest_run_trace_summary"), ensure_ascii=False)
    latest_run_status_detail_json = json.dumps(payload.get("latest_run_status_detail"), ensure_ascii=False)
    latest_run_result_detail_json = json.dumps(payload.get("latest_run_result_detail"), ensure_ascii=False)
    latest_run_artifacts_detail_json = json.dumps(payload.get("latest_run_artifacts_detail"), ensure_ascii=False)
    latest_run_trace_detail_json = json.dumps(payload.get("latest_run_trace_detail"), ensure_ascii=False)
    status_history_section_json = json.dumps(payload.get("status_history_section"), ensure_ascii=False)
    result_history_section_json = json.dumps(payload.get("result_history_section"), ensure_ascii=False)
    trace_history_section_json = json.dumps(payload.get("trace_history_section"), ensure_ascii=False)
    artifacts_history_section_json = json.dumps(payload.get("artifacts_history_section"), ensure_ascii=False)
    recent_activity_section_json = json.dumps(payload.get("recent_activity_section"), ensure_ascii=False)
    history_summary_section_json = json.dumps(payload.get("history_summary_section"), ensure_ascii=False)
    designer_section_json = json.dumps(payload.get("designer_section"), ensure_ascii=False)
    validation_section_json = json.dumps(payload.get("validation_section"), ensure_ascii=False)
    step_state_banner_json = json.dumps(payload.get("step_state_banner"), ensure_ascii=False)
    navigation = payload.get("navigation") or {}
    navigation_json = json.dumps(navigation, ensure_ascii=False)
    client_continuity_json = json.dumps(payload.get("client_continuity"), ensure_ascii=False)
    continuity_json = json.dumps(payload.get("continuity"), ensure_ascii=False)
    localized_ui_json = json.dumps({
        'statusPrefix': ui_text('server.shell.status', app_language=app_language, fallback_text='Status') + ': ',
        'summaryPrefix': ui_text('server.shell.summary_prefix', app_language=app_language, fallback_text='Summary: '),
        'messagePrefix': ui_text('server.shell.message_prefix', app_language=app_language, fallback_text='Message: '),
        'traceStatusPrefix': ui_text('server.shell.trace_status_prefix', app_language=app_language, fallback_text='Trace status: '),
        'previewPrefix': ui_text('server.shell.preview_prefix', app_language=app_language, fallback_text='Preview: '),
        'latestMessagePrefix': ui_text('server.shell.latest_message_prefix', app_language=app_language, fallback_text='Latest message: '),
        'firstArtifactLabelPrefix': ui_text('server.shell.first_artifact_label_prefix', app_language=app_language, fallback_text='First artifact label: '),
        'noRecentRun': ui_text('server.shell.no_recent_run', app_language=app_language, fallback_text='No recent run is available yet.'),
        'noRecentResult': ui_text('server.shell.no_recent_result', app_language=app_language, fallback_text='No recent run result is available yet.'),
        'noRecentTrace': ui_text('server.shell.no_recent_trace', app_language=app_language, fallback_text='No recent trace is available yet.'),
        'noRecentArtifacts': ui_text('server.shell.no_recent_artifacts', app_language=app_language, fallback_text='No recent artifacts are available yet.'),
        'openLatestStatusDetailPrompt': ui_text('server.shell.status_detail_prompt', app_language=app_language, fallback_text='Open latest run status to view the detail layer.'),
        'openLatestResultDetailPrompt': ui_text('server.shell.result_detail_prompt', app_language=app_language, fallback_text='Open latest run result to view the detail layer.'),
        'openLatestTraceDetailPrompt': ui_text('server.shell.trace_detail_prompt', app_language=app_language, fallback_text='Open latest trace to view the detail layer.'),
        'openLatestArtifactsDetailPrompt': ui_text('server.shell.artifacts_detail_prompt', app_language=app_language, fallback_text='Open latest artifacts to view the detail layer.'),
        'actionFallback': ui_text('server.shell.action_fallback', app_language=app_language, fallback_text='Action'),
        'starterTemplateFallback': ui_text('server.shell.starter_template_fallback', app_language=app_language, fallback_text='starter template'),
        'templateSelectedSummary': ui_text('server.shell.template_selected_summary', app_language=app_language, fallback_text='Template selected.'),
        'templateIdLabel': ui_text('server.shell.template_id', app_language=app_language, fallback_text='Template id: {{template_id}}', template_id='').replace('Template id: ', '').replace('{template_id}', ''),
        'templateRefLabel': ui_text('server.shell.template_ref', app_language=app_language, fallback_text='Template ref: {{template_ref}}', template_ref='').replace('Template ref: ', '').replace('{template_ref}', ''),
        'categoryLabel': ui_text('server.shell.category', app_language=app_language, fallback_text='Category: {{category}}', category='').replace('Category: ', '').replace('{category}', ''),
        'designerRequestLabel': ui_text('server.shell.designer_request', app_language=app_language, fallback_text='Designer request: {{request}}', request='').replace('Designer request: ', '').replace('{request}', ''),
        'templateLookupAliasesLabel': ui_text('server.shell.template_lookup_aliases', app_language=app_language, fallback_text='Lookup aliases: {{aliases}}', aliases='').replace('Lookup aliases: ', '').replace('{aliases}', ''),
        'templateProvenanceLabel': ui_text('server.shell.template_provenance', app_language=app_language, fallback_text='Provenance: {{source}} / {{family}}', source='', family='').replace('Provenance: ', '').replace('{source} / {family}', ''),
        'templateCompatibilityLabel': ui_text('server.shell.template_compatibility', app_language=app_language, fallback_text='Compatibility: {{family}} / {{behavior}}', family='', behavior='').replace('Compatibility: ', '').replace('{family} / {behavior}', ''),
        'designerWorkspace': ui_text('server.shell.designer_workspace', app_language=app_language, fallback_text='Designer workspace'),
        'reviewValidationAction': ui_text('server.shell.banner.review_validation', app_language=app_language, fallback_text='Review Validation'),
        'templateLoadedSummaryPrefix': ui_text('server.shell.template_loaded_summary_prefix', app_language=app_language, fallback_text='Template "'),
        'templateLoadedSummarySuffix': ui_text('server.shell.template_loaded_summary_suffix', app_language=app_language, fallback_text='" is loaded into Designer. Review the draft, then continue to Validation.'),
        'openNextStep': ui_text('server.shell.open_next_step', app_language=app_language, fallback_text='Open next step'),
        'openDesigner': ui_text('server.shell.open_designer', app_language=app_language, fallback_text='Open Designer'),
        'openStatus': ui_text('server.shell.open_status', app_language=app_language, fallback_text='Open Status'),
        'openResult': ui_text('server.shell.open_result', app_language=app_language, fallback_text='Open Result'),
        'openTrace': ui_text('server.shell.open_trace', app_language=app_language, fallback_text='Open Trace'),
        'openArtifacts': ui_text('server.shell.open_artifacts', app_language=app_language, fallback_text='Open Artifacts'),
        'stepRun': ui_text('server.shell.step.run', app_language=app_language, fallback_text='Step 4 of 5 — Run'),
        'stepReadResult': ui_text('server.shell.step.read_result', app_language=app_language, fallback_text='Step 5 of 5 — Read result'),
        'runInProgressSummary': ui_text('server.shell.run_in_progress_summary', app_language=app_language, fallback_text='Run is in progress. Watch Status while Nexa prepares the result.'),
        'runNeedsDiagnosisSummary': ui_text('server.shell.run_needs_diagnosis_summary', app_language=app_language, fallback_text='Run needs diagnosis. Open Trace next to understand what happened.'),
        'resultReadySummary': ui_text('server.shell.result_ready_summary', app_language=app_language, fallback_text='Result is ready. Open Result next to finish the first-run path.'),
        'artifactsReadySummary': ui_text('server.shell.artifacts_ready_summary', app_language=app_language, fallback_text='A readable result is not ready yet, but artifacts are available. Open Artifacts next.'),
        'focusPrefix': ui_text('server.shell.focus_state', app_language=app_language, fallback_text='Focus: {section}', section='').replace('{section}', ''),
        'focusDetailSuffix': ui_text('server.shell.focus_detail_suffix', app_language=app_language, fallback_text=' detail'),
        'focusSummarySuffix': ui_text('server.shell.focus_summary_suffix', app_language=app_language, fallback_text=' summary'),
        'launchAcceptedSummary': ui_text('server.shell.launch_accepted_summary', app_language=app_language, fallback_text='Launch accepted. Watch Status while Nexa starts the run.'),
    }, ensure_ascii=False)
    template_items = []
    for template in (template_gallery.get("templates") or [])[:6]:
        title = escape(str(template.get("display_name") or template.get("template_id") or ui_text("server.feedback.option_fallback", app_language=app_language, fallback_text="Template")))
        summary = escape(str(template.get("summary") or ""))
        template_items.append(f"<li><strong>{title}</strong><br><span>{summary}</span></li>")
    template_empty_label = ui_text("server.shell.mobile_unavailable", app_language=app_language, fallback_text="No starter templates projected yet.")
    template_markup = "".join(template_items) or f"<li>{escape(template_empty_label)}</li>"
    privacy_items = []
    for fact in (privacy.get("facts") or []):
        label = escape(str(fact.get("label") or fact.get("fact_id") or ui_text("server.feedback.option_fallback", app_language=app_language, fallback_text="Fact")))
        value = escape(str(fact.get("value") or ""))
        privacy_items.append(f"<li><strong>{label}:</strong> {value}</li>")
    privacy_empty_label = ui_text("server.shell.review_projected_action", app_language=app_language, fallback_text="No privacy facts projected.")
    privacy_markup = "".join(privacy_items) or f"<li>{escape(privacy_empty_label)}</li>"
    mobile_items = []
    for step in mobile.get("steps") or []:
        label = escape(str(step.get("label") or step.get("step_id") or ui_text("server.shell.status", app_language=app_language, fallback_text="Step")))
        raw_status = str(step.get("status") or "pending").strip().lower() or "pending"
        localized_status = ui_text(f"server.shell.mobile_status.{raw_status}", app_language=app_language, fallback_text=raw_status)
        status = escape(localized_status)
        mobile_items.append(f"<li>{label} — <em>{status}</em></li>")
    mobile_empty_label = ui_text("server.shell.mobile_unavailable", app_language=app_language, fallback_text="Mobile first-run projection unavailable.")
    mobile_markup = "".join(mobile_items) or f"<li>{escape(mobile_empty_label)}</li>"
    latest_run_status_path = escape(str(routes.get("latest_run_status") or ""))
    latest_run_trace_path = escape(str(routes.get("latest_run_trace") or ""))
    latest_run_artifacts_path = escape(str(routes.get("latest_run_artifacts") or ""))
    help_title = escape(str(contextual_help.get("title") or ui_text("server.shell.contextual_help", app_language=app_language, fallback_text="Contextual help")))
    help_summary = escape(str(contextual_help.get("summary") or ui_text("server.shell.contextual_help_default", app_language=app_language, fallback_text="Review the projected next action.")))
    shell_status = escape(str((shell.get("shell_status_label") or payload.get("storage_role") or "ready")))
    html = f"""<!doctype html>
<html lang="{app_language}">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>{escape(ui_text("server.shell.page_title", app_language=app_language, fallback_text="Nexa Runtime Shell — {workspace}", workspace=workspace_title))}</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 0; padding: 24px; background: #f7f7f8; color: #111; }}
    .shell {{ max-width: 960px; margin: 0 auto; background: white; border-radius: 16px; padding: 24px; box-shadow: 0 10px 30px rgba(0,0,0,0.08); }}
    .row {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 16px; margin-top: 16px; }}
    .card {{ border: 1px solid #e5e7eb; border-radius: 12px; padding: 16px; background: #fff; }}
    button {{ border: 0; border-radius: 10px; padding: 12px 16px; cursor: pointer; background: #111827; color: white; }}
    button.secondary {{ background: #374151; }}
    code {{ background: #f3f4f6; padding: 2px 6px; border-radius: 6px; }}
    pre {{ white-space: pre-wrap; word-break: break-word; background: #f9fafb; padding: 12px; border-radius: 10px; border: 1px solid #e5e7eb; }}
    .actions {{ display: flex; gap: 12px; flex-wrap: wrap; margin-top: 16px; }}
    .nav {{ display: flex; gap: 8px; flex-wrap: wrap; margin-top: 16px; }}
    .nav button[aria-pressed="true"] {{ background: #2563eb; }}
    .focus-target:focus {{ outline: 3px solid #2563eb; outline-offset: 2px; }}
  </style>
</head>
<body>
  <main class=\"shell\" role=\"main\" aria-labelledby=\"workspace-shell-title\">
    <h1 id="workspace-shell-title">{escape(ui_text("server.shell.title", app_language=app_language, fallback_text="Nexa Runtime Shell"))}</h1>
    <p><strong>{workspace_title}</strong></p>
    <p>{escape(ui_text("server.shell.status", app_language=app_language, fallback_text="Status"))}: <strong>{shell_status}</strong></p>
    <div class="actions" role="toolbar" aria-label="{escape(ui_text("server.shell.actions", app_language=app_language, fallback_text="Workspace shell actions"))}">
      <button id="run-draft" {'disabled' if payload.get('launch_request_template') is None else ''}>{escape(ui_text("server.shell.run_draft", app_language=app_language, fallback_text="Run draft"))}</button>
      <button id="refresh" class="secondary">{escape(ui_text("server.shell.refresh", app_language=app_language, fallback_text="Refresh shell"))}</button>
      <button id="open-status" class="secondary" {'disabled' if not latest_run_status_path else ''}>{escape(ui_text("server.shell.open_latest_status", app_language=app_language, fallback_text="Open latest run status"))}</button>
      <button id="open-result" class="secondary" {'disabled' if not routes.get('latest_run_result') else ''}>{escape(ui_text("server.shell.open_latest_result", app_language=app_language, fallback_text="Open latest result"))}</button>
      <button id="open-trace" class="secondary" {'disabled' if not latest_run_trace_path else ''}>{escape(ui_text("server.shell.open_latest_trace", app_language=app_language, fallback_text="Open latest trace"))}</button>
      <button id="open-artifacts" class="secondary" {'disabled' if not latest_run_artifacts_path else ''}>{escape(ui_text("server.shell.open_latest_artifacts", app_language=app_language, fallback_text="Open latest artifacts"))}</button>
    </div>
    <section class="card" style="margin-top:16px;" role="region" aria-labelledby="runtime-focus-title">
      <h2 id="runtime-focus-title">{escape(ui_text("server.shell.runtime_focus", app_language=app_language, fallback_text="Runtime focus"))}</h2>
      <div id="runtime-nav" class="nav" aria-label="{escape(ui_text("server.shell.runtime_nav_aria", app_language=app_language, fallback_text="Runtime section navigation"))}"></div>
      <p id="focus-guidance"><strong>{escape(str(navigation.get('guidance_label') or 'Recommended next: Status'))}</strong> — {escape(str(navigation.get('guidance_summary') or 'Open status first to follow the current runtime state.'))}</p>
      <pre id="focus-state">{escape(ui_text('server.shell.focus_state', app_language=app_language, fallback_text='Focus: {section}', section=_localized_runtime_section_label(str(navigation.get('default_section') or 'status'), app_language=app_language)))}</pre>
    </section>
    <section class="card" style="margin-top:16px;" role="region" aria-labelledby="step-state-banner-heading">
      <h2 id="step-state-banner-heading">{escape(ui_text("server.shell.step_state_banner", app_language=app_language, fallback_text="Step state banner"))}</h2>
      <p id="step-state-banner-title">{escape(str((payload.get('step_state_banner') or {}).get('title') or ui_text('server.shell.step.enter_goal', app_language=app_language, fallback_text='Step 1 of 5 — Enter goal')))}</p>
      <pre id="step-state-banner-summary" aria-live="polite">{escape(str((payload.get('step_state_banner') or {}).get('summary') or ui_text('server.shell.summary.enter_goal', app_language=app_language, fallback_text='Describe your goal to start the first-run path.')))}</pre>
      <p id="step-state-banner-action">{escape(str((payload.get('step_state_banner') or {}).get('action_label') or ui_text('server.shell.open_designer', app_language=app_language, fallback_text='Open Designer')))} → <code>{escape(_localized_runtime_action_target_label(str((payload.get('step_state_banner') or {}).get('action_target') or 'designer'), app_language=app_language) or 'designer')}</code></p>
      <button id="step-state-banner-action-button" class="secondary">{escape(str((payload.get('step_state_banner') or {}).get('action_label') or ui_text('server.shell.open_designer', app_language=app_language, fallback_text='Open Designer')))}</button>
    </section>
    <div class="row">
      <section id="designer-summary-card" tabindex="-1" class="card focus-target" role="region" aria-labelledby="designer-summary-title">
        <h2 id="designer-summary-title">{escape(ui_text("server.shell.designer_workspace", app_language=app_language, fallback_text="Designer workspace"))}</h2>
        <pre id="designer-summary">{escape(ui_text("server.shell.designer_open_default", app_language=app_language, fallback_text="Open Designer to start drafting your workflow."))}</pre>
        <div id="designer-controls" class="actions"></div>
      </section>
      <section id="validation-summary-card" tabindex="-1" class="card focus-target" role="region" aria-labelledby="validation-summary-title">
        <h2 id="validation-summary-title">{escape(ui_text("server.shell.validation_review", app_language=app_language, fallback_text="Validation review"))}</h2>
        <pre id="validation-summary">{escape(ui_text("server.shell.validation_default", app_language=app_language, fallback_text="Validation guidance will appear here."))}</pre>
        <div id="validation-controls" class="actions"></div>
      </section>
    </div>
    <div class="row">
      <section id="designer-detail-card" tabindex="-1" class="card focus-target" role="region" aria-labelledby="designer-detail-title">
        <h2 id="designer-detail-title">{escape(ui_text("server.shell.designer_detail_layer", app_language=app_language, fallback_text="Designer detail layer"))}</h2>
        <pre id="designer-detail">{escape(ui_text("server.shell.designer_detail_default", app_language=app_language, fallback_text="Designer detail will appear here."))}</pre>
      </section>
      <section id="validation-detail-card" tabindex="-1" class="card focus-target" role="region" aria-labelledby="validation-detail-title">
        <h2 id="validation-detail-title">{escape(ui_text("server.shell.validation_detail_layer", app_language=app_language, fallback_text="Validation detail layer"))}</h2>
        <pre id="validation-detail">{escape(ui_text("server.shell.validation_detail_default", app_language=app_language, fallback_text="Validation detail will appear here."))}</pre>
      </section>
    </div>
    <div class="row">
      <section id="contextual-help-card" tabindex="-1" class="card focus-target" role="region" aria-labelledby="contextual-help-title">
        <h2 id="contextual-help-title">{help_title}</h2>
        <p>{help_summary}</p>
      </section>
      <section id="privacy-card" tabindex="-1" class="card focus-target" role="region" aria-labelledby="privacy-title">
        <h2 id="privacy-title">{escape(str(privacy.get('title') or ui_text('server.shell.privacy', app_language=app_language, fallback_text='Privacy and data handling')))}</h2>
        <ul>{privacy_markup}</ul>
      </section>
    </div>
    <div class="row">
      <section id="mobile-first-run-card" tabindex="-1" class="card focus-target" role="region" aria-labelledby="mobile-first-run-title">
        <h2 id="mobile-first-run-title">{escape(ui_text("server.shell.mobile_first_run", app_language=app_language, fallback_text="Mobile first-run"))}</h2>
        <ul>{mobile_markup}</ul>
      </section>
      <section id="starter-templates-card" tabindex="-1" class="card focus-target" role="region" aria-labelledby="starter-templates-title">
        <h2 id="starter-templates-title">{escape(ui_text("server.shell.starter_templates", app_language=app_language, fallback_text="Starter templates"))}</h2>
        <ul>{template_markup}</ul>
      </section>
    </div>
    <div class="row">
      <section id="latest-run-status-card" tabindex="-1" class="card focus-target" role="region" aria-labelledby="latest-run-status-title">
        <h2 id="latest-run-status-title">{escape(ui_text("server.shell.latest_run_status", app_language=app_language, fallback_text="Latest run status"))}</h2>
        <pre id="latest-run-status">{escape(ui_text("server.shell.waiting_status", app_language=app_language, fallback_text="Waiting for run status."))}</pre>
      </section>
      <section id="latest-run-result-card" tabindex="-1" class="card focus-target" role="region" aria-labelledby="latest-run-result-title">
        <h2 id="latest-run-result-title">{escape(ui_text("server.shell.latest_run_result", app_language=app_language, fallback_text="Latest run result"))}</h2>
        <pre id="latest-run-result">{escape(ui_text("server.shell.waiting_result", app_language=app_language, fallback_text="Waiting for run result."))}</pre>
      </section>
    </div>
    <div class="row">
      <section id="latest-run-status-detail-card" tabindex="-1" class="card focus-target" role="region" aria-labelledby="latest-run-status-detail-title">
        <h2 id="latest-run-status-detail-title">{escape(ui_text("server.shell.status_detail_layer", app_language=app_language, fallback_text="Status detail layer"))}</h2>
        <pre id="latest-run-status-detail">{escape(ui_text("server.shell.status_detail_prompt", app_language=app_language, fallback_text="Open latest run status to view the detail layer."))}</pre>
      </section>
      <section id="latest-run-result-detail-card" tabindex="-1" class="card focus-target" role="region" aria-labelledby="latest-run-result-detail-title">
        <h2 id="latest-run-result-detail-title">{escape(ui_text("server.shell.result_detail_layer", app_language=app_language, fallback_text="Result detail layer"))}</h2>
        <pre id="latest-run-result-detail">{escape(ui_text("server.shell.result_detail_prompt", app_language=app_language, fallback_text="Open latest run result to view the detail layer."))}</pre>
      </section>
    </div>
    <div class="row">
      <section id="status-history-card" tabindex="-1" class="card focus-target" role="region" aria-labelledby="status-history-title">
        <h2 id="status-history-title">{escape(ui_text("server.shell.run_status_history", app_language=app_language, fallback_text="Run status history"))}</h2>
        <pre id="status-history-summary">{escape(ui_text("server.shell.status_history_summary", app_language=app_language, fallback_text="Recent status history will appear here."))}</pre>
        <pre id="status-history-detail">{escape(ui_text("server.shell.status_history_detail", app_language=app_language, fallback_text="Status history detail will appear here."))}</pre>
        <div id="status-history-controls" class="actions"></div>
      </section>
      <section id="result-history-card" tabindex="-1" class="card focus-target" role="region" aria-labelledby="result-history-card-title">
        <h2 id="result-history-card-title">{escape(ui_text("server.shell.run_result_history", app_language=app_language, fallback_text="Run result history"))}</h2>
        <pre id="result-history-summary">{escape(ui_text("server.shell.result_history_summary", app_language=app_language, fallback_text="Recent result history will appear here."))}</pre>
        <pre id="result-history-detail">{escape(ui_text("server.shell.result_history_detail", app_language=app_language, fallback_text="Result history detail will appear here."))}</pre>
        <div id="result-history-controls" class="actions"></div>
      </section>
    </div>
    <div class="row">
      <section id="trace-history-card" tabindex="-1" class="card focus-target" role="region" aria-labelledby="trace-history-title">
        <h2 id="trace-history-title">{escape(ui_text("server.shell.trace_history", app_language=app_language, fallback_text="Trace history"))}</h2>
        <pre id="trace-history-summary">{escape(ui_text("server.shell.trace_history_summary", app_language=app_language, fallback_text="Recent trace history will appear here."))}</pre>
        <pre id="trace-history-detail">{escape(ui_text("server.shell.trace_history_detail", app_language=app_language, fallback_text="Trace history detail will appear here."))}</pre>
        <div id="trace-history-controls" class="actions"></div>
      </section>
      <section id="artifacts-history-card" tabindex="-1" class="card focus-target" role="region" aria-labelledby="artifacts-history-title">
        <h2 id="artifacts-history-title">{escape(ui_text("server.shell.artifacts_history", app_language=app_language, fallback_text="Artifacts history"))}</h2>
        <pre id="artifacts-history-summary">{escape(ui_text("server.shell.artifacts_history_summary", app_language=app_language, fallback_text="Recent artifacts history will appear here."))}</pre>
        <pre id="artifacts-history-detail">{escape(ui_text("server.shell.artifacts_history_detail", app_language=app_language, fallback_text="Artifacts history detail will appear here."))}</pre>
        <div id="artifacts-history-controls" class="actions"></div>
      </section>
    </div>
    <div class="row">
      <section id="latest-run-trace-card" tabindex="-1" class="card focus-target" role="region" aria-labelledby="latest-run-trace-title">
        <h2 id="latest-run-trace-title">{escape(ui_text("server.shell.latest_trace", app_language=app_language, fallback_text="Latest trace"))}</h2>
        <pre id="latest-run-trace">{escape(ui_text("server.shell.waiting_trace", app_language=app_language, fallback_text="Waiting for trace details."))}</pre>
      </section>
      <section id="latest-run-artifacts-card" tabindex="-1" class="card focus-target" role="region" aria-labelledby="latest-run-artifacts-title">
        <h2 id="latest-run-artifacts-title">{escape(ui_text("server.shell.latest_artifacts", app_language=app_language, fallback_text="Latest artifacts"))}</h2>
        <pre id="latest-run-artifacts">{escape(ui_text("server.shell.waiting_artifacts", app_language=app_language, fallback_text="Waiting for artifact details."))}</pre>
      </section>
    </div>
    <div class="row">
      <section id="latest-run-trace-detail-card" tabindex="-1" class="card focus-target" role="region" aria-labelledby="latest-run-trace-detail-title">
        <h2 id="latest-run-trace-detail-title">{escape(ui_text("server.shell.trace_detail_layer", app_language=app_language, fallback_text="Trace detail layer"))}</h2>
        <pre id="latest-run-trace-detail">{escape(ui_text("server.shell.trace_detail_prompt", app_language=app_language, fallback_text="Open latest trace to view the detail layer."))}</pre>
      </section>
      <section id="latest-run-artifacts-detail-card" tabindex="-1" class="card focus-target" role="region" aria-labelledby="latest-run-artifacts-detail-title">
        <h2 id="latest-run-artifacts-detail-title">{escape(ui_text("server.shell.artifacts_detail_layer", app_language=app_language, fallback_text="Artifacts detail layer"))}</h2>
        <pre id="latest-run-artifacts-detail">{escape(ui_text("server.shell.artifacts_detail_prompt", app_language=app_language, fallback_text="Open latest artifacts to view the detail layer."))}</pre>
      </section>
    </div>
    <div class="row">
      <section id="recent-activity-card" tabindex="-1" class="card focus-target" role="region" aria-labelledby="recent-activity-title">
        <h2 id="recent-activity-title">{escape(ui_text("server.shell.recent_activity", app_language=app_language, fallback_text="Recent activity"))}</h2>
        <pre id="recent-activity-summary">{escape(ui_text("server.shell.recent_activity_summary", app_language=app_language, fallback_text="Recent activity will appear here."))}</pre>
        <pre id="recent-activity-detail">{escape(ui_text("server.shell.recent_activity_detail", app_language=app_language, fallback_text="Recent activity detail will appear here."))}</pre>
        <div id="recent-activity-controls" class="actions"></div>
      </section>
      <section id="history-summary-card" tabindex="-1" class="card focus-target" role="region" aria-labelledby="history-summary-title">
        <h2 id="history-summary-title">{escape(ui_text("server.shell.history_summary", app_language=app_language, fallback_text="History summary"))}</h2>
        <pre id="history-summary-summary">{escape(ui_text("server.shell.history_summary_summary", app_language=app_language, fallback_text="History summary will appear here."))}</pre>
        <pre id="history-summary-detail">{escape(ui_text("server.shell.history_summary_detail", app_language=app_language, fallback_text="History summary detail will appear here."))}</pre>
        <div id="history-summary-controls" class="actions"></div>
      </section>
    </div>
    <section class="card" style="margin-top:16px;" role="region" aria-labelledby="browser-log-title">
      <h2 id=\"browser-log-title\">Last action log</h2>
      <pre id=\"browser-log\" aria-live=\"polite\">Ready.</pre>
    </section>
  </main>
  <script>
    const initialPayload = {payload_json};
    const launchTemplate = {launch_template_json};
    const initialRunStatusPreview = {latest_run_status_preview_json};
    const initialRunResultPreview = {latest_run_result_preview_json};
    const initialRunArtifactsPreview = {latest_run_artifacts_preview_json};
    const initialRunTracePreview = {latest_run_trace_preview_json};
    const initialRunStatusSummary = {latest_run_status_summary_json};
    const initialRunResultSummary = {latest_run_result_summary_json};
    const initialRunArtifactsSummary = {latest_run_artifacts_summary_json};
    const initialRunTraceSummary = {latest_run_trace_summary_json};
    const initialRunStatusDetail = {latest_run_status_detail_json};
    const initialRunResultDetail = {latest_run_result_detail_json};
    const initialRunArtifactsDetail = {latest_run_artifacts_detail_json};
    const initialRunTraceDetail = {latest_run_trace_detail_json};
    const initialStatusHistorySection = {status_history_section_json};
    const initialResultHistorySection = {result_history_section_json};
    const initialTraceHistorySection = {trace_history_section_json};
    const initialArtifactsHistorySection = {artifacts_history_section_json};
    const initialRecentActivitySection = {recent_activity_section_json};
    const initialHistorySummarySection = {history_summary_section_json};
    const initialDesignerSection = {designer_section_json};
    const initialValidationSection = {validation_section_json};
    const initialStepStateBanner = {step_state_banner_json};
    const initialNavigation = {navigation_json};
    const initialClientContinuity = {client_continuity_json};
    const initialContinuity = {continuity_json};
    const logEl = document.getElementById('browser-log');
    const latestRunStatusEl = document.getElementById('latest-run-status');
    const latestRunResultEl = document.getElementById('latest-run-result');
    const latestRunTraceEl = document.getElementById('latest-run-trace');
    const latestRunArtifactsEl = document.getElementById('latest-run-artifacts');
    const latestRunStatusDetailEl = document.getElementById('latest-run-status-detail');
    const latestRunResultDetailEl = document.getElementById('latest-run-result-detail');
    const latestRunTraceDetailEl = document.getElementById('latest-run-trace-detail');
    const latestRunArtifactsDetailEl = document.getElementById('latest-run-artifacts-detail');
    const statusHistorySummaryEl = document.getElementById('status-history-summary');
    const statusHistoryDetailEl = document.getElementById('status-history-detail');
    const statusHistoryControlsEl = document.getElementById('status-history-controls');
    const resultHistorySummaryEl = document.getElementById('result-history-summary');
    const resultHistoryDetailEl = document.getElementById('result-history-detail');
    const resultHistoryControlsEl = document.getElementById('result-history-controls');
    const traceHistorySummaryEl = document.getElementById('trace-history-summary');
    const traceHistoryDetailEl = document.getElementById('trace-history-detail');
    const traceHistoryControlsEl = document.getElementById('trace-history-controls');
    const artifactsHistorySummaryEl = document.getElementById('artifacts-history-summary');
    const artifactsHistoryDetailEl = document.getElementById('artifacts-history-detail');
    const artifactsHistoryControlsEl = document.getElementById('artifacts-history-controls');
    const recentActivitySummaryEl = document.getElementById('recent-activity-summary');
    const recentActivityDetailEl = document.getElementById('recent-activity-detail');
    const recentActivityControlsEl = document.getElementById('recent-activity-controls');
    const historySummarySummaryEl = document.getElementById('history-summary-summary');
    const historySummaryDetailEl = document.getElementById('history-summary-detail');
    const historySummaryControlsEl = document.getElementById('history-summary-controls');
    const designerSummaryEl = document.getElementById('designer-summary');
    const designerDetailEl = document.getElementById('designer-detail');
    const designerControlsEl = document.getElementById('designer-controls');
    const validationSummaryEl = document.getElementById('validation-summary');
    const validationDetailEl = document.getElementById('validation-detail');
    const validationControlsEl = document.getElementById('validation-controls');
    const runtimeNavEl = document.getElementById('runtime-nav');
    const focusStateEl = document.getElementById('focus-state');
    const focusGuidanceEl = document.getElementById('focus-guidance');
    const stepStateBannerTitleEl = document.getElementById('step-state-banner-title');
    const stepStateBannerSummaryEl = document.getElementById('step-state-banner-summary');
    const stepStateBannerActionEl = document.getElementById('step-state-banner-action');
    const stepStateBannerActionButtonEl = document.getElementById('step-state-banner-action-button');
    let activeRunId = initialRunStatusPreview ? initialRunStatusPreview.run_id : null;
    let currentNavigation = initialNavigation || null;
    let focusedSectionId = (currentNavigation && currentNavigation.default_section) || 'status';
    let focusedLevel = (currentNavigation && currentNavigation.default_level) || 'summary';
    let activeRunStatusPath = initialPayload.routes.latest_run_status || null;
    let activeRunResultPath = initialPayload.routes.latest_run_result || null;
    let activeRunTracePath = initialPayload.routes.latest_run_trace || null;
    let activeRunArtifactsPath = initialPayload.routes.latest_run_artifacts || null;
    let latestStatusBodyState = null;
    let latestResultBodyState = null;
    let latestTraceBodyState = null;
    let latestArtifactsBodyState = null;
    let currentStatusHistorySection = initialStatusHistorySection || null;
    let currentResultHistorySection = initialResultHistorySection || null;
    let currentTraceHistorySection = initialTraceHistorySection || null;
    let currentArtifactsHistorySection = initialArtifactsHistorySection || null;
    let currentRecentActivitySection = initialRecentActivitySection || null;
    let currentHistorySummarySection = initialHistorySummarySection || null;
    let currentDesignerSection = initialDesignerSection || null;
    let currentValidationSection = initialValidationSection || null;
    let currentStepStateBanner = initialStepStateBanner || null;
    let continuityHydrating = true;
    let currentOnboardingState = initialContinuity && typeof initialContinuity === 'object' ? (initialContinuity.onboarding_state || null) : null;
    const localizedUi = {localized_ui_json};
    function writeLog(message) {{
      logEl.textContent = typeof message === 'string' ? message : JSON.stringify(message, null, 2);
    }}
    function continuityStorageKey() {{
      return initialClientContinuity && initialClientContinuity.enabled && typeof initialClientContinuity.storage_key === 'string'
        ? initialClientContinuity.storage_key
        : null;
    }}
    function onboardingWritePath() {{
      return initialPayload && initialPayload.routes && typeof initialPayload.routes.onboarding_write === 'string' && initialPayload.routes.onboarding_write
        ? initialPayload.routes.onboarding_write
        : '/api/users/me/onboarding';
    }}
    async function persistOnboardingState(partialState) {{
      if (!partialState || typeof partialState !== 'object') return null;
      const requestBody = Object.assign({{ workspace_id: initialPayload.workspace_id }}, partialState);
      const response = await fetch(onboardingWritePath(), {{
        method: 'PUT',
        credentials: 'same-origin',
        headers: {{ 'content-type': 'application/json' }},
        body: JSON.stringify(requestBody),
      }});
      const body = await response.json();
      if (response.ok && body && typeof body === 'object' && body.state) {{
        currentOnboardingState = body.state;
        return body.state;
      }}
      writeLog(body);
      return null;
    }}
    async function persistCurrentStep(currentStep, extras) {{
      if (typeof currentStep !== 'string' || !currentStep) return null;
      const payload = Object.assign({{ current_step: currentStep }}, extras && typeof extras === 'object' ? extras : {{}});
      return persistOnboardingState(payload);
    }}
    function readShellContinuity() {{
      const key = continuityStorageKey();
      if (!key || !window.sessionStorage) return null;
      try {{
        const raw = window.sessionStorage.getItem(key);
        if (!raw) return null;
        const parsed = JSON.parse(raw);
        return parsed && typeof parsed === 'object' ? parsed : null;
      }} catch (error) {{
        writeLog('Failed to read shell continuity: ' + String(error));
        return null;
      }}
    }}
    function captureShellContinuity() {{
      return {{
        focusedSectionId,
        focusedLevel,
        designerSection: currentDesignerSection,
        validationSection: currentValidationSection,
        traceHistorySection: currentTraceHistorySection,
        artifactsHistorySection: currentArtifactsHistorySection,
        stepStateBanner: currentStepStateBanner,
      }};
    }}
    function writeShellContinuity(snapshot) {{
      if (continuityHydrating) return;
      const key = continuityStorageKey();
      if (!key || !window.sessionStorage) return;
      try {{
        window.sessionStorage.setItem(key, JSON.stringify(snapshot));
      }} catch (error) {{
        writeLog('Failed to persist shell continuity: ' + String(error));
      }}
    }}
    function applyShellContinuity(snapshot) {{
      if (!snapshot || typeof snapshot !== 'object') return;
      if (snapshot.designerSection) {{
        currentDesignerSection = snapshot.designerSection;
        writeDesignerSection(snapshot.designerSection);
      }}
      if (snapshot.validationSection) {{
        currentValidationSection = snapshot.validationSection;
        writeValidationSection(snapshot.validationSection);
      }}
      if (snapshot.stepStateBanner) {{
        currentStepStateBanner = snapshot.stepStateBanner;
        writeStepStateBanner(snapshot.stepStateBanner);
      }}
      if (typeof snapshot.focusedSectionId === 'string' && snapshot.focusedSectionId) {{
        focusedSectionId = snapshot.focusedSectionId;
      }}
      if (typeof snapshot.focusedLevel === 'string' && snapshot.focusedLevel) {{
        focusedLevel = snapshot.focusedLevel;
      }}
    }}
    function formatSummary(summary, fallbackMessage) {{
      if (!summary) return fallbackMessage;
      const headline = typeof summary.headline === 'string' && summary.headline ? summary.headline : fallbackMessage;
      const lines = Array.isArray(summary.lines) ? summary.lines.filter((line) => typeof line === 'string' && line) : [];
      return [headline, ...lines].join('\n');
    }}
    function summarizeStatusBody(body) {{
      if (!body || typeof body !== 'object') return null;
      return {{
        headline: localizedUi.statusPrefix + String(body.status || body.summary || 'unknown'),
        lines: [
          body.run_id ? ('Run id: ' + body.run_id) : null,
          body.summary ? (localizedUi.summaryPrefix + body.summary) : null,
          body.started_at ? ('Started: ' + body.started_at) : null,
          body.updated_at ? ('Updated: ' + body.updated_at) : null,
        ].filter(Boolean),
      }};
    }}
    function summarizeResultBody(body) {{
      if (!body || typeof body !== 'object') return null;
      return {{
        headline: String(body.summary || body.result_summary || body.result_state || 'Result available.'),
        lines: [
          body.result_state ? ('Result state: ' + body.result_state) : null,
          body.final_status ? ('Final status: ' + body.final_status) : null,
          body.message ? (localizedUi.messagePrefix + body.message) : null,
        ].filter(Boolean),
      }};
    }}
    function summarizeTraceBody(body) {{
      if (!body || typeof body !== 'object') return null;
      const events = Array.isArray(body.events) ? body.events : [];
      const latest = events.length ? events[events.length - 1] : null;
      return {{
        headline: 'Trace events: ' + String(Number(body.event_count || events.length || 0)),
        lines: [
          latest && latest.event_type ? ('Latest event: ' + latest.event_type) : null,
          latest && latest.node_id ? ('Latest node: ' + latest.node_id) : null,
          latest && latest.message ? (localizedUi.latestMessagePrefix + latest.message) : null,
          body.message ? (localizedUi.traceStatusPrefix + body.message) : null,
        ].filter(Boolean),
      }};
    }}
    function summarizeArtifactsBody(body) {{
      if (!body || typeof body !== 'object') return null;
      const artifacts = Array.isArray(body.artifacts) ? body.artifacts : [];
      const first = artifacts.length ? artifacts[0] : null;
      return {{
        headline: 'Artifacts: ' + String(Number(body.artifact_count || artifacts.length || 0)),
        lines: [
          first && first.artifact_id ? ('First artifact id: ' + first.artifact_id) : null,
          first && first.label ? (localizedUi.previewPrefix + first.label) : null,
          first && first.preview ? ('Payload preview: ' + first.preview) : null,
        ].filter(Boolean),
      }};
    }}
    function detailFromStatusBody(body) {{
      if (!body || typeof body !== 'object') return null;
      return {{
        title: 'Status detail',
        items: [
          body.run_id ? ('Run id: ' + body.run_id) : null,
          body.status ? (localizedUi.statusPrefix + body.status) : null,
          body.summary ? (localizedUi.summaryPrefix + body.summary) : null,
          body.started_at ? ('Started: ' + body.started_at) : null,
          body.updated_at ? ('Updated: ' + body.updated_at) : null,
          body.progress && typeof body.progress.percent !== 'undefined' ? ('Progress: ' + body.progress.percent + '%') : null,
        ].filter(Boolean),
      }};
    }}
    function detailFromResultBody(body) {{
      if (!body || typeof body !== 'object') return null;
      return {{
        title: 'Result detail',
        items: [
          body.run_id ? ('Run id: ' + body.run_id) : null,
          body.result_state ? ('Result state: ' + body.result_state) : null,
          body.final_status ? ('Final status: ' + body.final_status) : null,
          body.summary ? (localizedUi.summaryPrefix + body.summary) : (body.result_summary ? (localizedUi.summaryPrefix + body.result_summary) : null),
          body.final_output && body.final_output.output_key ? ('Output key: ' + body.final_output.output_key) : null,
          body.final_output && body.final_output.value_type ? ('Output type: ' + body.final_output.value_type) : null,
        ].filter(Boolean),
      }};
    }}
    function formatDetail(detail, fallbackMessage) {{
      if (!detail) return fallbackMessage;
      const title = typeof detail.title === 'string' && detail.title ? detail.title : 'Detail';
      const items = Array.isArray(detail.items) ? detail.items.filter((item) => typeof item === 'string' && item) : [];
      return [title, ...items.map((item) => '- ' + item)].join('\n');
    }}
    function detailFromTraceBody(body) {{
      if (!body || typeof body !== 'object') return null;
      const events = Array.isArray(body.events) ? body.events : [];
      const latest = events.length ? events[events.length - 1] : null;
      return {{
        title: 'Trace detail',
        items: [
          localizedUi.statusPrefix + String(body.status || 'unknown'),
          'Event count: ' + String(Number(body.event_count || events.length || 0)),
          latest && latest.event_type ? ('Latest event type: ' + latest.event_type) : null,
          latest && latest.node_id ? ('Latest node id: ' + latest.node_id) : null,
          latest && latest.message ? (localizedUi.latestMessagePrefix + latest.message) : null,
          body.current_focus && body.current_focus.node_id ? ('Current focus node: ' + body.current_focus.node_id) : null,
        ].filter(Boolean),
      }};
    }}
    function detailFromArtifactsBody(body) {{
      if (!body || typeof body !== 'object') return null;
      const artifacts = Array.isArray(body.artifacts) ? body.artifacts : [];
      const first = artifacts.length ? artifacts[0] : null;
      return {{
        title: 'Artifacts detail',
        items: [
          'Artifact count: ' + String(Number(body.artifact_count || artifacts.length || 0)),
          first && first.artifact_id ? ('First artifact id: ' + first.artifact_id) : null,
          first && first.kind ? ('First artifact kind: ' + first.kind) : null,
          first && first.label ? (localizedUi.firstArtifactLabelPrefix + first.label) : null,
          first && first.preview ? ('First artifact preview: ' + first.preview) : null,
        ].filter(Boolean),
      }};
    }}
    function formatStepStateBanner(banner, fallbackTitle, fallbackSummary) {{
      return {{
        title: banner && typeof banner.title === 'string' && banner.title ? banner.title : fallbackTitle,
        summary: banner && typeof banner.summary === 'string' && banner.summary ? banner.summary : fallbackSummary,
      }};
    }}
    function auxiliaryFocusTargetId(actionTarget) {{
      if (actionTarget === 'designer') return 'designer-summary-card';
      if (actionTarget === 'validation') return 'validation-summary-card';
      if (actionTarget === 'templates') return 'starter-templates-card';
      if (actionTarget === 'help') return 'contextual-help-card';
      return null;
    }}
    function renderSectionControls(container, controls) {{
      if (!container) return;
      container.innerHTML = '';
      const items = Array.isArray(controls) ? controls : [];
      for (const control of items) {{
        if (!control || typeof control !== 'object') continue;
        const button = document.createElement('button');
        button.type = 'button';
        button.className = 'secondary';
        button.textContent = String(control.label || control.control_id || localizedUi.actionFallback);
        button.dataset.actionKind = String(control.action_kind || 'none');
        button.dataset.actionTarget = String(control.action_target || '');
        button.addEventListener('click', async () => performShellAction(control));
        container.appendChild(button);
      }}
    }}
    function writeShellSection(section, currentValue, summaryEl, detailEl, controlsEl, summaryFallback, detailFallback) {{
      const nextValue = section || currentValue || {{}};
      const summary = nextValue && nextValue.summary ? nextValue.summary : null;
      const detail = nextValue && nextValue.detail ? nextValue.detail : null;
      if (summaryEl) summaryEl.textContent = formatSummary(summary, summaryFallback);
      if (detailEl) detailEl.textContent = formatDetail(detail, detailFallback);
      if (controlsEl) renderSectionControls(controlsEl, nextValue && nextValue.controls ? nextValue.controls : []);
      writeShellContinuity(captureShellContinuity());
      return nextValue;
    }}
    function writeStatusHistorySection(section) {{
      currentStatusHistorySection = writeShellSection(section, currentStatusHistorySection, statusHistorySummaryEl, statusHistoryDetailEl, statusHistoryControlsEl, 'Recent status history will appear here.', 'Status history detail will appear here.');
    }}
    function writeResultHistorySection(section) {{
      currentResultHistorySection = writeShellSection(section, currentResultHistorySection, resultHistorySummaryEl, resultHistoryDetailEl, resultHistoryControlsEl, 'Recent result history will appear here.', 'Result history detail will appear here.');
    }}
    function writeTraceHistorySection(section) {{
      currentTraceHistorySection = writeShellSection(section, currentTraceHistorySection, traceHistorySummaryEl, traceHistoryDetailEl, traceHistoryControlsEl, 'Recent trace history will appear here.', 'Trace history detail will appear here.');
    }}
    function writeArtifactsHistorySection(section) {{
      currentArtifactsHistorySection = writeShellSection(section, currentArtifactsHistorySection, artifactsHistorySummaryEl, artifactsHistoryDetailEl, artifactsHistoryControlsEl, 'Recent artifacts history will appear here.', 'Artifacts history detail will appear here.');
    }}
    function writeRecentActivitySection(section) {{
      currentRecentActivitySection = writeShellSection(section, currentRecentActivitySection, recentActivitySummaryEl, recentActivityDetailEl, recentActivityControlsEl, 'Recent activity will appear here.', 'Recent activity detail will appear here.');
    }}
    function writeHistorySummarySection(section) {{
      currentHistorySummarySection = writeShellSection(section, currentHistorySummarySection, historySummarySummaryEl, historySummaryDetailEl, historySummaryControlsEl, 'History summary will appear here.', 'History summary detail will appear here.');
    }}
    function writeDesignerSection(section) {{
      currentDesignerSection = writeShellSection(section, currentDesignerSection, designerSummaryEl, designerDetailEl, designerControlsEl, 'Open Designer to start drafting your workflow.', 'Designer detail will appear here.');
    }}
    function writeValidationSection(section) {{
      currentValidationSection = writeShellSection(section, currentValidationSection, validationSummaryEl, validationDetailEl, validationControlsEl, 'Validation guidance will appear here.', 'Validation detail will appear here.');
    }}
    async function applyTemplateControl(control) {{
      const displayName = String(control && (control.template_display_name || control.label) || localizedUi.starterTemplateFallback);
      const templateSummary = String(control && control.template_summary || localizedUi.templateSelectedSummary);
      const requestText = String(control && control.request_text || '').trim();
      const category = String(control && control.template_category || '').trim();
      const templateId = String(control && control.template_id || '').trim();
      const templateRef = String(control && (control.template_ref || control.action_target) || '').trim();
      const lookupAliases = Array.isArray(control && control.template_lookup_aliases) ? control.template_lookup_aliases.map((item) => String(item || '').trim()).filter(Boolean) : [];
      const provenance = control && control.template_provenance && typeof control.template_provenance === 'object' ? control.template_provenance : {{}};
      const compatibility = control && control.template_compatibility && typeof control.template_compatibility === 'object' ? control.template_compatibility : {{}};
      writeDesignerSection({{
        summary: {{ headline: localizedUi.designerWorkspace, lines: [
          uiText('server.shell.template_selected', 'Template selected: {{name}}', {{ name: displayName }}),
          templateSummary,
          requestText ? uiText('server.shell.designer_request', 'Designer request: {{request}}', {{ request: requestText }}) : null,
        ].filter(Boolean) }},
        detail: {{ title: 'Designer detail', items: [
          templateId ? uiText('server.shell.template_id', 'Template id: {{template_id}}', {{ template_id: templateId }}) : null,
          templateRef ? uiText('server.shell.template_ref', 'Template ref: {{template_ref}}', {{ template_ref: templateRef }}) : null,
          category ? uiText('server.shell.category', 'Category: {{category}}', {{ category }}) : null,
          lookupAliases.length ? uiText('server.shell.template_lookup_aliases', 'Lookup aliases: {{aliases}}', {{ aliases: lookupAliases.join(', ') }}) : null,
          provenance.source || provenance.family ? uiText('server.shell.template_provenance', 'Provenance: {{source}} / {{family}}', {{ source: String(provenance.source || '').trim(), family: String(provenance.family || '').trim() }}) : null,
          compatibility.family || compatibility.apply_behavior ? uiText('server.shell.template_compatibility', 'Compatibility: {{family}} / {{behavior}}', {{ family: String(compatibility.family || '').trim(), behavior: String(compatibility.apply_behavior || '').trim() }}) : null,
          requestText ? uiText('server.shell.designer_request', 'Designer request: {{request}}', {{ request: requestText }}) : null,
          uiText('server.shell.next_step_review_validation', 'Next step: review Validation, then run the draft when ready.'),
        ].filter(Boolean) }},
        controls: currentDesignerSection && currentDesignerSection.controls ? currentDesignerSection.controls : [],
      }});
      writeStepStateBanner({{
        title: 'Step 2 of 5 — Review template',
        summary: localizedUi.templateLoadedSummaryPrefix + displayName + localizedUi.templateLoadedSummarySuffix,
        action_label: localizedUi.reviewValidationAction,
        action_target: 'validation.detail',
        action_kind: 'focus_section',
        recommended_section: 'designer',
        phase: 'pre_run',
      }});
      setFocusedSection('designer', 'detail');
      writeLog('Loaded template into Designer: ' + displayName);
    }}
    async function performShellAction(control) {{
      const kind = control && typeof control.action_kind === 'string' ? control.action_kind : 'none';
      const target = control && typeof control.action_target === 'string' ? control.action_target : '';
      if (kind === 'run_draft') {{
        document.getElementById('run-draft').click();
        return;
      }}
      if (kind === 'apply_template') {{
        applyTemplateControl(control);
        return;
      }}
      if (kind === 'open_run_status') {{
        if (target) {{
          setActiveRun(target);
          await refreshLatestRunStatus();
          writeLog('Opened status for ' + target + '.');
          return;
        }}
      }}
      if (kind === 'open_run_result') {{
        if (target) {{
          setActiveRun(target);
          await refreshLatestRunResult();
          writeLog('Opened result for ' + target + '.');
          return;
        }}
      }}
      if (kind === 'open_run_trace') {{
        if (target) {{
          setActiveRun(target);
          await refreshLatestRunTrace();
          writeLog('Opened trace for ' + target + '.');
          return;
        }}
      }}
      if (kind === 'open_run_artifacts') {{
        if (target) {{
          setActiveRun(target);
          await refreshLatestRunArtifacts();
          writeLog('Opened artifacts for ' + target + '.');
          return;
        }}
      }}
      if (kind === 'open_route') {{
        if (target) {{
          window.open(target, '_blank', 'noopener');
          writeLog('Opened route ' + target + '.');
          return;
        }}
      }}
      if (kind === 'focus_auxiliary') {{
        const targetId = auxiliaryFocusTargetId(target);
        if (targetId) {{
          const node = document.getElementById(targetId);
          if (node) {{
            node.scrollIntoView({{ behavior: 'smooth', block: 'center' }});
            node.focus({{ preventScroll: true }});
            writeLog('Focused ' + target + '.');
            return;
          }}
        }}
      }}
      if (kind === 'focus_section') {{
        if (target === 'runtime.status') {{
          await persistCurrentStep('run');
          await refreshLatestRunStatus();
          return;
        }}
        if (target === 'runtime.result') {{
          await persistCurrentStep('read_result', {{ first_success_achieved: true, advanced_surfaces_unlocked: true }});
          await refreshLatestRunResult();
          return;
        }}
        if (target === 'runtime.trace') {{
          await persistCurrentStep('run');
          await refreshLatestRunTrace();
          return;
        }}
        if (target === 'runtime.artifacts') {{
          await persistCurrentStep('read_result');
          await refreshLatestRunArtifacts();
          return;
        }}
        let sectionId = target;
        let level = 'summary';
        if (target.endsWith('.detail')) {{
          const parts = target.split('.');
          sectionId = parts[0];
          level = 'detail';
        }}
        if (sectionConfig(sectionId)) {{
          if (sectionId === 'designer') {{
            await persistCurrentStep('enter_goal');
          }} else if (sectionId === 'validation') {{
            await persistCurrentStep('review_preview');
          }}
          setFocusedSection(sectionId, level);
          writeLog('Focused ' + target + '.');
          return;
        }}
        const targetId = auxiliaryFocusTargetId(sectionId);
        if (targetId) {{
          const node = document.getElementById(targetId);
          if (node) {{
            node.scrollIntoView({{ behavior: 'smooth', block: 'center' }});
            node.focus({{ preventScroll: true }});
            writeLog('Focused ' + target + '.');
            return;
          }}
        }}
      }}
      writeLog('Action target not yet wired: ' + String(target || kind));
    }}
    async function performBannerAction(banner) {{
      if (!banner || typeof banner !== 'object') {{
        writeLog('No recommended action is available.');
        return;
      }}
      await performShellAction({{
        action_kind: banner.action_kind || 'focus_section',
        action_target: banner.action_target || '',
        action_label: banner.action_label || localizedUi.openNextStep,
      }});
    }}
    function deriveStepStateBannerFromBodies(statusBody, resultBody, traceBody, artifactsBody) {{
      const normalizedStatus = String((statusBody || {{}}).status || '').toLowerCase();
      const normalizedResultState = String((resultBody || {{}}).result_state || '').toLowerCase();
      const traceCount = Number((traceBody || {{}}).event_count || (Array.isArray((traceBody || {{}}).events) ? traceBody.events.length : 0) || 0);
      const artifactCount = Number((artifactsBody || {{}}).artifact_count || (Array.isArray((artifactsBody || {{}}).artifacts) ? artifactsBody.artifacts.length : 0) || 0);
      if (normalizedResultState.startsWith('ready')) {{
        return {{ title: localizedUi.stepReadResult, summary: localizedUi.resultReadySummary }};
      }}
      if (['running', 'queued', 'accepted'].includes(normalizedStatus)) {{
        return {{ title: localizedUi.stepRun, summary: localizedUi.runInProgressSummary }};
      }}
      if (['failed', 'partial'].includes(normalizedStatus) && traceCount > 0) {{
        return {{ title: localizedUi.stepRun, summary: localizedUi.runNeedsDiagnosisSummary }};
      }}
      if (artifactCount > 0 && !normalizedResultState.startsWith('ready')) {{
        return {{ title: localizedUi.stepReadResult, summary: localizedUi.artifactsReadySummary }};
      }}
      return null;
    }}
    function writeStepStateBanner(banner) {{
      currentStepStateBanner = banner || currentStepStateBanner || initialStepStateBanner || null;
      const formatted = formatStepStateBanner(currentStepStateBanner, 'Step 1 of 5 — Enter goal', 'Describe your goal to start the first-run path.');
      const actionLabel = currentStepStateBanner && typeof currentStepStateBanner.action_label === 'string' && currentStepStateBanner.action_label ? currentStepStateBanner.action_label : localizedUi.openDesigner;
      const actionTarget = currentStepStateBanner && typeof currentStepStateBanner.action_target === 'string' && currentStepStateBanner.action_target ? currentStepStateBanner.action_target : 'designer';
      stepStateBannerTitleEl.textContent = formatted.title;
      stepStateBannerSummaryEl.textContent = formatted.summary;
      stepStateBannerActionEl.textContent = actionLabel + ' → ' + actionTarget;
      if (stepStateBannerActionButtonEl) {{
        stepStateBannerActionButtonEl.textContent = actionLabel;
        stepStateBannerActionButtonEl.disabled = !actionTarget;
        stepStateBannerActionButtonEl.dataset.actionTarget = actionTarget;
      }}
    }}
    function refreshStepStateBanner() {{
      const derived = deriveStepStateBannerFromBodies(latestStatusBodyState, latestResultBodyState, latestTraceBodyState, latestArtifactsBodyState);
      writeStepStateBanner(derived || currentStepStateBanner || initialStepStateBanner);
    }}
    function sectionConfig(sectionId) {{
      const sections = currentNavigation && Array.isArray(currentNavigation.sections) ? currentNavigation.sections : [];
      return sections.find((section) => section && section.section_id === sectionId) || null;
    }}
    function focusTargetFor(sectionId, level) {{
      const section = sectionConfig(sectionId);
      if (!section) return null;
      return document.getElementById(level === 'detail' ? section.detail_target_id : section.target_id);
    }}
    function renderRuntimeNav() {{
      const sections = currentNavigation && Array.isArray(currentNavigation.sections) ? currentNavigation.sections : [];
      runtimeNavEl.innerHTML = '';
      for (const section of sections) {{
        const button = document.createElement('button');
        button.type = 'button';
        button.className = 'secondary';
        button.textContent = section.label || section.section_id;
        button.dataset.sectionId = section.section_id;
        button.setAttribute('aria-pressed', section.section_id === focusedSectionId ? 'true' : 'false');
        button.addEventListener('click', () => setFocusedSection(section.section_id, 'summary'));
        runtimeNavEl.appendChild(button);
      }}
    }}
    function setFocusedSection(sectionId, level) {{
      focusedSectionId = sectionId || focusedSectionId || 'status';
      const target = focusTargetFor(focusedSectionId, level === 'detail' ? 'detail' : 'summary');
      const section = sectionConfig(focusedSectionId);
      if (focusStateEl) {{
        const label = section && section.label ? section.label : focusedSectionId;
        focusStateEl.textContent = localizedUi.focusPrefix + label + (focusedLevel === 'detail' ? localizedUi.focusDetailSuffix : localizedUi.focusSummarySuffix);
      }}
      const buttons = runtimeNavEl.querySelectorAll('button[data-section-id]');
      buttons.forEach((button) => {{
        button.setAttribute('aria-pressed', button.dataset.sectionId === focusedSectionId ? 'true' : 'false');
      }});
      if (target) {{
        target.scrollIntoView({{ behavior: 'smooth', block: 'center' }});
        target.focus({{ preventScroll: true }});
      }}
    }}

    function writeLatestRunStatus(message) {{
      latestRunStatusEl.textContent = typeof message === 'string' ? message : formatSummary(message, localizedUi.noRecentRun);
    }}
    function writeLatestRunResult(message) {{
      latestRunResultEl.textContent = typeof message === 'string' ? message : formatSummary(message, localizedUi.noRecentResult);
    }}
    function writeLatestRunStatusDetail(message) {{
      latestRunStatusDetailEl.textContent = typeof message === 'string' ? message : formatDetail(message, localizedUi.openLatestStatusDetailPrompt);
    }}
    function writeLatestRunResultDetail(message) {{
      latestRunResultDetailEl.textContent = typeof message === 'string' ? message : formatDetail(message, localizedUi.openLatestResultDetailPrompt);
    }}
    function writeLatestRunTrace(message) {{
      latestRunTraceEl.textContent = typeof message === 'string' ? message : formatSummary(message, localizedUi.noRecentTrace);
    }}
    function writeLatestRunArtifacts(message) {{
      latestRunArtifactsEl.textContent = typeof message === 'string' ? message : formatSummary(message, localizedUi.noRecentArtifacts);
    }}
    function writeLatestRunTraceDetail(message) {{
      latestRunTraceDetailEl.textContent = typeof message === 'string' ? message : formatDetail(message, localizedUi.openLatestTraceDetailPrompt);
    }}
    function writeLatestRunArtifactsDetail(message) {{
      latestRunArtifactsDetailEl.textContent = typeof message === 'string' ? message : formatDetail(message, localizedUi.openLatestArtifactsDetailPrompt);
    }}
    function setActiveRun(runId) {{
      if (!runId) return;
      activeRunId = runId;
      activeRunStatusPath = `/api/runs/${{runId}}`;
      activeRunResultPath = `/api/runs/${{runId}}/result`;
      activeRunTracePath = `/api/runs/${{runId}}/trace?limit=20`;
      activeRunArtifactsPath = `/api/runs/${{runId}}/artifacts`;
    }}
    async function refreshLatestRunStatus() {{
      if (!activeRunStatusPath) {{
        writeLatestRunStatus(localizedUi.noRecentRun);
        writeLatestRunStatusDetail(localizedUi.openLatestStatusDetailPrompt);
        return null;
      }}
      const response = await fetch(activeRunStatusPath, {{ credentials: 'same-origin' }});
      const body = await response.json();
      latestStatusBodyState = body;
      writeLatestRunStatus(summarizeStatusBody(body));
      writeLatestRunStatusDetail(detailFromStatusBody(body));
      refreshStepStateBanner();
      setFocusedSection('status', 'detail');
      return body;
    }}
    async function refreshLatestRunResult() {{
      if (!activeRunResultPath) {{
        writeLatestRunResult(localizedUi.noRecentResult);
        writeLatestRunResultDetail(localizedUi.openLatestResultDetailPrompt);
        return null;
      }}
      const response = await fetch(activeRunResultPath, {{ credentials: 'same-origin' }});
      const body = await response.json();
      latestResultBodyState = body;
      writeLatestRunResult(summarizeResultBody(body));
      writeLatestRunResultDetail(detailFromResultBody(body));
      const normalizedResultState = String((body || {{}}).result_state || '').toLowerCase();
      if (normalizedResultState.startsWith('ready')) {{
        await persistCurrentStep('read_result', {{ first_success_achieved: true, advanced_surfaces_unlocked: true }});
      }}
      refreshStepStateBanner();
      setFocusedSection('result', 'detail');
      return body;
    }}
    async function refreshLatestRunTrace() {{
      if (!activeRunTracePath) {{
        writeLatestRunTrace(localizedUi.noRecentTrace);
        writeLatestRunTraceDetail(localizedUi.openLatestTraceDetailPrompt);
        return null;
      }}
      const response = await fetch(activeRunTracePath, {{ credentials: 'same-origin' }});
      const body = await response.json();
      latestTraceBodyState = body;
      writeLatestRunTrace(summarizeTraceBody(body));
      writeLatestRunTraceDetail(detailFromTraceBody(body));
      refreshStepStateBanner();
      setFocusedSection('trace', 'detail');
      return body;
    }}
    async function refreshLatestRunArtifacts() {{
      if (!activeRunArtifactsPath) {{
        writeLatestRunArtifacts(localizedUi.noRecentArtifacts);
        writeLatestRunArtifactsDetail(localizedUi.openLatestArtifactsDetailPrompt);
        return null;
      }}
      const response = await fetch(activeRunArtifactsPath, {{ credentials: 'same-origin' }});
      const body = await response.json();
      latestArtifactsBodyState = body;
      writeLatestRunArtifacts(summarizeArtifactsBody(body));
      writeLatestRunArtifactsDetail(detailFromArtifactsBody(body));
      refreshStepStateBanner();
      setFocusedSection('artifacts', 'detail');
      return body;
    }}
    async function pollLatestRunUntilSettled() {{
      for (let attempt = 0; attempt < 6; attempt += 1) {{
        const statusBody = await refreshLatestRunStatus();
        const normalizedStatus = String((statusBody || {{}}).status || '').toLowerCase();
        if (['completed', 'failed', 'cancelled', 'partial'].includes(normalizedStatus)) {{
          await refreshLatestRunResult();
          await refreshLatestRunTrace();
          await refreshLatestRunArtifacts();
          return;
        }}
        await new Promise((resolve) => setTimeout(resolve, 750));
      }}
      await refreshLatestRunResult();
      await refreshLatestRunTrace();
      await refreshLatestRunArtifacts();
    }}
    renderRuntimeNav();
    writeFocusGuidance(currentNavigation);
    writeLatestRunStatus(initialRunStatusSummary || localizedUi.noRecentRun);
    writeLatestRunResult(initialRunResultSummary || localizedUi.noRecentResult);
    writeLatestRunTrace(initialRunTraceSummary || localizedUi.noRecentTrace);
    writeLatestRunArtifacts(initialRunArtifactsSummary || localizedUi.noRecentArtifacts);
    writeLatestRunStatusDetail(initialRunStatusDetail || localizedUi.openLatestStatusDetailPrompt);
    writeLatestRunResultDetail(initialRunResultDetail || localizedUi.openLatestResultDetailPrompt);
    writeLatestRunTraceDetail(initialRunTraceDetail || localizedUi.openLatestTraceDetailPrompt);
    writeLatestRunArtifactsDetail(initialRunArtifactsDetail || localizedUi.openLatestArtifactsDetailPrompt);
    writeStatusHistorySection(initialStatusHistorySection);
    writeResultHistorySection(initialResultHistorySection);
    writeTraceHistorySection(initialTraceHistorySection);
    writeArtifactsHistorySection(initialArtifactsHistorySection);
    writeRecentActivitySection(initialRecentActivitySection);
    writeHistorySummarySection(initialHistorySummarySection);
    writeDesignerSection(initialDesignerSection);
    writeValidationSection(initialValidationSection);
    writeStepStateBanner(initialStepStateBanner);
    applyShellContinuity(readShellContinuity());
    continuityHydrating = false;
    setFocusedSection(focusedSectionId, focusedLevel);
    writeShellContinuity(captureShellContinuity());
    document.getElementById('refresh').addEventListener('click', async () => {{
      const response = await fetch(initialPayload.routes.workspace_shell, {{ credentials: 'same-origin' }});
      const body = await response.json();
      writeLog(body);
      if (body.status_history_section) {{
        writeStatusHistorySection(body.status_history_section);
      }}
      if (body.result_history_section) {{
        writeResultHistorySection(body.result_history_section);
      }}
      if (body.trace_history_section) {{
        writeTraceHistorySection(body.trace_history_section);
      }}
      if (body.artifacts_history_section) {{
        writeArtifactsHistorySection(body.artifacts_history_section);
      }}
      if (body.recent_activity_section) {{
        writeRecentActivitySection(body.recent_activity_section);
      }}
      if (body.history_summary_section) {{
        writeHistorySummarySection(body.history_summary_section);
      }}
      if (body.designer_section) {{
        writeDesignerSection(body.designer_section);
      }}
      if (body.validation_section) {{
        writeValidationSection(body.validation_section);
      }}
      if (body.navigation) {{
        currentNavigation = body.navigation;
        renderRuntimeNav();
        writeFocusGuidance(currentNavigation);
      }}
      if (body.step_state_banner) {{
        writeStepStateBanner(body.step_state_banner);
      }}
      if (body.continuity && typeof body.continuity === 'object' && body.continuity.onboarding_state) {{
        currentOnboardingState = body.continuity.onboarding_state;
      }}
      if (body.latest_run_status_preview && body.latest_run_status_preview.run_id) {{
        setActiveRun(body.latest_run_status_preview.run_id);
        writeLatestRunStatus(body.latest_run_status_summary || summarizeStatusBody(body.latest_run_status_preview));
      }}
      if (body.latest_run_status_detail) {{
        writeLatestRunStatusDetail(body.latest_run_status_detail);
      }}
      if (body.latest_run_result_preview) {{
        writeLatestRunResult(body.latest_run_result_summary || summarizeResultBody(body.latest_run_result_preview));
      }}
      if (body.latest_run_result_detail) {{
        writeLatestRunResultDetail(body.latest_run_result_detail);
      }}
      if (body.latest_run_trace_preview) {{
        writeLatestRunTrace(body.latest_run_trace_summary || summarizeTraceBody(body.latest_run_trace_preview));
      }}
      if (body.latest_run_trace_detail) {{
        writeLatestRunTraceDetail(body.latest_run_trace_detail);
      }}
      if (body.latest_run_artifacts_preview) {{
        writeLatestRunArtifacts(body.latest_run_artifacts_summary || summarizeArtifactsBody(body.latest_run_artifacts_preview));
      }}
      if (body.latest_run_artifacts_detail) {{
        writeLatestRunArtifactsDetail(body.latest_run_artifacts_detail);
      }}
      if (body.navigation && body.navigation.default_section) {{
        setFocusedSection(body.navigation.default_section, body.navigation.default_level || 'summary');
      }}
      applyShellContinuity(readShellContinuity());
      setFocusedSection(focusedSectionId, focusedLevel);
      writeShellContinuity(captureShellContinuity());
    }});
    document.getElementById('run-draft').addEventListener('click', async () => {{
      if (!launchTemplate) {{
        writeLog('No runnable execution target is projected for this workspace.');
        return;
      }}
      const response = await fetch(initialPayload.routes.launch_run, {{
        method: 'POST',
        credentials: 'same-origin',
        headers: {{ 'content-type': 'application/json' }},
        body: JSON.stringify(launchTemplate),
      }});
      const body = await response.json();
      writeLog(body);
      if (body.run_id) {{
        setActiveRun(body.run_id);
        writeLatestRunStatus({{ headline: 'Status: accepted', lines: ['Run id: ' + body.run_id, 'Summary: Launch accepted.'] }});
        writeLatestRunStatusDetail({{ title: 'Status detail', items: ['Run id: ' + body.run_id, 'Status: accepted', 'Summary: Launch accepted.'] }});
        await persistCurrentStep('run');
        setFocusedSection('status', 'detail');
        writeLatestRunResult('Waiting for run result.');
        writeLatestRunResultDetail(localizedUi.openLatestResultDetailPrompt);
        writeLatestRunTrace('Waiting for trace details.');
        writeLatestRunArtifacts('Waiting for artifact details.');
        writeLatestRunTraceDetail(localizedUi.openLatestTraceDetailPrompt);
        writeLatestRunArtifactsDetail(localizedUi.openLatestArtifactsDetailPrompt);
        writeStepStateBanner({{ title: localizedUi.stepRun, summary: localizedUi.launchAcceptedSummary, action_label: localizedUi.openStatus, action_target: 'runtime.status', action_kind: 'focus_section' }});
        await pollLatestRunUntilSettled();
      }}
    }});
    document.getElementById('open-status').addEventListener('click', async () => {{
      if (!activeRunStatusPath) {{
        writeLog(localizedUi.noRecentRun);
        return;
      }}
      const body = await refreshLatestRunStatus();
      writeLog(body || localizedUi.noRecentRun);
      await refreshLatestRunResult();
      await refreshLatestRunTrace();
      await refreshLatestRunArtifacts();
    }});
    document.getElementById('open-result').addEventListener('click', async () => {{
      const body = await refreshLatestRunResult();
      writeLog(body || localizedUi.noRecentResult);
    }});
    document.getElementById('step-state-banner-action-button').addEventListener('click', async () => {{
      await performBannerAction(deriveStepStateBannerFromBodies(latestStatusBodyState, latestResultBodyState, latestTraceBodyState, latestArtifactsBodyState) || initialStepStateBanner);
    }});
    document.getElementById('open-trace').addEventListener('click', async () => {{
      const body = await refreshLatestRunTrace();
      writeLog(body || localizedUi.noRecentTrace);
    }});
    document.getElementById('open-artifacts').addEventListener('click', async () => {{
      const body = await refreshLatestRunArtifacts();
      writeLog(body || localizedUi.noRecentArtifacts);
    }});
  </script>
</body>
</html>"""
    replacements = {
        'Nexa Runtime Shell': ui_text('server.shell.title', app_language=app_language, fallback_text='Nexa Runtime Shell'),
        'Status:': ui_text('server.shell.status', app_language=app_language, fallback_text='Status') + ':',
        'Workspace shell actions': ui_text('server.shell.actions', app_language=app_language, fallback_text='Workspace shell actions'),
        'Run draft': ui_text('server.shell.run_draft', app_language=app_language, fallback_text='Run draft'),
        'Refresh shell': ui_text('server.shell.refresh', app_language=app_language, fallback_text='Refresh shell'),
        'Open latest run status': ui_text('server.shell.open_latest_status', app_language=app_language, fallback_text='Open latest run status'),
        'Open latest result': ui_text('server.shell.open_latest_result', app_language=app_language, fallback_text='Open latest result'),
        'Open latest trace': ui_text('server.shell.open_latest_trace', app_language=app_language, fallback_text='Open latest trace'),
        'Open latest artifacts': ui_text('server.shell.open_latest_artifacts', app_language=app_language, fallback_text='Open latest artifacts'),
        'Runtime focus': ui_text('server.shell.runtime_focus', app_language=app_language, fallback_text='Runtime focus'),
        'Runtime section navigation': ui_text('server.shell.runtime_nav_aria', app_language=app_language, fallback_text='Runtime section navigation'),
        'Step state banner': ui_text('server.shell.step_state_banner', app_language=app_language, fallback_text='Step state banner'),
        'Designer workspace': ui_text('server.shell.designer_workspace', app_language=app_language, fallback_text='Designer workspace'),
        'Open Designer to start drafting your workflow.': ui_text('server.shell.designer_open_default', app_language=app_language, fallback_text='Open Designer to start drafting your workflow.'),
        'Validation review': ui_text('server.shell.validation_review', app_language=app_language, fallback_text='Validation review'),
        'Validation guidance will appear here.': ui_text('server.shell.validation_default', app_language=app_language, fallback_text='Validation guidance will appear here.'),
        'Designer detail layer': ui_text('server.shell.designer_detail_layer', app_language=app_language, fallback_text='Designer detail layer'),
        'Designer detail will appear here.': ui_text('server.shell.designer_detail_default', app_language=app_language, fallback_text='Designer detail will appear here.'),
        'Validation detail layer': ui_text('server.shell.validation_detail_layer', app_language=app_language, fallback_text='Validation detail layer'),
        'Validation detail will appear here.': ui_text('server.shell.validation_detail_default', app_language=app_language, fallback_text='Validation detail will appear here.'),
        'Privacy and data handling': ui_text('server.shell.privacy', app_language=app_language, fallback_text='Privacy and data handling'),
        'Mobile first-run': ui_text('server.shell.mobile_first_run', app_language=app_language, fallback_text='Mobile first-run'),
        'Mobile first-run projection unavailable.': ui_text('server.shell.mobile_unavailable', app_language=app_language, fallback_text='Mobile first-run projection unavailable.'),
        'Starter templates': ui_text('server.shell.starter_templates', app_language=app_language, fallback_text='Starter templates'),
        'Latest run status': ui_text('server.shell.latest_run_status', app_language=app_language, fallback_text='Latest run status'),
        'Waiting for run status.': ui_text('server.shell.waiting_status', app_language=app_language, fallback_text='Waiting for run status.'),
        'Latest run result': ui_text('server.shell.latest_run_result', app_language=app_language, fallback_text='Latest run result'),
        'Waiting for run result.': ui_text('server.shell.waiting_result', app_language=app_language, fallback_text='Waiting for run result.'),
        'Status detail layer': ui_text('server.shell.status_detail_layer', app_language=app_language, fallback_text='Status detail layer'),
        'Open latest run status to view the detail layer.': ui_text('server.shell.status_detail_prompt', app_language=app_language, fallback_text='Open latest run status to view the detail layer.'),
        'Result detail layer': ui_text('server.shell.result_detail_layer', app_language=app_language, fallback_text='Result detail layer'),
        'Open latest run result to view the detail layer.': ui_text('server.shell.result_detail_prompt', app_language=app_language, fallback_text='Open latest run result to view the detail layer.'),
        'Run status history': ui_text('server.shell.run_status_history', app_language=app_language, fallback_text='Run status history'),
        'Recent status history will appear here.': ui_text('server.shell.status_history_summary', app_language=app_language, fallback_text='Recent status history will appear here.'),
        'Status history detail will appear here.': ui_text('server.shell.status_history_detail', app_language=app_language, fallback_text='Status history detail will appear here.'),
        'Run result history': ui_text('server.shell.run_result_history', app_language=app_language, fallback_text='Run result history'),
        'Recent result history will appear here.': ui_text('server.shell.result_history_summary', app_language=app_language, fallback_text='Recent result history will appear here.'),
        'Result history detail will appear here.': ui_text('server.shell.result_history_detail', app_language=app_language, fallback_text='Result history detail will appear here.'),
        'Trace history': ui_text('server.shell.trace_history', app_language=app_language, fallback_text='Trace history'),
        'Recent trace history will appear here.': ui_text('server.shell.trace_history_summary', app_language=app_language, fallback_text='Recent trace history will appear here.'),
        'Trace history detail will appear here.': ui_text('server.shell.trace_history_detail', app_language=app_language, fallback_text='Trace history detail will appear here.'),
        'Artifacts history': ui_text('server.shell.artifacts_history', app_language=app_language, fallback_text='Artifacts history'),
        'Recent artifacts history will appear here.': ui_text('server.shell.artifacts_history_summary', app_language=app_language, fallback_text='Recent artifacts history will appear here.'),
        'Artifacts history detail will appear here.': ui_text('server.shell.artifacts_history_detail', app_language=app_language, fallback_text='Artifacts history detail will appear here.'),
        'Latest trace': ui_text('server.shell.latest_trace', app_language=app_language, fallback_text='Latest trace'),
        'Waiting for trace details.': ui_text('server.shell.waiting_trace', app_language=app_language, fallback_text='Waiting for trace details.'),
        'Latest artifacts': ui_text('server.shell.latest_artifacts', app_language=app_language, fallback_text='Latest artifacts'),
        'Waiting for artifact details.': ui_text('server.shell.waiting_artifacts', app_language=app_language, fallback_text='Waiting for artifact details.'),
        'Trace detail layer': ui_text('server.shell.trace_detail_layer', app_language=app_language, fallback_text='Trace detail layer'),
        'Open latest trace to view the detail layer.': ui_text('server.shell.trace_detail_prompt', app_language=app_language, fallback_text='Open latest trace to view the detail layer.'),
        'Artifacts detail layer': ui_text('server.shell.artifacts_detail_layer', app_language=app_language, fallback_text='Artifacts detail layer'),
        'Open latest artifacts to view the detail layer.': ui_text('server.shell.artifacts_detail_prompt', app_language=app_language, fallback_text='Open latest artifacts to view the detail layer.'),
        'Last action log': ui_text('server.shell.last_action_log', app_language=app_language, fallback_text='Last action log'),
        'Ready.': ui_text('server.shell.ready', app_language=app_language, fallback_text='Ready.'),
        'Recommended next: ': ui_text('server.shell.recommended_next_prefix', app_language=app_language, fallback_text='Recommended next: '),
        'Focus: ': ui_text('server.shell.focus_state', app_language=app_language, fallback_text='Focus: {section}', section='').replace('{section}', ''),
        'Open Designer': ui_text('server.shell.open_designer', app_language=app_language, fallback_text='Open Designer'),
        'Open Status': ui_text('server.shell.open_status', app_language=app_language, fallback_text='Open Status'),
        'Open Result': ui_text('server.shell.open_result', app_language=app_language, fallback_text='Open Result'),
        'Open Trace': ui_text('server.shell.open_trace', app_language=app_language, fallback_text='Open Trace'),
        'Open Artifacts': ui_text('server.shell.open_artifacts', app_language=app_language, fallback_text='Open Artifacts'),
        'Step 1 of 5 — Enter goal': ui_text('server.shell.step.enter_goal', app_language=app_language, fallback_text='Step 1 of 5 — Enter goal'),
        'Step 4 of 5 — Run': ui_text('server.shell.step.run', app_language=app_language, fallback_text='Step 4 of 5 — Run'),
        'Step 5 of 5 — Read result': ui_text('server.shell.step.read_result', app_language=app_language, fallback_text='Step 5 of 5 — Read result'),
        'Run id: ': ui_text('server.shell.run_id_prefix', app_language=app_language, fallback_text='Run id: '),
        'Summary: ': ui_text('server.shell.summary_prefix', app_language=app_language, fallback_text='Summary: '),
        'Result state: ': ui_text('server.shell.result_state_prefix', app_language=app_language, fallback_text='Result state: '),
        'Trace events: ': ui_text('server.shell.trace_events_prefix', app_language=app_language, fallback_text='Trace events: '),
        'Latest event: ': ui_text('server.shell.latest_event_prefix', app_language=app_language, fallback_text='Latest event: '),
        'Latest event type: ': ui_text('server.shell.latest_event_type_prefix', app_language=app_language, fallback_text='Latest event type: '),
        'Latest node: ': ui_text('server.shell.latest_node_prefix', app_language=app_language, fallback_text='Latest node: '),
        'Latest node id: ': ui_text('server.shell.latest_node_id_prefix', app_language=app_language, fallback_text='Latest node id: '),
        'Latest message: ': ui_text('server.shell.latest_message_prefix', app_language=app_language, fallback_text='Latest message: '),
        'Trace status: ': ui_text('server.shell.trace_status_prefix', app_language=app_language, fallback_text='Trace status: '),
        'Artifacts: ': ui_text('server.shell.artifacts_prefix', app_language=app_language, fallback_text='Artifacts: '),
        'Status detail': ui_text('server.shell.status_detail_title', app_language=app_language, fallback_text='Status detail'),
        'Result detail': ui_text('server.shell.result_detail_title', app_language=app_language, fallback_text='Result detail'),
        'Trace detail': ui_text('server.shell.trace_detail_title', app_language=app_language, fallback_text='Trace detail'),
        'Artifacts detail': ui_text('server.shell.artifacts_detail_title', app_language=app_language, fallback_text='Artifacts detail'),
        'No recent run is available yet.': ui_text('server.shell.no_recent_run', app_language=app_language, fallback_text='No recent run is available yet.'),
        'No recent run result is available yet.': ui_text('server.shell.no_recent_result', app_language=app_language, fallback_text='No recent run result is available yet.'),
        'No recent trace is available yet.': ui_text('server.shell.no_recent_trace', app_language=app_language, fallback_text='No recent trace is available yet.'),
        'No recent artifacts are available yet.': ui_text('server.shell.no_recent_artifacts', app_language=app_language, fallback_text='No recent artifacts are available yet.'),
        'Recent runs: ': ui_text('server.shell.recent_runs_prefix', app_language=app_language, fallback_text='Recent runs: '),
        'Recent results: ': ui_text('server.shell.recent_results_prefix', app_language=app_language, fallback_text='Recent results: '),
        'Recent traces: ': ui_text('server.shell.recent_traces_prefix', app_language=app_language, fallback_text='Recent traces: '),
        'Recent artifact sets: ': ui_text('server.shell.recent_artifact_sets_prefix', app_language=app_language, fallback_text='Recent artifact sets: '),
        'Validation: ': ui_text('server.shell.validation_prefix', app_language=app_language, fallback_text='Validation: '),
        'Request status: ': ui_text('server.shell.request_status_prefix', app_language=app_language, fallback_text='Request status: '),
        'Preview status: ': ui_text('server.shell.preview_status_prefix', app_language=app_language, fallback_text='Preview status: '),
        'Approval status: ': ui_text('server.shell.approval_status_prefix', app_language=app_language, fallback_text='Approval status: '),
        'Submit enabled: ': ui_text('server.shell.submit_enabled_prefix', app_language=app_language, fallback_text='Submit enabled: '),
        'Opened status for ': ui_text('server.shell.opened_status_prefix', app_language=app_language, fallback_text='Opened status for '),
        'Opened result for ': ui_text('server.shell.opened_result_prefix', app_language=app_language, fallback_text='Opened result for '),
        'Opened trace for ': ui_text('server.shell.opened_trace_prefix', app_language=app_language, fallback_text='Opened trace for '),
        'Opened artifacts for ': ui_text('server.shell.opened_artifacts_prefix', app_language=app_language, fallback_text='Opened artifacts for '),
        'Launch accepted.': ui_text('server.shell.launch_accepted', app_language=app_language, fallback_text='Launch accepted.'),
        'Run is in progress. Watch Status while Nexa prepares the result.': ui_text('server.shell.run_in_progress_summary', app_language=app_language, fallback_text='Run is in progress. Watch Status while Nexa prepares the result.'),
        'Run needs diagnosis. Open Trace next to understand what happened.': ui_text('server.shell.run_needs_diagnosis_summary', app_language=app_language, fallback_text='Run needs diagnosis. Open Trace next to understand what happened.'),
        'Result is ready. Open Result next to finish the first-run path.': ui_text('server.shell.result_ready_summary', app_language=app_language, fallback_text='Result is ready. Open Result next to finish the first-run path.'),
        'A readable result is not ready yet, but artifacts are available. Open Artifacts next.': ui_text('server.shell.artifacts_ready_summary', app_language=app_language, fallback_text='A readable result is not ready yet, but artifacts are available. Open Artifacts next.'),
        'Launch accepted. Watch Status while Nexa starts the run.': ui_text('server.shell.launch_accepted_summary', app_language=app_language, fallback_text='Launch accepted. Watch Status while Nexa starts the run.'),
        'Review the projected next action.': ui_text('server.shell.review_projected_action', app_language=app_language, fallback_text='Review the projected next action.'),
        'Contextual help': ui_text('server.shell.contextual_help', app_language=app_language, fallback_text='Contextual help'),
        'Open status first to follow the current runtime state.': ui_text('server.shell.guidance.status_follow', app_language=app_language, fallback_text='Open status first to follow the current runtime state.'),
        'Resolve the blocking validation issue before continuing the first-run path.': ui_text('server.shell.guidance.validation_blocked', app_language=app_language, fallback_text='Resolve the blocking validation issue before continuing the first-run path.'),
        'A readable result is ready, so the mobile first-run path should move to Result next.': ui_text('server.shell.guidance.result_ready', app_language=app_language, fallback_text='A readable result is ready, so the mobile first-run path should move to Result next.'),
        'The latest run needs explanation, so open Trace next in the first-run path.': ui_text('server.shell.guidance.trace_next', app_language=app_language, fallback_text='The latest run needs explanation, so open Trace next in the first-run path.'),
        'Artifacts are available before a readable result summary, so open Artifacts next.': ui_text('server.shell.guidance.artifacts_next', app_language=app_language, fallback_text='Artifacts are available before a readable result summary, so open Artifacts next.'),
        'The mobile first-run path is still in progress, so follow Status first.': ui_text('server.shell.guidance.status_running', app_language=app_language, fallback_text='The mobile first-run path is still in progress, so follow Status first.'),
        'Server-backed workspace progression points to Result as the next first-run step.': ui_text('server.shell.guidance.result_progression', app_language=app_language, fallback_text='Server-backed workspace progression points to Result as the next first-run step.'),
        'Server-backed workspace progression points to Status while the run step is active.': ui_text('server.shell.guidance.status_progression', app_language=app_language, fallback_text='Server-backed workspace progression points to Status while the run step is active.'),
        'Server-backed workspace progression points to Validation before the run step.': ui_text('server.shell.guidance.validation_progression', app_language=app_language, fallback_text='Server-backed workspace progression points to Validation before the run step.'),
        'Use Designer first to describe or review the workflow before running.': ui_text('server.shell.guidance.designer_progression', app_language=app_language, fallback_text='Use Designer first to describe or review the workflow before running.'),
        'Start with Designer, then move to Validation and Run when the workflow is ready.': ui_text('server.shell.guidance.designer_default', app_language=app_language, fallback_text='Start with Designer, then move to Validation and Run when the workflow is ready.'),
        'Review the proposed workflow preview before approving.': ui_text('server.shell.summary.review_preview', app_language=app_language, fallback_text='Review the proposed workflow preview before approving.'),
        'Approve the proposed workflow so Nexa can prepare it for running.': ui_text('server.shell.summary.approve', app_language=app_language, fallback_text='Approve the proposed workflow so Nexa can prepare it for running.'),
        'Run the workflow to generate your first result.': ui_text('server.shell.summary.run', app_language=app_language, fallback_text='Run the workflow to generate your first result.'),
        'Read the result to finish the first-run path.': ui_text('server.shell.summary.read_result', app_language=app_language, fallback_text='Read the result to finish the first-run path.'),
        'Follow the guided first-run path one step at a time.': ui_text('server.shell.summary.follow_steps', app_language=app_language, fallback_text='Follow the guided first-run path one step at a time.'),
        'Server-backed workspace progression says review and validation come next before the run step.': ui_text('server.shell.summary.review_before_run', app_language=app_language, fallback_text='Server-backed workspace progression says review and validation come next before the run step.'),
        'Server-backed workspace progression says start in Designer by describing your goal.': ui_text('server.shell.summary.start_in_designer', app_language=app_language, fallback_text='Server-backed workspace progression says start in Designer by describing your goal.'),
        'Server-backed workspace progression says the run step is next. Open Status to follow it.': ui_text('server.shell.summary.run_next', app_language=app_language, fallback_text='Server-backed workspace progression says the run step is next. Open Status to follow it.'),
        'Server-backed workspace progression says read the latest result next.': ui_text('server.shell.summary.read_result_next', app_language=app_language, fallback_text='Server-backed workspace progression says read the latest result next.'),
        'Resolve the blocking review issue before you run.': ui_text('server.shell.summary.resolve_blocking_review', app_language=app_language, fallback_text='Resolve the blocking review issue before you run.'),
        'Step 2 of 5 — Review preview': ui_text('server.shell.step.review_preview', app_language=app_language, fallback_text='Step 2 of 5 — Review preview'),
        'Step 3 of 5 — Approve': ui_text('server.shell.step.approve', app_language=app_language, fallback_text='Step 3 of 5 — Approve'),
        'Output type: ': ui_text('server.shell.output_type_prefix', app_language=app_language, fallback_text='Output type: '),
        'Current focus node: ': ui_text('server.shell.current_focus_node_prefix', app_language=app_language, fallback_text='Current focus node: '),
        'First artifact kind: ': ui_text('server.shell.first_artifact_kind_prefix', app_language=app_language, fallback_text='First artifact kind: '),
        'First artifact label: ': ui_text('server.shell.first_artifact_label_prefix', app_language=app_language, fallback_text='First artifact label: '),
        'Action target not yet wired: ': ui_text('server.shell.action_target_unwired_prefix', app_language=app_language, fallback_text='Action target not yet wired: '),
        'No recommended action is available.': ui_text('server.shell.no_recommended_action', app_language=app_language, fallback_text='No recommended action is available.'),
        'Open next step': ui_text('server.shell.open_next_step', app_language=app_language, fallback_text='Open next step'),
        'Loaded template into Designer: ': ui_text('server.shell.loaded_template_log_prefix', app_language=app_language, fallback_text='Loaded template into Designer: '),
        'Focused ': ui_text('server.shell.focused_prefix', app_language=app_language, fallback_text='Focused '),
        ' detail': ui_text('server.shell.focus_detail_suffix', app_language=app_language, fallback_text=' detail'),
        ' summary': ui_text('server.shell.focus_summary_suffix', app_language=app_language, fallback_text=' summary'),
        'Template selected.': ui_text('server.shell.template_selected_summary', app_language=app_language, fallback_text='Template selected.'),
        'Template id: ': ui_text('server.shell.template_id', app_language=app_language, fallback_text='Template id: {{template_id}}', template_id='').replace('{template_id}', ''),
        'Category: ': ui_text('server.shell.category', app_language=app_language, fallback_text='Category: {{category}}', category='').replace('{category}', ''),
        'Next step: review Validation, then run the draft when ready.': ui_text('server.shell.next_step_review_validation', app_language=app_language, fallback_text='Next step: review Validation, then run the draft when ready.'),
        'Step 2 of 5 — Review template': ui_text('server.shell.banner.review_template_title', app_language=app_language, fallback_text='Step 2 of 5 — Review template'),
        'Template "': 'Template "',
        'Review Validation': ui_text('server.shell.banner.review_validation', app_language=app_language, fallback_text='Review Validation'),
    }
    for old, new in replacements.items():
        if new and old in html:
            html = html.replace(old, new)
    return html
