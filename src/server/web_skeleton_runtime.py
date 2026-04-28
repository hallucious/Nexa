from __future__ import annotations

from html import escape
from typing import Any, Mapping, Sequence

from src.ui.i18n import normalize_ui_language, ui_text


def _workspace_title(row: Mapping[str, Any]) -> str:
    return str(row.get("title") or row.get("workspace_id") or "Workspace").strip() or "Workspace"


def _workspace_id(row: Mapping[str, Any]) -> str:
    return str(row.get("workspace_id") or "").strip()


def _html_page(*, title: str, app_language: str, body: str) -> str:
    app_language = normalize_ui_language(app_language)
    return f"""<!doctype html>
<html lang="{escape(app_language)}">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{escape(title)}</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 0; padding: 24px; background: #f7f7f8; color: #111827; }}
    main {{ max-width: 960px; margin: 0 auto; background: white; border-radius: 16px; padding: 24px; box-shadow: 0 10px 30px rgba(0,0,0,0.08); }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 16px; }}
    .card {{ border: 1px solid #e5e7eb; border-radius: 12px; padding: 16px; background: #fff; }}
    .actions {{ display: flex; gap: 10px; flex-wrap: wrap; margin-top: 12px; }}
    a.button {{ display: inline-block; border-radius: 10px; padding: 10px 14px; text-decoration: none; background: #111827; color: white; }}
    a.secondary {{ background: #374151; }}
    code {{ background: #f3f4f6; padding: 2px 6px; border-radius: 6px; }}
    ol, ul {{ padding-left: 22px; }}
  </style>
</head>
<body>
  <main id="nexa-web-skeleton" role="main">
{body}
  </main>
</body>
</html>"""


def render_web_sign_in_html(*, app_language: str = "en") -> str:
    app_language = normalize_ui_language(app_language)
    title = ui_text("web.sign_in.title", app_language=app_language, fallback_text="Sign in to Nexa")
    body = f"""
    <h1>{escape(title)}</h1>
    <section id="access-boundary" class="card" aria-label="Access boundary">
      <p>{escape(ui_text("web.sign_in.summary", app_language=app_language, fallback_text="Sign in before opening protected workspace pages."))}</p>
      <p><code>/app/workspaces</code></p>
    </section>
"""
    return _html_page(title=title, app_language=app_language, body=body)


def render_web_workspace_dashboard_html(
    *,
    workspace_rows: Sequence[Mapping[str, Any]],
    app_language: str = "en",
) -> str:
    app_language = normalize_ui_language(app_language)
    title = ui_text("web.dashboard.title", app_language=app_language, fallback_text="Nexa workspaces")
    cards: list[str] = []
    for row in workspace_rows:
        workspace_id = _workspace_id(row)
        if not workspace_id:
            continue
        workspace_title = _workspace_title(row)
        description = str(row.get("description") or "").strip()
        cards.append(
            f"""
      <article class="card workspace-card">
        <h2>{escape(workspace_title)}</h2>
        <p>{escape(description or ui_text("web.dashboard.workspace_default", app_language=app_language, fallback_text="Continue your first workflow."))}</p>
        <div class="actions">
          <a class="button" href="/app/workspaces/{escape(workspace_id)}?app_language={escape(app_language)}">Open workspace</a>
          <a class="button secondary" href="/app/workspaces/{escape(workspace_id)}/upload?app_language={escape(app_language)}">Upload document</a>
          <a class="button secondary" href="/app/workspaces/{escape(workspace_id)}/run?app_language={escape(app_language)}">Submit run</a>
          <a class="button secondary" href="/app/workspaces/{escape(workspace_id)}/results?app_language={escape(app_language)}">Results</a>
        </div>
      </article>
"""
        )
    if not cards:
        cards.append(
            f"""
      <article class="card empty-workspaces">
        <h2>{escape(ui_text("web.dashboard.empty.title", app_language=app_language, fallback_text="No workspaces yet"))}</h2>
        <p>{escape(ui_text("web.dashboard.empty.summary", app_language=app_language, fallback_text="Create or import a workspace before starting the first-success path."))}</p>
      </article>
"""
        )
    body = f"""
    <h1>{escape(title)}</h1>
    <p id="web-skeleton-summary">{escape(ui_text("web.dashboard.summary", app_language=app_language, fallback_text="Choose a workspace, upload a document, submit a run, then read the result."))}</p>
    <section id="workspace-dashboard" class="grid" aria-label="Workspace dashboard">
{''.join(cards)}
    </section>
"""
    return _html_page(title=title, app_language=app_language, body=body)


def render_web_upload_entry_html(
    *,
    workspace_id: str,
    workspace_row: Mapping[str, Any] | None = None,
    app_language: str = "en",
) -> str:
    app_language = normalize_ui_language(app_language)
    workspace_title = _workspace_title(workspace_row or {"workspace_id": workspace_id})
    title = ui_text("web.upload.title", app_language=app_language, fallback_text="Upload document")
    body = f"""
    <h1>{escape(title)}</h1>
    <p><strong>{escape(workspace_title)}</strong></p>
    <section id="upload-entry" class="card" aria-label="Upload entry">
      <p>{escape(ui_text("web.upload.summary", app_language=app_language, fallback_text="Upload a document, wait for scanning, then continue only when the file is safe."))}</p>
      <ol>
        <li>{escape(ui_text("web.upload.step.presign", app_language=app_language, fallback_text="Request upload permission."))} <code>POST /api/workspaces/{escape(workspace_id)}/uploads/presign</code></li>
        <li>{escape(ui_text("web.upload.step.confirm", app_language=app_language, fallback_text="Confirm uploaded bytes."))} <code>POST /api/workspaces/{escape(workspace_id)}/uploads/{{upload_id}}/confirm</code></li>
        <li>{escape(ui_text("web.upload.step.status", app_language=app_language, fallback_text="Check status: uploading, scanning, quarantine, rejected, or safe."))}</li>
      </ol>
      <div class="actions">
        <a class="button" href="/app/workspaces/{escape(workspace_id)}?app_language={escape(app_language)}">Back to workspace</a>
        <a class="button secondary" href="/app/workspaces/{escape(workspace_id)}/run?app_language={escape(app_language)}">Continue to run</a>
      </div>
    </section>
"""
    return _html_page(title=title, app_language=app_language, body=body)


def render_web_run_entry_html(
    *,
    workspace_id: str,
    workspace_row: Mapping[str, Any] | None = None,
    app_language: str = "en",
) -> str:
    app_language = normalize_ui_language(app_language)
    workspace_title = _workspace_title(workspace_row or {"workspace_id": workspace_id})
    title = ui_text("web.run.title", app_language=app_language, fallback_text="Submit run")
    body = f"""
    <h1>{escape(title)}</h1>
    <p><strong>{escape(workspace_title)}</strong></p>
    <section id="submit-run-entry" class="card" aria-label="Submit run entry">
      <p>{escape(ui_text("web.run.summary", app_language=app_language, fallback_text="Submit the run asynchronously, monitor progress, then open the result screen."))}</p>
      <ol>
        <li>{escape(ui_text("web.run.step.submit", app_language=app_language, fallback_text="Submit run."))} <code>POST /api/runs</code></li>
        <li>{escape(ui_text("web.run.step.poll", app_language=app_language, fallback_text="Poll workspace runs or run status."))} <code>/api/workspaces/{escape(workspace_id)}/runs</code></li>
        <li>{escape(ui_text("web.run.step.result", app_language=app_language, fallback_text="Read the result."))} <code>/app/workspaces/{escape(workspace_id)}/results</code></li>
      </ol>
      <div id="result-screen-minimum" class="card">
        <h2>{escape(ui_text("web.result.minimum.title", app_language=app_language, fallback_text="Result screen minimum"))}</h2>
        <p>{escape(ui_text("web.result.minimum.summary", app_language=app_language, fallback_text="The result page must show completed, running, failed, and empty states without exposing raw internals."))}</p>
      </div>
      <div class="actions">
        <a class="button" href="/app/workspaces/{escape(workspace_id)}/results?app_language={escape(app_language)}">Open results</a>
        <a class="button secondary" href="/app/workspaces/{escape(workspace_id)}?app_language={escape(app_language)}">Back to workspace</a>
      </div>
    </section>
"""
    return _html_page(title=title, app_language=app_language, body=body)
