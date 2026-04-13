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



def build_workspace_shell_runtime_payload(
    *,
    workspace_row: Mapping[str, Any] | None,
    artifact_source: Any | None = None,
    recent_run_rows: Sequence[Mapping[str, Any]] = (),
    onboarding_rows: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    source = resolve_workspace_artifact_source(workspace_row, artifact_source)
    model, loaded = _load_workspace_model(source, workspace_row)
    shell_vm = read_builder_shell_view_model(model)
    template_gallery = read_template_gallery_view_model(model) if isinstance(model, WorkingSaveModel) else None
    workspace_id = str((workspace_row or {}).get("workspace_id") or getattr(getattr(model, "meta", None), "working_save_id", "workspace")).strip() or "workspace"
    workspace_title = str((workspace_row or {}).get("title") or getattr(getattr(model, "meta", None), "name", "Workspace")).strip() or "Workspace"
    target = _execution_target_for(model)
    latest_run_id = _last_run_id(recent_run_rows, workspace_id)
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
            "workspace_runs": f"/api/workspaces/{workspace_id}/runs",
            "onboarding": f"/api/users/me/onboarding?workspace_id={workspace_id}",
        },
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
    <div class=\"actions\">
      <button id=\"run-draft\" {'disabled' if payload.get('launch_request_template') is None else ''}>Run draft</button>
      <button id=\"refresh\" class=\"secondary\">Refresh shell</button>
      <button id=\"open-status\" class=\"secondary\" {'disabled' if not latest_run_status_path else ''}>Open latest run status</button>
    </div>
    <div class=\"row\">
      <section class=\"card\">
        <h2>{help_title}</h2>
        <p>{help_summary}</p>
      </section>
      <section class=\"card\">
        <h2>{escape(str(privacy.get('title') or 'Privacy and data handling'))}</h2>
        <ul>{privacy_markup}</ul>
      </section>
    </div>
    <div class=\"row\">
      <section class=\"card\">
        <h2>Mobile first-run</h2>
        <ul>{mobile_markup}</ul>
      </section>
      <section class=\"card\">
        <h2>Starter templates</h2>
        <ul>{template_markup}</ul>
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
    const logEl = document.getElementById('browser-log');
    function writeLog(message) {{
      logEl.textContent = typeof message === 'string' ? message : JSON.stringify(message, null, 2);
    }}
    document.getElementById('refresh').addEventListener('click', async () => {{
      const response = await fetch(initialPayload.routes.workspace_shell, {{ credentials: 'same-origin' }});
      const body = await response.json();
      writeLog(body);
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
    }});
    document.getElementById('open-status').addEventListener('click', async () => {{
      if (!initialPayload.routes.latest_run_status) {{
        writeLog('No recent run is available yet.');
        return;
      }}
      const response = await fetch(initialPayload.routes.latest_run_status, {{ credentials: 'same-origin' }});
      const body = await response.json();
      writeLog(body);
    }});
  </script>
</body>
</html>"""
