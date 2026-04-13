from __future__ import annotations

from dataclasses import asdict
from html import escape
from typing import Any, Mapping, Sequence

from src.server.auth_models import RunAuthorizationContext, WorkspaceAuthorizationContext
from src.server.run_list_api import RunListReadService
from src.server.run_read_api import RunResultReadService
from src.server.workspace_shell_sections import build_shell_section
from src.ui.result_history import read_result_history_view_model


def _run_context_for_row(workspace_context: WorkspaceAuthorizationContext, row: Mapping[str, Any]) -> RunAuthorizationContext | None:
    run_id = str(row.get("run_id") or "").strip()
    if not run_id:
        return None
    owner = str(row.get("requested_by_user_id") or "").strip() or None
    return RunAuthorizationContext(run_id=run_id, workspace_context=workspace_context, run_owner_user_ref=owner)


def build_workspace_result_history_payload(*, request_auth, workspace_context: WorkspaceAuthorizationContext | None, workspace_row: Mapping[str, Any] | None, run_rows: Sequence[Mapping[str, Any]] = (), result_rows_by_run_id: Mapping[str, Mapping[str, Any]] | None = None, artifact_rows_lookup=None, recent_run_rows: Sequence[Mapping[str, Any]] = (), provider_binding_rows: Sequence[Mapping[str, Any]] = (), managed_secret_rows: Sequence[Mapping[str, Any]] = (), provider_probe_rows: Sequence[Mapping[str, Any]] = (), onboarding_rows: Sequence[Mapping[str, Any]] = (), selected_run_id: str | None = None, app_language: str = "en") -> dict[str, Any] | None:
    outcome = RunListReadService.list_workspace_runs(
        request_auth=request_auth,
        workspace_context=workspace_context,
        run_rows=run_rows,
        result_rows_by_run_id=result_rows_by_run_id,
        workspace_row=workspace_row,
        recent_run_rows=recent_run_rows,
        provider_binding_rows=provider_binding_rows,
        managed_secret_rows=managed_secret_rows,
        provider_probe_rows=provider_probe_rows,
        onboarding_rows=onboarding_rows,
        limit=10,
    )
    if not outcome.ok or outcome.response is None or workspace_context is None:
        return None
    response = outcome.response
    run_row_lookup = {str(row.get("run_id") or "").strip(): dict(row) for row in run_rows if str(row.get("run_id") or "").strip()}
    result_map: dict[str, Any] = {}
    for item in response.runs:
        run_context = _run_context_for_row(workspace_context, run_row_lookup.get(item.run_id, {}))
        if run_context is None:
            continue
        read_outcome = RunResultReadService.read_result(
            request_auth=request_auth,
            run_context=run_context,
            run_record_row=run_row_lookup.get(item.run_id),
            result_row=(result_rows_by_run_id or {}).get(item.run_id),
            artifact_rows=artifact_rows_lookup(item.run_id) if artifact_rows_lookup is not None else (),
            workspace_row=workspace_row,
            recent_run_rows=recent_run_rows,
            provider_binding_rows=provider_binding_rows,
            managed_secret_rows=managed_secret_rows,
            provider_probe_rows=provider_probe_rows,
            onboarding_rows=onboarding_rows,
        )
        if read_outcome.ok and read_outcome.response is not None:
            result_map[item.run_id] = read_outcome.response
    view_model = read_result_history_view_model(response, result_rows_by_run_id=result_map, app_language=app_language, selected_run_id=selected_run_id)
    overview = build_shell_section(
        headline=view_model.title or "Recent results",
        lines=[view_model.subtitle or "", f"Visible results: {view_model.returned_count}"],
        detail_title="Result history overview",
        detail_items=[
            "Source of truth: server-backed run history + result history",
            "Beginner path: recent result snapshots instead of advanced trace literacy",
            "Artifact reopen remains a secondary import/export path",
        ],
        summary_empty="No recent results are visible yet.",
        detail_empty="Result history detail will appear here once runs complete.",
    )
    item_sections = []
    for item in view_model.items:
        selected = item.run_id == view_model.selected_run_id
        detail_items = [item.timestamp_label, item.result_summary]
        if item.output_preview:
            detail_items.append(f"Latest output preview: {item.output_preview}")
        item_sections.append({
            "run_id": item.run_id,
            "workspace_id": item.workspace_id,
            "status_label": item.status_label,
            "open_result_href": item.open_result_href,
            "continue_href": item.continue_href,
            "section": build_shell_section(
                headline=item.result_title,
                lines=[item.status_label] + list(item.summary_lines),
                detail_title="Result detail",
                detail_items=detail_items,
                controls=(
                    {"control_id": f"open-result-{item.run_id}", "label": "Open result", "action_kind": "navigate", "action_target": item.open_result_href},
                    {"control_id": f"continue-workflow-{item.run_id}", "label": "Continue workflow", "action_kind": "navigate", "action_target": item.continue_href},
                ),
            ),
            "selected": selected,
        })
    selected_item = next((item for item in view_model.items if item.run_id == view_model.selected_run_id), None)
    return {
        "status": "ready",
        "workspace_id": response.workspace_id,
        "workspace_title": response.workspace_title,
        "source_of_truth": "run_history_result_history",
        "result_history": asdict(view_model),
        "overview_section": overview,
        "item_sections": item_sections,
        "selected_result": asdict(selected_item) if selected_item is not None else None,
        "routes": {
            "workspace_list": "/api/workspaces",
            "library": "/app/library",
            "workspace_page": f"/app/workspaces/{response.workspace_id}",
            "api_history": f"/api/workspaces/{response.workspace_id}/result-history",
            "app_history": f"/app/workspaces/{response.workspace_id}/results",
        },
    }


def render_workspace_result_history_html(payload: Mapping[str, Any]) -> str:
    history = dict(payload.get("result_history") or {})
    title = escape(str(history.get("title") or "Recent results"))
    subtitle = escape(str(history.get("subtitle") or "Reopen recent results."))
    empty_title = escape(str(history.get("empty_title") or "No recent results yet"))
    empty_summary = escape(str(history.get("empty_summary") or "Run a workflow once to see recent results here."))
    workspace_title = escape(str(payload.get("workspace_title") or history.get("workspace_title") or "Workflow"))
    item_sections = list(payload.get("item_sections") or [])
    selected = dict(payload.get("selected_result") or {})

    def _render_lines(lines: Sequence[str]) -> str:
        return "".join(f"<li>{escape(str(line))}</li>" for line in lines if str(line).strip())

    cards_html = ""
    for item in item_sections:
        section = dict(item.get("section") or {})
        summary = dict(section.get("summary") or {})
        detail = dict(section.get("detail") or {})
        selected_class = " selected" if item.get("selected") else ""
        open_href = escape(str(item.get("open_result_href") or "#"))
        continue_href = escape(str(item.get("continue_href") or "#"))
        cards_html += f"""
        <article class="result-card{selected_class}">
          <div class="result-card-head">
            <h2>{escape(str(summary.get('headline') or item.get('run_id') or 'Result'))}</h2>
            <span class="status-badge">{escape(str(item.get('status_label') or ''))}</span>
          </div>
          <ul class="summary-lines">{_render_lines(summary.get('lines') or [])}</ul>
          <details {'open' if item.get('selected') else ''}>
            <summary>{escape(str(detail.get('title') or 'Result detail'))}</summary>
            <ul class="detail-lines">{_render_lines(detail.get('items') or [])}</ul>
          </details>
          <div class="actions">
            <a class="action-link secondary" href="{open_href}">Open result</a>
            <a class="action-link" href="{continue_href}">Continue workflow</a>
          </div>
        </article>
        """
    if not cards_html:
        cards_html = f"""
        <article class="result-card empty">
          <h2>{empty_title}</h2>
          <p>{empty_summary}</p>
        </article>
        """
    selected_output_html = ""
    if selected.get("output_preview"):
        selected_output_html = f'<section class="selected-output"><h2>{escape(str(selected.get("output_label") or "Latest output"))}</h2><pre>{escape(str(selected.get("output_preview") or ""))}</pre></section>'
    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>{title}</title>
    <style>
      body {{ font-family: Arial, sans-serif; margin: 0; background: #0b1220; color: #e5e7eb; }}
      main {{ max-width: 1040px; margin: 0 auto; padding: 24px; }}
      header {{ margin-bottom: 24px; }}
      h1 {{ margin: 0 0 8px; font-size: 2rem; }}
      p {{ margin: 0; color: #cbd5e1; }}
      .result-grid {{ display: grid; gap: 16px; }}
      .result-card, .selected-output {{ background: #111827; border: 1px solid #334155; border-radius: 16px; padding: 16px; }}
      .result-card.selected {{ border-color: #60a5fa; box-shadow: 0 0 0 1px #60a5fa inset; }}
      .result-card-head {{ display: flex; justify-content: space-between; gap: 12px; align-items: center; }}
      .status-badge {{ background: #1f2937; border: 1px solid #475569; border-radius: 999px; padding: 4px 10px; font-size: 0.875rem; }}
      .summary-lines, .detail-lines {{ margin: 12px 0 0; padding-left: 18px; }}
      .actions {{ margin-top: 16px; display: flex; gap: 10px; flex-wrap: wrap; }}
      .action-link {{ display: inline-block; padding: 10px 14px; border-radius: 10px; background: #2563eb; color: white; text-decoration: none; }}
      .action-link.secondary {{ background: #1f2937; border: 1px solid #475569; }}
      a.top-link {{ color: #93c5fd; text-decoration: none; margin-right: 12px; }}
      details summary {{ cursor: pointer; margin-top: 12px; }}
      pre {{ white-space: pre-wrap; word-break: break-word; }}
    </style>
  </head>
  <body>
    <main>
      <header>
        <a class="top-link" href="/app/library">Back to library</a>
        <a class="top-link" href="{escape(str(payload.get('routes', {}).get('workspace_page') or '#'))}">Continue workflow</a>
        <h1>{title}</h1>
        <p>{workspace_title} · {subtitle}</p>
      </header>
      {selected_output_html}
      <section class="result-grid">{cards_html}</section>
    </main>
  </body>
</html>
"""
