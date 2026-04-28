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
from src.ui.builder_shell import read_builder_shell_view_model
from src.ui.i18n import normalize_ui_language, ui_language_from_sources, ui_text
from src.ui.template_gallery import read_template_gallery_view_model
from src.server.workspace_shell_sections import build_shell_section
from src.server.provider_setup_readiness import evaluate_required_provider_setup
from src.server.workspace_onboarding_api import _provider_continuity_summary_for_workspace
from src.storage.nex_api import coerce_nex_loaded_artifact, resolve_nex_execution_target
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
    loaded = coerce_nex_loaded_artifact(source)
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
    try:
        descriptor = resolve_nex_execution_target(model)
    except (TypeError, ValueError):
        return None
    return {
        "target_type": descriptor.target_type,
        "target_ref": descriptor.target_ref,
    }


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
        "execution_state": status,
        "status_family": summary,
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
    updated_at = str(result_row.get("updated_at") or "").strip() or None
    final_output = result_row.get("final_output") if isinstance(result_row.get("final_output"), Mapping) else None
    output_preview = str((final_output or {}).get("value_preview") or "").strip() or None
    if not any((summary, result_state, final_status, output_preview)):
        return None
    return {
        "run_id": run_id,
        "result_state": result_state,
        "final_status": final_status,
        "result_summary": summary,
        "summary": summary,
        "output_preview": output_preview,
        "updated_at": updated_at,
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
    summary = str(preview.get("result_summary") or preview.get("summary") or "Result available.").strip() or "Result available."
    result_state = str(preview.get("result_state") or "").strip() or None
    final_status = str(preview.get("final_status") or "").strip() or None
    output_preview = str(preview.get("output_preview") or "").strip() or None
    lines = _summary_lines(
        f"Result state: {result_state}" if result_state else None,
        f"Final status: {final_status}" if final_status else None,
        f"Output preview: {output_preview}" if output_preview else None,
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
            f"Summary: {preview.get('result_summary') or preview.get('summary')}" if preview.get("result_summary") or preview.get("summary") else None,
            f"Output preview: {preview.get('output_preview')}" if preview.get("output_preview") else None,
            f"Updated: {preview.get('updated_at')}" if preview.get("updated_at") else None,
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
    *,
    app_language: str = "en",
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
            "label": ui_text("server.shell.open_latest_result", app_language=app_language, fallback_text="Open latest result"),
            "action_kind": "focus_section",
            "action_target": "runtime.result",
        },
        {
            "control_id": "result-history-open-page",
            "label": ui_text("server.shell.open_result_history_page", app_language=app_language, fallback_text="Open result history page"),
            "action_kind": "open_route",
            "action_target": f"/app/workspaces/{workspace_id}/results?app_language={app_language}",
        },
        {
            "control_id": "result-history-open-route",
            "label": ui_text("server.shell.open_result_history_route", app_language=app_language, fallback_text="Open result history"),
            "action_kind": "open_route",
            "action_target": f"/api/workspaces/{workspace_id}/result-history",
        },
    ]
    if len(entries) > 1:
        previous = entries[1]
        controls.append(
            {
                "control_id": f"result-history-open-{previous['run_id']}",
                "label": ui_text(
                    "server.shell.open_previous_result",
                    app_language=app_language,
                    fallback_text="Open {run_id} result",
                    run_id=previous["run_id"],
                ),
                "action_kind": "open_run_result",
                "action_target": previous["run_id"],
            }
        )
    return build_shell_section(
        headline=ui_text("server.shell.result_history_section", app_language=app_language, fallback_text="Result history"),
        lines=_summary_lines(
            ui_text("server.shell.recent_results_prefix", app_language=app_language, fallback_text="Recent results: ") + str(len(entries)) if entries else ui_text("server.shell.no_recent_result_history", app_language=app_language, fallback_text="No recent result history is available yet."),
            ui_text("server.shell.latest_prefix", app_language=app_language, fallback_text="Latest: ") + f"{latest['run_id']} — {latest['result_state']}" if latest else None,
        ),
        detail_title=ui_text("server.shell.result_history_detail", app_language=app_language, fallback_text="Result history detail"),
        detail_items=[f"{index + 1}. {entry['run_id']} — {entry['result_state']} — {entry['summary']}" for index, entry in enumerate(entries[:3])],
        detail_empty="Result history entries will appear here as runs complete.",
        controls=controls,
        history=entries[:3],
    )



def _recent_activity_entries(
    recent_run_rows: Sequence[Mapping[str, Any]],
    onboarding_rows: Sequence[Mapping[str, Any]],
    provider_binding_rows: Sequence[Mapping[str, Any]],
    managed_secret_rows: Sequence[Mapping[str, Any]],
    provider_probe_rows: Sequence[Mapping[str, Any]],
    workspace_id: str,
) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    normalized_workspace_id = str(workspace_id or "").strip()
    for row in _recent_run_rows_for_workspace(recent_run_rows, normalized_workspace_id):
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
    for row in _recent_onboarding_rows_for_workspace(onboarding_rows, normalized_workspace_id):
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
    binding_name_by_key = {
        str(row.get("provider_key") or "").strip().lower(): str(row.get("display_name") or row.get("provider_key") or "provider").strip() or "provider"
        for row in provider_binding_rows
        if str(row.get("workspace_id") or "").strip() == normalized_workspace_id
    }
    for row in provider_binding_rows:
        if str(row.get("workspace_id") or "").strip() != normalized_workspace_id:
            continue
        provider_key = str(row.get("provider_key") or "").strip().lower()
        binding_id = str(row.get("binding_id") or "").strip()
        occurred_at = str(row.get("updated_at") or row.get("created_at") or "").strip() or None
        if not provider_key or not binding_id or not occurred_at:
            continue
        enabled = bool(row.get("enabled", True))
        secret_ref = str(row.get("secret_ref") or "").strip()
        status = "disabled" if not enabled else ("missing_secret" if not secret_ref else "configured")
        entries.append({
            "activity_id": f"binding:{binding_id}:{occurred_at or ''}",
            "activity_type": "provider_binding",
            "label": provider_key,
            "status": status,
            "occurred_at": occurred_at,
            "summary": f"Provider binding for {binding_name_by_key.get(provider_key, provider_key)} is {status}.",
        })
    for row in managed_secret_rows:
        if str(row.get("workspace_id") or "").strip() != normalized_workspace_id:
            continue
        provider_key = str(row.get("provider_key") or "").strip().lower()
        secret_ref = str(row.get("secret_ref") or "").strip()
        occurred_at = str(row.get("last_rotated_at") or "").strip() or None
        if not provider_key or not secret_ref or not occurred_at:
            continue
        entries.append({
            "activity_id": f"secret:{provider_key}:{secret_ref}:{occurred_at or ''}",
            "activity_type": "managed_secret",
            "label": provider_key,
            "status": "resolved",
            "occurred_at": occurred_at,
            "summary": f"Managed secret for {binding_name_by_key.get(provider_key, provider_key)} was updated.",
        })
    for row in provider_probe_rows:
        if str(row.get("workspace_id") or "").strip() != normalized_workspace_id:
            continue
        provider_key = str(row.get("provider_key") or "").strip().lower()
        probe_event_id = str(row.get("probe_event_id") or "").strip()
        occurred_at = str(row.get("occurred_at") or "").strip() or None
        probe_status = str(row.get("probe_status") or "updated").strip() or "updated"
        if not provider_key or not probe_event_id or not occurred_at:
            continue
        entries.append({
            "activity_id": f"probe:{probe_event_id}:{occurred_at or ''}",
            "activity_type": "provider_probe",
            "label": provider_key,
            "status": probe_status,
            "occurred_at": occurred_at,
            "summary": f"Provider probe for {binding_name_by_key.get(provider_key, provider_key)} is {probe_status}.",
        })
    entries.sort(key=lambda item: (str(item.get("occurred_at") or ""), str(item.get("activity_id") or "")), reverse=True)
    return entries[:5]


def _recent_activity_section(
    recent_run_rows: Sequence[Mapping[str, Any]],
    onboarding_rows: Sequence[Mapping[str, Any]],
    provider_binding_rows: Sequence[Mapping[str, Any]],
    managed_secret_rows: Sequence[Mapping[str, Any]],
    provider_probe_rows: Sequence[Mapping[str, Any]],
    workspace_id: str,
    *,
    app_language: str = "en",
) -> dict[str, Any]:
    entries = _recent_activity_entries(recent_run_rows, onboarding_rows, provider_binding_rows, managed_secret_rows, provider_probe_rows, workspace_id)
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



def _provider_readiness_entries(
    provider_binding_rows: Sequence[Mapping[str, Any]],
    provider_probe_rows: Sequence[Mapping[str, Any]],
    workspace_id: str,
) -> list[dict[str, Any]]:
    normalized_workspace_id = str(workspace_id or "").strip()
    if not normalized_workspace_id:
        return []
    bindings = [
        dict(row) for row in provider_binding_rows
        if str(row.get("workspace_id") or "").strip() == normalized_workspace_id
    ]
    probes = [
        dict(row) for row in provider_probe_rows
        if str(row.get("workspace_id") or "").strip() == normalized_workspace_id
    ]
    probes.sort(key=lambda row: (str(row.get("occurred_at") or ""), str(row.get("probe_event_id") or "")), reverse=True)
    latest_probe_by_key: dict[str, Mapping[str, Any]] = {}
    for row in probes:
        key = str(row.get("provider_key") or "").strip()
        if key and key not in latest_probe_by_key:
            latest_probe_by_key[key] = row
    bindings.sort(key=lambda row: (str(row.get("updated_at") or row.get("created_at") or ""), str(row.get("binding_id") or "")), reverse=True)
    entries: list[dict[str, Any]] = []
    if bindings:
        for row in bindings[:3]:
            provider_key = str(row.get("provider_key") or "").strip() or "provider"
            latest_probe = latest_probe_by_key.get(provider_key)
            entries.append({
                "provider_key": provider_key,
                "display_name": str(row.get("display_name") or provider_key).strip() or provider_key,
                "binding_id": str(row.get("binding_id") or "").strip() or None,
                "enabled": bool(row.get("enabled", True)),
                "credential_source": str(row.get("credential_source") or "").strip() or None,
                "probe_status": str((latest_probe or {}).get("probe_status") or "not_checked").strip() or "not_checked",
                "probe_event_id": str((latest_probe or {}).get("probe_event_id") or "").strip() or None,
                "occurred_at": str((latest_probe or {}).get("occurred_at") or row.get("updated_at") or row.get("created_at") or "").strip() or None,
            })
    else:
        for row in probes[:3]:
            provider_key = str(row.get("provider_key") or "").strip() or "provider"
            entries.append({
                "provider_key": provider_key,
                "display_name": str(row.get("display_name") or provider_key).strip() or provider_key,
                "binding_id": None,
                "enabled": None,
                "credential_source": None,
                "probe_status": str(row.get("probe_status") or "not_checked").strip() or "not_checked",
                "probe_event_id": str(row.get("probe_event_id") or "").strip() or None,
                "occurred_at": str(row.get("occurred_at") or "").strip() or None,
            })
    return entries


def _provider_readiness_section(
    provider_binding_rows: Sequence[Mapping[str, Any]],
    managed_secret_rows: Sequence[Mapping[str, Any]],
    provider_probe_rows: Sequence[Mapping[str, Any]],
    workspace_id: str,
    *,
    app_language: str = "en",
) -> dict[str, Any]:
    continuity = _provider_continuity_summary_for_workspace(
        workspace_id,
        provider_binding_rows=provider_binding_rows,
        managed_secret_rows=managed_secret_rows,
        provider_probe_rows=provider_probe_rows,
    )
    entries = _provider_readiness_entries(provider_binding_rows, provider_probe_rows, workspace_id)
    lines = _summary_lines(
        ui_text("server.shell.configured_providers_prefix", app_language=app_language, fallback_text="Configured providers: ") + str(getattr(continuity, "provider_binding_count", 0)) if continuity is not None else ui_text("server.shell.no_provider_readiness", app_language=app_language, fallback_text="No provider readiness data is available yet."),
        ui_text("server.shell.recent_provider_probes_prefix", app_language=app_language, fallback_text="Recent provider probes: ") + str(getattr(continuity, "recent_probe_count", 0)) if continuity is not None else None,
        ui_text("server.shell.latest_provider_activity_prefix", app_language=app_language, fallback_text="Latest provider activity: ") + str(getattr(continuity, "latest_provider_activity_at", "")) if continuity is not None and getattr(continuity, "latest_provider_activity_at", None) else None,
    )
    detail_items = [
        f"{index + 1}. {entry['provider_key']} — {entry['probe_status']}"
        + (f" — {entry['display_name']}" if entry.get('display_name') else '')
        + (f" — {entry['binding_id']}" if entry.get('binding_id') else '')
        for index, entry in enumerate(entries)
    ]
    controls = [
        {
            "control_id": "provider-readiness-open-bindings",
            "label": ui_text("server.shell.open_provider_bindings", app_language=app_language, fallback_text="Open provider bindings"),
            "action_kind": "open_route",
            "action_target": f"/api/workspaces/{workspace_id}/provider-bindings",
        },
        {
            "control_id": "provider-readiness-open-health",
            "label": ui_text("server.shell.open_provider_health", app_language=app_language, fallback_text="Open provider health"),
            "action_kind": "open_route",
            "action_target": f"/api/workspaces/{workspace_id}/provider-bindings/health",
        },
    ]
    return build_shell_section(
        headline=ui_text("server.shell.provider_readiness", app_language=app_language, fallback_text="Provider readiness"),
        lines=lines,
        detail_title=ui_text("server.shell.provider_readiness_detail", app_language=app_language, fallback_text="Provider readiness detail"),
        detail_items=detail_items,
        summary_empty=ui_text("server.shell.no_provider_readiness", app_language=app_language, fallback_text="No provider readiness data is available yet."),
        detail_empty=ui_text("server.shell.provider_readiness_pending", app_language=app_language, fallback_text="Provider readiness details will appear here after provider setup or health checks."),
        controls=controls,
        history=entries,
    )



def _first_success_setup_section(
    shell_map: Mapping[str, Any],
    template_gallery: Mapping[str, Any] | None,
    server_product_readiness_review: Mapping[str, Any] | None,
    *,
    onboarding_state: Mapping[str, Any] | None,
    provider_binding_rows: Sequence[Mapping[str, Any]],
    managed_secret_rows: Sequence[Mapping[str, Any]],
    provider_probe_rows: Sequence[Mapping[str, Any]],
    workspace_id: str,
    routes: Mapping[str, Any],
    app_language: str = "en",
    persisted_state: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    designer = shell_map.get("designer") or {}
    request_state = designer.get("request_state") or {}
    provider_inline = designer.get("provider_inline_key_entry") or {}
    provider_guidance = designer.get("provider_setup_guidance") or {}
    gallery = template_gallery or designer.get("template_gallery") or {}
    templates = tuple(gallery.get("templates") or ())
    persisted = dict(persisted_state or {})
    selected_template_display = str(
        persisted.get("selected_template_display_name")
        or persisted.get("selected_template_id")
        or ""
    ).strip() or None
    connected_inline = int(provider_inline.get("connected_count") or 0)
    continuity = _provider_continuity_summary_for_workspace(
        workspace_id,
        provider_binding_rows=provider_binding_rows,
        managed_secret_rows=managed_secret_rows,
        provider_probe_rows=provider_probe_rows,
    )
    connected_server = int(getattr(continuity, "provider_binding_count", 0) or 0)
    latest_probe = str(getattr(continuity, "latest_probe_status", "") or "").strip() or None
    setup_stage = {}
    if isinstance(server_product_readiness_review, Mapping):
        stages = server_product_readiness_review.get("stages") or ()
        if len(stages) > 0 and isinstance(stages[0], Mapping):
            setup_stage = dict(stages[0])
    setup_state = str(setup_stage.get("stage_state") or "inactive").strip() or "inactive"
    setup_summary = str(setup_stage.get("summary") or "").strip()
    onboarding_step = _normalized_onboarding_current_step(onboarding_state)
    entry_path_kind = str(setup_stage.get("entry_path_kind") or "goal_entry").strip() or "goal_entry"
    current_step_id = str(setup_stage.get("current_step_id") or "choose_entry_path").strip() or "choose_entry_path"
    next_step_id = str(setup_stage.get("next_step_id") or "").strip() or None
    provider_step_needed = bool(setup_stage.get("provider_step_needed"))
    step_order = tuple(setup_stage.get("step_order") or ("choose_entry_path", "connect_provider", "review_draft", "run"))
    controls: list[dict[str, Any]] = []

    def _append_control(control_id: str, label: str | None, action_target: str | None):
        if not label or not action_target:
            return
        if any(item.get("action_target") == action_target for item in controls):
            return
        controls.append({
            "control_id": control_id,
            "label": label,
            "action_kind": "open_route" if action_target.startswith("/") else "focus_section",
            "action_target": action_target,
        })

    starter_templates_target = str(routes.get("starter_template_catalog_page") or routes.get("starter_template_catalog") or "").strip() or None
    provider_bindings_target = str(routes.get("workspace_provider_bindings") or "").strip() or None
    provider_health_target = str(routes.get("workspace_provider_health") or "").strip() or None
    onboarding_target = str(routes.get("onboarding") or "").strip() or None

    if setup_state == "goal_entry_needed":
        _append_control("setup-open-designer", ui_text("server.shell.open_designer", app_language=app_language, fallback_text="Open Designer"), "designer")
        if current_step_id == "run":
            _append_control("setup-open-onboarding", ui_text("server.shell.open_onboarding", app_language=app_language, fallback_text="Open onboarding"), onboarding_target)
            _append_control("setup-open-starter-templates", ui_text("server.shell.open_starter_templates", app_language=app_language, fallback_text="Open starter templates"), starter_templates_target)
        else:
            _append_control("setup-open-starter-templates", ui_text("server.shell.open_starter_templates", app_language=app_language, fallback_text="Open starter templates"), starter_templates_target)
            _append_control("setup-open-onboarding", ui_text("server.shell.open_onboarding", app_language=app_language, fallback_text="Open onboarding"), onboarding_target)
    elif setup_state == "starter_template_path":
        _append_control("setup-open-starter-templates", ui_text("server.shell.open_starter_templates", app_language=app_language, fallback_text="Open starter templates"), starter_templates_target)
        _append_control("setup-open-designer", ui_text("server.shell.open_designer", app_language=app_language, fallback_text="Open Designer"), "designer")
    elif setup_state == "provider_setup_needed":
        _append_control("setup-open-provider-bindings", ui_text("server.shell.open_provider_bindings", app_language=app_language, fallback_text="Open provider bindings"), provider_bindings_target)
        if entry_path_kind == "starter_template":
            _append_control("setup-open-starter-templates", ui_text("server.shell.open_starter_templates", app_language=app_language, fallback_text="Open starter templates"), starter_templates_target)
        else:
            _append_control("setup-open-designer", ui_text("server.shell.open_designer", app_language=app_language, fallback_text="Open Designer"), "designer")
        _append_control("setup-open-provider-health", ui_text("server.shell.open_provider_health", app_language=app_language, fallback_text="Open provider health"), provider_health_target)
    elif setup_state == "onboarding_continuation":
        _append_control("setup-open-review", ui_text("server.shell.review_preview_action", app_language=app_language, fallback_text="Review preview"), "validation.detail")
        if provider_step_needed:
            _append_control("setup-open-provider-bindings", ui_text("server.shell.open_provider_bindings", app_language=app_language, fallback_text="Open provider bindings"), provider_bindings_target)
        _append_control("setup-open-onboarding", ui_text("server.shell.open_onboarding", app_language=app_language, fallback_text="Open onboarding"), onboarding_target)
    else:
        if entry_path_kind == "starter_template":
            _append_control("setup-open-starter-templates", ui_text("server.shell.open_starter_templates", app_language=app_language, fallback_text="Open starter templates"), starter_templates_target)
        else:
            _append_control("setup-open-designer", ui_text("server.shell.open_designer", app_language=app_language, fallback_text="Open Designer"), "designer")

    if setup_state != "onboarding_continuation":
        _append_control("setup-open-onboarding", ui_text("server.shell.open_onboarding", app_language=app_language, fallback_text="Open onboarding"), onboarding_target)

    path_fallbacks = {
        "goal_entry": "Goal entry",
        "starter_template": "Starter template",
        "onboarding_continuation": "Onboarding continuation",
    }
    step_fallbacks = {
        "choose_entry_path": "Choose entry path",
        "connect_provider": "Connect AI model if needed",
        "review_draft": "Review draft or proposal",
        "run": "Run",
    }
    path_label = ui_text(
        f"server.shell.setup_path.{entry_path_kind}",
        app_language=app_language,
        fallback_text=path_fallbacks.get(entry_path_kind, entry_path_kind.replace("_", " ").title()),
    )
    current_step_label = ui_text(
        f"server.shell.setup_step.{current_step_id}",
        app_language=app_language,
        fallback_text=step_fallbacks.get(current_step_id, current_step_id.replace("_", " ").title()),
    )
    next_step_label = ui_text(
        f"server.shell.setup_step.{next_step_id}",
        app_language=app_language,
        fallback_text=step_fallbacks.get(next_step_id, next_step_id.replace("_", " ").title()),
    ) if next_step_id else None
    ordered_step_labels = [
        ui_text(
            f"server.shell.setup_step.{step_id}",
            app_language=app_language,
            fallback_text=step_fallbacks.get(step_id, step_id.replace("_", " ").title()),
        )
        for step_id in step_order
    ]
    step_order_summary = " → ".join(f"{index + 1}. {label}" for index, label in enumerate(ordered_step_labels))

    lines = _summary_lines(
        ui_text("server.shell.first_success_setup_state_prefix", app_language=app_language, fallback_text="Setup state: {state}", state=ui_text(f"shell.product_readiness.stage_state.{setup_state}", app_language=app_language, fallback_text=setup_state.replace("_", " ")) if setup_state != "inactive" else ui_text("shell.product_readiness.stage_state.inactive", app_language=app_language, fallback_text="Inactive")),
        ui_text("server.shell.first_success_setup_path_prefix", app_language=app_language, fallback_text="Current path: {path}", path=path_label),
        ui_text("server.shell.first_success_setup_current_step_prefix", app_language=app_language, fallback_text="Current step: {step}", step=current_step_label),
        ui_text("server.shell.first_success_setup_next_step_prefix", app_language=app_language, fallback_text="Next after this: {step}", step=next_step_label) if next_step_label else None,
        setup_summary or None,
        ui_text("server.shell.first_success_setup_selected_template_prefix", app_language=app_language, fallback_text="Selected starter template: {name}", name=selected_template_display) if selected_template_display else None,
        ui_text("server.shell.first_success_setup_templates_prefix", app_language=app_language, fallback_text="Starter templates: {count}", count=str(len(templates))),
        ui_text("server.shell.first_success_setup_providers_prefix", app_language=app_language, fallback_text="Connected providers: {count}", count=str(max(connected_inline, connected_server))),
    )
    detail_items = _summary_lines(
        ui_text("server.shell.first_success_setup_step_order_prefix", app_language=app_language, fallback_text="Step order: {steps}", steps=step_order_summary),
        ui_text("server.shell.first_success_setup_request_prefix", app_language=app_language, fallback_text="Request status: {status}", status=str(request_state.get("request_status") or "empty")),
        ui_text("server.shell.first_success_setup_onboarding_prefix", app_language=app_language, fallback_text="Onboarding step: {step}", step=onboarding_step) if onboarding_step else None,
        ui_text("server.shell.first_success_setup_provider_guidance_prefix", app_language=app_language, fallback_text="Provider setup summary: {summary}", summary=str(provider_guidance.get("summary") or setup_summary or "")) if provider_guidance.get("summary") or setup_summary else None,
        ui_text("server.shell.first_success_setup_probe_prefix", app_language=app_language, fallback_text="Latest provider probe: {status}", status=latest_probe) if latest_probe else None,
        ui_text("server.shell.first_success_setup_inline_prefix", app_language=app_language, fallback_text="Inline provider options: {count}", count=str(len(tuple(provider_inline.get("preset_options") or ())))) if provider_inline else None,
    )
    section = build_shell_section(
        headline=ui_text("server.shell.first_success_setup", app_language=app_language, fallback_text="First-success setup"),
        lines=lines,
        detail_title=ui_text("server.shell.first_success_setup_detail", app_language=app_language, fallback_text="First-success setup detail"),
        detail_items=detail_items,
        controls=controls,
        summary_empty=ui_text("server.shell.first_success_setup_pending", app_language=app_language, fallback_text="First-success setup guidance will appear here once the workspace shell is available."),
        detail_empty=ui_text("server.shell.first_success_setup_pending", app_language=app_language, fallback_text="First-success setup guidance will appear here once the workspace shell is available."),
    )
    section["setup_state"] = setup_state
    section["entry_path_kind"] = entry_path_kind
    section["current_step_id"] = current_step_id
    section["next_step_id"] = next_step_id
    section["step_order"] = list(step_order)
    section["recommended_action_target"] = setup_stage.get("recommended_action_target")
    section["recommended_action_label"] = setup_stage.get("recommended_action_label")
    section["blocker_count"] = int(setup_stage.get("blocker_count") or 0)
    section["pending_count"] = int(setup_stage.get("pending_count") or 0)
    return section


def _first_success_run_section(
    shell_map: Mapping[str, Any],
    server_product_readiness_review: Mapping[str, Any] | None,
    *,
    latest_run_status_preview: Mapping[str, Any] | None,
    latest_run_result_preview: Mapping[str, Any] | None,
    latest_run_trace_preview: Mapping[str, Any] | None,
    latest_run_artifacts_preview: Mapping[str, Any] | None,
    onboarding_state: Mapping[str, Any] | None,
    workspace_id: str,
    routes: Mapping[str, Any],
    app_language: str = "en",
) -> dict[str, Any]:
    validation = shell_map.get("validation") or {}
    validation_summary = (validation.get("summary") or {}).get("headline")
    setup_stage = {}
    run_stage = {}
    if isinstance(server_product_readiness_review, Mapping):
        stages = server_product_readiness_review.get("stages") or ()
        if len(stages) > 0 and isinstance(stages[0], Mapping):
            setup_stage = dict(stages[0])
        if len(stages) > 1 and isinstance(stages[1], Mapping):
            run_stage = dict(stages[1])

    setup_state = str(setup_stage.get("stage_state") or "inactive").strip() or "inactive"
    setup_action_label = str(setup_stage.get("recommended_action_label") or "").strip() or None
    setup_action_target = str(setup_stage.get("recommended_action_target") or "").strip() or None
    setup_current_step_id = str(setup_stage.get("current_step_id") or "").strip() or None
    onboarding_step = _normalized_onboarding_current_step(onboarding_state)

    run_state = str(run_stage.get("stage_state") or "inactive").strip() or "inactive"
    run_summary = str(run_stage.get("summary") or "").strip()
    run_action_id = str(run_stage.get("recommended_action_id") or "").strip() or None
    run_action_label = str(run_stage.get("recommended_action_label") or "").strip() or None
    run_action_target = str(run_stage.get("recommended_action_target") or "").strip() or None

    latest_run_status_preview = latest_run_status_preview or {}
    latest_run_result_preview = latest_run_result_preview or {}
    latest_run_trace_preview = latest_run_trace_preview or {}
    latest_run_artifacts_preview = latest_run_artifacts_preview or {}
    latest_status = str(latest_run_status_preview.get("status") or latest_run_status_preview.get("execution_state") or "").strip() or None
    latest_run_id = str(latest_run_status_preview.get("run_id") or latest_run_result_preview.get("run_id") or "").strip() or None
    latest_result_state = str(latest_run_result_preview.get("result_state") or "").strip() or None
    latest_result_summary = str(latest_run_result_preview.get("result_summary") or latest_run_result_preview.get("summary") or latest_run_result_preview.get("final_status") or "").strip() or None
    latest_trace_events = int(latest_run_trace_preview.get("event_count") or 0)
    latest_artifact_count = int(latest_run_artifacts_preview.get("artifact_count") or 0)

    controls: list[dict[str, Any]] = []

    def _append_control(control_id: str, label: str | None, action_target: str | None):
        if not label or not action_target:
            return
        if any(item.get("action_target") == action_target for item in controls):
            return
        action_kind = "open_route" if action_target.startswith("/") else "focus_section"
        if action_target == "execution":
            action_kind = "run_draft"
        controls.append({
            "control_id": control_id,
            "label": label,
            "action_kind": action_kind,
            "action_target": action_target,
        })

    onboarding_target = str(routes.get("onboarding") or "").strip() or None
    validation_target = "validation.detail"
    launch_target = str(routes.get("workspace_shell_launch") or routes.get("launch_run") or "").strip() or None
    run_status_target = str(routes.get("latest_run_status") or "").strip() or None
    result_history_target = str(routes.get("workspace_result_history_page") or "").strip() or None

    if run_state in {"waiting", "inactive"}:
        run_path_kind = "setup_prerequisite"
        current_step_id = setup_current_step_id or ("review_draft" if setup_state in {"entry_ready", "ready", "starter_template_path", "onboarding_continuation"} else "choose_entry_path")
        next_step_id = "run" if current_step_id == "review_draft" else "review_draft"
        if setup_action_target:
            _append_control(f"first-success-run-return-to-{setup_state}", setup_action_label, setup_action_target)
        else:
            _append_control("first-success-run-open-validation", ui_text("server.shell.open_validation_detail", app_language=app_language, fallback_text="Open Validation detail"), validation_target)
            _append_control("first-success-run-open-designer", ui_text("server.shell.open_designer", app_language=app_language, fallback_text="Open Designer"), "designer")
        _append_control("first-success-run-open-onboarding", ui_text("server.shell.open_onboarding", app_language=app_language, fallback_text="Open onboarding"), onboarding_target)
    elif run_state == "fix_before_run":
        if onboarding_step in {"review_preview", "approve"}:
            run_path_kind = "review_before_run"
            current_step_id = "review_draft"
            next_step_id = "run"
            _append_control("first-success-run-open-review", ui_text("server.shell.review_preview_action", app_language=app_language, fallback_text="Review preview"), validation_target)
            _append_control("first-success-run-open-onboarding", ui_text("server.shell.open_onboarding", app_language=app_language, fallback_text="Open onboarding"), onboarding_target)
        else:
            run_path_kind = "validation_fix"
            current_step_id = "review_draft"
            next_step_id = "run"
            _append_control("first-success-run-open-validation", ui_text("server.shell.open_validation_detail", app_language=app_language, fallback_text="Open Validation detail"), validation_target)
            _append_control("first-success-run-open-designer", ui_text("server.shell.open_designer", app_language=app_language, fallback_text="Open Designer"), "designer")
    elif run_state == "ready_to_run":
        run_path_kind = "launch_run"
        current_step_id = "run"
        next_step_id = "read_result"
        _append_control("first-success-run-launch", ui_text("server.shell.launch_run", app_language=app_language, fallback_text="Launch run"), launch_target)
        _append_control("first-success-run-open-validation", ui_text("server.shell.open_validation_detail", app_language=app_language, fallback_text="Open Validation detail"), validation_target)
    elif run_state == "run_in_progress":
        run_path_kind = "monitor_run"
        current_step_id = "run"
        next_step_id = "read_result"
        _append_control("first-success-run-open-status", ui_text("server.shell.open_run_status", app_language=app_language, fallback_text="Open run status"), run_status_target)
        _append_control("first-success-run-open-trace", ui_text("server.shell.open_trace", app_language=app_language, fallback_text="Open Trace"), "runtime.trace")
    else:
        run_path_kind = "read_result"
        current_step_id = "read_result"
        next_step_id = None
        _append_control("first-success-run-open-result", ui_text("server.shell.open_result", app_language=app_language, fallback_text="Open Result"), "runtime.result")
        draft_write_target = str(routes.get("workspace_shell_draft_write") or "").strip() or None
        if draft_write_target:
            completion_patch = {
                "beginner_first_success_achieved": True,
                "advanced_surfaces_unlocked": True,
                "beginner_current_step": "read_result",
            }
            if latest_run_id:
                completion_patch["beginner_first_success_run_id"] = latest_run_id
            if latest_run_result_preview.get("output_ref"):
                completion_patch["beginner_first_success_output_ref"] = str(latest_run_result_preview.get("output_ref"))
            elif latest_run_result_preview.get("final_output") and isinstance(latest_run_result_preview.get("final_output"), Mapping):
                output_key = str((latest_run_result_preview.get("final_output") or {}).get("output_key") or "").strip()
                if output_key:
                    completion_patch["beginner_first_success_output_ref"] = output_key
            if latest_run_artifacts_preview.get("first_artifact_id"):
                completion_patch["beginner_first_success_artifact_ref"] = str(latest_run_artifacts_preview.get("first_artifact_id"))
            controls.append({
                "control_id": "first-success-run-mark-result-read",
                "label": ui_text("builder.action.mark_first_result_read", app_language=app_language, fallback_text="Mark result as read"),
                "action_kind": "first_success_completion",
                "action_target": draft_write_target,
                "fallback_focus_target": "runtime.result",
                "completion_metadata_patch": completion_patch,
            })
        _append_control("first-success-run-open-results-page", ui_text("server.shell.open_result_history_page", app_language=app_language, fallback_text="Open result history page"), result_history_target)

    if run_action_target:
        _append_control(f"first-success-run-{run_action_id or 'primary'}", run_action_label, run_action_target)

    path_fallbacks = {
        "setup_prerequisite": "Setup prerequisite",
        "validation_fix": "Validation fix",
        "review_before_run": "Review before run",
        "launch_run": "Launch run",
        "monitor_run": "Monitor active run",
        "read_result": "Read result",
    }
    step_fallbacks = {
        "choose_entry_path": "Choose entry path",
        "connect_provider": "Connect AI model if needed",
        "review_draft": "Review draft or proposal",
        "run": "Run",
        "read_result": "Read result",
    }
    path_label = ui_text(
        f"server.shell.run_path.{run_path_kind}",
        app_language=app_language,
        fallback_text=path_fallbacks.get(run_path_kind, run_path_kind.replace("_", " ").title()),
    )
    current_step_label = ui_text(
        f"server.shell.run_step.{current_step_id}",
        app_language=app_language,
        fallback_text=step_fallbacks.get(current_step_id, current_step_id.replace("_", " ").title()),
    )
    next_step_label = ui_text(
        f"server.shell.run_step.{next_step_id}",
        app_language=app_language,
        fallback_text=step_fallbacks.get(next_step_id, next_step_id.replace("_", " ").title()),
    ) if next_step_id else None
    step_order = ["review_draft", "run", "read_result"]
    step_order_summary = " → ".join(
        f"{index + 1}. {ui_text(f'server.shell.run_step.{step_id}', app_language=app_language, fallback_text=step_fallbacks.get(step_id, step_id.replace('_', ' ').title()))}"
        for index, step_id in enumerate(step_order)
    )

    lines = _summary_lines(
        ui_text("server.shell.first_success_run_state_prefix", app_language=app_language, fallback_text="Run state: {state}", state=ui_text(f"shell.product_readiness.stage_state.{run_state}", app_language=app_language, fallback_text=run_state.replace("_", " "))),
        ui_text("server.shell.first_success_run_path_prefix", app_language=app_language, fallback_text="Current path: {path}", path=path_label),
        ui_text("server.shell.first_success_run_current_step_prefix", app_language=app_language, fallback_text="Current step: {step}", step=current_step_label),
        ui_text("server.shell.first_success_run_next_step_prefix", app_language=app_language, fallback_text="Next after this: {step}", step=next_step_label) if next_step_label else None,
        run_summary or None,
        ui_text("server.shell.first_success_run_validation_prefix", app_language=app_language, fallback_text="Validation: {status}", status=str(validation_summary or "unknown")),
        ui_text("server.shell.first_success_run_status_prefix", app_language=app_language, fallback_text="Current run status: {status}", status=latest_status) if latest_status else None,
    )

    detail_items = _summary_lines(
        ui_text("server.shell.first_success_run_step_order_prefix", app_language=app_language, fallback_text="Step order: {steps}", steps=step_order_summary),
        ui_text("server.shell.first_success_run_run_id_prefix", app_language=app_language, fallback_text="Latest run id: {run_id}", run_id=latest_run_id) if latest_run_id else None,
        ui_text("server.shell.first_success_run_result_prefix", app_language=app_language, fallback_text="Latest result: {state}", state=latest_result_state) if latest_result_state else None,
        ui_text("server.shell.first_success_run_result_summary_prefix", app_language=app_language, fallback_text="Result summary: {summary}", summary=latest_result_summary) if latest_result_summary else None,
        ui_text("server.shell.first_success_run_trace_prefix", app_language=app_language, fallback_text="Trace events: {count}", count=str(latest_trace_events)),
        ui_text("server.shell.first_success_run_artifacts_prefix", app_language=app_language, fallback_text="Artifacts ready: {count}", count=str(latest_artifact_count)),
    )

    section = build_shell_section(
        headline=ui_text("server.shell.first_success_run", app_language=app_language, fallback_text="First-success run"),
        lines=lines,
        detail_title=ui_text("server.shell.first_success_run_detail", app_language=app_language, fallback_text="First-success run detail"),
        detail_items=detail_items,
        controls=controls,
        summary_empty=ui_text("server.shell.first_success_run_pending", app_language=app_language, fallback_text="First-success run guidance will appear here once the workflow is ready to execute."),
        detail_empty=ui_text("server.shell.first_success_run_pending", app_language=app_language, fallback_text="First-success run guidance will appear here once the workflow is ready to execute."),
    )
    section["run_state"] = run_state
    section["run_path_kind"] = run_path_kind
    section["current_step_id"] = current_step_id
    section["next_step_id"] = next_step_id
    section["step_order"] = step_order
    section["recommended_action_id"] = run_action_id
    section["recommended_action_target"] = run_action_target
    return section



def _first_success_flow_section(
    shell_map: Mapping[str, Any],
    routes: Mapping[str, Any],
    *,
    app_language: str = "en",
) -> dict[str, Any]:
    flow = shell_map.get("first_success_flow") if isinstance(shell_map, Mapping) else {}
    flow = flow if isinstance(flow, Mapping) else {}
    result = flow.get("result_reading") if isinstance(flow.get("result_reading"), Mapping) else {}
    designer = flow.get("designer_proposal") if isinstance(flow.get("designer_proposal"), Mapping) else {}
    steps = tuple(item for item in (flow.get("steps") or ()) if isinstance(item, Mapping))

    flow_state = str(flow.get("flow_state") or "hidden").strip() or "hidden"
    current_step_id = str(flow.get("current_step_id") or "").strip() or None
    current_step_label = str(flow.get("current_step_label") or current_step_id or "").strip() or None
    summary = str(flow.get("summary") or "").strip() or None
    next_action_id = str(flow.get("next_action_id") or "").strip() or None
    next_action_label = str(flow.get("next_action_label") or "").strip() or None
    unlock_condition = str(flow.get("unlock_condition") or "").strip() or None
    advanced_unlocked = bool(flow.get("advanced_surfaces_unlocked"))

    def _action_target(action_id: str | None) -> str | None:
        if action_id == "open_result_history":
            return str(routes.get("workspace_result_history_page") or "").strip() or None
        if action_id in {"open_runtime_monitoring", "mark_first_result_read"}:
            return "runtime.result"
        if action_id in {"open_designer", "approve_for_commit"}:
            return "designer"
        if action_id == "open_provider_setup":
            return str(routes.get("workspace_provider_bindings") or "").strip() or "designer"
        if action_id == "open_file_input":
            return str(routes.get("workspace_upload_page") or "").strip() or None
        if action_id == "open_node_configuration":
            return "validation.detail"
        return None

    controls: list[dict[str, Any]] = []
    target = _action_target(next_action_id)
    if next_action_label and target:
        controls.append({
            "control_id": f"first-success-flow-{next_action_id}",
            "label": next_action_label,
            "action_kind": "open_route" if target.startswith("/") else "focus_section",
            "action_target": target,
        })

    completion_action_id = str(result.get("completion_action_id") or "").strip() or None
    completion_action_label = str(result.get("completion_action_label") or "").strip() or None
    completion_target = _action_target(completion_action_id)
    if completion_action_label and completion_target:
        completion_patch = result.get("completion_metadata_patch") if isinstance(result.get("completion_metadata_patch"), Mapping) else {}
        if completion_action_id == "mark_first_result_read":
            controls.append({
                "control_id": f"first-success-flow-{completion_action_id}",
                "label": completion_action_label,
                "action_kind": "first_success_completion",
                "action_target": str(routes.get("workspace_shell_draft_write") or "").strip() or completion_target,
                "fallback_focus_target": completion_target,
                "completion_metadata_patch": dict(completion_patch),
            })
        else:
            controls.append({
                "control_id": f"first-success-flow-{completion_action_id}",
                "label": completion_action_label,
                "action_kind": "focus_section",
                "action_target": completion_target,
            })

    lines = _summary_lines(
        ui_text("server.shell.first_success_flow_state_prefix", app_language=app_language, fallback_text="Flow state: {state}", state=flow_state.replace("_", " ")),
        ui_text("server.shell.first_success_flow_current_step_prefix", app_language=app_language, fallback_text="Current step: {step}", step=current_step_label or ui_text("server.shell.first_success_flow_no_step", app_language=app_language, fallback_text="No active step")),
        summary,
        ui_text("server.shell.first_success_flow_unlock_prefix", app_language=app_language, fallback_text="Advanced surfaces: {state}", state=(ui_text("server.shell.unlocked", app_language=app_language, fallback_text="unlocked") if advanced_unlocked else ui_text("server.shell.locked", app_language=app_language, fallback_text="locked"))),
        ui_text("server.shell.first_success_flow_unlock_condition_prefix", app_language=app_language, fallback_text="Unlock condition: {condition}", condition=unlock_condition) if unlock_condition else None,
    )

    detail_items: list[str] = []
    for step in steps:
        step_id = str(step.get("step_id") or "").strip() or "step"
        label = str(step.get("label") or step_id).strip()
        state = str(step.get("state") or "pending").strip() or "pending"
        step_summary = str(step.get("summary") or "").strip()
        detail_items.append(f"{label}: {state}")
        if step_summary:
            detail_items.append(f"{label} summary: {step_summary}")
    if designer and designer.get("visible"):
        detail_items.append(f"Designer proposal: {designer.get('proposal_state') or 'available'}")
        if designer.get("summary"):
            detail_items.append(f"Designer summary: {designer.get('summary')}")
    if result and result.get("visible"):
        detail_items.append(f"Result reading: {result.get('state') or 'available'}")
        if result.get("summary"):
            detail_items.append(f"Result summary: {result.get('summary')}")
        if result.get("output_ref"):
            detail_items.append(f"Output ref: {result.get('output_ref')}")
        if result.get("artifact_ref"):
            detail_items.append(f"Artifact ref: {result.get('artifact_ref')}")

    section = build_shell_section(
        headline=ui_text("server.shell.first_success_flow", app_language=app_language, fallback_text="First-success flow"),
        lines=lines,
        detail_title=ui_text("server.shell.first_success_flow_detail", app_language=app_language, fallback_text="First-success flow detail"),
        detail_items=detail_items,
        summary_empty=ui_text("server.shell.first_success_flow_pending", app_language=app_language, fallback_text="First-success flow guidance will appear here once the workspace shell is available."),
        detail_empty=ui_text("server.shell.first_success_flow_pending", app_language=app_language, fallback_text="First-success flow guidance will appear here once the workspace shell is available."),
        controls=controls,
        history=steps,
    )
    section.update({
        "flow_state": flow_state,
        "current_step_id": current_step_id,
        "next_action_id": next_action_id,
        "advanced_surfaces_unlocked": advanced_unlocked,
        "unlock_condition": unlock_condition,
        "result_reading": dict(result),
        "designer_proposal": dict(designer),
    })
    return section



def _return_use_reentry_context_from_request(
    request: Mapping[str, Any] | None,
    *,
    workspace_id: str,
    result_rows_by_run_id: Mapping[str, Mapping[str, Any]] | None,
    app_language: str,
) -> dict[str, Any] | None:
    if not isinstance(request, Mapping):
        return None
    return_use = str(request.get("return_use") or "").strip()
    if return_use != "selected_result":
        return None
    run_id = str(request.get("run_id") or "").strip()
    if not run_id:
        return None
    result_row = dict((result_rows_by_run_id or {}).get(run_id) or {})
    if result_row and str(result_row.get("workspace_id") or workspace_id).strip() not in {"", workspace_id}:
        return None
    final_output = result_row.get("final_output") if isinstance(result_row.get("final_output"), Mapping) else {}
    output_ref = str(result_row.get("output_ref") or final_output.get("output_key") or request.get("output_ref") or "").strip() or None
    summary = str(result_row.get("result_summary") or result_row.get("final_status") or "").strip() or None
    result_state = str(result_row.get("result_state") or "selected_result").strip() or "selected_result"
    workspace_href = f"/app/workspaces/{workspace_id}?app_language={app_language}&return_use=selected_result&run_id={run_id}"
    result_href = f"/app/workspaces/{workspace_id}/results?app_language={app_language}&run_id={run_id}"
    return {
        "source": "result_history",
        "source_label": ui_text("server.shell.return_use_selected_source_label", app_language=app_language, fallback_text="Selected result"),
        "run_id": run_id,
        "output_ref": output_ref,
        "result_state": result_state,
        "summary": summary or ui_text("server.shell.return_use_selected_summary", app_language=app_language, fallback_text="Continue with the selected result as the current return-use context."),
        "workspace_href": workspace_href,
        "result_href": result_href,
        "action_label": ui_text("server.shell.return_use_selected_action", app_language=app_language, fallback_text="Continue with selected result"),
        "open_result_label": ui_text("server.shell.return_use_selected_open_result", app_language=app_language, fallback_text="Reopen selected result"),
    }

def _return_use_continuity_section(
    server_product_readiness_review: Mapping[str, Any] | None,
    *,
    recent_run_rows: Sequence[Mapping[str, Any]],
    result_rows_by_run_id: Mapping[str, Mapping[str, Any]] | None,
    feedback_rows: Sequence[Mapping[str, Any]],
    onboarding_state: Mapping[str, Any] | None,
    workspace_id: str,
    routes: Mapping[str, Any],
    app_language: str = "en",
    selected_result_reentry_context: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    result_rows_by_run_id = result_rows_by_run_id or {}
    return_stage = {}
    if isinstance(server_product_readiness_review, Mapping):
        stages = server_product_readiness_review.get("stages") or ()
        if len(stages) > 2 and isinstance(stages[2], Mapping):
            return_stage = dict(stages[2])

    return_state = str(return_stage.get("stage_state") or "inactive").strip() or "inactive"
    return_summary = str(return_stage.get("summary") or "").strip()
    return_path_kind = str(return_stage.get("return_path_kind") or "first_success_prerequisite").strip() or "first_success_prerequisite"
    current_step_id = str(return_stage.get("current_step_id") or "complete_first_success").strip() or "complete_first_success"
    next_step_id = str(return_stage.get("next_step_id") or "").strip() or None
    step_order = tuple(return_stage.get("step_order") or ("complete_first_success", "reopen_result", "reopen_workflow", "share_feedback"))
    recent_runs = list(_recent_run_rows_for_workspace(recent_run_rows, workspace_id, limit=5))
    result_entries = [
        {
            "run_id": run_id,
            "result_state": str((result_rows_by_run_id.get(run_id) or {}).get("result_state") or "missing").strip() or "missing",
            "summary": str((result_rows_by_run_id.get(run_id) or {}).get("result_summary") or (result_rows_by_run_id.get(run_id) or {}).get("final_status") or "").strip() or None,
        }
        for run_id in [str(row.get("run_id") or "").strip() for row in recent_runs]
        if run_id
    ]
    latest_result = result_entries[0] if result_entries else None
    latest_feedback = (_feedback_continuity_entries(feedback_rows, workspace_id) or [None])[0]
    feedback_count = len(_feedback_continuity_entries(feedback_rows, workspace_id))
    onboarding_step = _normalized_onboarding_current_step(onboarding_state)
    library_target = str(routes.get("workspace_circuit_library_page") or routes.get("circuit_library_page") or routes.get("workspace_circuit_library") or routes.get("circuit_library") or "").strip() or None
    result_history_target = str(routes.get("workspace_result_history_page") or routes.get("workspace_result_history") or routes.get("latest_run_result") or "").strip() or None
    feedback_target = str(routes.get("workspace_feedback_page") or routes.get("workspace_feedback") or "").strip() or None
    onboarding_route = str(routes.get("onboarding") or "").strip() or None

    controls: list[dict[str, Any]] = []

    def _append_control(control_id: str, label: str | None, action_target: str | None):
        if not label or not action_target:
            return
        if any(item.get("action_target") == action_target for item in controls):
            return
        controls.append({
            "control_id": control_id,
            "label": label,
            "action_kind": "open_route" if action_target.startswith("/") else "focus_section",
            "action_target": action_target,
        })

    if return_path_kind == "first_success_prerequisite":
        _append_control("return-use-open-onboarding", ui_text("server.shell.open_onboarding", app_language=app_language, fallback_text="Open onboarding"), onboarding_route)
        _append_control("return-use-open-designer", ui_text("server.shell.open_designer", app_language=app_language, fallback_text="Open Designer"), "designer")
    elif return_path_kind in {"result_history_setup", "result_reentry"}:
        _append_control("return-use-open-results", ui_text("server.shell.open_result_history_page", app_language=app_language, fallback_text="Open result history page"), result_history_target)
        _append_control("return-use-open-library", ui_text("builder.action.open_circuit_library", app_language=app_language, fallback_text="Open workflow library"), library_target)
        _append_control("return-use-open-feedback", ui_text("server.shell.open_feedback_page", app_language=app_language, fallback_text="Open feedback page"), feedback_target)
    elif return_path_kind == "feedback_followup":
        _append_control("return-use-open-feedback", ui_text("server.shell.open_feedback_page", app_language=app_language, fallback_text="Open feedback page"), feedback_target)
        _append_control("return-use-open-library", ui_text("builder.action.open_circuit_library", app_language=app_language, fallback_text="Open workflow library"), library_target)
        _append_control("return-use-open-results", ui_text("server.shell.open_result_history_page", app_language=app_language, fallback_text="Open result history page"), result_history_target)
    else:
        _append_control("return-use-open-library", ui_text("builder.action.open_circuit_library", app_language=app_language, fallback_text="Open workflow library"), library_target)
        _append_control("return-use-open-results", ui_text("server.shell.open_result_history_page", app_language=app_language, fallback_text="Open result history page"), result_history_target)
        _append_control("return-use-open-feedback", ui_text("server.shell.open_feedback_page", app_language=app_language, fallback_text="Open feedback page"), feedback_target)

    if selected_result_reentry_context:
        _append_control(
            "return-use-continue-selected-result",
            str(selected_result_reentry_context.get("action_label") or ui_text("server.shell.return_use_selected_action", app_language=app_language, fallback_text="Continue with selected result")),
            str(selected_result_reentry_context.get("workspace_href") or "").strip() or None,
        )
        _append_control(
            "return-use-reopen-selected-result",
            str(selected_result_reentry_context.get("open_result_label") or ui_text("server.shell.return_use_selected_open_result", app_language=app_language, fallback_text="Reopen selected result")),
            str(selected_result_reentry_context.get("result_href") or "").strip() or None,
        )

    path_fallbacks = {
        "first_success_prerequisite": "First-success prerequisite",
        "result_history_setup": "Result history setup",
        "result_reentry": "Result reentry",
        "workflow_reentry": "Workflow reentry",
        "feedback_followup": "Feedback follow-up",
    }
    step_fallbacks = {
        "complete_first_success": "Complete first success",
        "reopen_result": "Reopen a recent result",
        "reopen_workflow": "Reopen a saved workflow",
        "share_feedback": "Capture follow-up feedback",
    }
    path_label = ui_text(
        f"server.shell.return_path.{return_path_kind}",
        app_language=app_language,
        fallback_text=path_fallbacks.get(return_path_kind, return_path_kind.replace("_", " ").title()),
    )
    current_step_label = ui_text(
        f"server.shell.return_step.{current_step_id}",
        app_language=app_language,
        fallback_text=step_fallbacks.get(current_step_id, current_step_id.replace("_", " ").title()),
    )
    next_step_label = ui_text(
        f"server.shell.return_step.{next_step_id}",
        app_language=app_language,
        fallback_text=step_fallbacks.get(next_step_id, next_step_id.replace("_", " ").title()),
    ) if next_step_id else None
    step_order_summary = " → ".join(
        f"{index + 1}. {ui_text(f'server.shell.return_step.{step_id}', app_language=app_language, fallback_text=step_fallbacks.get(step_id, step_id.replace('_', ' ').title()))}"
        for index, step_id in enumerate(step_order)
    )

    lines = _summary_lines(
        ui_text(
            "server.shell.return_use_continuity_state_prefix",
            app_language=app_language,
            fallback_text="Return-use state: {state}",
            state=ui_text(f"shell.product_readiness.stage_state.{return_state}", app_language=app_language, fallback_text=return_state.replace("_", " ")),
        ),
        ui_text("server.shell.return_use_path_prefix", app_language=app_language, fallback_text="Current path: {path}", path=path_label),
        ui_text("server.shell.return_use_current_step_prefix", app_language=app_language, fallback_text="Current step: {step}", step=current_step_label),
        ui_text("server.shell.return_use_next_step_prefix", app_language=app_language, fallback_text="Next after this: {step}", step=next_step_label) if next_step_label else None,
        return_summary or None,
        ui_text("server.shell.return_use_selected_result_prefix", app_language=app_language, fallback_text="Selected result: {run_id}", run_id=str(selected_result_reentry_context.get("run_id") or "")) if selected_result_reentry_context else None,
        ui_text("server.shell.return_use_selected_output_prefix", app_language=app_language, fallback_text="Selected output: {output_ref}", output_ref=str(selected_result_reentry_context.get("output_ref") or "")) if selected_result_reentry_context and selected_result_reentry_context.get("output_ref") else None,
        ui_text("server.shell.return_use_recent_runs_prefix", app_language=app_language, fallback_text="Recent runs: {count}", count=str(len(recent_runs))),
        ui_text("server.shell.return_use_recent_results_prefix", app_language=app_language, fallback_text="Recent results: {count}", count=str(len(result_entries))),
        ui_text("server.shell.return_use_feedback_prefix", app_language=app_language, fallback_text="Feedback items: {count}", count=str(feedback_count)),
    )
    detail_items = _summary_lines(
        ui_text("server.shell.return_use_step_order_prefix", app_language=app_language, fallback_text="Step order: {steps}", steps=step_order_summary),
        ui_text("server.shell.return_use_selected_summary_prefix", app_language=app_language, fallback_text="Selected result summary: {summary}", summary=str(selected_result_reentry_context.get("summary") or "")) if selected_result_reentry_context and selected_result_reentry_context.get("summary") else None,
        ui_text("server.shell.return_use_onboarding_prefix", app_language=app_language, fallback_text="Onboarding step: {step}", step=onboarding_step) if onboarding_step else None,
        ui_text("server.shell.return_use_latest_run_prefix", app_language=app_language, fallback_text="Latest run: {run_id}", run_id=str(recent_runs[0].get("run_id") or "").strip()) if recent_runs else None,
        ui_text("server.shell.return_use_latest_result_prefix", app_language=app_language, fallback_text="Latest result: {state}", state=str(latest_result.get("result_state") or "unknown")) if latest_result else None,
        ui_text("server.shell.return_use_latest_result_summary_prefix", app_language=app_language, fallback_text="Latest result summary: {summary}", summary=str(latest_result.get("summary") or "")) if latest_result and latest_result.get("summary") else None,
        ui_text("server.shell.return_use_latest_feedback_prefix", app_language=app_language, fallback_text="Latest feedback: {category}", category=str(latest_feedback.get("category") or "feedback")) if latest_feedback else None,
    )
    section = build_shell_section(
        headline=ui_text("server.shell.return_use_continuity", app_language=app_language, fallback_text="Return-use continuity"),
        lines=lines,
        detail_title=ui_text("server.shell.return_use_continuity_detail", app_language=app_language, fallback_text="Return-use continuity detail"),
        detail_items=detail_items,
        controls=controls,
        summary_empty=ui_text("server.shell.return_use_continuity_pending", app_language=app_language, fallback_text="Return-use continuity guidance will appear here once first success is established."),
        detail_empty=ui_text("server.shell.return_use_continuity_pending", app_language=app_language, fallback_text="Return-use continuity guidance will appear here once first success is established."),
    )
    section["return_use_state"] = return_state
    section["return_path_kind"] = return_path_kind
    section["current_step_id"] = current_step_id
    section["next_step_id"] = next_step_id
    section["step_order"] = list(step_order)
    section["recommended_action_target"] = return_stage.get("recommended_action_target")
    section["recommended_action_label"] = return_stage.get("recommended_action_label")
    section["blocker_count"] = int(return_stage.get("blocker_count") or 0)
    section["pending_count"] = int(return_stage.get("pending_count") or 0)
    section["selected_result_reentry_context"] = dict(selected_result_reentry_context) if selected_result_reentry_context else None
    return section



def _product_surface_review_section(
    server_product_readiness_review: Mapping[str, Any] | None,
    feedback_rows: Sequence[Mapping[str, Any]],
    workspace_id: str,
    *,
    routes: Mapping[str, Any],
    app_language: str = "en",
) -> dict[str, Any]:
    review = dict(server_product_readiness_review or {})
    review_state = str(review.get("review_state") or "hold_first_success_setup").strip() or "hold_first_success_setup"
    review_summary = str(review.get("summary") or "").strip()
    stages = tuple(review.get("stages") or ())
    next_bottleneck_stage = str(review.get("next_bottleneck_stage") or "").strip() or None
    recommended_action_target = str(review.get("recommended_action_target") or "").strip() or None
    recommended_action_label = str(review.get("recommended_action_label") or "").strip() or None
    stage_by_id = {
        str(stage.get("stage_id") or "").strip(): dict(stage)
        for stage in stages
        if isinstance(stage, Mapping) and str(stage.get("stage_id") or "").strip()
    }
    setup_stage = stage_by_id.get("first_success_setup", {})
    run_stage = stage_by_id.get("first_success_run", {})
    return_stage = stage_by_id.get("return_use", {})
    feedback_entries = _feedback_continuity_entries(feedback_rows, workspace_id)
    feedback_target = str(routes.get("workspace_feedback_page") or routes.get("workspace_feedback") or "").strip() or None
    result_history_target = str(routes.get("workspace_result_history_page") or routes.get("workspace_result_history") or routes.get("latest_run_result") or "").strip() or None
    library_target = str(routes.get("workspace_circuit_library_page") or routes.get("circuit_library_page") or routes.get("workspace_circuit_library") or routes.get("circuit_library") or "").strip() or None

    def _localize_path(path_family: str, path_kind: str | None) -> str | None:
        normalized_kind = str(path_kind or "").strip() or None
        if not normalized_kind:
            return None
        if path_family == "setup":
            fallbacks = {
                "goal_entry": "Goal entry",
                "starter_template": "Starter template",
                "onboarding_continuation": "Onboarding continuation",
            }
            return ui_text(
                f"server.shell.setup_path.{normalized_kind}",
                app_language=app_language,
                fallback_text=fallbacks.get(normalized_kind, normalized_kind.replace("_", " ").title()),
            )
        if path_family == "run":
            fallbacks = {
                "setup_prerequisite": "Setup prerequisite",
                "validation_fix": "Validation fix",
                "review_before_run": "Review before run",
                "launch_run": "Launch run",
                "monitor_run": "Monitor active run",
                "read_result": "Read result",
            }
            return ui_text(
                f"server.shell.run_path.{normalized_kind}",
                app_language=app_language,
                fallback_text=fallbacks.get(normalized_kind, normalized_kind.replace("_", " ").title()),
            )
        if path_family == "return":
            fallbacks = {
                "first_success_prerequisite": "First-success prerequisite",
                "result_history_setup": "Result history setup",
                "result_reentry": "Result reentry",
                "workflow_reentry": "Workflow reentry",
                "feedback_followup": "Feedback follow-up",
            }
            return ui_text(
                f"server.shell.return_path.{normalized_kind}",
                app_language=app_language,
                fallback_text=fallbacks.get(normalized_kind, normalized_kind.replace("_", " ").title()),
            )
        fallbacks = {
            "blocked_help": "Blocked help",
            "run_issue_followup": "Run issue follow-up",
            "feedback_thread_reentry": "Feedback thread reentry",
            "product_learning_followup": "Product learning follow-up",
        }
        return ui_text(
            f"server.shell.feedback_path.{normalized_kind}",
            app_language=app_language,
            fallback_text=fallbacks.get(normalized_kind, normalized_kind.replace("_", " ").title()),
        )

    def _localize_step(path_family: str, step_id: str | None) -> str | None:
        normalized_step = str(step_id or "").strip() or None
        if not normalized_step:
            return None
        if path_family == "setup":
            fallbacks = {
                "choose_entry_path": "Choose entry path",
                "connect_provider": "Connect AI model if needed",
                "review_draft": "Review draft or proposal",
                "run": "Run",
            }
            return ui_text(
                f"server.shell.setup_step.{normalized_step}",
                app_language=app_language,
                fallback_text=fallbacks.get(normalized_step, normalized_step.replace("_", " ").title()),
            )
        if path_family == "run":
            fallbacks = {
                "choose_entry_path": "Choose entry path",
                "connect_provider": "Connect AI model if needed",
                "review_draft": "Review draft or proposal",
                "run": "Run",
                "read_result": "Read result",
            }
            return ui_text(
                f"server.shell.run_step.{normalized_step}",
                app_language=app_language,
                fallback_text=fallbacks.get(normalized_step, normalized_step.replace("_", " ").title()),
            )
        if path_family == "return":
            fallbacks = {
                "complete_first_success": "Complete first success",
                "reopen_result": "Reopen a recent result",
                "reopen_workflow": "Reopen a saved workflow",
                "share_feedback": "Capture follow-up feedback",
            }
            return ui_text(
                f"server.shell.return_step.{normalized_step}",
                app_language=app_language,
                fallback_text=fallbacks.get(normalized_step, normalized_step.replace("_", " ").title()),
            )
        fallbacks = {
            "report_confusion": "Report confusing screen",
            "continue_setup": "Continue first-success setup",
            "report_run_issue": "Report recent run issue",
            "reopen_feedback_thread": "Reopen feedback thread",
            "share_friction_note": "Share a quick friction note",
            "reopen_result": "Reopen a recent result",
        }
        return ui_text(
            f"server.shell.feedback_step.{normalized_step}",
            app_language=app_language,
            fallback_text=fallbacks.get(normalized_step, normalized_step.replace("_", " ").title()),
        )

    def _stage_path_metadata(stage_id: str | None) -> tuple[str, str | None, str | None, str | None, list[str]]:
        if stage_id == "first_success_setup":
            return (
                "setup",
                str(setup_stage.get("entry_path_kind") or "goal_entry").strip() or "goal_entry",
                str(setup_stage.get("current_step_id") or "choose_entry_path").strip() or "choose_entry_path",
                str(setup_stage.get("next_step_id") or "").strip() or None,
                list(setup_stage.get("step_order") or ["choose_entry_path", "connect_provider", "review_draft", "run"]),
            )
        if stage_id == "first_success_run":
            return (
                "run",
                str(run_stage.get("run_path_kind") or "review_before_run").strip() or "review_before_run",
                str(run_stage.get("current_step_id") or "review_draft").strip() or "review_draft",
                str(run_stage.get("next_step_id") or "").strip() or None,
                list(run_stage.get("step_order") or ["review_draft", "run", "read_result"]),
            )
        return (
            "return",
            str(return_stage.get("return_path_kind") or "result_reentry").strip() or "result_reentry",
            str(return_stage.get("current_step_id") or "reopen_result").strip() or "reopen_result",
            str(return_stage.get("next_step_id") or "").strip() or None,
            list(return_stage.get("step_order") or ["complete_first_success", "reopen_result", "reopen_workflow", "share_feedback"]),
        )

    lines = _summary_lines(
        ui_text(
            "server.shell.product_surface_review_state_prefix",
            app_language=app_language,
            fallback_text="Review state: {state}",
            state=ui_text(
                f"shell.product_readiness.state.{review_state}",
                app_language=app_language,
                fallback_text=review_state.replace("_", " "),
            ),
        ),
        review_summary or None,
        ui_text(
            "server.shell.product_surface_review_bottleneck_prefix",
            app_language=app_language,
            fallback_text="Next bottleneck: {stage}",
            stage=(
                ui_text(
                    f"shell.product_readiness.stage.{next_bottleneck_stage}",
                    app_language=app_language,
                    fallback_text=next_bottleneck_stage.replace("_", " "),
                )
                if next_bottleneck_stage
                else ui_text("server.shell.product_surface_review_stable", app_language=app_language, fallback_text="Stable")
            ),
        ),
    )

    detail_items: list[str] = []
    for stage in stages:
        if not isinstance(stage, Mapping):
            continue
        stage_label = str(stage.get("stage_label") or stage.get("stage_id") or ui_text("server.shell.product_surface_review_stage_fallback", app_language=app_language, fallback_text="Stage")).strip()
        stage_state = str(stage.get("stage_state") or "inactive").strip() or "inactive"
        localized_state = ui_text(
            f"shell.product_readiness.stage_state.{stage_state}",
            app_language=app_language,
            fallback_text=stage_state.replace("_", " "),
        )
        blocker_count = int(stage.get("blocker_count") or 0)
        pending_count = int(stage.get("pending_count") or 0)
        summary = str(stage.get("summary") or "").strip()
        detail_items.append(
            ui_text(
                "server.shell.product_surface_review_stage_line",
                app_language=app_language,
                fallback_text="{label}: {state} — blockers {blockers}, pending {pending}",
                label=stage_label,
                state=localized_state,
                blockers=str(blocker_count),
                pending=str(pending_count),
            )
        )
        if summary:
            detail_items.append(
                ui_text(
                    "server.shell.product_surface_review_stage_summary_prefix",
                    app_language=app_language,
                    fallback_text="Summary: {summary}",
                    summary=summary,
                )
            )

    controls: list[dict[str, Any]] = []

    def _append_control(control_id: str, label: str | None, action_target: str | None):
        if not label or not action_target:
            return
        if any(item.get("action_target") == action_target for item in controls):
            return
        controls.append({
            "control_id": control_id,
            "label": label,
            "action_kind": "open_route" if action_target.startswith("/") else "focus_section",
            "action_target": action_target,
        })

    product_path_family: str
    product_path_kind: str | None
    current_step_id: str | None
    next_step_id: str | None
    step_order: list[str]

    if review_state == "product_surface_stable" and feedback_entries and feedback_target:
        product_path_family = "feedback"
        product_path_kind = "feedback_thread_reentry"
        current_step_id = "reopen_feedback_thread"
        next_step_id = "reopen_result" if result_history_target else ("reopen_workflow" if library_target else None)
        step_order = ["reopen_feedback_thread"] + ([next_step_id] if next_step_id else [])
        _append_control(
            "product-surface-open-feedback",
            ui_text("server.shell.open_feedback_page", app_language=app_language, fallback_text="Open feedback page"),
            feedback_target,
        )
        _append_control(
            "product-surface-open-results",
            ui_text("server.shell.open_result_history_page", app_language=app_language, fallback_text="Open result history page"),
            result_history_target,
        )
        _append_control(
            "product-surface-open-library",
            ui_text("builder.action.open_circuit_library", app_language=app_language, fallback_text="Open workflow library"),
            library_target,
        )
    elif review_state == "product_surface_stable":
        product_path_family, product_path_kind, current_step_id, next_step_id, step_order = _stage_path_metadata("return_use")
        if product_path_kind == "workflow_reentry":
            _append_control(
                "product-surface-open-library",
                ui_text("builder.action.open_circuit_library", app_language=app_language, fallback_text="Open workflow library"),
                library_target,
            )
            _append_control(
                "product-surface-open-results",
                ui_text("server.shell.open_result_history_page", app_language=app_language, fallback_text="Open result history page"),
                result_history_target,
            )
        else:
            _append_control(
                "product-surface-open-results",
                ui_text("server.shell.open_result_history_page", app_language=app_language, fallback_text="Open result history page"),
                result_history_target,
            )
            _append_control(
                "product-surface-open-library",
                ui_text("builder.action.open_circuit_library", app_language=app_language, fallback_text="Open workflow library"),
                library_target,
            )
        _append_control(
            "product-surface-open-feedback",
            ui_text("server.shell.open_feedback_page", app_language=app_language, fallback_text="Open feedback page"),
            feedback_target,
        )
    else:
        product_path_family, product_path_kind, current_step_id, next_step_id, step_order = _stage_path_metadata(next_bottleneck_stage)
        _append_control(
            f"product-surface-{next_bottleneck_stage or 'primary'}",
            recommended_action_label,
            recommended_action_target,
        )

    path_label = _localize_path(product_path_family, product_path_kind)
    current_step_label = _localize_step(product_path_family, current_step_id)
    next_step_label = _localize_step(product_path_family, next_step_id) if next_step_id else None
    step_order_summary = " → ".join(
        f"{index + 1}. {_localize_step(product_path_family, step_id) or step_id.replace('_', ' ').title()}"
        for index, step_id in enumerate(step_order)
    ) if step_order else None

    lines = _summary_lines(
        *lines,
        ui_text("server.shell.product_surface_review_path_prefix", app_language=app_language, fallback_text="Current path: {path}", path=path_label) if path_label else None,
        ui_text("server.shell.product_surface_review_current_step_prefix", app_language=app_language, fallback_text="Current step: {step}", step=current_step_label) if current_step_label else None,
        ui_text("server.shell.product_surface_review_next_step_prefix", app_language=app_language, fallback_text="Next after this: {step}", step=next_step_label) if next_step_label else None,
    )
    detail_items = _summary_lines(
        ui_text("server.shell.product_surface_review_step_order_prefix", app_language=app_language, fallback_text="Step order: {steps}", steps=step_order_summary) if step_order_summary else None,
        *detail_items,
    )

    section = build_shell_section(
        headline=ui_text("server.shell.product_surface_review", app_language=app_language, fallback_text="Product surface review"),
        lines=lines,
        detail_title=ui_text("server.shell.product_surface_review_detail", app_language=app_language, fallback_text="Product surface review detail"),
        detail_items=detail_items,
        controls=controls,
        summary_empty=ui_text("server.shell.product_surface_review_pending", app_language=app_language, fallback_text="Product surface review will appear here once the server shell is available."),
        detail_empty=ui_text("server.shell.product_surface_review_pending", app_language=app_language, fallback_text="Product surface review will appear here once the server shell is available."),
    )
    section["review_state"] = review_state
    section["next_bottleneck_stage"] = next_bottleneck_stage
    section["recommended_action_target"] = recommended_action_target
    section["recommended_action_label"] = recommended_action_label
    section["product_path_family"] = product_path_family
    section["product_path_kind"] = product_path_kind
    section["current_step_id"] = current_step_id
    section["next_step_id"] = next_step_id
    section["step_order"] = step_order
    return section


def _feedback_continuity_entries(
    feedback_rows: Sequence[Mapping[str, Any]],
    workspace_id: str,
) -> list[dict[str, Any]]:
    normalized_workspace_id = str(workspace_id or "").strip()
    if not normalized_workspace_id:
        return []
    entries: list[dict[str, Any]] = []
    for row in feedback_rows:
        if str(row.get("workspace_id") or "").strip() != normalized_workspace_id:
            continue
        feedback_id = str(row.get("feedback_id") or "").strip() or None
        category = str(row.get("category") or "unknown").strip() or "unknown"
        surface = str(row.get("surface") or "unknown").strip() or "unknown"
        status = str(row.get("status") or "received").strip() or "received"
        created_at = str(row.get("created_at") or "").strip() or None
        message = str(row.get("message") or "").strip() or None
        entries.append({
            "feedback_id": feedback_id,
            "category": category,
            "surface": surface,
            "status": status,
            "created_at": created_at,
            "message": message,
        })
    entries.sort(key=lambda item: (str(item.get("created_at") or ""), str(item.get("feedback_id") or "")), reverse=True)
    return entries[:5]


def _feedback_continuity_section(
    server_product_readiness_review: Mapping[str, Any] | None,
    feedback_rows: Sequence[Mapping[str, Any]],
    workspace_id: str,
    *,
    recent_run_rows: Sequence[Mapping[str, Any]],
    onboarding_state: Mapping[str, Any] | None,
    routes: Mapping[str, Any],
    app_language: str = "en",
) -> dict[str, Any]:
    entries = _feedback_continuity_entries(feedback_rows, workspace_id)
    latest = entries[0] if entries else None
    recent_runs = list(_recent_run_rows_for_workspace(recent_run_rows, workspace_id, limit=5))
    latest_run = recent_runs[0] if recent_runs else None
    latest_run_status_family = str((latest_run or {}).get("status_family") or (latest_run or {}).get("status") or "").strip() or None
    onboarding_step = _normalized_onboarding_current_step(onboarding_state)
    review = dict(server_product_readiness_review or {})
    stages = tuple(review.get("stages") or ())
    setup_stage = dict(stages[0]) if len(stages) > 0 and isinstance(stages[0], Mapping) else {}
    run_stage = dict(stages[1]) if len(stages) > 1 and isinstance(stages[1], Mapping) else {}
    return_stage = dict(stages[2]) if len(stages) > 2 and isinstance(stages[2], Mapping) else {}
    first_success_established = bool((onboarding_state or {}).get("first_success_achieved"))

    feedback_api_target = str(routes.get("workspace_feedback") or f"/api/workspaces/{workspace_id}/feedback").strip() or None
    feedback_page_target = str(routes.get("workspace_feedback_page") or f"/app/workspaces/{workspace_id}/feedback").strip() or None
    onboarding_target = str(routes.get("onboarding") or "").strip() or None
    result_history_target = str(routes.get("workspace_result_history_page") or routes.get("workspace_result_history") or routes.get("latest_run_result") or "").strip() or None
    designer_target = "designer"
    setup_continue_target = str(setup_stage.get("recommended_action_target") or "").strip() or onboarding_target or designer_target
    setup_continue_label = str(setup_stage.get("recommended_action_label") or "").strip() or ui_text("server.shell.open_onboarding", app_language=app_language, fallback_text="Open onboarding")

    controls: list[dict[str, Any]] = []

    def _append_control(control_id: str, label: str | None, action_target: str | None):
        if not label or not action_target:
            return
        if any(item.get("action_target") == action_target for item in controls):
            return
        controls.append({
            "control_id": control_id,
            "label": label,
            "action_kind": "open_route" if action_target.startswith("/") else "focus_section",
            "action_target": action_target,
        })

    if entries:
        feedback_state = "feedback_thread_reentry"
        feedback_path_kind = "feedback_thread_reentry"
        current_step_id = "reopen_feedback_thread"
        next_step_id = "reopen_result" if result_history_target else None
        feedback_summary = ui_text(
            "server.shell.feedback_summary.feedback_thread_reentry",
            app_language=app_language,
            fallback_text="A feedback thread already exists. Reopen it first so follow-up context stays attached to the original report.",
        )
        _append_control("feedback-open-page", ui_text("server.shell.open_feedback_page", app_language=app_language, fallback_text="Open feedback page"), feedback_page_target)
        _append_control("feedback-open-api", ui_text("server.shell.open_feedback", app_language=app_language, fallback_text="Open feedback"), feedback_api_target)
        _append_control("feedback-open-results", ui_text("server.shell.open_result_history_page", app_language=app_language, fallback_text="Open result history page"), result_history_target)
    elif not first_success_established:
        feedback_state = "blocked_help"
        feedback_path_kind = "blocked_help"
        current_step_id = "report_confusion"
        next_step_id = "continue_setup"
        feedback_summary = ui_text(
            "server.shell.feedback_summary.blocked_help",
            app_language=app_language,
            fallback_text="Use the feedback path to report confusing or blocked first-success screens while you continue setup.",
        )
        _append_control("feedback-open-page", ui_text("server.shell.open_feedback_page", app_language=app_language, fallback_text="Open feedback page"), feedback_page_target)
        _append_control("feedback-open-api", ui_text("server.shell.open_feedback", app_language=app_language, fallback_text="Open feedback"), feedback_api_target)
        _append_control("feedback-continue-setup", setup_continue_label, setup_continue_target)
    elif latest_run_status_family == "terminal_failure" and not entries:
        feedback_state = "run_issue_followup"
        feedback_path_kind = "run_issue_followup"
        current_step_id = "report_run_issue"
        next_step_id = "reopen_result"
        feedback_summary = ui_text(
            "server.shell.feedback_summary.run_issue_followup",
            app_language=app_language,
            fallback_text="A recent run failed after first success. Capture the issue so the product path does not lose the failure context.",
        )
        _append_control("feedback-open-page", ui_text("server.shell.open_feedback_page", app_language=app_language, fallback_text="Open feedback page"), feedback_page_target)
        _append_control("feedback-open-api", ui_text("server.shell.open_feedback", app_language=app_language, fallback_text="Open feedback"), feedback_api_target)
        _append_control("feedback-open-results", ui_text("server.shell.open_result_history_page", app_language=app_language, fallback_text="Open result history page"), result_history_target)
    else:
        feedback_state = "product_learning_followup"
        feedback_path_kind = "product_learning_followup"
        current_step_id = "share_friction_note"
        next_step_id = "reopen_result" if result_history_target else None
        feedback_summary = ui_text(
            "server.shell.feedback_summary.product_learning_followup",
            app_language=app_language,
            fallback_text="Leave a quick friction note so the next return-use pass keeps the product-learning signal from this session.",
        )
        _append_control("feedback-open-page", ui_text("server.shell.open_feedback_page", app_language=app_language, fallback_text="Open feedback page"), feedback_page_target)
        _append_control("feedback-open-api", ui_text("server.shell.open_feedback", app_language=app_language, fallback_text="Open feedback"), feedback_api_target)
        _append_control("feedback-open-results", ui_text("server.shell.open_result_history_page", app_language=app_language, fallback_text="Open result history page"), result_history_target)

    path_fallbacks = {
        "blocked_help": "Blocked help",
        "run_issue_followup": "Run issue follow-up",
        "feedback_thread_reentry": "Feedback thread reentry",
        "product_learning_followup": "Product learning follow-up",
    }
    step_fallbacks = {
        "report_confusion": "Report confusing screen",
        "continue_setup": "Continue first-success setup",
        "report_run_issue": "Report recent run issue",
        "reopen_feedback_thread": "Reopen feedback thread",
        "share_friction_note": "Share a quick friction note",
        "reopen_result": "Reopen a recent result",
    }
    path_label = ui_text(
        f"server.shell.feedback_path.{feedback_path_kind}",
        app_language=app_language,
        fallback_text=path_fallbacks.get(feedback_path_kind, feedback_path_kind.replace("_", " ").title()),
    )
    current_step_label = ui_text(
        f"server.shell.feedback_step.{current_step_id}",
        app_language=app_language,
        fallback_text=step_fallbacks.get(current_step_id, current_step_id.replace("_", " ").title()),
    )
    next_step_label = ui_text(
        f"server.shell.feedback_step.{next_step_id}",
        app_language=app_language,
        fallback_text=step_fallbacks.get(next_step_id, next_step_id.replace("_", " ").title()),
    ) if next_step_id else None
    step_order = [current_step_id] + ([next_step_id] if next_step_id else [])
    step_order_summary = " → ".join(
        f"{index + 1}. {ui_text(f'server.shell.feedback_step.{step_id}', app_language=app_language, fallback_text=step_fallbacks.get(step_id, step_id.replace('_', ' ').title()))}"
        for index, step_id in enumerate(step_order)
    )

    section = build_shell_section(
        headline=ui_text("server.shell.feedback_continuity", app_language=app_language, fallback_text="Feedback continuity"),
        lines=_summary_lines(
            ui_text("server.shell.feedback_state_prefix", app_language=app_language, fallback_text="Feedback state: {state}", state=ui_text(f"server.shell.feedback_state.{feedback_state}", app_language=app_language, fallback_text=feedback_state.replace("_", " "))),
            ui_text("server.shell.feedback_path_prefix", app_language=app_language, fallback_text="Current path: {path}", path=path_label),
            ui_text("server.shell.feedback_current_step_prefix", app_language=app_language, fallback_text="Current step: {step}", step=current_step_label),
            ui_text("server.shell.feedback_next_step_prefix", app_language=app_language, fallback_text="Next after this: {step}", step=next_step_label) if next_step_label else None,
            feedback_summary,
            ui_text("server.shell.feedback_items_count_prefix", app_language=app_language, fallback_text="Feedback items: {count}", count=str(len(entries))),
            ui_text("server.shell.feedback_onboarding_prefix", app_language=app_language, fallback_text="Onboarding step: {step}", step=onboarding_step) if onboarding_step else None,
            ui_text("server.shell.feedback_latest_run_prefix", app_language=app_language, fallback_text="Latest run state: {state}", state=latest_run_status_family) if latest_run_status_family else None,
        ),
        detail_title=ui_text("server.shell.feedback_continuity_detail", app_language=app_language, fallback_text="Feedback continuity detail"),
        detail_items=_summary_lines(
            ui_text("server.shell.feedback_step_order_prefix", app_language=app_language, fallback_text="Step order: {steps}", steps=step_order_summary),
            ui_text("server.shell.latest_feedback_prefix", app_language=app_language, fallback_text="Latest feedback: {feedback}", feedback=f"{latest['category']} — {latest['feedback_id'] or 'feedback'}") if latest else None,
            *[
                f"{index + 1}. {entry['category']} — {entry['surface']} — {entry['status']}" + (f" — {entry['feedback_id']}" if entry.get('feedback_id') else "")
                for index, entry in enumerate(entries[:3])
            ],
        ),
        detail_empty=ui_text("server.shell.feedback_continuity_pending", app_language=app_language, fallback_text="Feedback continuity will appear here after product notes are sent."),
        controls=controls,
        history=entries[:3],
    )
    section["feedback_state"] = feedback_state
    section["feedback_path_kind"] = feedback_path_kind
    section["current_step_id"] = current_step_id
    section["next_step_id"] = next_step_id
    section["step_order"] = step_order
    return section

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
    provider_binding_rows: Sequence[Mapping[str, Any]],
    managed_secret_rows: Sequence[Mapping[str, Any]],
    provider_probe_rows: Sequence[Mapping[str, Any]],
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
    binding_entries = [
        row for row in provider_binding_rows
        if str(row.get("workspace_id") or "").strip() == str(workspace_id or "").strip()
        and str(row.get("updated_at") or row.get("created_at") or "").strip()
    ]
    secret_entries = [
        row for row in managed_secret_rows
        if str(row.get("workspace_id") or "").strip() == str(workspace_id or "").strip()
        and str(row.get("last_rotated_at") or "").strip()
    ]
    probe_entries = [
        row for row in provider_probe_rows
        if str(row.get("workspace_id") or "").strip() == str(workspace_id or "").strip()
        and str(row.get("occurred_at") or "").strip()
    ]
    failed_probe_count = sum(1 for row in probe_entries if str(row.get("probe_status") or "").strip().lower() not in {"reachable", "warning"})
    latest_values = [
        str(row.get("updated_at") or row.get("created_at") or "").strip()
        for row in run_entries
    ] + [
        str(row.get("updated_at") or row.get("created_at") or "").strip()
        for row in onboarding_entries
    ] + [
        str(entry.get("updated_at") or "").strip()
        for entry in share_entries
    ] + [
        str(row.get("updated_at") or row.get("created_at") or "").strip()
        for row in binding_entries
    ] + [
        str(row.get("last_rotated_at") or "").strip()
        for row in secret_entries
    ] + [
        str(row.get("occurred_at") or "").strip()
        for row in probe_entries
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
            "Provider binding updates: " + str(len(binding_entries)),
            "Managed secret updates: " + str(len(secret_entries)),
            "Provider probe checks: " + str(len(probe_entries)),
            "Failed provider probes: " + str(failed_probe_count),
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
            {
                "control_id": "history-summary-open-library-page",
                "label": ui_text("server.shell.open_workflow_library", app_language=app_language, fallback_text="Open workflow library"),
                "action_kind": "open_route",
                "action_target": f"/app/workspaces/{workspace_id}/library?app_language={app_language}",
            },
            {
                "control_id": "history-summary-open-results-page",
                "label": ui_text("server.shell.open_result_history_page", app_language=app_language, fallback_text="Open result history page"),
                "action_kind": "open_route",
                "action_target": f"/app/workspaces/{workspace_id}/results?app_language={app_language}",
            },
        ],
        history=[{
            "total_runs": len(run_entries),
            "successful_runs": success_runs,
            "failed_runs": failure_runs,
            "onboarding_updates": len(onboarding_entries),
            "share_history_entries": len(share_entries),
            "provider_binding_updates": len(binding_entries),
            "managed_secret_updates": len(secret_entries),
            "provider_probe_checks": len(probe_entries),
            "failed_provider_probes": failed_probe_count,
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
            "label": ui_text("server.shell.open_starter_templates", app_language=app_language, fallback_text="Open starter templates"),
            "action_kind": "focus_auxiliary",
            "action_target": "templates",
        },
        {
            "control_id": "designer-open-template-catalog-page",
            "label": ui_text("server.shell.open_starter_template_catalog_page", app_language=app_language, fallback_text="Browse starter template page"),
            "action_kind": "open_route",
            "action_target": f"/app/templates/starter-circuits?app_language={app_language}",
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
    }, {
        "control_id": "share-history-open-page",
        "label": ui_text("server.shell.open_share_history_page", app_language=app_language, fallback_text="Open share history page"),
        "action_kind": "open_route",
        "action_target": f"/app/workspaces/{workspace_id}/shares?app_language={app_language}",
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




def _server_product_stage(*, stage_id: str, stage_label: str, stage_state: str, blocker_count: int, pending_count: int, summary: str | None, recommended_action_id: str | None, recommended_action_label: str | None, recommended_action_target: str | None, app_language: str) -> dict[str, Any]:
    return {
        "stage_id": stage_id,
        "stage_label": stage_label,
        "stage_state": stage_state,
        "stage_state_label": ui_text(
            f"shell.product_readiness.stage_state.{stage_state}",
            app_language=app_language,
            fallback_text=stage_state.replace("_", " "),
        ),
        "blocker_count": blocker_count,
        "pending_count": pending_count,
        "summary": summary,
        "recommended_action_id": recommended_action_id,
        "recommended_action_label": recommended_action_label,
        "recommended_action_target": recommended_action_target,
    }


def _server_product_readiness_review(
    shell_map: Mapping[str, Any],
    *,
    artifact_model: WorkingSaveModel | CommitSnapshotModel | ExecutionRecordModel | None,
    onboarding_state: Mapping[str, Any] | None,
    latest_run_row: Mapping[str, Any] | None,
    latest_run_status_preview: Mapping[str, Any] | None,
    latest_run_result_preview: Mapping[str, Any] | None,
    provider_binding_rows: Sequence[Mapping[str, Any]],
    managed_secret_rows: Sequence[Mapping[str, Any]],
    provider_probe_rows: Sequence[Mapping[str, Any]],
    feedback_rows: Sequence[Mapping[str, Any]],
    workspace_id: str,
    routes: Mapping[str, Any],
    app_language: str,
    persisted_designer_state: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    product_readiness = shell_map.get("product_readiness") or {}
    local_stages = list(product_readiness.get("stages") or [])
    local_setup_state = str((local_stages[0].get("stage_state") if len(local_stages) > 0 and isinstance(local_stages[0], Mapping) else "") or "").strip()
    local_run_state = str((local_stages[1].get("stage_state") if len(local_stages) > 1 and isinstance(local_stages[1], Mapping) else "") or "").strip()

    onboarding_step = _normalized_onboarding_current_step(onboarding_state)
    persisted_designer = dict(persisted_designer_state or {})
    persisted_request_text = str(
        persisted_designer.get("request_text")
        or (((shell_map.get("designer") or {}).get("request_state") or {}).get("current_request_text") or "")
    ).strip()
    selected_template_id = str(persisted_designer.get("selected_template_id") or "").strip()
    selected_template_ref = str(persisted_designer.get("selected_template_ref") or "").strip()
    selected_template_display_name = str(persisted_designer.get("selected_template_display_name") or selected_template_id or "").strip()
    has_selected_template = bool(selected_template_id or selected_template_ref or selected_template_display_name)
    entry_path_kind = "goal_entry"
    if onboarding_step in {"review_preview", "approve"}:
        entry_path_kind = "onboarding_continuation"
    elif has_selected_template:
        entry_path_kind = "starter_template"
    first_success = bool((onboarding_state or {}).get("first_success_achieved"))
    provider_setup_readiness = evaluate_required_provider_setup(
        workspace_id=workspace_id,
        source_payload=artifact_model,
        provider_binding_rows=provider_binding_rows,
        managed_secret_rows=managed_secret_rows,
        provider_probe_rows=provider_probe_rows,
    )
    has_server_provider = any(
        str(row.get("workspace_id") or "").strip() == workspace_id and bool(row.get("enabled", True))
        for row in provider_binding_rows
    ) or any(str(row.get("workspace_id") or "").strip() == workspace_id for row in managed_secret_rows)
    provider_setup_missing = (
        provider_setup_readiness.requires_provider_setup
        if provider_setup_readiness.required_provider_keys
        else (not has_server_provider)
    )
    provider_step_needed = provider_setup_missing and bool(
        has_selected_template
        or persisted_request_text
        or onboarding_step in {"review_preview", "approve", "run", "read_result"}
        or local_setup_state == "provider_setup_needed"
        or bool(provider_setup_readiness.required_provider_keys)
    )
    has_history = latest_run_row is not None
    has_feedback_route = bool(routes.get("workspace_feedback") and routes.get("workspace_feedback_page"))
    has_library_route = bool(routes.get("circuit_library_page") or routes.get("workspace_circuit_library_page"))
    has_result_history_route = bool(routes.get("workspace_result_history_page"))
    current_status = str((latest_run_status_preview or {}).get("execution_state") or (latest_run_row or {}).get("status") or "").strip()
    run_active = current_status in {"queued", "running", "paused", "claimed", "pending", "in_progress"}
    result_ready = str((latest_run_result_preview or {}).get("result_state") or "").strip() in {"ready_success", "ready_partial"}
    result_reading_path_complete = bool(result_ready and has_history and has_result_history_route)
    validation_status = str(((shell_map.get("validation") or {}).get("overall_status") or "")).strip()
    graph_nodes = tuple(((shell_map.get("graph") or {}).get("nodes") or ()))
    has_existing_structure = bool(graph_nodes) or str(shell_map.get("storage_role") or "").strip() in {"commit_snapshot", "execution_record"}

    if first_success or result_reading_path_complete:
        setup_state = "complete"
        setup_blockers = 0
        setup_pending = 0
        setup_summary = ui_text(
            "shell.product_readiness.summary.entry_complete",
            app_language=app_language,
            fallback_text="The beginner entry path is already crossed. Reuse the existing workflow surfaces instead of reopening first-step setup.",
        )
        setup_action_id = None
        setup_action_label = None
        setup_action_target = None
        current_step_id = "run"
        next_step_id = None
    elif onboarding_step in {"review_preview", "approve"}:
        setup_state = "onboarding_continuation"
        setup_blockers = 0
        setup_pending = 1
        setup_summary = ui_text(
            "shell.product_readiness.summary.onboarding_continuation",
            app_language=app_language,
            fallback_text="Resume the guided first-run path from review and approval before switching to a different entry surface.",
        )
        setup_action_id = "open_validation_detail"
        setup_action_label = ui_text("server.shell.review_preview_action", app_language=app_language, fallback_text="Review preview")
        setup_action_target = "validation.detail"
        current_step_id = "review_draft"
        next_step_id = "run"
    elif (not has_existing_structure) and (
        has_selected_template
        and not provider_step_needed
    ):
        setup_state = "starter_template_path"
        setup_blockers = 0
        setup_pending = 1
        setup_summary = ui_text(
            "shell.product_readiness.summary.starter_template_path",
            app_language=app_language,
            fallback_text="A starter template path is already selected. Continue there so the first workflow shape materializes cleanly.",
        )
        setup_action_id = "open_starter_templates"
        setup_action_label = ui_text("server.shell.open_starter_templates", app_language=app_language, fallback_text="Open starter templates")
        setup_action_target = str(routes.get("starter_template_catalog_page") or routes.get("starter_template_catalog") or "") or None
        current_step_id = "choose_entry_path"
        next_step_id = "review_draft"
    elif (not has_existing_structure) and not persisted_request_text and not has_selected_template and (local_setup_state == "goal_entry_needed" or onboarding_step == "enter_goal" or str((((shell_map.get("designer") or {}).get("request_state") or {}).get("request_status") or "")).strip() == "empty"):
        setup_state = "goal_entry_needed"
        setup_blockers = 0
        setup_pending = 1
        setup_summary = ui_text(
            "shell.product_readiness.summary.goal_entry_needed",
            app_language=app_language,
            fallback_text="Start from a goal, starter template, file, or web address so the first workflow shape exists.",
        )
        setup_action_id = "open_designer"
        setup_action_label = ui_text("server.shell.open_designer", app_language=app_language, fallback_text="Open Designer")
        setup_action_target = "designer"
        current_step_id = "choose_entry_path"
        next_step_id = "connect_provider" if not has_server_provider else "review_draft"
    elif provider_step_needed:
        setup_state = "provider_setup_needed"
        setup_blockers = 1
        setup_pending = 0
        provider_finding = provider_setup_readiness.primary_finding
        setup_summary = (
            provider_finding.message
            if provider_finding is not None
            else ui_text(
                "shell.product_readiness.summary.provider_setup_needed",
                app_language=app_language,
                fallback_text="Connect an AI model before the first workflow can run successfully.",
            )
        )
        setup_action_id = "open_provider_bindings"
        setup_action_label = ui_text("server.shell.open_provider_bindings", app_language=app_language, fallback_text="Open provider bindings")
        setup_action_target = str(routes.get("workspace_provider_bindings") or "") or None
        current_step_id = "connect_provider"
        next_step_id = "review_draft"
    else:
        setup_state = "entry_ready" if local_setup_state in {"", "provider_setup_needed", "entry_ready", "ready", "starter_template_path", "onboarding_continuation"} else local_setup_state
        setup_blockers = 0
        setup_pending = 0 if setup_state == "complete" else 1
        setup_summary = ui_text(
            "shell.product_readiness.summary.entry_ready",
            app_language=app_language,
            fallback_text="Starter entry surfaces are available. You can continue from a template, file, URL, or direct goal entry.",
        )
        setup_action_id = "open_starter_templates" if has_selected_template else "open_designer"
        setup_action_label = ui_text(
            "server.shell.open_starter_templates" if has_selected_template else "server.shell.open_designer",
            app_language=app_language,
            fallback_text=("Open starter templates" if has_selected_template else "Open Designer"),
        )
        setup_action_target = (str(routes.get("starter_template_catalog_page") or routes.get("starter_template_catalog") or "") if has_selected_template else "designer") or None
        current_step_id = "review_draft"
        next_step_id = "run"

    setup_stage = _server_product_stage(
        stage_id="first_success_setup",
        stage_label=ui_text("shell.product_readiness.stage.first_success_setup", app_language=app_language, fallback_text="First success setup"),
        stage_state=setup_state,
        blocker_count=setup_blockers,
        pending_count=setup_pending,
        summary=setup_summary,
        recommended_action_id=setup_action_id,
        recommended_action_label=setup_action_label,
        recommended_action_target=setup_action_target,
        app_language=app_language,
    )
    setup_stage["entry_path_kind"] = entry_path_kind
    setup_stage["current_step_id"] = current_step_id
    setup_stage["next_step_id"] = next_step_id
    setup_stage["provider_step_needed"] = provider_step_needed
    setup_stage["required_provider_keys"] = list(provider_setup_readiness.required_provider_keys)
    setup_stage["provider_ready"] = not provider_setup_readiness.requires_provider_setup
    if provider_setup_readiness.primary_finding is not None:
        setup_stage["provider_setup_reason_code"] = provider_setup_readiness.primary_finding.reason_code
    setup_stage["selected_template_display_name"] = selected_template_display_name or None
    setup_stage["step_order"] = ["choose_entry_path", "connect_provider", "review_draft", "run"]
    if result_ready and not first_success:
        setup_stage["current_step_id"] = "run"
        setup_stage["next_step_id"] = "read_result"


    if result_ready:
        run_state = "complete"
        run_blockers = 0
        run_pending = 0
        run_summary = ui_text(
            "shell.product_readiness.summary.result_ready",
            app_language=app_language,
            fallback_text="A readable result is already available for the first-success path.",
        )
        run_action_id = "open_result_history"
        run_action_label = ui_text("server.shell.open_result_history_page", app_language=app_language, fallback_text="Open result history page")
        run_action_target = str(routes.get("workspace_result_history_page") or routes.get("latest_run_result") or "") or None
    elif run_active:
        run_state = "run_in_progress"
        run_blockers = 1
        run_pending = 0
        run_summary = ui_text(
            "shell.product_readiness.summary.run_in_progress",
            app_language=app_language,
            fallback_text="A run is still active. Keep monitoring it before treating the first-success path as settled.",
        )
        run_action_id = "open_runtime_status"
        run_action_label = ui_text("server.shell.open_run_status", app_language=app_language, fallback_text="Open run status")
        run_action_target = str(routes.get("latest_run_status") or "") or None
    elif validation_status == "blocked" or local_run_state == "fix_before_run" or onboarding_step in {"review_preview", "approve"}:
        run_state = "fix_before_run"
        run_blockers = 1
        run_pending = 0
        run_summary = ui_text(
            "shell.product_readiness.summary.fix_before_run",
            app_language=app_language,
            fallback_text="Fix the blocking issue before the first run can continue.",
        )
        run_action_id = "open_validation_detail"
        run_action_label = ui_text("server.shell.open_validation_detail", app_language=app_language, fallback_text="Open Validation detail")
        run_action_target = "validation.detail"
    elif setup_state in {"goal_entry_needed", "provider_setup_needed"}:
        run_state = "waiting"
        run_blockers = 0
        run_pending = 1
        run_summary = ui_text(
            "shell.product_readiness.summary.run_waiting",
            app_language=app_language,
            fallback_text="The run path is not active yet. Keep moving through review and approval until the run action becomes available.",
        )
        run_action_id = None
        run_action_label = None
        run_action_target = None
    elif has_server_provider and has_existing_structure and bool(str(routes.get("workspace_shell_launch") or routes.get("launch_run") or "").strip()):
        run_state = "ready_to_run"
        run_blockers = 0
        run_pending = 1
        run_summary = ui_text(
            "shell.product_readiness.summary.ready_to_run",
            app_language=app_language,
            fallback_text="The workflow is ready enough to run. Review the expected usage, then launch it and read the result.",
        )
        run_action_id = "launch_run"
        run_action_label = ui_text("server.shell.launch_run", app_language=app_language, fallback_text="Launch run")
        run_action_target = str(routes.get("workspace_shell_launch") or routes.get("launch_run") or "") or None
    else:
        run_state = local_run_state or "inactive"
        run_blockers = 0
        run_pending = 1 if not first_success else 0
        run_summary = ui_text(
            "shell.product_readiness.summary.run_waiting",
            app_language=app_language,
            fallback_text="The run path is not active yet. Keep moving through review and approval until the run action becomes available.",
        )
        run_action_id = None
        run_action_label = None
        run_action_target = None

    run_stage = _server_product_stage(
        stage_id="first_success_run",
        stage_label=ui_text("shell.product_readiness.stage.first_success_run", app_language=app_language, fallback_text="First success run"),
        stage_state=run_state,
        blocker_count=run_blockers,
        pending_count=run_pending,
        summary=run_summary,
        recommended_action_id=run_action_id,
        recommended_action_label=run_action_label,
        recommended_action_target=run_action_target,
        app_language=app_language,
    )
    if run_state in {"waiting", "inactive"}:
        run_path_kind = "setup_prerequisite"
        run_current_step_id = current_step_id if current_step_id in {"choose_entry_path", "connect_provider", "review_draft", "run"} else ("review_draft" if setup_state in {"entry_ready", "ready", "starter_template_path", "onboarding_continuation"} else "choose_entry_path")
        run_next_step_id = "run" if run_current_step_id == "review_draft" else "review_draft"
    elif run_state == "fix_before_run":
        run_path_kind = "review_before_run" if onboarding_step in {"review_preview", "approve"} else "validation_fix"
        run_current_step_id = "review_draft"
        run_next_step_id = "run"
    elif run_state == "ready_to_run":
        run_path_kind = "launch_run"
        run_current_step_id = "run"
        run_next_step_id = "read_result"
    elif run_state == "run_in_progress":
        run_path_kind = "monitor_run"
        run_current_step_id = "run"
        run_next_step_id = "read_result"
    else:
        run_path_kind = "read_result"
        run_current_step_id = "read_result"
        run_next_step_id = None
    run_stage["run_path_kind"] = run_path_kind
    run_stage["current_step_id"] = run_current_step_id
    run_stage["next_step_id"] = run_next_step_id
    run_stage["step_order"] = ["review_draft", "run", "read_result"]

    library_target = str(routes.get("workspace_circuit_library_page") or routes.get("circuit_library_page") or routes.get("workspace_circuit_library") or routes.get("circuit_library") or "").strip() or None
    result_history_target = str(routes.get("workspace_result_history_page") or routes.get("workspace_result_history") or routes.get("latest_run_result") or "").strip() or None
    feedback_target = str(routes.get("workspace_feedback_page") or routes.get("workspace_feedback") or "").strip() or None

    if (not first_success) and not result_reading_path_complete:
        return_state = "inactive"
        return_blockers = 0
        return_pending = 0
        return_summary = ui_text(
            "shell.product_readiness.summary.return_use_inactive",
            app_language=app_language,
            fallback_text="Return-use surfaces unlock after the first successful run and result reading path are established.",
        )
        return_action_id = None
        return_action_label = None
        return_action_target = None
        return_path_kind = "first_success_prerequisite"
        return_current_step_id = "complete_first_success"
        return_next_step_id = "reopen_result"
    elif not has_history or not has_result_history_route:
        return_state = "history_needed"
        return_blockers = 1
        return_pending = 0
        return_summary = ui_text(
            "shell.product_readiness.summary.history_needed",
            app_language=app_language,
            fallback_text="The return-use path still needs readable result history so people can reopen what happened last time without entering deep trace tooling.",
        )
        return_action_id = "open_result_history"
        return_action_label = ui_text("server.shell.open_result_history_page", app_language=app_language, fallback_text="Open result history page")
        return_action_target = result_history_target
        return_path_kind = "result_history_setup"
        return_current_step_id = "reopen_result"
        return_next_step_id = "reopen_workflow"
    elif latest_run_row is not None:
        return_state = "complete" if has_library_route and has_feedback_route else "return_use_ready"
        return_blockers = 0
        return_pending = 0 if return_state == "complete" else 1
        return_summary = ui_text(
            "shell.product_readiness.summary.return_use_ready",
            app_language=app_language,
            fallback_text="Library, recent results, and feedback routes are all available for return visits.",
        )
        return_action_id = "open_result_history"
        return_action_label = ui_text("server.shell.open_result_history_page", app_language=app_language, fallback_text="Open result history page")
        return_action_target = result_history_target
        return_path_kind = "result_reentry"
        return_current_step_id = "reopen_result"
        return_next_step_id = "reopen_workflow"
    else:
        return_state = "complete" if has_library_route and has_feedback_route else "return_use_ready"
        return_blockers = 0
        return_pending = 0 if return_state == "complete" else 1
        return_summary = ui_text(
            "shell.product_readiness.summary.return_use_ready",
            app_language=app_language,
            fallback_text="Library, recent results, and feedback routes are all available for return visits.",
        )
        return_action_id = "open_circuit_library" if library_target else "open_feedback"
        return_action_label = ui_text(
            "builder.action.open_circuit_library" if library_target else "server.shell.open_feedback_page",
            app_language=app_language,
            fallback_text=("Open workflow library" if library_target else "Open feedback page"),
        )
        return_action_target = library_target or feedback_target
        return_path_kind = "workflow_reentry" if library_target else "feedback_followup"
        return_current_step_id = "reopen_workflow" if library_target else "share_feedback"
        return_next_step_id = "share_feedback" if library_target and feedback_target else None

    return_stage = _server_product_stage(
        stage_id="return_use",
        stage_label=ui_text("shell.product_readiness.stage.return_use", app_language=app_language, fallback_text="Return use"),
        stage_state=return_state,
        blocker_count=return_blockers,
        pending_count=return_pending,
        summary=return_summary,
        recommended_action_id=return_action_id,
        recommended_action_label=return_action_label,
        recommended_action_target=return_action_target,
        app_language=app_language,
    )
    return_stage["return_path_kind"] = return_path_kind
    return_stage["current_step_id"] = return_current_step_id
    return_stage["next_step_id"] = return_next_step_id
    return_stage["step_order"] = ["complete_first_success", "reopen_result", "reopen_workflow", "share_feedback"]

    stages = [setup_stage, run_stage, return_stage]
    if (setup_stage["blocker_count"] or setup_stage["stage_state"] in {"goal_entry_needed", "provider_setup_needed"}) and not has_history:
        review_state = "hold_first_success_setup"
        bottleneck_stage = setup_stage
        summary = ui_text(
            "shell.product_readiness.summary.hold_first_success_setup",
            app_language=app_language,
            fallback_text="The next real product bottleneck is still inside the first-success setup path. Finish goal entry or provider setup before widening scope.",
        )
    elif ((not first_success) and not result_reading_path_complete) or run_stage["blocker_count"] or run_stage["stage_state"] in {"fix_before_run", "ready_to_run", "run_in_progress", "waiting"}:
        review_state = "hold_first_success_run"
        bottleneck_stage = run_stage
        summary = ui_text(
            "shell.product_readiness.summary.hold_first_success_run",
            app_language=app_language,
            fallback_text="The next real product bottleneck is still inside the first-success run path. Finish review, run, and readable result follow-through before widening scope.",
        )
    elif return_stage["blocker_count"]:
        review_state = "hold_return_use"
        bottleneck_stage = return_stage
        summary = ui_text(
            "shell.product_readiness.summary.hold_return_use",
            app_language=app_language,
            fallback_text="The first-success path is healthy enough, but return-use is still the next product bottleneck. Strengthen library/result-history/feedback continuity before widening scope.",
        )
    else:
        review_state = "product_surface_stable"
        bottleneck_stage = return_stage
        summary = ui_text(
            "shell.product_readiness.summary.product_surface_stable",
            app_language=app_language,
            fallback_text="The current beginner-first and return-use product surfaces are provisionally stable. Choose the next true project bottleneck instead of polishing these paths further.",
        )

    return {
        "authority": "server",
        "review_state": review_state,
        "review_label": ui_text(
            f"shell.product_readiness.state.{review_state}",
            app_language=app_language,
            fallback_text=review_state.replace("_", " "),
        ),
        "next_bottleneck_stage": None if review_state == "product_surface_stable" else bottleneck_stage["stage_id"],
        "next_bottleneck_label": None if review_state == "product_surface_stable" else bottleneck_stage["stage_label"],
        "recommended_action_id": None if review_state == "product_surface_stable" else bottleneck_stage["recommended_action_id"],
        "recommended_action_label": None if review_state == "product_surface_stable" else bottleneck_stage["recommended_action_label"],
        "recommended_action_target": None if review_state == "product_surface_stable" else bottleneck_stage["recommended_action_target"],
        "uses_onboarding_state": onboarding_state is not None,
        "uses_provider_bindings": has_server_provider,
        "uses_run_history": has_history,
        "stages": stages,
        "summary": summary,
    }


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
    provider_binding_rows: Sequence[Mapping[str, Any]] = (),
    managed_secret_rows: Sequence[Mapping[str, Any]] = (),
    provider_probe_rows: Sequence[Mapping[str, Any]] = (),
    feedback_rows: Sequence[Mapping[str, Any]] = (),
    app_language_override: str | None = None,
    return_use_reentry_request: Mapping[str, Any] | None = None,
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
    selected_result_reentry_context = _return_use_reentry_context_from_request(
        return_use_reentry_request,
        workspace_id=workspace_id,
        result_rows_by_run_id=result_rows_by_run_id,
        app_language=app_language,
    )

    navigation = _navigation_model(
        asdict(shell_vm),
        app_language=app_language,
        latest_run_status_preview=latest_run_status_preview,
        latest_run_result_preview=latest_run_result_preview,
        latest_run_trace_preview=latest_run_trace_preview,
        latest_run_artifacts_preview=latest_run_artifacts_preview,
        onboarding_state=onboarding_state,
    )

    routes = {
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
            "workspace_public_share_create": f"/api/workspaces/{workspace_id}/shares",
            "workspace_shell_share": f"/api/workspaces/{workspace_id}/shares",
            "workspace_shell_share_legacy": f"/api/workspaces/{workspace_id}/shell/share",
            "workspace_share_history_page": f"/app/workspaces/{workspace_id}/shares?app_language={app_language}",
            "workspace_share_create_page": f"/app/workspaces/{workspace_id}/shares/create?app_language={app_language}",
            "public_share_page_template": f"/app/public-shares/{{share_id}}?app_language={app_language}&workspace_id={workspace_id}",
            "public_share_history_page_template": f"/app/public-shares/{{share_id}}/history?app_language={app_language}&workspace_id={workspace_id}",
            "workspace_recent_activity": f"/api/users/me/activity?workspace_id={workspace_id}",
            "workspace_history_summary": f"/api/users/me/history-summary?workspace_id={workspace_id}",
            "workspace_provider_bindings": f"/api/workspaces/{workspace_id}/provider-bindings",
            "workspace_provider_health": f"/api/workspaces/{workspace_id}/provider-bindings/health",
            "workspace_feedback": f"/api/workspaces/{workspace_id}/feedback",
            "workspace_feedback_page": f"/app/workspaces/{workspace_id}/feedback",
            "workspace_result_history": f"/api/workspaces/{workspace_id}/result-history",
            "workspace_result_history_page": f"/app/workspaces/{workspace_id}/results?app_language={app_language}",
            "workspace_upload_page": f"/app/workspaces/{workspace_id}/upload?app_language={app_language}",
            "workspace_run_page": f"/app/workspaces/{workspace_id}/run?app_language={app_language}",
            "workspace_dashboard_page": f"/app/workspaces?app_language={app_language}",
            "circuit_library": f"/api/workspaces/{workspace_id}/library",
            "circuit_library_page": f"/app/library?app_language={app_language}",
            "workspace_circuit_library_page": f"/app/workspaces/{workspace_id}/library?app_language={app_language}",
            "starter_template_catalog": "/api/templates/starter-circuits",
            "starter_template_catalog_page": f"/app/workspaces/{workspace_id}/starter-templates?app_language={app_language}",
        }

    server_product_readiness_review = _server_product_readiness_review(
        asdict(shell_vm),
        artifact_model=model,
        onboarding_state=onboarding_state,
        latest_run_row=latest_run_row,
        latest_run_status_preview=latest_run_status_preview,
        latest_run_result_preview=latest_run_result_preview,
        provider_binding_rows=provider_binding_rows,
        managed_secret_rows=managed_secret_rows,
        provider_probe_rows=provider_probe_rows,
        feedback_rows=feedback_rows,
        workspace_id=workspace_id,
        routes=routes,
        app_language=app_language,
        persisted_designer_state=server_backed_state.get("designer"),
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
        "routes": routes,
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
        "result_history_section": _result_history_section(recent_run_rows, workspace_id, result_rows_by_run_id, app_language=app_language),
        "trace_history_section": _trace_history_section(recent_run_rows, workspace_id, trace_rows_lookup, app_language=app_language),
        "artifacts_history_section": _artifacts_history_section(recent_run_rows, workspace_id, artifact_rows_lookup),
        "recent_activity_section": _recent_activity_section(recent_run_rows, onboarding_rows, provider_binding_rows, managed_secret_rows, provider_probe_rows, workspace_id, app_language=app_language),
        "history_summary_section": _history_summary_section(recent_run_rows, onboarding_rows, share_payload_rows, provider_binding_rows, managed_secret_rows, provider_probe_rows, model, workspace_id, app_language=app_language),
        "provider_readiness_section": _provider_readiness_section(provider_binding_rows, managed_secret_rows, provider_probe_rows, workspace_id, app_language=app_language),
        "first_success_setup_section": _first_success_setup_section(asdict(shell_vm), asdict(template_gallery) if template_gallery is not None else None, server_product_readiness_review, onboarding_state=onboarding_state, provider_binding_rows=provider_binding_rows, managed_secret_rows=managed_secret_rows, provider_probe_rows=provider_probe_rows, workspace_id=workspace_id, routes=routes, app_language=app_language, persisted_state=server_backed_state.get("designer")),
        "first_success_run_section": _first_success_run_section(asdict(shell_vm), server_product_readiness_review, latest_run_status_preview=latest_run_status_preview, latest_run_result_preview=latest_run_result_preview, latest_run_trace_preview=latest_run_trace_preview, latest_run_artifacts_preview=latest_run_artifacts_preview, onboarding_state=onboarding_state, workspace_id=workspace_id, routes=routes, app_language=app_language),
        "first_success_flow_section": _first_success_flow_section(asdict(shell_vm), routes, app_language=app_language),
        "return_use_continuity_section": _return_use_continuity_section(server_product_readiness_review, recent_run_rows=recent_run_rows, result_rows_by_run_id=result_rows_by_run_id, feedback_rows=feedback_rows, onboarding_state=onboarding_state, workspace_id=workspace_id, routes=routes, app_language=app_language, selected_result_reentry_context=selected_result_reentry_context),
        "return_use_reentry_context": selected_result_reentry_context,
        "product_surface_review_section": _product_surface_review_section(server_product_readiness_review, feedback_rows, workspace_id, routes=routes, app_language=app_language),
        "feedback_continuity_section": _feedback_continuity_section(server_product_readiness_review, feedback_rows, workspace_id, recent_run_rows=recent_run_rows, onboarding_state=onboarding_state, routes=routes, app_language=app_language),
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
        "server_product_readiness_review": server_product_readiness_review,
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
    return_use_reentry_context = payload.get("return_use_reentry_context") if isinstance(payload.get("return_use_reentry_context"), Mapping) else {}
    return_use_reentry_hidden_attr = "" if return_use_reentry_context else " hidden"
    return_use_reentry_source_attr = escape(str(return_use_reentry_context.get("source") or ""))
    return_use_reentry_run_id_attr = escape(str(return_use_reentry_context.get("run_id") or ""))
    return_use_reentry_output_ref_attr = escape(str(return_use_reentry_context.get("output_ref") or ""))
    return_use_reentry_summary_text = "\n".join(
        item
        for item in (
            str(return_use_reentry_context.get("source_label") or "").strip(),
            f"Run: {return_use_reentry_context.get('run_id')}" if return_use_reentry_context.get("run_id") else "",
            f"Output: {return_use_reentry_context.get('output_ref')}" if return_use_reentry_context.get("output_ref") else "",
            str(return_use_reentry_context.get("summary") or "").strip(),
        )
        if item
    ) or ui_text("server.shell.return_use_selected_pending", app_language=app_language, fallback_text="No selected result return-use context.")
    return_use_reentry_controls_html = ""
    if return_use_reentry_context.get("workspace_href"):
        return_use_reentry_controls_html += (
            f'<a id="continue-with-selected-result" class="button" href="{escape(str(return_use_reentry_context.get("workspace_href") or ""))}">'
            f'{escape(str(return_use_reentry_context.get("action_label") or ui_text("server.shell.return_use_selected_action", app_language=app_language, fallback_text="Continue with selected result")))}</a>'
        )
    if return_use_reentry_context.get("result_href"):
        return_use_reentry_controls_html += (
            f'<a id="reopen-selected-result" class="button secondary" href="{escape(str(return_use_reentry_context.get("result_href") or ""))}">'
            f'{escape(str(return_use_reentry_context.get("open_result_label") or ui_text("server.shell.return_use_selected_open_result", app_language=app_language, fallback_text="Reopen selected result")))}</a>'
        )
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
    provider_readiness_section_json = json.dumps(payload.get("provider_readiness_section"), ensure_ascii=False)
    first_success_setup_section_json = json.dumps(payload.get("first_success_setup_section"), ensure_ascii=False)
    first_success_run_section_json = json.dumps(payload.get("first_success_run_section"), ensure_ascii=False)
    first_success_flow_section_json = json.dumps(payload.get("first_success_flow_section"), ensure_ascii=False)
    return_use_continuity_section_json = json.dumps(payload.get("return_use_continuity_section"), ensure_ascii=False)
    return_use_reentry_context_json = json.dumps(payload.get("return_use_reentry_context"), ensure_ascii=False)
    product_surface_review_section_json = json.dumps(payload.get("product_surface_review_section"), ensure_ascii=False)
    feedback_continuity_section_json = json.dumps(payload.get("feedback_continuity_section"), ensure_ascii=False)
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
        'noSelectedReturnUseContext': ui_text('server.shell.return_use_selected_pending', app_language=app_language, fallback_text='No selected result return-use context.'),
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
      <button id="open-workflow-library" class="secondary" {'disabled' if not routes.get('circuit_library_page') else ''}>{escape(ui_text("server.shell.open_workflow_library", app_language=app_language, fallback_text="Open workflow library"))}</button>
      <button id="open-result-history-page" class="secondary" {'disabled' if not routes.get('workspace_result_history_page') else ''}>{escape(ui_text("server.shell.open_result_history_page", app_language=app_language, fallback_text="Open result history page"))}</button>
      <button id="open-upload-page" class="secondary" {'disabled' if not routes.get('workspace_upload_page') else ''}>{escape(ui_text("server.shell.open_upload_page", app_language=app_language, fallback_text="Upload document"))}</button>
      <button id="open-submit-run-page" class="secondary" {'disabled' if not routes.get('workspace_run_page') else ''}>{escape(ui_text("server.shell.open_submit_run_page", app_language=app_language, fallback_text="Submit run"))}</button>
      <button id="open-dashboard-page" class="secondary" {'disabled' if not routes.get('workspace_dashboard_page') else ''}>{escape(ui_text("server.shell.open_dashboard_page", app_language=app_language, fallback_text="Workspace dashboard"))}</button>
      <button id="open-share-history-page" class="secondary" {'disabled' if not routes.get('workspace_share_history_page') else ''}>{escape(ui_text("server.shell.open_share_history_page", app_language=app_language, fallback_text="Open share history page"))}</button>
      <button id="create-share" class="secondary" {'disabled' if not routes.get('workspace_shell_share') else ''}>{escape(ui_text("server.shell.create_share", app_language=app_language, fallback_text="Create share"))}</button>
      <button id="open-starter-template-catalog-page" class="secondary" {'disabled' if not routes.get('starter_template_catalog_page') else ''}>{escape(ui_text("server.shell.open_starter_template_catalog_page", app_language=app_language, fallback_text="Browse starter template page"))}</button>
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
    <div class="row">
      <section id="provider-readiness-card" tabindex="-1" class="card focus-target" role="region" aria-labelledby="provider-readiness-title">
        <h2 id="provider-readiness-title">{escape(ui_text("server.shell.provider_readiness", app_language=app_language, fallback_text="Provider readiness"))}</h2>
        <pre id="provider-readiness-summary">{escape(ui_text("server.shell.provider_readiness_summary", app_language=app_language, fallback_text="Provider readiness will appear here."))}</pre>
        <pre id="provider-readiness-detail">{escape(ui_text("server.shell.provider_readiness_detail", app_language=app_language, fallback_text="Provider readiness detail will appear here."))}</pre>
        <div id="provider-readiness-controls" class="actions"></div>
      </section>
      <section id="first-success-setup-card" tabindex="-1" class="card focus-target" role="region" aria-labelledby="first-success-setup-title">
        <h2 id="first-success-setup-title">{escape(ui_text("server.shell.first_success_setup", app_language=app_language, fallback_text="First-success setup"))}</h2>
        <pre id="first-success-setup-summary">{escape(ui_text("server.shell.first_success_setup_pending", app_language=app_language, fallback_text="First-success setup guidance will appear here once the workspace shell is available."))}</pre>
        <pre id="first-success-setup-detail">{escape(ui_text("server.shell.first_success_setup_pending", app_language=app_language, fallback_text="First-success setup guidance will appear here once the workspace shell is available."))}</pre>
        <div id="first-success-setup-controls" class="actions"></div>
      </section>
      <section id="first-success-run-card" tabindex="-1" class="card focus-target" role="region" aria-labelledby="first-success-run-title">
        <h2 id="first-success-run-title">{escape(ui_text("server.shell.first_success_run", app_language=app_language, fallback_text="First-success run"))}</h2>
        <pre id="first-success-run-summary">{escape(ui_text("server.shell.first_success_run_pending", app_language=app_language, fallback_text="First-success run guidance will appear here once the workspace shell is available."))}</pre>
        <pre id="first-success-run-detail">{escape(ui_text("server.shell.first_success_run_pending", app_language=app_language, fallback_text="First-success run guidance will appear here once the workspace shell is available."))}</pre>
        <div id="first-success-run-controls" class="actions"></div>
      </section>
      <section id="first-success-flow-card" tabindex="-1" class="card focus-target" role="region" aria-labelledby="first-success-flow-title">
        <h2 id="first-success-flow-title">{escape(ui_text("server.shell.first_success_flow", app_language=app_language, fallback_text="First-success flow"))}</h2>
        <pre id="first-success-flow-summary">{escape(ui_text("server.shell.first_success_flow_pending", app_language=app_language, fallback_text="First-success flow guidance will appear here once the workspace shell is available."))}</pre>
        <pre id="first-success-flow-detail">{escape(ui_text("server.shell.first_success_flow_pending", app_language=app_language, fallback_text="First-success flow guidance will appear here once the workspace shell is available."))}</pre>
        <div id="first-success-flow-controls" class="actions"></div>
      </section>
    </div>
    <div class="row">
      <section id="return-use-continuity-card" tabindex="-1" class="card focus-target" role="region" aria-labelledby="return-use-continuity-title">
        <h2 id="return-use-continuity-title">{escape(ui_text("server.shell.return_use_continuity", app_language=app_language, fallback_text="Return-use continuity"))}</h2>
        <pre id="return-use-continuity-summary">{escape(ui_text("server.shell.return_use_continuity_summary", app_language=app_language, fallback_text="Return-use continuity will appear here."))}</pre>
        <pre id="return-use-continuity-detail">{escape(ui_text("server.shell.return_use_continuity_detail", app_language=app_language, fallback_text="Return-use continuity detail will appear here."))}</pre>
        <div id="return-use-continuity-controls" class="actions"></div>
      </section>
      <section id="return-use-selected-result-card" tabindex="-1" class="card focus-target" role="region" aria-labelledby="return-use-selected-result-title" data-return-use-source="{return_use_reentry_source_attr}" data-return-use-run-id="{return_use_reentry_run_id_attr}" data-output-ref="{return_use_reentry_output_ref_attr}"{return_use_reentry_hidden_attr}>
        <h2 id="return-use-selected-result-title">{escape(ui_text("server.shell.return_use_selected_title", app_language=app_language, fallback_text="Selected result context"))}</h2>
        <pre id="return-use-selected-result-summary">{escape(return_use_reentry_summary_text)}</pre>
        <div id="return-use-selected-result-controls" class="actions">{return_use_reentry_controls_html}</div>
      </section>
      <section id="product-surface-review-card" tabindex="-1" class="card focus-target" role="region" aria-labelledby="product-surface-review-title">
        <h2 id="product-surface-review-title">{escape(ui_text("server.shell.product_surface_review", app_language=app_language, fallback_text="Product surface review"))}</h2>
        <pre id="product-surface-review-summary">{escape(ui_text("server.shell.product_surface_review_summary", app_language=app_language, fallback_text="Product surface review will appear here."))}</pre>
        <pre id="product-surface-review-detail">{escape(ui_text("server.shell.product_surface_review_detail", app_language=app_language, fallback_text="Product surface review detail will appear here."))}</pre>
        <div id="product-surface-review-controls" class="actions"></div>
      </section>
      <section id="feedback-continuity-card" tabindex="-1" class="card focus-target" role="region" aria-labelledby="feedback-continuity-title">
        <h2 id="feedback-continuity-title">{escape(ui_text("server.shell.feedback_continuity", app_language=app_language, fallback_text="Feedback continuity"))}</h2>
        <pre id="feedback-continuity-summary">{escape(ui_text("server.shell.feedback_continuity_summary", app_language=app_language, fallback_text="Feedback continuity will appear here."))}</pre>
        <pre id="feedback-continuity-detail">{escape(ui_text("server.shell.feedback_continuity_detail", app_language=app_language, fallback_text="Feedback continuity detail will appear here."))}</pre>
        <div id="feedback-continuity-controls" class="actions"></div>
      </section>
    </div>
    <section class="card" style="margin-top:16px;" role="region" aria-labelledby="browser-log-title">
      <h2 id=\"browser-log-title\">Last action log</h2>
      <pre id=\"browser-log\" aria-live=\"polite\">Ready.</pre>
    </section>
  </main>
  <script>
    const initialPayload = {payload_json};
    let routes = initialPayload && initialPayload.routes ? initialPayload.routes : {{}};
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
    const initialProviderReadinessSection = {provider_readiness_section_json};
    const initialFirstSuccessSetupSection = {first_success_setup_section_json};
    const initialFirstSuccessRunSection = {first_success_run_section_json};
    const initialFirstSuccessFlowSection = {first_success_flow_section_json};
    const initialReturnUseContinuitySection = {return_use_continuity_section_json};
    const initialReturnUseReentryContext = {return_use_reentry_context_json};
    const initialProductSurfaceReviewSection = {product_surface_review_section_json};
    const initialFeedbackContinuitySection = {feedback_continuity_section_json};
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
    const providerReadinessSummaryEl = document.getElementById('provider-readiness-summary');
    const providerReadinessDetailEl = document.getElementById('provider-readiness-detail');
    const providerReadinessControlsEl = document.getElementById('provider-readiness-controls');
    const firstSuccessSetupSummaryEl = document.getElementById('first-success-setup-summary');
    const firstSuccessSetupDetailEl = document.getElementById('first-success-setup-detail');
    const firstSuccessSetupControlsEl = document.getElementById('first-success-setup-controls');
    const firstSuccessRunSummaryEl = document.getElementById('first-success-run-summary');
    const firstSuccessRunDetailEl = document.getElementById('first-success-run-detail');
    const firstSuccessRunControlsEl = document.getElementById('first-success-run-controls');
    const firstSuccessFlowSummaryEl = document.getElementById('first-success-flow-summary');
    const firstSuccessFlowDetailEl = document.getElementById('first-success-flow-detail');
    const firstSuccessFlowControlsEl = document.getElementById('first-success-flow-controls');
    const returnUseContinuitySummaryEl = document.getElementById('return-use-continuity-summary');
    const returnUseContinuityDetailEl = document.getElementById('return-use-continuity-detail');
    const returnUseContinuityControlsEl = document.getElementById('return-use-continuity-controls');
    const returnUseSelectedResultCardEl = document.getElementById('return-use-selected-result-card');
    const returnUseSelectedResultSummaryEl = document.getElementById('return-use-selected-result-summary');
    const returnUseSelectedResultControlsEl = document.getElementById('return-use-selected-result-controls');
    const productSurfaceReviewSummaryEl = document.getElementById('product-surface-review-summary');
    const productSurfaceReviewDetailEl = document.getElementById('product-surface-review-detail');
    const productSurfaceReviewControlsEl = document.getElementById('product-surface-review-controls');
    const feedbackContinuitySummaryEl = document.getElementById('feedback-continuity-summary');
    const feedbackContinuityDetailEl = document.getElementById('feedback-continuity-detail');
    const feedbackContinuityControlsEl = document.getElementById('feedback-continuity-controls');
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
    let activeRunStatusPath = routes.latest_run_status || null;
    let activeRunResultPath = routes.latest_run_result || null;
    let activeRunTracePath = routes.latest_run_trace || null;
    let activeRunArtifactsPath = routes.latest_run_artifacts || null;
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
    let currentProviderReadinessSection = initialProviderReadinessSection || null;
    let currentFirstSuccessSetupSection = initialFirstSuccessSetupSection || null;
    let currentFirstSuccessRunSection = initialFirstSuccessRunSection || null;
    let currentFirstSuccessFlowSection = initialFirstSuccessFlowSection || null;
    let currentReturnUseContinuitySection = initialReturnUseContinuitySection || null;
    let currentProductSurfaceReviewSection = initialProductSurfaceReviewSection || null;
    let currentFeedbackContinuitySection = initialFeedbackContinuitySection || null;
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
    function writeProviderReadinessSection(section) {{
      currentProviderReadinessSection = writeShellSection(section, currentProviderReadinessSection, providerReadinessSummaryEl, providerReadinessDetailEl, providerReadinessControlsEl, 'Provider readiness will appear here.', 'Provider readiness detail will appear here.');
    }}
    function writeFirstSuccessSetupSection(section) {{
      currentFirstSuccessSetupSection = writeShellSection(section, currentFirstSuccessSetupSection, firstSuccessSetupSummaryEl, firstSuccessSetupDetailEl, firstSuccessSetupControlsEl, 'First-success setup guidance will appear here once the workspace shell is available.', 'First-success setup guidance will appear here once the workspace shell is available.');
    }}
    function writeFirstSuccessRunSection(section) {{
      currentFirstSuccessRunSection = writeShellSection(section, currentFirstSuccessRunSection, firstSuccessRunSummaryEl, firstSuccessRunDetailEl, firstSuccessRunControlsEl, 'First-success run guidance will appear here once the workspace shell is available.', 'First-success run guidance will appear here once the workspace shell is available.');
    }}
    function writeFirstSuccessFlowSection(section) {{
      currentFirstSuccessFlowSection = writeShellSection(section, currentFirstSuccessFlowSection, firstSuccessFlowSummaryEl, firstSuccessFlowDetailEl, firstSuccessFlowControlsEl, 'First-success flow guidance will appear here once the workspace shell is available.', 'First-success flow guidance will appear here once the workspace shell is available.');
    }}
    function writeReturnUseReentryContext(context) {{
      if (!returnUseSelectedResultCardEl || !returnUseSelectedResultSummaryEl || !returnUseSelectedResultControlsEl) return;
      if (!context || !context.run_id) {{
        returnUseSelectedResultCardEl.hidden = true;
        returnUseSelectedResultSummaryEl.textContent = localizedUi.noSelectedReturnUseContext || 'No selected result return-use context.';
        returnUseSelectedResultControlsEl.innerHTML = '';
        return;
      }}
      returnUseSelectedResultCardEl.hidden = false;
      returnUseSelectedResultCardEl.dataset.returnUseSource = String(context.source || 'result_history');
      returnUseSelectedResultCardEl.dataset.returnUseRunId = String(context.run_id || '');
      returnUseSelectedResultCardEl.dataset.outputRef = String(context.output_ref || '');
      const summaryLines = [
        context.source_label ? String(context.source_label) : null,
        context.run_id ? 'Run: ' + String(context.run_id) : null,
        context.output_ref ? 'Output: ' + String(context.output_ref) : null,
        context.summary ? String(context.summary) : null,
      ].filter(Boolean);
      returnUseSelectedResultSummaryEl.textContent = summaryLines.join('\n');
      returnUseSelectedResultControlsEl.innerHTML = '';
      if (context.workspace_href) {{
        const link = document.createElement('a');
        link.className = 'button';
        link.id = 'continue-with-selected-result';
        link.href = String(context.workspace_href);
        link.textContent = String(context.action_label || 'Continue with selected result');
        returnUseSelectedResultControlsEl.appendChild(link);
      }}
      if (context.result_href) {{
        const link = document.createElement('a');
        link.className = 'button secondary';
        link.id = 'reopen-selected-result';
        link.href = String(context.result_href);
        link.textContent = String(context.open_result_label || 'Reopen selected result');
        returnUseSelectedResultControlsEl.appendChild(link);
      }}
    }}

    function writeReturnUseContinuitySection(section) {{
      currentReturnUseContinuitySection = writeShellSection(section, currentReturnUseContinuitySection, returnUseContinuitySummaryEl, returnUseContinuityDetailEl, returnUseContinuityControlsEl, 'Return-use continuity will appear here.', 'Return-use continuity detail will appear here.');
    }}
    function writeProductSurfaceReviewSection(section) {{
      currentProductSurfaceReviewSection = writeShellSection(section, currentProductSurfaceReviewSection, productSurfaceReviewSummaryEl, productSurfaceReviewDetailEl, productSurfaceReviewControlsEl, 'Product surface review will appear here.', 'Product surface review detail will appear here.');
    }}
    function writeFeedbackContinuitySection(section) {{
      currentFeedbackContinuitySection = writeShellSection(section, currentFeedbackContinuitySection, feedbackContinuitySummaryEl, feedbackContinuityDetailEl, feedbackContinuityControlsEl, 'Feedback continuity will appear here.', 'Feedback continuity detail will appear here.');
    }}
    function writeDesignerSection(section) {{
      currentDesignerSection = writeShellSection(section, currentDesignerSection, designerSummaryEl, designerDetailEl, designerControlsEl, 'Open Designer to start drafting your workflow.', 'Designer detail will appear here.');
    }}
    function writeValidationSection(section) {{
      currentValidationSection = writeShellSection(section, currentValidationSection, validationSummaryEl, validationDetailEl, validationControlsEl, 'Validation guidance will appear here.', 'Validation detail will appear here.');
    }}
    function applyWorkspaceShellRuntimePayload(body) {{
      if (!body || typeof body !== 'object') return;
      if (body.routes && typeof body.routes === 'object') {{
        routes = body.routes;
        activeRunStatusPath = routes.latest_run_status || activeRunStatusPath;
        activeRunResultPath = routes.latest_run_result || activeRunResultPath;
        activeRunTracePath = routes.latest_run_trace || activeRunTracePath;
        activeRunArtifactsPath = routes.latest_run_artifacts || activeRunArtifactsPath;
      }}
      if (body.navigation) {{
        currentNavigation = body.navigation;
        renderRuntimeNav();
      }}
      if (body.first_success_setup_section) writeFirstSuccessSetupSection(body.first_success_setup_section);
      if (body.first_success_run_section) writeFirstSuccessRunSection(body.first_success_run_section);
      if (body.first_success_flow_section) writeFirstSuccessFlowSection(body.first_success_flow_section);
      if (body.return_use_continuity_section) writeReturnUseContinuitySection(body.return_use_continuity_section);
      if (body.return_use_reentry_context !== undefined) writeReturnUseReentryContext(body.return_use_reentry_context);
      if (body.product_surface_review_section) writeProductSurfaceReviewSection(body.product_surface_review_section);
      if (body.feedback_continuity_section) writeFeedbackContinuitySection(body.feedback_continuity_section);
      if (body.designer_section) writeDesignerSection(body.designer_section);
      if (body.validation_section) writeValidationSection(body.validation_section);
      if (body.step_state_banner) writeStepStateBanner(body.step_state_banner);
      writeShellContinuity(captureShellContinuity());
    }}
    async function persistFirstSuccessCompletion(control) {{
      const target = String((control && control.action_target) || routes.workspace_shell_draft_write || '').trim();
      const fallbackTarget = String((control && control.fallback_focus_target) || 'runtime.result');
      if (!target || !target.startsWith('/')) {{
        await performShellAction({{ action_kind: 'focus_section', action_target: fallbackTarget }});
        return;
      }}
      const resultReading = currentFirstSuccessFlowSection && currentFirstSuccessFlowSection.result_reading && typeof currentFirstSuccessFlowSection.result_reading === 'object' ? currentFirstSuccessFlowSection.result_reading : {{}};
      const completionPatch = control && control.completion_metadata_patch && typeof control.completion_metadata_patch === 'object'
        ? control.completion_metadata_patch
        : (resultReading.completion_metadata_patch || {{}});
      const response = await fetch(target, {{
        method: 'PUT',
        credentials: 'same-origin',
        headers: {{ 'content-type': 'application/json' }},
        body: JSON.stringify({{
          first_success_action: 'mark_first_result_read',
          completion_action_id: 'mark_first_result_read',
          completion_metadata_patch: completionPatch,
        }}),
      }});
      const body = await response.json();
      if (!response.ok) {{
        writeLog(body);
        return;
      }}
      applyWorkspaceShellRuntimePayload(body);
      await persistCurrentStep('read_result', {{ first_success_achieved: true, advanced_surfaces_unlocked: true }});
      setFocusedSection('result', 'summary');
      writeLog('Marked first result as read.');
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
      if (kind === 'first_success_completion') {{
        await persistFirstSuccessCompletion(control);
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
      if (kind === 'open_public_share') {{
        if (target) {{
          const template = routes && typeof routes.public_share_page_template === 'string' ? routes.public_share_page_template : '';
          const nextHref = template ? template.replace('{{share_id}}', encodeURIComponent(target)) : '/api/public-shares/' + encodeURIComponent(target);
          window.location.href = nextHref;
          return;
        }}
      }}
      if (kind === 'open_workspace_share_create') {{
        const shareCreatePage = routes && typeof routes.workspace_share_create_page === 'string' ? routes.workspace_share_create_page : '';
        if (shareCreatePage) {{
          window.location.href = shareCreatePage;
          return;
        }}
        const shareCreatePath = routes && typeof routes.workspace_shell_share === 'string' ? routes.workspace_shell_share : '';
        if (shareCreatePath) {{
          const response = await fetch(shareCreatePath, {{
            method: 'POST',
            credentials: 'same-origin',
            headers: {{ 'content-type': 'application/json' }},
            body: JSON.stringify({{}}),
          }});
          const body = await response.json();
          if (!response.ok) {{
            writeLog(body);
            return;
          }}
          const shareId = body && typeof body.share_id === 'string' ? body.share_id : '';
          if (shareId) {{
            const template = routes && typeof routes.public_share_page_template === 'string' ? routes.public_share_page_template : '';
            const nextHref = template ? template.replace('{{share_id}}', encodeURIComponent(shareId)) : '/api/public-shares/' + encodeURIComponent(shareId);
            window.location.href = nextHref;
            return;
          }}
          writeLog(body);
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
    writeProviderReadinessSection(initialProviderReadinessSection);
    writeFirstSuccessSetupSection(initialFirstSuccessSetupSection);
    writeFirstSuccessRunSection(initialFirstSuccessRunSection);
    writeFirstSuccessFlowSection(initialFirstSuccessFlowSection);
    writeReturnUseContinuitySection(initialReturnUseContinuitySection);
    writeReturnUseReentryContext(initialReturnUseReentryContext);
    writeProductSurfaceReviewSection(initialProductSurfaceReviewSection);
    writeFeedbackContinuitySection(initialFeedbackContinuitySection);
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
      if (body.provider_readiness_section) {{
        writeProviderReadinessSection(body.provider_readiness_section);
      }}
      if (body.first_success_setup_section) {{
        writeFirstSuccessSetupSection(body.first_success_setup_section);
      }}
      if (body.first_success_run_section) {{
        writeFirstSuccessRunSection(body.first_success_run_section);
      }}
      if (body.first_success_flow_section) {{
        writeFirstSuccessFlowSection(body.first_success_flow_section);
      }}
      if (body.return_use_continuity_section) {{
        writeReturnUseContinuitySection(body.return_use_continuity_section);
      }}
      if (body.product_surface_review_section) {{
        writeProductSurfaceReviewSection(body.product_surface_review_section);
      }}
      if (body.feedback_continuity_section) {{
        writeFeedbackContinuitySection(body.feedback_continuity_section);
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
    document.getElementById('open-workflow-library').addEventListener('click', () => {{
      const target = (routes && (routes.workspace_circuit_library_page || routes.circuit_library_page)) || null;
      if (!target) {{
        writeLog('No workflow library page is available.');
        return;
      }}
      window.open(target, '_blank', 'noopener');
      writeLog('Opened route ' + target + '.');
    }});
    document.getElementById('open-result-history-page').addEventListener('click', () => {{
      const target = routes && routes.workspace_result_history_page;
      if (!target) {{
        writeLog('No result history page is available.');
        return;
      }}
      window.open(target, '_blank', 'noopener');
      writeLog('Opened route ' + target + '.');
    }});
    document.getElementById('open-starter-template-catalog-page').addEventListener('click', () => {{
      const target = routes && routes.starter_template_catalog_page;
      if (!target) {{
        writeLog('No starter template page is available.');
        return;
      }}
      window.open(target, '_blank', 'noopener');
      writeLog('Opened route ' + target + '.');
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
