from __future__ import annotations

from dataclasses import asdict
from html import escape
from typing import Any, Mapping, Sequence

from src.server.workspace_onboarding_api import WorkspaceRegistryService
from src.server.workspace_onboarding_models import ProductWorkspaceListResponse
from src.server.workspace_shell_sections import build_shell_section
from src.ui.i18n import normalize_ui_language, ui_text
from src.ui.circuit_library import read_circuit_library_view_model


def _onboarding_state_map(*, request_auth, onboarding_rows: Sequence[Mapping[str, Any]] = ()) -> dict[str, dict[str, Any]]:
    user_id = str(getattr(request_auth, "requested_by_user_ref", "") or "").strip()
    if not user_id:
        return {}
    state_by_workspace_id: dict[str, dict[str, Any]] = {}
    for row in onboarding_rows:
        if str(row.get("user_id") or "").strip() != user_id:
            continue
        workspace_id = str(row.get("workspace_id") or "").strip()
        if not workspace_id:
            continue
        state_by_workspace_id[workspace_id] = dict(row)
    return state_by_workspace_id


def build_circuit_library_payload(
    *,
    request_auth,
    workspace_rows: Sequence[Mapping[str, Any]] = (),
    membership_rows: Sequence[Mapping[str, Any]] = (),
    recent_run_rows: Sequence[Mapping[str, Any]] = (),
    provider_binding_rows: Sequence[Mapping[str, Any]] = (),
    managed_secret_rows: Sequence[Mapping[str, Any]] = (),
    provider_probe_rows: Sequence[Mapping[str, Any]] = (),
    onboarding_rows: Sequence[Mapping[str, Any]] = (),
    app_language: str = "en",
) -> dict[str, Any] | None:
    outcome = WorkspaceRegistryService.list_workspaces(
        request_auth=request_auth,
        workspace_rows=workspace_rows,
        membership_rows=membership_rows,
        recent_run_rows=recent_run_rows,
        provider_binding_rows=provider_binding_rows,
        managed_secret_rows=managed_secret_rows,
        provider_probe_rows=provider_probe_rows,
        onboarding_rows=onboarding_rows,
    )
    if not outcome.ok or outcome.response is None:
        return None
    app_language = normalize_ui_language(app_language)
    response: ProductWorkspaceListResponse = outcome.response
    onboarding_state_by_workspace_id = _onboarding_state_map(request_auth=request_auth, onboarding_rows=onboarding_rows)
    view_model = read_circuit_library_view_model(
        response,
        app_language=app_language,
        onboarding_state_by_workspace_id=onboarding_state_by_workspace_id,
    )
    overview = build_shell_section(
        headline=view_model.title or "My workflows",
        lines=[view_model.subtitle or "", ui_text("server.library.visible_count", app_language=app_language, fallback_text="Visible workflows: {count}", count=view_model.returned_count)],
        detail_title=ui_text("server.library.overview_title", app_language=app_language, fallback_text="Library overview"),
        detail_items=[
            ui_text("server.library.source_of_truth", app_language=app_language, fallback_text="Source of truth: server-backed workspace registry"),
            ui_text("server.library.return_use_path", app_language=app_language, fallback_text="Return-use path: continue an existing workflow from the product surface"),
            ui_text("server.library.artifact_path", app_language=app_language, fallback_text="Artifact reopen remains a secondary import/export path"),
            ui_text("server.library.onboarding_projection", app_language=app_language, fallback_text="Onboarding continuity is projected from canonical server state"),
        ],
        summary_empty=ui_text("server.library.summary_empty", app_language=app_language, fallback_text="No workflows are visible yet."),
        detail_empty=ui_text("server.library.detail_empty", app_language=app_language, fallback_text="Library detail will appear here once workflows exist."),
    )
    item_sections = []
    for item in view_model.items:
        controls = [
            {
                "control_id": f"continue-{item.workspace_id}",
                "label": item.continue_label,
                "action_kind": "navigate",
                "action_target": item.continue_href,
            },
        ]
        if item.has_recent_result_history and item.result_history_href:
            controls.insert(
                0,
                {
                    "control_id": f"open-results-{item.workspace_id}",
                    "label": item.result_history_action_label or ui_text("server.library.open_results", app_language=app_language, fallback_text="Open results"),
                    "action_kind": "navigate",
                    "action_target": item.result_history_href,
                },
            )
        item_sections.append(
            {
                "workspace_id": item.workspace_id,
                "title": item.title,
                "status_label": item.status_label,
                "continue_href": item.continue_href,
                "continue_label": item.continue_label,
                "result_history_href": item.result_history_href,
                "result_history_action_label": item.result_history_action_label,
                "has_recent_result_history": item.has_recent_result_history,
                "onboarding_incomplete": item.onboarding_incomplete,
                "onboarding_step_id": item.onboarding_step_id,
                "onboarding_progress_label": item.onboarding_progress_label,
                "section": build_shell_section(
                    headline=item.status_label,
                    lines=[item.updated_label] + list(item.summary_lines),
                    detail_title=ui_text("server.library.workflow_detail", app_language=app_language, fallback_text="Workflow detail"),
                    detail_items=[
                        item.role_label,
                        item.result_history_label,
                        item.onboarding_progress_label,
                        ui_text("server.library.continue_route", app_language=app_language, fallback_text="Continue route: {href}", href=item.continue_href),
                        ui_text("server.library.result_history_route", app_language=app_language, fallback_text="Result history route: {href}", href=item.result_history_href) if item.result_history_href else None,
                    ],
                    controls=tuple(controls),
                ),
            }
        )
    return {
        "status": "ready",
        "source_of_truth": "workspace_registry",
        "library": asdict(view_model),
        "overview_section": overview,
        "item_sections": item_sections,
        "app_language": app_language,
        "routes": {"workspace_list": "/api/workspaces", "app_library": f"/app/library?app_language={app_language}"},
    }


def render_circuit_library_runtime_html(payload: Mapping[str, Any]) -> str:
    app_language = normalize_ui_language(payload.get("app_language") or "en")
    library = dict(payload.get("library") or {})
    title = escape(str(library.get("title") or ui_text("circuit_library.title", app_language=app_language, fallback_text="My workflows")))
    subtitle = escape(str(library.get("subtitle") or ui_text("circuit_library.subtitle", app_language=app_language, fallback_text="Continue a saved workflow without reopening files.")))
    empty_title = escape(str(library.get("empty_title") or ui_text("circuit_library.empty.title", app_language=app_language, fallback_text="No workflows yet")))
    empty_summary = escape(str(library.get("empty_summary") or ui_text("circuit_library.empty.summary", app_language=app_language, fallback_text="Create your first workflow to see it here.")))
    item_sections = list(payload.get("item_sections") or [])
    raw_registry_href = escape(str((payload.get("routes") or {}).get("workspace_list") or "/api/workspaces"))
    raw_registry_label = escape(ui_text("server.library.open_raw_registry", app_language=app_language, fallback_text="Open raw workspace registry"))
    raw_registry_aria = escape(ui_text("server.library.open_raw_registry_aria", app_language=app_language, fallback_text="Open raw workspace registry JSON"))
    workflow_library_aria = escape(ui_text("server.library.workflow_library_aria", app_language=app_language, fallback_text="Workflow library"))

    def _render_lines(lines: Sequence[str]) -> str:
        if not lines:
            return ""
        return "".join(f"<li>{escape(str(line))}</li>" for line in lines if str(line).strip())

    cards_html = ""
    for item in item_sections:
        section = dict(item.get("section") or {})
        summary = dict(section.get("summary") or {})
        detail = dict(section.get("detail") or {})
        continue_href = escape(str(item.get("continue_href") or "#"))
        continue_label = escape(str(item.get("continue_label") or ui_text("circuit_library.action.continue", app_language=app_language, fallback_text="Continue")))
        status_label = escape(str(item.get("status_label") or ""))
        title_text = escape(str(item.get("title") or item.get("workspace_id") or ui_text("server.library.workflow_fallback", app_language=app_language, fallback_text="Workflow")))
        result_history_href = escape(str(item.get("result_history_href") or ""))
        result_history_label = escape(str(item.get("result_history_action_label") or ui_text("server.library.open_results", app_language=app_language, fallback_text="Open results")))
        detail_title = escape(str(detail.get("title") or ui_text("server.library.workflow_detail", app_language=app_language, fallback_text="Workflow detail")))
        status_aria = escape(ui_text("server.library.workflow_status_aria", app_language=app_language, fallback_text="Workflow status {status}", status=status_label))
        control_html = ""
        if result_history_href:
            control_html += f'<a class="action-link secondary" href="{result_history_href}">{result_history_label}</a>'
        control_html += f'<a class="action-link" href="{continue_href}">{continue_label}</a>'
        cards_html += f"""
        <article class="workflow-card" aria-labelledby="workflow-title-{escape(str(item.get('workspace_id') or 'workflow'))}">
          <div class="workflow-card-head">
            <h2 id="workflow-title-{escape(str(item.get('workspace_id') or 'workflow'))}">{title_text}</h2>
            <span class="status-badge" aria-label="{status_aria}">{status_label}</span>
          </div>
          <ul class="summary-lines">{_render_lines(summary.get('lines') or [])}</ul>
          <details>
            <summary>{detail_title}</summary>
            <ul class="detail-lines">{_render_lines(detail.get('items') or [])}</ul>
          </details>
          <div class="actions">{control_html}</div>
        </article>
        """
    if not cards_html:
        cards_html = f"""
        <article class="workflow-card empty">
          <h2>{empty_title}</h2>
          <p>{empty_summary}</p>
        </article>
        """

    return f"""<!doctype html>
<html lang="{app_language}">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>{title}</title>
    <style>
      body {{ font-family: Arial, sans-serif; margin: 0; background: #0b1220; color: #e5e7eb; }}
      main {{ max-width: 960px; margin: 0 auto; padding: 24px; }}
      header {{ margin-bottom: 24px; }}
      h1 {{ margin: 0 0 8px; font-size: 2rem; }}
      p {{ margin: 0; color: #cbd5e1; }}
      .workflow-grid {{ display: grid; gap: 16px; }}
      .workflow-card {{ background: #111827; border: 1px solid #334155; border-radius: 16px; padding: 16px; }}
      .workflow-card-head {{ display: flex; justify-content: space-between; gap: 12px; align-items: center; }}
      .status-badge {{ background: #1f2937; border: 1px solid #475569; border-radius: 999px; padding: 4px 10px; font-size: 0.875rem; }}
      .summary-lines, .detail-lines {{ margin: 12px 0 0; padding-left: 18px; }}
      .actions {{ margin-top: 16px; }}
      .action-link {{ display: inline-block; padding: 10px 14px; border-radius: 10px; background: #2563eb; color: white; text-decoration: none; }}
      .action-link.secondary {{ background: #1f2937; border: 1px solid #475569; margin-right: 8px; }}
      a.top-link {{ color: #93c5fd; text-decoration: none; }}
      details summary {{ cursor: pointer; margin-top: 12px; }}
    </style>
  </head>
  <body>
    <main role="main" aria-labelledby="library-title">
      <header aria-labelledby="library-title">
        <a class="top-link" href="{raw_registry_href}" aria-label="{raw_registry_aria}">{raw_registry_label}</a>
        <h1 id="library-title">{title}</h1>
        <p>{subtitle}</p>
      </header>
      <section class="workflow-grid" aria-label="{workflow_library_aria}">{cards_html}</section>
    </main>
  </body>
</html>
"""
