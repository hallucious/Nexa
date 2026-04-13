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
from src.ui.template_gallery import read_template_gallery_view_model

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

def _summary_lines(*values: str | None) -> list[str]:
    return [value for value in values if isinstance(value, str) and value.strip()]


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


def build_workspace_shell_runtime_payload(
    *,
    workspace_row: Mapping[str, Any] | None,
    artifact_source: Any | None = None,
    recent_run_rows: Sequence[Mapping[str, Any]] = (),
    result_rows_by_run_id: Mapping[str, Mapping[str, Any]] | None = None,
    onboarding_rows: Sequence[Mapping[str, Any]] = (),
    artifact_rows_lookup: Any | None = None,
    trace_rows_lookup: Any | None = None,
) -> dict[str, Any]:
    source = resolve_workspace_artifact_source(workspace_row, artifact_source)
    model, loaded = _load_workspace_model(source, workspace_row)
    shell_vm = read_builder_shell_view_model(model)
    template_gallery = read_template_gallery_view_model(model) if isinstance(model, WorkingSaveModel) else None
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

    payload = {
        "workspace_id": workspace_id,
        "workspace_title": workspace_title,
        "storage_role": _storage_role(model),
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
        },
        "latest_run_status_preview": latest_run_status_preview,
        "latest_run_result_preview": latest_run_result_preview,
        "latest_run_artifacts_preview": latest_run_artifacts_preview,
        "latest_run_trace_preview": latest_run_trace_preview,
        "latest_run_status_summary": _latest_run_status_summary(latest_run_status_preview),
        "latest_run_result_summary": _latest_run_result_summary(latest_run_result_preview),
        "latest_run_artifacts_summary": _latest_run_artifacts_summary(latest_run_artifacts_preview),
        "latest_run_trace_summary": _latest_run_trace_summary(latest_run_trace_preview),
        "latest_run_artifacts_detail": _latest_run_artifacts_detail(latest_run_artifacts_preview),
        "latest_run_trace_detail": _latest_run_trace_detail(latest_run_trace_preview),
        "continuity": {
            "onboarding_state": onboarding_state,
            "load_status": getattr(loaded, "load_status", "generated_default") if loaded is not None else "generated_default",
            "load_finding_count": len(getattr(loaded, "findings", ()) or ()) if loaded is not None else 0,
        },
    }
    return payload


def render_workspace_shell_runtime_html(payload: Mapping[str, Any]) -> str:
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
    latest_run_artifacts_detail_json = json.dumps(payload.get("latest_run_artifacts_detail"), ensure_ascii=False)
    latest_run_trace_detail_json = json.dumps(payload.get("latest_run_trace_detail"), ensure_ascii=False)
    template_items = []
    for template in (template_gallery.get("templates") or [])[:6]:
        title = escape(str(template.get("display_name") or template.get("template_id") or "Template"))
        summary = escape(str(template.get("summary") or ""))
        template_items.append(f"<li><strong>{title}</strong><br><span>{summary}</span></li>")
    template_markup = "".join(template_items) or "<li>No starter templates projected yet.</li>"
    privacy_items = []
    for fact in (privacy.get("facts") or []):
        label = escape(str(fact.get("label") or fact.get("fact_id") or "Fact"))
        value = escape(str(fact.get("value") or ""))
        privacy_items.append(f"<li><strong>{label}:</strong> {value}</li>")
    privacy_markup = "".join(privacy_items) or "<li>No privacy facts projected.</li>"
    mobile_items = []
    for step in mobile.get("steps") or []:
        label = escape(str(step.get("label") or step.get("step_id") or "Step"))
        status = escape(str(step.get("status") or "pending"))
        mobile_items.append(f"<li>{label} — <em>{status}</em></li>")
    mobile_markup = "".join(mobile_items) or "<li>Mobile first-run projection unavailable.</li>"
    latest_run_status_path = escape(str(routes.get("latest_run_status") or ""))
    latest_run_trace_path = escape(str(routes.get("latest_run_trace") or ""))
    latest_run_artifacts_path = escape(str(routes.get("latest_run_artifacts") or ""))
    help_title = escape(str(contextual_help.get("title") or "Contextual help"))
    help_summary = escape(str(contextual_help.get("summary") or "Review the projected next action."))
    shell_status = escape(str((shell.get("shell_status_label") or payload.get("storage_role") or "ready")))
    return f"""<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>Nexa Runtime Shell — {workspace_title}</title>
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
  </style>
</head>
<body>
  <div class=\"shell\">
    <h1>Nexa Runtime Shell</h1>
    <p><strong>{workspace_title}</strong> (<code>{workspace_id}</code>)</p>
    <p>Status: <strong>{shell_status}</strong></p>
    <div class="actions">
      <button id="run-draft" {'disabled' if payload.get('launch_request_template') is None else ''}>Run draft</button>
      <button id="refresh" class="secondary">Refresh shell</button>
      <button id="open-status" class="secondary" {'disabled' if not latest_run_status_path else ''}>Open latest run status</button>
      <button id="open-trace" class="secondary" {'disabled' if not latest_run_trace_path else ''}>Open latest trace</button>
      <button id="open-artifacts" class="secondary" {'disabled' if not latest_run_artifacts_path else ''}>Open latest artifacts</button>
    </div>
    <div class="row">
      <section class="card">
        <h2>{help_title}</h2>
        <p>{help_summary}</p>
      </section>
      <section class="card">
        <h2>{escape(str(privacy.get('title') or 'Privacy and data handling'))}</h2>
        <ul>{privacy_markup}</ul>
      </section>
    </div>
    <div class="row">
      <section class="card">
        <h2>Mobile first-run</h2>
        <ul>{mobile_markup}</ul>
      </section>
      <section class="card">
        <h2>Starter templates</h2>
        <ul>{template_markup}</ul>
      </section>
    </div>
    <div class="row">
      <section class="card">
        <h2>Latest run status</h2>
        <pre id="latest-run-status">Waiting for run status.</pre>
      </section>
      <section class="card">
        <h2>Latest run result</h2>
        <pre id="latest-run-result">Waiting for run result.</pre>
      </section>
    </div>
    <div class="row">
      <section class="card">
        <h2>Latest trace</h2>
        <pre id="latest-run-trace">Waiting for trace details.</pre>
      </section>
      <section class="card">
        <h2>Latest artifacts</h2>
        <pre id="latest-run-artifacts">Waiting for artifact details.</pre>
      </section>
    </div>
    <div class="row">
      <section class="card">
        <h2>Trace detail layer</h2>
        <pre id="latest-run-trace-detail">Open latest trace to view the detail layer.</pre>
      </section>
      <section class="card">
        <h2>Artifacts detail layer</h2>
        <pre id="latest-run-artifacts-detail">Open latest artifacts to view the detail layer.</pre>
      </section>
    </div>
    <section class=\"card\" style=\"margin-top:16px;\">
      <h2>Last action log</h2>
      <pre id=\"browser-log\">Ready.</pre>
    </section>
  </div>
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
    const initialRunArtifactsDetail = {latest_run_artifacts_detail_json};
    const initialRunTraceDetail = {latest_run_trace_detail_json};
    const logEl = document.getElementById('browser-log');
    const latestRunStatusEl = document.getElementById('latest-run-status');
    const latestRunResultEl = document.getElementById('latest-run-result');
    const latestRunTraceEl = document.getElementById('latest-run-trace');
    const latestRunArtifactsEl = document.getElementById('latest-run-artifacts');
    const latestRunTraceDetailEl = document.getElementById('latest-run-trace-detail');
    const latestRunArtifactsDetailEl = document.getElementById('latest-run-artifacts-detail');
    let activeRunId = initialRunStatusPreview ? initialRunStatusPreview.run_id : null;
    let activeRunStatusPath = initialPayload.routes.latest_run_status || null;
    let activeRunResultPath = initialPayload.routes.latest_run_result || null;
    let activeRunTracePath = initialPayload.routes.latest_run_trace || null;
    let activeRunArtifactsPath = initialPayload.routes.latest_run_artifacts || null;
    function writeLog(message) {{
      logEl.textContent = typeof message === 'string' ? message : JSON.stringify(message, null, 2);
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
        headline: 'Status: ' + String(body.status || body.summary || 'unknown'),
        lines: [
          body.run_id ? ('Run id: ' + body.run_id) : null,
          body.summary ? ('Summary: ' + body.summary) : null,
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
          body.message ? ('Message: ' + body.message) : null,
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
          latest && latest.message ? ('Latest message: ' + latest.message) : null,
          body.message ? ('Trace status: ' + body.message) : null,
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
          first && first.label ? ('Preview: ' + first.label) : null,
          first && first.preview ? ('Payload preview: ' + first.preview) : null,
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
          'Status: ' + String(body.status || 'unknown'),
          'Event count: ' + String(Number(body.event_count || events.length || 0)),
          latest && latest.event_type ? ('Latest event type: ' + latest.event_type) : null,
          latest && latest.node_id ? ('Latest node id: ' + latest.node_id) : null,
          latest && latest.message ? ('Latest message: ' + latest.message) : null,
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
          first && first.label ? ('First artifact label: ' + first.label) : null,
          first && first.preview ? ('First artifact preview: ' + first.preview) : null,
        ].filter(Boolean),
      }};
    }}
    function writeLatestRunStatus(message) {{
      latestRunStatusEl.textContent = typeof message === 'string' ? message : formatSummary(message, 'No recent run is available yet.');
    }}
    function writeLatestRunResult(message) {{
      latestRunResultEl.textContent = typeof message === 'string' ? message : formatSummary(message, 'No recent run result is available yet.');
    }}
    function writeLatestRunTrace(message) {{
      latestRunTraceEl.textContent = typeof message === 'string' ? message : formatSummary(message, 'No recent trace is available yet.');
    }}
    function writeLatestRunArtifacts(message) {{
      latestRunArtifactsEl.textContent = typeof message === 'string' ? message : formatSummary(message, 'No recent artifacts are available yet.');
    }}
    function writeLatestRunTraceDetail(message) {{
      latestRunTraceDetailEl.textContent = typeof message === 'string' ? message : formatDetail(message, 'Open latest trace to view the detail layer.');
    }}
    function writeLatestRunArtifactsDetail(message) {{
      latestRunArtifactsDetailEl.textContent = typeof message === 'string' ? message : formatDetail(message, 'Open latest artifacts to view the detail layer.');
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
        writeLatestRunStatus('No recent run is available yet.');
        return null;
      }}
      const response = await fetch(activeRunStatusPath, {{ credentials: 'same-origin' }});
      const body = await response.json();
      writeLatestRunStatus(summarizeStatusBody(body));
      return body;
    }}
    async function refreshLatestRunResult() {{
      if (!activeRunResultPath) {{
        writeLatestRunResult('No recent run result is available yet.');
        return null;
      }}
      const response = await fetch(activeRunResultPath, {{ credentials: 'same-origin' }});
      const body = await response.json();
      writeLatestRunResult(summarizeResultBody(body));
      return body;
    }}
    async function refreshLatestRunTrace() {{
      if (!activeRunTracePath) {{
        writeLatestRunTrace('No recent trace is available yet.');
        writeLatestRunTraceDetail('Open latest trace to view the detail layer.');
        return null;
      }}
      const response = await fetch(activeRunTracePath, {{ credentials: 'same-origin' }});
      const body = await response.json();
      writeLatestRunTrace(summarizeTraceBody(body));
      writeLatestRunTraceDetail(detailFromTraceBody(body));
      return body;
    }}
    async function refreshLatestRunArtifacts() {{
      if (!activeRunArtifactsPath) {{
        writeLatestRunArtifacts('No recent artifacts are available yet.');
        writeLatestRunArtifactsDetail('Open latest artifacts to view the detail layer.');
        return null;
      }}
      const response = await fetch(activeRunArtifactsPath, {{ credentials: 'same-origin' }});
      const body = await response.json();
      writeLatestRunArtifacts(summarizeArtifactsBody(body));
      writeLatestRunArtifactsDetail(detailFromArtifactsBody(body));
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
    writeLatestRunStatus(initialRunStatusSummary || 'No recent run is available yet.');
    writeLatestRunResult(initialRunResultSummary || 'No recent run result is available yet.');
    writeLatestRunTrace(initialRunTraceSummary || 'No recent trace is available yet.');
    writeLatestRunArtifacts(initialRunArtifactsSummary || 'No recent artifacts are available yet.');
    writeLatestRunTraceDetail(initialRunTraceDetail || 'Open latest trace to view the detail layer.');
    writeLatestRunArtifactsDetail(initialRunArtifactsDetail || 'Open latest artifacts to view the detail layer.');
    document.getElementById('refresh').addEventListener('click', async () => {{
      const response = await fetch(initialPayload.routes.workspace_shell, {{ credentials: 'same-origin' }});
      const body = await response.json();
      writeLog(body);
      if (body.latest_run_status_preview && body.latest_run_status_preview.run_id) {{
        setActiveRun(body.latest_run_status_preview.run_id);
        writeLatestRunStatus(body.latest_run_status_summary || summarizeStatusBody(body.latest_run_status_preview));
      }}
      if (body.latest_run_result_preview) {{
        writeLatestRunResult(body.latest_run_result_summary || summarizeResultBody(body.latest_run_result_preview));
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
        writeLatestRunResult('Waiting for run result.');
        writeLatestRunTrace('Waiting for trace details.');
        writeLatestRunArtifacts('Waiting for artifact details.');
        writeLatestRunTraceDetail('Open latest trace to view the detail layer.');
        writeLatestRunArtifactsDetail('Open latest artifacts to view the detail layer.');
        await pollLatestRunUntilSettled();
      }}
    }});
    document.getElementById('open-status').addEventListener('click', async () => {{
      if (!activeRunStatusPath) {{
        writeLog('No recent run is available yet.');
        return;
      }}
      const body = await refreshLatestRunStatus();
      writeLog(body || 'No recent run is available yet.');
      await refreshLatestRunResult();
      await refreshLatestRunTrace();
      await refreshLatestRunArtifacts();
    }});
    document.getElementById('open-trace').addEventListener('click', async () => {{
      const body = await refreshLatestRunTrace();
      writeLog(body || 'No recent trace is available yet.');
    }});
    document.getElementById('open-artifacts').addEventListener('click', async () => {{
      const body = await refreshLatestRunArtifacts();
      writeLog(body || 'No recent artifacts are available yet.');
    }});
  </script>
</body>
</html>"""
