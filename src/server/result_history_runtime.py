from __future__ import annotations

from dataclasses import asdict
from html import escape
from typing import Any, Mapping, Sequence

from src.server.contract_review_slice_runtime import contract_review_structured_result_payload
from src.server.auth_models import RunAuthorizationContext, WorkspaceAuthorizationContext
from src.server.run_list_api import RunListReadService
from src.server.run_read_api import RunResultReadService
from src.server.workspace_shell_sections import build_shell_section
from src.ui.i18n import normalize_ui_language, ui_text
from src.ui.result_history import read_result_history_view_model


def _run_context_for_row(workspace_context: WorkspaceAuthorizationContext, row: Mapping[str, Any]) -> RunAuthorizationContext | None:
    run_id = str(row.get("run_id") or "").strip()
    if not run_id:
        return None
    owner = str(row.get("requested_by_user_id") or "").strip() or None
    return RunAuthorizationContext(run_id=run_id, workspace_context=workspace_context, run_owner_user_ref=owner)




def _first_artifact_ref_for_run(run_id: str, artifact_rows_lookup: Any | None) -> str | None:
    if not run_id or artifact_rows_lookup is None:
        return None
    try:
        artifact_rows = tuple(artifact_rows_lookup(run_id) or ())
    except (TypeError, ValueError):
        return None
    for row in artifact_rows:
        artifact_id = str((row or {}).get("artifact_id") or "").strip()
        if artifact_id:
            return artifact_id
    return None


def _workspace_onboarding_state(*, request_auth, onboarding_rows: Sequence[Mapping[str, Any]], workspace_id: str) -> dict[str, Any] | None:
    user_id = str(getattr(request_auth, "requested_by_user_ref", "") or "").strip()
    if not user_id or not workspace_id:
        return None
    for row in onboarding_rows:
        if str(row.get("user_id") or "").strip() != user_id:
            continue
        if str(row.get("workspace_id") or "").strip() != workspace_id:
            continue
        return dict(row)
    return None


def build_workspace_result_history_payload(
    *,
    request_auth,
    workspace_context: WorkspaceAuthorizationContext | None,
    workspace_row: Mapping[str, Any] | None,
    run_rows: Sequence[Mapping[str, Any]] = (),
    result_rows_by_run_id: Mapping[str, Mapping[str, Any]] | None = None,
    artifact_rows_lookup=None,
    recent_run_rows: Sequence[Mapping[str, Any]] = (),
    provider_binding_rows: Sequence[Mapping[str, Any]] = (),
    managed_secret_rows: Sequence[Mapping[str, Any]] = (),
    provider_probe_rows: Sequence[Mapping[str, Any]] = (),
    onboarding_rows: Sequence[Mapping[str, Any]] = (),
    app_language: str = "en",
    selected_run_id: str | None = None,
) -> dict[str, Any] | None:
    if workspace_context is None or workspace_row is None:
        return None
    app_language = normalize_ui_language(app_language)
    list_outcome = RunListReadService.list_workspace_runs(
        request_auth=request_auth,
        workspace_context=workspace_context,
        run_rows=run_rows,
        limit=20,
        cursor=None,
        recent_run_rows=recent_run_rows,
        provider_binding_rows=provider_binding_rows,
        managed_secret_rows=managed_secret_rows,
        provider_probe_rows=provider_probe_rows,
        onboarding_rows=onboarding_rows,
    )
    if not list_outcome.ok or list_outcome.response is None:
        return None
    response = list_outcome.response
    result_map: dict[str, Any] = {}
    run_record_rows_by_id = {str(row.get("run_id") or "").strip(): row for row in run_rows}
    for row in response.runs:
        run_record_row = run_record_rows_by_id.get(row.run_id)
        context = _run_context_for_row(
            workspace_context,
            run_record_row
            or {"run_id": row.run_id, "requested_by_user_id": request_auth.requested_by_user_ref, "workspace_id": response.workspace_id},
        )
        if context is None:
            continue
        if result_rows_by_run_id is not None and row.run_id in result_rows_by_run_id:
            result_row = result_rows_by_run_id[row.run_id]
            result_outcome = RunResultReadService.read_result(
                request_auth=request_auth,
                run_context=context,
                run_record_row=run_record_row,
                result_row=result_row,
                artifact_rows=artifact_rows_lookup(row.run_id) if artifact_rows_lookup is not None else (),
                workspace_row=workspace_row,
                recent_run_rows=recent_run_rows,
                provider_binding_rows=provider_binding_rows,
                managed_secret_rows=managed_secret_rows,
                provider_probe_rows=provider_probe_rows,
                onboarding_rows=onboarding_rows,
            )
            if result_outcome.ok and result_outcome.response is not None:
                result_map[row.run_id] = result_outcome.response
    onboarding_state = _workspace_onboarding_state(
        request_auth=request_auth,
        onboarding_rows=onboarding_rows,
        workspace_id=response.workspace_id,
    )
    view_model = read_result_history_view_model(
        response,
        result_rows_by_run_id=result_map,
        app_language=app_language,
        selected_run_id=selected_run_id,
        onboarding_state=onboarding_state,
    )
    overview_lines = [view_model.subtitle or "", ui_text("server.result_history.visible_count", app_language=app_language, fallback_text="Visible results: {count}", count=view_model.returned_count)]
    if view_model.onboarding_incomplete and view_model.onboarding_summary:
        overview_lines.append(view_model.onboarding_summary)
    overview = build_shell_section(
        headline=view_model.title or "Recent results",
        lines=overview_lines,
        detail_title=ui_text("server.result_history.overview_title", app_language=app_language, fallback_text="Result history overview"),
        detail_items=[
            ui_text("server.result_history.workspace", app_language=app_language, fallback_text="Workspace: {workspace}", workspace=response.workspace_title),
            ui_text("server.result_history.source_of_truth", app_language=app_language, fallback_text="Source of truth: server-backed run history and result history"),
            ui_text("server.result_history.trace_optional", app_language=app_language, fallback_text="Trace literacy is optional on this surface"),
            ui_text("server.result_history.onboarding_projection", app_language=app_language, fallback_text="Onboarding continuity is projected from canonical server state") if view_model.onboarding_incomplete else None,
        ],
        summary_empty=ui_text("server.result_history.summary_empty", app_language=app_language, fallback_text="No recent results are visible yet."),
        detail_empty=ui_text("server.result_history.detail_empty", app_language=app_language, fallback_text="Result history detail will appear here once runs exist."),
    )
    first_artifact_ref_by_run_id = {
        item.run_id: _first_artifact_ref_for_run(item.run_id, artifact_rows_lookup)
        for item in view_model.items
    }
    item_sections = []
    for item in view_model.items:
        selected = item.run_id == view_model.selected_run_id
        detail_items = [item.timestamp_label, item.result_summary]
        if item.output_preview:
            detail_items.append(ui_text("server.result_history.latest_output_preview", app_language=app_language, fallback_text="Latest output preview: {preview}", preview=item.output_preview))
        item_sections.append(
            {
                "run_id": item.run_id,
                "workspace_id": item.workspace_id,
                "status_label": item.status_label,
                "open_result_href": item.open_result_href,
                "continue_href": item.continue_href,
                "feedback_href": f"/app/workspaces/{response.workspace_id}/feedback?surface=result_history&run_id={item.run_id}&app_language={app_language}",
                "output_key": item.output_key,
                "first_artifact_ref": first_artifact_ref_by_run_id.get(item.run_id),
                "return_use_context": item.return_use_context,
                "first_success_completion": {
                    "action_id": "mark_first_result_read",
                    "action_kind": "first_success_completion",
                    "draft_write_path": f"/api/workspaces/{response.workspace_id}/shell/draft",
                    "run_id": item.run_id,
                    "output_ref": item.output_key,
                    "artifact_ref": first_artifact_ref_by_run_id.get(item.run_id),
                },
                "section": build_shell_section(
                    headline=item.result_title,
                    lines=[item.status_label] + list(item.summary_lines),
                    detail_title=ui_text("server.result_history.result_detail", app_language=app_language, fallback_text="Result detail"),
                    detail_items=detail_items,
                    controls=(
                        {"control_id": f"open-result-{item.run_id}", "label": ui_text("server.result_history.open_result", app_language=app_language, fallback_text="Open result"), "action_kind": "navigate", "action_target": item.open_result_href},
                        {"control_id": f"continue-workflow-{item.run_id}", "label": ui_text("server.result_history.continue_workflow", app_language=app_language, fallback_text="Continue workflow"), "action_kind": "navigate", "action_target": item.continue_href},
                    ),
                ),
                "selected": selected,
            }
        )
    selected_item = next((item for item in view_model.items if item.run_id == view_model.selected_run_id), None)
    selected_result_payload = asdict(selected_item) if selected_item is not None else None
    if selected_result_payload is not None:
        selected_result_payload["first_artifact_ref"] = first_artifact_ref_by_run_id.get(str(selected_result_payload.get("run_id") or ""))
        selected_result_payload["contract_review_result"] = contract_review_structured_result_payload(
            output_key=selected_result_payload.get("output_key"),
            value_type=selected_result_payload.get("output_value_type"),
            value_preview=selected_result_payload.get("copy_output_text"),
        )
    onboarding_banner = None
    if view_model.onboarding_incomplete:
        onboarding_banner = {
            "title": view_model.onboarding_title,
            "summary": view_model.onboarding_summary,
            "action_label": view_model.onboarding_action_label,
            "action_href": view_model.onboarding_action_href,
            "current_step": view_model.onboarding_step_id,
        }
    return {
        "status": "ready",
        "workspace_id": response.workspace_id,
        "workspace_title": response.workspace_title,
        "source_of_truth": "run_history_result_history",
        "result_history": asdict(view_model),
        "overview_section": overview,
        "item_sections": item_sections,
        "selected_result": selected_result_payload,
        "onboarding_banner": onboarding_banner,
        "app_language": app_language,
        "routes": {
            "workspace_list": "/api/workspaces",
            "library": "/app/library",
            "workspace_library": f"/app/workspaces/{response.workspace_id}/library?app_language={app_language}",
            "workspace_page": f"/app/workspaces/{response.workspace_id}?app_language={app_language}",
            "api_history": f"/api/workspaces/{response.workspace_id}/result-history",
            "app_history": f"/app/workspaces/{response.workspace_id}/results?app_language={app_language}",
            "workspace_feedback_page": f"/app/workspaces/{response.workspace_id}/feedback?surface=result_history&app_language={app_language}",
            "starter_template_catalog_page": f"/app/workspaces/{response.workspace_id}/starter-templates?app_language={app_language}",
        },
    }


def render_workspace_result_history_html(payload: Mapping[str, Any]) -> str:
    app_language = normalize_ui_language(payload.get("app_language") or "en")
    history = dict(payload.get("result_history") or {})
    title = escape(str(history.get("title") or ui_text("server.result_history.title", app_language=app_language, fallback_text="Recent results")))
    subtitle = escape(str(history.get("subtitle") or ui_text("server.result_history.subtitle", app_language=app_language, fallback_text="Reopen recent results.")))
    empty_title = escape(str(history.get("empty_title") or ui_text("server.result_history.empty_title", app_language=app_language, fallback_text="No recent results yet")))
    empty_summary = escape(str(history.get("empty_summary") or ui_text("server.result_history.empty_summary", app_language=app_language, fallback_text="Run a workflow once to see recent results here.")))
    workspace_title = escape(str(payload.get("workspace_title") or history.get("workspace_title") or ui_text("server.result_history.workflow_fallback", app_language=app_language, fallback_text="Workflow")))
    item_sections = list(payload.get("item_sections") or [])
    selected = dict(payload.get("selected_result") or {})
    onboarding_banner = dict(payload.get("onboarding_banner") or {})

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
        feedback_href = escape(str(item.get("feedback_href") or ""))
        feedback_label = escape(ui_text('server.result_history.send_feedback', app_language=app_language, fallback_text='Send feedback'))
        feedback_action_html = f'<a class="action-link secondary" href="{feedback_href}">{feedback_label}</a>' if feedback_href else ''
        cards_html += f"""
        <article class="result-card{selected_class}" aria-labelledby="result-title-{escape(str(item.get('run_id') or 'result'))}" {'aria-current="true"' if item.get('selected') else ''}>
          <div class="result-card-head">
            <h2 id="result-title-{escape(str(item.get('run_id') or 'result'))}">{escape(str(summary.get('headline') or item.get('run_id') or ui_text('server.result_history.card_fallback', app_language=app_language, fallback_text='Result')))}</h2>
            <span class="status-badge" aria-label="{escape(ui_text('server.result_history.status_aria', app_language=app_language, fallback_text='Result status {status}', status=str(item.get('status_label') or '')))}">{escape(str(item.get('status_label') or ''))}</span>
          </div>
          <ul class="summary-lines">{_render_lines(summary.get('lines') or [])}</ul>
          <details {'open' if item.get('selected') else ''}>
            <summary>{escape(str(detail.get('title') or ui_text('server.result_history.result_detail', app_language=app_language, fallback_text='Result detail')))}</summary>
            <ul class="detail-lines">{_render_lines(detail.get('items') or [])}</ul>
          </details>
          <div class="actions">
            <a class="action-link secondary" href="{open_href}">{escape(ui_text('server.result_history.open_result_label', app_language=app_language, fallback_text='Open result'))}</a>
            {feedback_action_html}
            <a class="action-link" href="{continue_href}">{escape(ui_text('server.result_history.open_workflow', app_language=app_language, fallback_text='Open workflow'))}</a>
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
    contract_review_result_html = ""
    return_use_reentry_html = ""
    if selected.get("output_preview"):
        render_kind = escape(str(selected.get("result_render_kind") or "plain_text"))
        render_label = escape(str(selected.get("result_render_label") or ui_text("server.result_history.result_render_kind", app_language=app_language, fallback_text="Result format")))
        output_label = escape(str(selected.get("output_label") or ui_text("server.result_history.selected_output_title", app_language=app_language, fallback_text="Selected output")))
        output_key = escape(str(selected.get("output_key") or ""))
        copy_output = escape(str(selected.get("copy_output_text") or selected.get("output_preview") or ""), quote=True)
        continue_href = escape(str(selected.get("continue_href") or (payload.get("routes") or {}).get("workspace_page") or "#"))
        feedback_href = escape(str((payload.get("routes") or {}).get("workspace_feedback_page") or "#"))
        result_body_html = f'<pre class="plain-result">{escape(str(selected.get("output_preview") or ""))}</pre>'
        if selected.get("output_key_value_pairs"):
            pairs_html = "".join(
                f'<dt>{escape(str(pair.get("key") or ""))}</dt><dd>{escape(str(pair.get("value") or ""))}</dd>'
                for pair in selected.get("output_key_value_pairs") or []
            )
            result_body_html = f'<dl class="structured-result">{pairs_html}</dl>'
        elif selected.get("output_lines") and selected.get("result_render_kind") == "list_text":
            lines_html = "".join(f'<li>{escape(str(line))}</li>' for line in selected.get("output_lines") or [])
            result_body_html = f'<ul class="list-result">{lines_html}</ul>'
        contract_review_result = dict(selected.get("contract_review_result") or {})
        if contract_review_result:
            clause_cards = ""
            for clause in contract_review_result.get("clauses") or []:
                source = dict(clause.get("source_reference") or {})
                source_start = escape(str(source.get("start") if source.get("start") is not None else ""))
                source_end = escape(str(source.get("end") if source.get("end") is not None else ""))
                source_label = escape(str(source.get("label") or ""))
                clause_cards += (
                    '<article class="contract-review-clause" '
                    f'data-clause-id="{escape(str(clause.get("clause_id") or ""))}" '
                    f'data-risk-level="{escape(str(clause.get("risk_level") or "unknown"))}" '
                    f'data-source-start="{source_start}" data-source-end="{source_end}">'
                    f'<h3>{escape(str(clause.get("title") or "Clause"))}</h3>'
                    f'<p>{escape(str(clause.get("plain_language_explanation") or ""))}</p>'
                    f'<p class="source-reference">{escape(ui_text("server.result_history.contract_review_source", app_language=app_language, fallback_text="Source"))}: {source_start}-{source_end} {source_label}</p>'
                    '</article>'
                )
            question_items = "".join(
                f'<li>{escape(str(question))}</li>'
                for question in contract_review_result.get("pre_signature_questions") or []
            )
            contract_review_result_html = (
                '<section id="contract-review-structured-result" class="selected-output" role="region" aria-labelledby="contract-review-result-title" '
                f'data-template-id="{escape(str(contract_review_result.get("template_id") or ""))}" '
                f'data-source-reference-mode="{escape(str(contract_review_result.get("source_reference_mode") or ""))}" '
                'data-render-kind="contract_review_structured">'
                f'<h2 id="contract-review-result-title">{escape(str(contract_review_result.get("title") or ui_text("server.result_history.contract_review_title", app_language=app_language, fallback_text="Contract review result")))}</h2>'
                f'<p>{escape(str(contract_review_result.get("summary") or ""))}</p>'
                f'<div id="contract-review-clause-list">{clause_cards}</div>'
                f'<h3>{escape(ui_text("server.result_history.contract_review_questions", app_language=app_language, fallback_text="Questions before signing"))}</h3>'
                f'<ul id="contract-review-pre-signature-questions">{question_items}</ul>'
                '</section>'
            )
        selected_output_html = (
            '<section id="beginner-result-screen" class="selected-output" role="region" aria-labelledby="selected-output-title" '
            f'data-result-render-kind="{render_kind}" data-output-key="{output_key}">'
            f'<h2 id="selected-output-title">{output_label}</h2>'
            f'<p class="result-render-label">{render_label}</p>'
            f'{result_body_html}'
            '<div id="result-surface-action-panel" class="actions" aria-label="Result actions">'
            f'<button id="copy-selected-result" type="button" data-copy-output="{copy_output}">{escape(ui_text("server.result_history.copy_result", app_language=app_language, fallback_text="Copy result"))}</button>'
            f'<a id="continue-from-selected-result" class="action-link" href="{continue_href}">{escape(ui_text("server.result_history.continue_from_result", app_language=app_language, fallback_text="Continue from this result"))}</a>'
            f'<a id="report-selected-result-issue" class="action-link secondary" href="{feedback_href}">{escape(ui_text("server.result_history.report_result_issue", app_language=app_language, fallback_text="Report result issue"))}</a>'
            '</div>'
            '</section>'
        )
        return_use_context = dict(selected.get("return_use_context") or {})
        return_use_source = escape(str(return_use_context.get("source") or "result_history"))
        return_use_summary = escape(str(return_use_context.get("summary") or ui_text("server.result_history.return_use_summary", app_language=app_language, fallback_text="Continue from this selected result without losing return-use context.")))
        return_use_href = escape(str(return_use_context.get("action_href") or continue_href))
        return_use_reentry_html = (
            '<section id="return-use-reentry-panel" class="selected-output" role="region" aria-labelledby="return-use-reentry-title" '
            f'data-return-use-source="{return_use_source}" data-return-use-run-id="{escape(str(selected.get("run_id") or ""))}" '
            f'data-output-ref="{output_key}">'
            f'<h2 id="return-use-reentry-title">{escape(ui_text("server.result_history.return_use_title", app_language=app_language, fallback_text="Continue from this result"))}</h2>'
            f'<p>{return_use_summary}</p>'
            '<div class="actions">'
            f'<a id="return-use-selected-result" class="action-link" href="{return_use_href}">{escape(ui_text("server.result_history.return_use_continue", app_language=app_language, fallback_text="Continue with this result"))}</a>'
            '</div>'
            '</section>'
        )
    first_success_completion_html = ""
    selected_run_id = str(selected.get("run_id") or "").strip()
    if selected_run_id:
        selected_output_ref = escape(str(selected.get("output_key") or ""))
        selected_artifact_ref = escape(str(selected.get("first_artifact_ref") or ""))
        selected_run_ref = escape(selected_run_id)
        workspace_id = escape(str(payload.get("workspace_id") or history.get("workspace_id") or ""))
        first_success_completion_html = (
            '<section id="first-success-result-read-panel" class="selected-output" role="region" aria-labelledby="first-success-result-read-title">'
            f'<h2 id="first-success-result-read-title">{escape(ui_text("server.result_history.first_success_read_title", app_language=app_language, fallback_text="Finish first result reading"))}</h2>'
            f'<p>{escape(ui_text("server.result_history.first_success_read_summary", app_language=app_language, fallback_text="Mark this result as read using UI-owned Working Save metadata. Execution records are not mutated."))}</p>'
            f'<button id="mark-selected-result-read" type="button" data-action-kind="first_success_completion" data-first-success-action="mark_first_result_read" data-shell-draft-path="/api/workspaces/{workspace_id}/shell/draft" data-run-id="{selected_run_ref}" data-output-ref="{selected_output_ref}" data-artifact-ref="{selected_artifact_ref}">{escape(ui_text("server.result_history.mark_result_read", app_language=app_language, fallback_text="Mark result as read"))}</button>'
            '</section>'
        )
    onboarding_html = ""
    workspace_feedback_href = escape(str((payload.get('routes') or {}).get('workspace_feedback_page') or '#'))
    if onboarding_banner:
        action_href = escape(str(onboarding_banner.get("action_href") or "#"))
        action_label = escape(str(onboarding_banner.get("action_label") or ui_text("server.result_history.onboarding_continue", app_language=app_language, fallback_text="Continue workflow")))
        onboarding_html = (
            '<section class="onboarding-banner" role="region" aria-labelledby="onboarding-banner-title">'
            f'<h2 id="onboarding-banner-title">{escape(str(onboarding_banner.get("title") or ui_text("server.result_history.resume_onboarding", app_language=app_language, fallback_text="Resume onboarding")))}</h2>'
            f'<p>{escape(str(onboarding_banner.get("summary") or ""))}</p>'
            f'<a class="action-link" href="{action_href}">{action_label}</a>'
            '</section>'
        )
    return f"""<!doctype html>
<html lang="{app_language}">
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
      .result-card, .selected-output, .onboarding-banner {{ background: #111827; border: 1px solid #334155; border-radius: 16px; padding: 16px; }}
      .onboarding-banner {{ margin-bottom: 16px; border-color: #2563eb; }}
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
    <main role="main" aria-labelledby="result-history-title">
      <header aria-labelledby="result-history-title">
        <a class="top-link" href="{escape(str(payload.get('routes', {}).get('library') or '/app/library'))}" aria-label="{escape(ui_text('server.result_history.back_to_library', app_language=app_language, fallback_text='Back to library'))}">{escape(ui_text('server.result_history.back_to_library', app_language=app_language, fallback_text='Back to library'))}</a>
        <a class="top-link" href="{escape(str(payload.get('routes', {}).get('workspace_page') or '#'))}">{escape(ui_text('server.result_history.open_workflow', app_language=app_language, fallback_text='Open workflow'))}</a>
        <a class="top-link" href="{escape(str(payload.get('routes', {}).get('starter_template_catalog_page') or '#'))}">{escape(ui_text('server.shell.open_starter_templates', app_language=app_language, fallback_text='Open starter templates'))}</a>
        <a class="top-link" href="{workspace_feedback_href}">{escape(ui_text('server.result_history.send_feedback', app_language=app_language, fallback_text='Send feedback'))}</a>
        <h1 id="result-history-title">{title}</h1>
        <p>{workspace_title} · {subtitle}</p>
      </header>
      {onboarding_html}
      {selected_output_html}
      {contract_review_result_html}
      {return_use_reentry_html}
      {first_success_completion_html}
      <section class="result-grid" aria-label="{escape(ui_text('server.result_history.recent_history_aria', app_language=app_language, fallback_text='Recent result history'))}">{cards_html}</section>
    </main>
  </body>
</html>
"""
