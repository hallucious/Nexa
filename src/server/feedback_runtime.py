from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import asdict
from html import escape
from typing import Any

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
        "workspace_id": workspace_id,
        "workspace_title": workspace_title,
        "feedback_channel": asdict(view_model),
        "routes": {
            "submit": f"/api/workspaces/{workspace_id}/feedback",
            "feedback_page": f"/app/workspaces/{workspace_id}/feedback",
            "workspace_page": f"/app/workspaces/{workspace_id}",
            "result_history": f"/app/workspaces/{workspace_id}/results",
            "library": "/app/library",
        },
    }


def build_feedback_submission_payload(*, row: Mapping[str, object], workspace_title: str, app_language: str = "en") -> dict[str, Any]:
    category = str(row.get("category") or "friction_note").strip().lower()
    surface = str(row.get("surface") or "unknown").strip().lower() or "unknown"
    category_label = {
        "confusing_screen": "Report confusing screen",
        "friction_note": "Quick friction note",
        "bug_report": "Bug report shortcut",
    }.get(category, category.replace("_", " ").title())
    surface_label = {
        "circuit_library": "Library",
        "result_history": "Result history",
        "workspace_shell": "Workflow",
        "unknown": "Current screen",
    }.get(surface, surface.replace("_", " ").title())
    workspace_id = str(row.get("workspace_id") or "").strip()
    return {
        "status": "accepted",
        "message": "Feedback recorded for product learning.",
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
            "feedback_page": f"/app/workspaces/{workspace_id}/feedback",
            "workspace_page": f"/app/workspaces/{workspace_id}",
            "result_history": f"/app/workspaces/{workspace_id}/results",
            "library": "/app/library",
        },
    }


def render_workspace_feedback_html(payload: Mapping[str, Any]) -> str:
    channel = dict(payload.get("feedback_channel") or {})
    workspace_title = escape(str(payload.get("workspace_title") or channel.get("workspace_title") or "Workflow"))
    title = escape(str(channel.get("title") or "Feedback"))
    subtitle = escape(str(channel.get("subtitle") or ""))
    submit_path = escape(str(channel.get("submit_path") or "#"))
    prefill_category = escape(str(channel.get("prefill_category") or "friction_note"))
    prefill_surface = escape(str(channel.get("prefill_surface") or "unknown"))
    prefill_run_id = escape(str(channel.get("prefill_run_id") or ""))
    options = list(channel.get("options") or [])
    items = list(channel.get("items") or [])
    empty_title = escape(str(channel.get("empty_title") or "No feedback sent yet"))
    empty_summary = escape(str(channel.get("empty_summary") or ""))
    confirmation_title = escape(str(channel.get("confirmation_title") or ""))
    confirmation_summary = escape(str(channel.get("confirmation_summary") or ""))
    library_href = escape(str((payload.get("routes") or {}).get("library") or "/app/library"))
    workspace_href = escape(str((payload.get("routes") or {}).get("workspace_page") or "#"))
    result_history_href = escape(str((payload.get("routes") or {}).get("result_history") or "#"))
    options_html = "".join(
        f'<button type="button" class="option" data-category="{escape(str(option.get("category_key") or "friction_note"))}"><strong>{escape(str(option.get("title") or "Option"))}</strong><span>{escape(str(option.get("summary") or ""))}</span></button>'
        for option in options
    )
    items_html = "".join(
        f'<article class="feedback-item"><div class="meta"><span class="badge">{escape(str(item.get("category_label") or ""))}</span><span>{escape(str(item.get("surface_label") or ""))}</span><span>{escape(str(item.get("created_at_label") or ""))}</span></div><p>{escape(str(item.get("message") or ""))}</p></article>'
        for item in items
    )
    if not items_html:
        items_html = f'<article class="feedback-item empty"><h2>{empty_title}</h2><p>{empty_summary}</p></article>'
    confirmation_html = ""
    if confirmation_title or confirmation_summary:
        confirmation_html = f'<section class="confirmation"><h2>{confirmation_title}</h2><p>{confirmation_summary}</p></section>'
    return f"""<!doctype html>
<html lang=\"en\">
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
    <main>
      <header>
        <h1>{title}</h1>
        <p>{subtitle}</p>
        <p>Workflow: {workspace_title}</p>
        <div class=\"nav-links\">
          <a class=\"secondary\" href=\"{library_href}\">Back to library</a>
          <a class=\"secondary\" href=\"{workspace_href}\">Open workflow</a>
          <a class=\"secondary\" href=\"{result_history_href}\">Open results</a>
        </div>
      </header>
      {confirmation_html}
      <section class=\"form-card\">
        <h2>Send a quick product note</h2>
        <div class=\"option-grid\">{options_html}</div>
        <form id=\"feedback-form\">
          <label for=\"category\">Feedback type</label>
          <select id=\"category\" name=\"category\">
            <option value=\"confusing_screen\">Report confusing screen</option>
            <option value=\"friction_note\">Quick friction note</option>
            <option value=\"bug_report\">Bug report shortcut</option>
          </select>
          <label for=\"surface\">Screen</label>
          <select id=\"surface\" name=\"surface\">
            <option value=\"circuit_library\">Library</option>
            <option value=\"result_history\">Result history</option>
            <option value=\"workspace_shell\">Workflow</option>
            <option value=\"unknown\">Current screen</option>
          </select>
          <label for=\"run_id\">Run id (optional)</label>
          <input id=\"run_id\" name=\"run_id\" value=\"{prefill_run_id}\" placeholder=\"run-001\" />
          <label for=\"message\">What happened?</label>
          <textarea id=\"message\" name=\"message\" placeholder=\"Tell us what felt confusing, slow, or broken.\"></textarea>
          <div class=\"actions\">
            <button type=\"submit\">Send feedback</button>
          </div>
          <div class=\"status\" id=\"feedback-status\"></div>
        </form>
      </section>
      <section>
        <h2>Recent feedback from this workflow</h2>
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
        statusEl.textContent = 'Sending feedback…';
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
          statusEl.textContent = data.message || 'Feedback could not be recorded.';
          return;
        }}
        statusEl.textContent = data.message || 'Feedback recorded.';
        window.location.search = new URLSearchParams({{ category: categoryEl.value, surface: surfaceEl.value, run_id: runIdEl.value || '', feedback_id: data.feedback.feedback_id }}).toString();
      }});
    </script>
  </body>
</html>"""
