from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import asdict
from html import escape
from typing import Any

from src.ui.i18n import normalize_ui_language, ui_text
from src.ui.feedback_channel import read_feedback_channel_view_model

_ALLOWED_CATEGORIES = {"confusing_screen", "friction_note", "bug_report"}
_ALLOWED_SURFACES = {"circuit_library", "result_history", "workspace_shell", "unknown"}


def _normalized_prefill(value: object | None, *, allowed: set[str], default: str) -> str:
    normalized = str(value or "").strip().lower()
    return normalized if normalized in allowed else default


def build_workspace_feedback_payload(
    *,
    workspace_id: str,
    workspace_title: str,
    feedback_rows: Sequence[Mapping[str, object]] = (),
    current_user_id: str | None = None,
    app_language: str = "en",
    prefill_category: str | None = None,
    prefill_surface: str | None = None,
    prefill_run_id: str | None = None,
    confirmation_feedback_id: str | None = None,
) -> dict[str, Any]:
    app_language = normalize_ui_language(app_language)
    view_model = read_feedback_channel_view_model(
        workspace_id=workspace_id,
        workspace_title=workspace_title,
        feedback_rows=feedback_rows,
        current_user_id=current_user_id,
        app_language=app_language,
        prefill_category=_normalized_prefill(prefill_category, allowed=_ALLOWED_CATEGORIES, default="friction_note"),
        prefill_surface=_normalized_prefill(prefill_surface, allowed=_ALLOWED_SURFACES, default="unknown"),
        prefill_run_id=str(prefill_run_id or "").strip() or None,
        confirmation_feedback_id=confirmation_feedback_id,
    )
    return {
        "status": "ready",
        "app_language": app_language,
        "workspace_id": workspace_id,
        "workspace_title": workspace_title,
        "feedback_channel": asdict(view_model),
        "routes": {
            "submit": f"/api/workspaces/{workspace_id}/feedback?app_language={app_language}",
            "feedback_page": f"/app/workspaces/{workspace_id}/feedback?app_language={app_language}",
            "workspace_page": f"/app/workspaces/{workspace_id}?app_language={app_language}",
            "result_history": f"/app/workspaces/{workspace_id}/results?app_language={app_language}",
            "library": f"/app/library?app_language={app_language}",
            "workspace_library": f"/app/workspaces/{workspace_id}/library?app_language={app_language}",
            "starter_template_catalog_page": f"/app/workspaces/{workspace_id}/starter-templates?app_language={app_language}",
        },
    }


def build_feedback_submission_payload(*, row: Mapping[str, object], workspace_title: str, app_language: str = "en") -> dict[str, Any]:
    app_language = normalize_ui_language(app_language)
    category = str(row.get("category") or "friction_note").strip().lower()
    surface = str(row.get("surface") or "unknown").strip().lower() or "unknown"
    category_label = ui_text(f"feedback.category.{category}", app_language=app_language, fallback_text=category.replace("_", " ").title())
    surface_label = ui_text(f"feedback.surface.{surface}", app_language=app_language, fallback_text=surface.replace("_", " ").title())
    workspace_id = str(row.get("workspace_id") or "").strip()
    return {
        "status": "accepted",
        "message": ui_text("server.feedback.message_recorded", app_language=app_language, fallback_text="Feedback recorded for product learning."),
        "workspace_id": workspace_id,
        "feedback": {
            "feedback_id": str(row.get("feedback_id") or ""),
            "workspace_id": workspace_id,
            "workspace_title": workspace_title,
            "category": category,
            "category_label": category_label,
            "surface": surface,
            "surface_label": surface_label,
            "message": str(row.get("message") or "").strip(),
            "run_id": str(row.get("run_id") or "").strip() or None,
            "status": str(row.get("status") or "received").strip() or "received",
            "created_at": str(row.get("created_at") or "").strip(),
        },
        "links": {
            "feedback_page": f"/app/workspaces/{workspace_id}/feedback?app_language={app_language}",
            "workspace_page": f"/app/workspaces/{workspace_id}?app_language={app_language}",
            "result_history": f"/app/workspaces/{workspace_id}/results?app_language={app_language}",
            "library": f"/app/library?app_language={app_language}",
            "workspace_library": f"/app/workspaces/{workspace_id}/library?app_language={app_language}",
            "starter_template_catalog_page": f"/app/workspaces/{workspace_id}/starter-templates?app_language={app_language}",
        },
    }


def render_workspace_feedback_html(payload: Mapping[str, Any]) -> str:
    channel = dict(payload.get("feedback_channel") or {})
    app_language = normalize_ui_language(payload.get("app_language") or "en")
    workspace_title = escape(str(payload.get("workspace_title") or channel.get("workspace_title") or ui_text("server.feedback.workflow_fallback", app_language=app_language, fallback_text="Workflow")))
    title = escape(str(channel.get("title") or ui_text("feedback.title", app_language=app_language, fallback_text="Feedback")))
    subtitle = escape(str(channel.get("subtitle") or ""))
    submit_path = escape(str(channel.get("submit_path") or "#"))
    prefill_category = escape(str(channel.get("prefill_category") or "friction_note"))
    prefill_surface = escape(str(channel.get("prefill_surface") or "unknown"))
    prefill_run_id = escape(str(channel.get("prefill_run_id") or ""))
    options = list(channel.get("options") or [])
    items = list(channel.get("items") or [])
    empty_title = escape(str(channel.get("empty_title") or ui_text("server.feedback.empty_title", app_language=app_language, fallback_text="No feedback sent yet")))
    empty_summary = escape(str(channel.get("empty_summary") or ""))
    confirmation_title = escape(str(channel.get("confirmation_title") or ""))
    confirmation_summary = escape(str(channel.get("confirmation_summary") or ""))
    route_map = dict(payload.get("routes") or {})
    library_href = escape(str(route_map.get("workspace_library") or route_map.get("library") or "/app/library"))
    starter_templates_href = escape(str(route_map.get("starter_template_catalog_page") or "#"))
    back_to_library_label = escape(ui_text("server.feedback.back_to_library", app_language=app_language, fallback_text="Back to library"))
    open_starter_templates_label = escape(ui_text("server.feedback.open_starter_templates", app_language=app_language, fallback_text="Open starter templates"))
    open_workflow_label = escape(ui_text("server.feedback.open_workflow", app_language=app_language, fallback_text="Open workflow"))
    open_results_label = escape(ui_text("server.feedback.open_results", app_language=app_language, fallback_text="Open results"))
    form_title = escape(ui_text("server.feedback.form_title", app_language=app_language, fallback_text="Send a quick product note"))
    category_label = escape(ui_text("server.feedback.category_label", app_language=app_language, fallback_text="Feedback type"))
    surface_label = escape(ui_text("server.feedback.surface_label", app_language=app_language, fallback_text="Screen"))
    run_id_label = escape(ui_text("server.feedback.run_id_label", app_language=app_language, fallback_text="Run id (optional)"))
    run_id_placeholder = escape(ui_text("server.feedback.run_id_placeholder", app_language=app_language, fallback_text="run-001"))
    message_label = escape(ui_text("server.feedback.message_label", app_language=app_language, fallback_text="What happened?"))
    message_placeholder = escape(ui_text("server.feedback.message_placeholder", app_language=app_language, fallback_text="Tell us what felt confusing, slow, or broken."))
    submit_label = escape(ui_text("server.feedback.submit", app_language=app_language, fallback_text="Send feedback"))
    recent_title = escape(ui_text("server.feedback.recent_title", app_language=app_language, fallback_text="Recent feedback from this workflow"))
    sending_text = escape(ui_text("server.feedback.sending", app_language=app_language, fallback_text="Sending feedback…"))
    submit_failed_text = escape(ui_text("server.feedback.submit_failed", app_language=app_language, fallback_text="Could not submit feedback right now."))
    submit_recorded_text = escape(ui_text("server.feedback.submit_recorded", app_language=app_language, fallback_text="Feedback recorded."))
    workspace_href = escape(str(route_map.get("workspace_page") or "#"))
    result_history_href = escape(str(route_map.get("result_history") or "#"))
    option_fallback_label = ui_text("server.feedback.option_fallback", app_language=app_language, fallback_text="Option")
    options_html = "".join(
        f'<button type="button" class="option" data-category="{escape(str(option.get("category_key") or "friction_note"))}"><strong>{escape(str(option.get("title") or option_fallback_label))}</strong><span>{escape(str(option.get("summary") or ""))}</span></button>'
        for option in options
    )
    items_html = "".join(
        f'<article class="feedback-item"><div class="meta"><span class="badge">{escape(str(item.get("category_label") or ""))}</span><span>{escape(str(item.get("surface_label") or ""))}</span><span>{escape(str(item.get("created_at_label") or ""))}</span></div><p>{escape(str(item.get("message") or ""))}</p></article>'
        for item in items
    )
    if not items_html:
        items_html = f'<article class="feedback-item empty"><h2>{empty_title}</h2><p>{empty_summary}</p></article>'
    confirmation_html = ""
    confirmation_region_label = escape(ui_text("server.feedback.confirmation_region", app_language=app_language, fallback_text="Feedback confirmation"))
    if confirmation_title or confirmation_summary:
        confirmation_html = f'<section class="confirmation" role="region" aria-labelledby="feedback-confirmation-title" aria-label="{confirmation_region_label}"><h2 id="feedback-confirmation-title">{confirmation_title}</h2><p>{confirmation_summary}</p></section>'
    return f"""<!doctype html>
<html lang="{app_language}">
  <head>
    <meta charset=\"utf-8\" />
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
    <title>{title}</title>
    <style>
      body {{ font-family: Arial, sans-serif; margin: 0; background: #0b1220; color: #e5e7eb; }}
      main {{ max-width: 1040px; margin: 0 auto; padding: 24px; }}
      header, .form-card, .feedback-item, .confirmation {{ background: #111827; border: 1px solid #334155; border-radius: 16px; padding: 16px; margin-bottom: 16px; }}
      .confirmation {{ border-color: #2563eb; }}
      .nav-links, .actions, .option-grid {{ display: flex; gap: 12px; flex-wrap: wrap; }}
      .nav-links a, .actions a, .actions button {{ display: inline-block; padding: 10px 14px; border-radius: 10px; background: #2563eb; color: white; text-decoration: none; border: 0; cursor: pointer; }}
      .nav-links a.secondary, .actions a.secondary {{ background: #1f2937; border: 1px solid #475569; }}
      .option {{ width: 100%; text-align: left; padding: 14px; border-radius: 12px; background: #0f172a; border: 1px solid #334155; color: #e5e7eb; cursor: pointer; display: flex; flex-direction: column; gap: 6px; }}
      label {{ display: block; margin: 12px 0 6px; font-weight: 600; }}
      input, select, textarea {{ width: 100%; box-sizing: border-box; border-radius: 10px; border: 1px solid #475569; background: #0f172a; color: #e5e7eb; padding: 10px; }}
      textarea {{ min-height: 120px; }}
      .meta {{ display: flex; gap: 10px; flex-wrap: wrap; color: #cbd5e1; font-size: 0.875rem; }}
      .badge {{ background: #1f2937; border: 1px solid #475569; border-radius: 999px; padding: 4px 10px; }}
      .status {{ margin-top: 12px; color: #93c5fd; min-height: 1.2em; }}
    </style>
  </head>
  <body>
    <main role="main" aria-labelledby="feedback-title">
      <header aria-labelledby="feedback-title">
        <h1 id="feedback-title">{title}</h1>
        <p>{subtitle}</p>
        <p>{escape(ui_text("server.feedback.workflow_label", app_language=app_language, fallback_text="Workflow: {workspace}", workspace=workspace_title))}</p>
        <div class=\"nav-links\">
          <a class=\"secondary\" href=\"{library_href}\">{back_to_library_label}</a>
          <a class=\"secondary\" href=\"{workspace_href}\">{open_workflow_label}</a>
          <a class=\"secondary\" href=\"{result_history_href}\">{open_results_label}</a>
          <a class=\"secondary\" href=\"{starter_templates_href}\">{open_starter_templates_label}</a>
        </div>
      </header>
      {confirmation_html}
      <section class=\"form-card\" role=\"region\" aria-labelledby=\"feedback-form-title\">
        <h2 id="feedback-form-title">{form_title}</h2>
        <div class=\"option-grid\">{options_html}</div>
        <form id=\"feedback-form\" aria-describedby=\"feedback-status\">
          <label for=\"category\">{category_label}</label>
          <select id=\"category\" name=\"category\">
            <option value=\"confusing_screen\">{escape(ui_text("feedback.category.confusing_screen", app_language=app_language, fallback_text="Report confusing screen"))}</option>
            <option value=\"friction_note\">{escape(ui_text("feedback.category.friction_note", app_language=app_language, fallback_text="Quick friction note"))}</option>
            <option value=\"bug_report\">{escape(ui_text("feedback.category.bug_report", app_language=app_language, fallback_text="Bug report shortcut"))}</option>
          </select>
          <label for=\"surface\">{surface_label}</label>
          <select id=\"surface\" name=\"surface\">
            <option value=\"circuit_library\">{escape(ui_text("feedback.surface.circuit_library", app_language=app_language, fallback_text="Library"))}</option>
            <option value=\"result_history\">{escape(ui_text("feedback.surface.result_history", app_language=app_language, fallback_text="Result history"))}</option>
            <option value=\"workspace_shell\">{escape(ui_text("feedback.surface.workspace_shell", app_language=app_language, fallback_text="Workflow"))}</option>
            <option value=\"unknown\">{escape(ui_text("feedback.surface.unknown", app_language=app_language, fallback_text="Current screen"))}</option>
          </select>
          <label for=\"run_id\">{run_id_label}</label>
          <input id=\"run_id\" name=\"run_id\" value=\"{prefill_run_id}\" placeholder=\"{run_id_placeholder}\" />
          <label for=\"message\">{message_label}</label>
          <textarea id=\"message\" name=\"message\" placeholder=\"{message_placeholder}\"></textarea>
          <div class=\"actions\">
            <button type=\"submit\">{submit_label}</button>
          </div>
          <div class=\"status\" id=\"feedback-status\" aria-live=\"polite\"></div>
        </form>
      </section>
      <section role="region" aria-labelledby="recent-feedback-title" aria-label="{escape(ui_text('server.feedback.recent_region', app_language=app_language, fallback_text='Recent feedback'))}">
        <h2 id="recent-feedback-title">{recent_title}</h2>
        {items_html}
      </section>
    </main>
    <script>
      const form = document.getElementById('feedback-form');
      const statusEl = document.getElementById('feedback-status');
      const categoryEl = document.getElementById('category');
      const surfaceEl = document.getElementById('surface');
      const runIdEl = document.getElementById('run_id');
      categoryEl.value = {prefill_category!r};
      surfaceEl.value = {prefill_surface!r};
      document.querySelectorAll('.option').forEach((button) => {{
        button.addEventListener('click', () => {{
          categoryEl.value = button.getAttribute('data-category') || 'friction_note';
        }});
      }});
      form.addEventListener('submit', async (event) => {{
        event.preventDefault();
        statusEl.textContent = {sending_text!r};
        const payload = {{
          category: categoryEl.value,
          surface: surfaceEl.value,
          run_id: runIdEl.value || null,
          message: document.getElementById('message').value,
        }};
        const response = await fetch({submit_path!r}, {{
          method: 'POST',
          headers: {{ 'Content-Type': 'application/json' }},
          body: JSON.stringify(payload),
        }});
        const data = await response.json();
        if (!response.ok) {{
          statusEl.textContent = data.message || {submit_failed_text!r};
          return;
        }}
        statusEl.textContent = data.message || {submit_recorded_text!r};
        window.location.search = new URLSearchParams({{ category: categoryEl.value, surface: surfaceEl.value, run_id: runIdEl.value || '', feedback_id: data.feedback.feedback_id }}).toString();
      }});
    </script>
  </body>
</html>"""
