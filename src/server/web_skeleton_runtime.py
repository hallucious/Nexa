from __future__ import annotations

from html import escape
import json
from typing import Any, Mapping, Sequence

from src.ui.i18n import normalize_ui_language, ui_text
from src.server.contract_review_slice_runtime import contract_review_run_input_handoff_payload, contract_review_slice_payload


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
          <a class="button secondary" href="/app/workspaces/{escape(workspace_id)}/run?app_language={escape(app_language)}&amp;use_case=contract_review">Contract review</a>
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
    contract_review = contract_review_slice_payload(workspace_id=workspace_id, app_language=app_language)
    accepted_file_types = ", ".join(str(item) for item in contract_review['accepted_file_types'])
    output_contract = ", ".join(str(item) for item in contract_review['output_contract'])
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
      <section
        id="upload-status-panel"
        class="card"
        aria-label="Upload status panel"
        data-presign-path="/api/workspaces/{escape(workspace_id)}/uploads/presign"
        data-confirm-template="/api/workspaces/{escape(workspace_id)}/uploads/{{upload_id}}/confirm"
        data-status-template="/api/workspaces/{escape(workspace_id)}/uploads/{{upload_id}}"
      >
        <h2>{escape(ui_text("web.upload.status.title", app_language=app_language, fallback_text="Upload safety gate"))}</h2>
        <p id="upload-gate-summary">{escape(ui_text("web.upload.gate.summary", app_language=app_language, fallback_text="Run remains gated until the upload status is safe."))}</p>
        <ul>
          <li><code>filename</code>, <code>declared_mime_type</code>, and <code>declared_size_bytes</code> are sent to presign.</li>
          <li><code>observed_size_bytes</code>, <code>observed_mime_type</code>, and scan state are sent to confirm.</li>
          <li>The run entry remains gated while status is uploading, scanning, quarantine, or rejected.</li>
        </ul>
        <pre id="upload-status-output" aria-live="polite">{escape(ui_text("web.upload.status.pending", app_language=app_language, fallback_text="No upload status yet."))}</pre>
      </section>
      <section
        id="contract-review-upload-readiness"
        class="card"
        aria-label="Contract review upload readiness"
        data-template-id="{escape(str(contract_review['template_id']))}"
        data-use-case="contract_review"
        data-required-upload-state="{escape(str(contract_review['required_upload_state']))}"
        data-accepted-file-types="{escape(accepted_file_types)}"
        data-output-contract="{escape(output_contract)}"
      >
        <h2>Contract review starter path</h2>
        <p>{escape(str(contract_review['summary']))}</p>
        <p>Accepted files: <strong>{escape(accepted_file_types)}</strong>. Run remains gated until upload status is <code>{escape(str(contract_review['required_upload_state']))}</code>.</p>
      </section>

      <div class="actions">
        <a class="button" href="/app/workspaces/{escape(workspace_id)}?app_language={escape(app_language)}">Back to workspace</a>
        <a id="upload-run-gate" class="button secondary" aria-disabled="true" data-requires-upload-status="safe" href="/app/workspaces/{escape(workspace_id)}/run?app_language={escape(app_language)}">Continue to run</a>
      </div>

    </section>
"""
    return _html_page(title=title, app_language=app_language, body=body)


def render_web_run_entry_html(
    *,
    workspace_id: str,
    workspace_row: Mapping[str, Any] | None = None,
    app_language: str = "en",
    use_case: str | None = None,
    upload_id: str | None = None,
    upload_status: str | None = None,
    extraction_id: str | None = None,
) -> str:
    app_language = normalize_ui_language(app_language)
    workspace_title = _workspace_title(workspace_row or {"workspace_id": workspace_id})
    title = ui_text("web.run.title", app_language=app_language, fallback_text="Submit run")
    contract_review = contract_review_slice_payload(workspace_id=workspace_id, app_language=app_language)
    output_contract = ", ".join(str(item) for item in contract_review['output_contract'])
    next_actions = ", ".join(str(item) for item in contract_review['next_actions'])
    contract_review_handoff = contract_review_run_input_handoff_payload(
        workspace_id=workspace_id,
        app_language=app_language,
        upload_id=upload_id,
        upload_status=upload_status,
        extraction_id=extraction_id,
    )
    contract_review_handoff_json = json.dumps(contract_review_handoff["run_submission_payload"], ensure_ascii=False, sort_keys=True)
    contract_review_ready = "true" if contract_review_handoff["ready_for_run"] else "false"
    contract_review_blocked_reason = str(contract_review_handoff.get("blocked_reason") or "")
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
      <section
        id="contract-review-run-input-handoff"
        class="card"
        aria-label="Contract review run input handoff"
        data-use-case="contract_review"
        data-upload-id="{escape(str(contract_review_handoff.get('upload_id') or ''))}"
        data-upload-status="{escape(str(contract_review_handoff['upload_status']))}"
        data-extraction-id="{escape(str(contract_review_handoff.get('extraction_id') or ''))}"
        data-required-upload-state="{escape(str(contract_review_handoff['required_upload_state']))}"
        data-ready-for-run="{contract_review_ready}"
        data-blocked-reason="{escape(contract_review_blocked_reason)}"
      >
        <h2>Contract review input handoff</h2>
        <p>Use a safe uploaded contract as the document input for this review run.</p>
        <ul>
          <li>Upload status: <code>{escape(str(contract_review_handoff['upload_status']))}</code></li>
          <li>Required status: <code>{escape(str(contract_review_handoff['required_upload_state']))}</code></li>
          <li>Ready for run: <code>{contract_review_ready}</code></li>
        </ul>
        <pre id="contract-review-run-input-payload" aria-label="Contract review run input payload">{escape(contract_review_handoff_json)}</pre>
      </section>
      <form
        id="run-submit-form"
        class="card"
        aria-label="Run submission form"
        data-submit-path="/api/runs"
        data-upload-page-path="/app/workspaces/{escape(workspace_id)}/upload?app_language={escape(app_language)}"
        data-result-history-path="/app/workspaces/{escape(workspace_id)}/results?app_language={escape(app_language)}"
      >
        <h2>{escape(ui_text("web.run.submit.title", app_language=app_language, fallback_text="Submit run"))}</h2>
        <p>{escape(ui_text("web.run.submit.summary", app_language=app_language, fallback_text="Submit only after the current workspace draft and any required uploads are ready."))}</p>
        <pre id="run-submit-payload-example" aria-label="Run submit payload example">{{&quot;workspace_id&quot;:&quot;{escape(workspace_id)}&quot;,&quot;launch_source&quot;:&quot;web_skeleton&quot;}}</pre>
      </form>
      <section
        id="run-progress-panel"
        class="card"
        aria-label="Run progress panel"
        data-workspace-runs-path="/api/workspaces/{escape(workspace_id)}/runs"
        data-run-status-template="/api/runs/{{run_id}}"
        data-run-actions-template="/api/runs/{{run_id}}/actions"
      >
        <h2>{escape(ui_text("web.run.progress.title", app_language=app_language, fallback_text="Run progress"))}</h2>
        <p>{escape(ui_text("web.run.progress.summary", app_language=app_language, fallback_text="After submission, poll run status and available actions before opening the result."))}</p>
      </section>
      <section
        id="run-result-handoff-panel"
        class="card"
        aria-label="Run result handoff panel"
        data-run-result-template="/api/runs/{{run_id}}/result"
        data-result-history-path="/app/workspaces/{escape(workspace_id)}/results?app_language={escape(app_language)}"
        data-shell-draft-path="/api/workspaces/{escape(workspace_id)}/shell/draft"
      >
        <h2>{escape(ui_text("web.run.result_handoff.title", app_language=app_language, fallback_text="Result handoff"))}</h2>
        <p>{escape(ui_text("web.run.result_handoff.summary", app_language=app_language, fallback_text="Open the result page, read the selected output, then mark the first result as read through UI-owned Working Save metadata."))}</p>
      </section>
      <section
        id="contract-review-vertical-slice"
        class="card"
        aria-label="Contract review vertical slice"
        data-template-id="{escape(str(contract_review['template_id']))}"
        data-run-intent="{escape(str(contract_review['run_intent']))}"
        data-default-model-tier="{escape(str(contract_review['default_model_tier']))}"
        data-source-reference-mode="{escape(str(contract_review['source_reference_mode']))}"
        data-output-contract="{escape(output_contract)}"
        data-next-actions="{escape(next_actions)}"
      >
        <h2>Contract review run path</h2>
        <p>{escape(str(contract_review['summary']))}</p>
        <ol>
          <li>Use only uploads whose status is <code>{escape(str(contract_review['required_upload_state']))}</code>.</li>
          <li>Run intent: <code>{escape(str(contract_review['run_intent']))}</code> on the <code>{escape(str(contract_review['default_model_tier']))}</code> model tier.</li>
          <li>Return structured clauses, explanations, questions, and <code>{escape(str(contract_review['source_reference_mode']))}</code>.</li>
        </ol>
      </section>

      <div id="result-screen-minimum" class="card">
        <h2>{escape(ui_text("web.result.minimum.title", app_language=app_language, fallback_text="Result screen minimum"))}</h2>
        <p>{escape(ui_text("web.result.minimum.summary", app_language=app_language, fallback_text="The result page must show completed, running, failed, and empty states without exposing raw internals."))}</p>
      </div>
      <div class="actions">
        <a class="button" href="/app/workspaces/{escape(workspace_id)}/results?app_language={escape(app_language)}">Open results</a>
        <a class="button secondary" href="/app/workspaces/{escape(workspace_id)}/upload?app_language={escape(app_language)}">Back to upload safety gate</a>
        <a class="button secondary" href="/app/workspaces/{escape(workspace_id)}?app_language={escape(app_language)}">Back to workspace</a>
      </div>
    </section>
"""
    return _html_page(title=title, app_language=app_language, body=body)
