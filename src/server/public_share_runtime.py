from __future__ import annotations

import json
from html import escape
from typing import Any, Mapping, Sequence

from src.server.http_route_surface import RunHttpRouteSurface
from src.storage.share_api import describe_public_nex_link_share
from src.ui.i18n import normalize_ui_language, ui_text


def _canonical_ref_for_workspace_artifact(workspace_row: Mapping[str, Any] | None, artifact_source: Any | None) -> tuple[str | None, str | None]:
    _source, model, _loaded = RunHttpRouteSurface._load_workspace_shell_artifact_model(workspace_row, artifact_source)
    meta = getattr(model, "meta", None)
    storage_role = str(getattr(meta, "storage_role", "") or "").strip() or None
    canonical_ref = (
        str(getattr(meta, "working_save_id", "") or "").strip()
        or str(getattr(meta, "commit_id", "") or "").strip()
        or str(getattr(meta, "run_id", "") or "").strip()
        or None
    )
    return canonical_ref, storage_role


def build_workspace_public_share_history_payload(
    *,
    workspace_id: str,
    workspace_title: str | None,
    workspace_row: Mapping[str, Any] | None,
    artifact_source: Any | None,
    share_payload_rows: Sequence[Mapping[str, Any]] = (),
    app_language: str = "en",
) -> dict[str, Any]:
    app_language = normalize_ui_language(app_language)
    canonical_ref, storage_role = _canonical_ref_for_workspace_artifact(workspace_row, artifact_source)
    entries: list[dict[str, Any]] = []
    for row in share_payload_rows:
        try:
            descriptor = describe_public_nex_link_share(dict(row))
        except Exception:
            continue
        if canonical_ref and str(descriptor.canonical_ref or "").strip() != canonical_ref:
            continue
        entries.append(
            {
                "share_id": descriptor.share_id,
                "title": descriptor.title,
                "summary": descriptor.summary,
                "state": descriptor.lifecycle_state,
                "stored_state": descriptor.stored_lifecycle_state,
                "share_path": descriptor.share_path,
                "updated_at": descriptor.updated_at,
                "created_at": descriptor.created_at,
                "expires_at": descriptor.expires_at,
                "archived": descriptor.archived,
                "audit_event_count": descriptor.audit_event_count,
                "operation_capabilities": list(descriptor.operation_capabilities),
                "detail_href": f"/app/public-shares/{descriptor.share_id}?app_language={app_language}&workspace_id={workspace_id}",
                "history_href": f"/app/public-shares/{descriptor.share_id}/history?app_language={app_language}&workspace_id={workspace_id}",
                "artifact_href": f"/api/public-shares/{descriptor.share_id}/artifact",
                "api_href": f"/api/public-shares/{descriptor.share_id}",
            }
        )
    entries.sort(key=lambda item: (str(item.get("updated_at") or ""), str(item.get("share_id") or "")), reverse=True)
    return {
        "status": "ready",
        "workspace_id": workspace_id,
        "workspace_title": workspace_title or ui_text("server.public_share.workspace_fallback", app_language=app_language, fallback_text="Workflow"),
        "app_language": app_language,
        "canonical_ref": canonical_ref,
        "storage_role": storage_role,
        "share_count": len(entries),
        "entries": entries,
        "routes": {
            "workspace_page": f"/app/workspaces/{workspace_id}?app_language={app_language}",
            "workspace_feedback_page": f"/app/workspaces/{workspace_id}/feedback?surface=workspace_shell&app_language={app_language}",
            "workspace_share_create_api": f"/api/workspaces/{workspace_id}/shell/share",
            "workspace_share_create_page": f"/app/workspaces/{workspace_id}/shares/create?app_language={app_language}",
            "workspace_share_history_page": f"/app/workspaces/{workspace_id}/shares?app_language={app_language}",
            "public_share_page_template": f"/app/public-shares/{{share_id}}?app_language={app_language}&workspace_id={workspace_id}",
            "public_share_history_page_template": f"/app/public-shares/{{share_id}}/history?app_language={app_language}&workspace_id={workspace_id}",
            "library_page": f"/app/workspaces/{workspace_id}/library?app_language={app_language}",
            "result_history_page": f"/app/workspaces/{workspace_id}/results?app_language={app_language}",
            "starter_template_catalog_page": f"/app/workspaces/{workspace_id}/starter-templates?app_language={app_language}",
        },
    }


def _share_management_nav_html(routes: Mapping[str, Any], *, app_language: str) -> str:
    workspace_page = escape(str(routes.get("workspace_page") or "#"))
    feedback_page = escape(str(routes.get("workspace_feedback_page") or "#"))
    library_page = escape(str(routes.get("library_page") or "#"))
    result_page = escape(str(routes.get("result_history_page") or "#"))
    starter_templates = escape(str(routes.get("starter_template_catalog_page") or "#"))
    issuer_portfolio = escape(str(routes.get("issuer_public_share_portfolio_page") or f"/app/users/me/public-shares?app_language={app_language}"))
    issuer_summary = escape(str(routes.get("issuer_public_share_summary_page") or f"/app/users/me/public-shares/summary?app_language={app_language}"))
    issuer_reports = escape(str(routes.get("issuer_public_share_reports_page") or f"/app/users/me/public-shares/action-reports?app_language={app_language}"))
    return (
        '<nav class="actions">'
        f'<a class="action-link secondary" href="{workspace_page}">{escape(ui_text("server.public_share.back_to_workspace", app_language=app_language, fallback_text="Back to workflow"))}</a>'
        f'<a class="action-link secondary" href="{library_page}">{escape(ui_text("server.public_share.back_to_library", app_language=app_language, fallback_text="Back to library"))}</a>'
        f'<a class="action-link secondary" href="{result_page}">{escape(ui_text("server.public_share.back_to_results", app_language=app_language, fallback_text="Back to results"))}</a>'
        f'<a class="action-link secondary" href="{starter_templates}">{escape(ui_text("server.public_share.back_to_starter_templates", app_language=app_language, fallback_text="Back to starter templates"))}</a>'
        f'<a class="action-link secondary" href="{issuer_portfolio}">{escape(ui_text("server.public_share.issuer_portfolio", app_language=app_language, fallback_text="My shares"))}</a>'
        f'<a class="action-link secondary" href="{issuer_summary}">{escape(ui_text("server.public_share.issuer_summary", app_language=app_language, fallback_text="Share summary"))}</a>'
        f'<a class="action-link secondary" href="{issuer_reports}">{escape(ui_text("server.public_share.issuer_reports", app_language=app_language, fallback_text="Action reports"))}</a>'
        f'<a class="action-link secondary" href="{feedback_page}">{escape(ui_text("server.public_share.send_feedback", app_language=app_language, fallback_text="Send feedback"))}</a>'
        '</nav>'
    )


def _public_share_notice_html(notice: Mapping[str, Any] | None, *, app_language: str) -> str:
    if not notice:
        return ""
    status = str(notice.get("status") or "").strip().lower()
    action = str(notice.get("action") or "share action").strip()
    reason = str(notice.get("reason") or "").strip()
    action_label = action.replace("_", " ").title() or ui_text("server.public_share.action_status_fallback", app_language=app_language, fallback_text="Share action")
    if status == "done":
        message = ui_text("server.public_share.action_status_done", app_language=app_language, fallback_text="{action} completed.", action=action_label)
        css_class = "notice success"
    elif status == "error":
        message = ui_text("server.public_share.action_status_error", app_language=app_language, fallback_text="{action} failed.", action=action_label)
        if reason:
            message = f"{message} {reason}"
        css_class = "notice error"
    else:
        return ""
    return f'<section class="{css_class}" role="status"><p>{escape(message)}</p></section>'


def _public_share_management_controls_html(
    *,
    share_id: str,
    lifecycle_state: str,
    archived: bool,
    app_language: str,
    workspace_id: str | None,
    origin: str,
    current_expires_at: str | None = None,
) -> str:
    workspace_query = f"&workspace_id={workspace_id}" if workspace_id else ""
    form_suffix = f"?app_language={app_language}{workspace_query}"
    archive_target = "false" if archived else "true"
    archive_label = ui_text(
        "server.public_share.unarchive_share" if archived else "server.public_share.archive_share",
        app_language=app_language,
        fallback_text="Unarchive share" if archived else "Archive share",
    )
    revoke_form = ""
    if lifecycle_state == "active":
        revoke_form = (
            f'<form class="inline" method="post" action="{escape(f"/app/public-shares/{share_id}/revoke{form_suffix}")}">'
            f'<input type="hidden" name="origin" value="{escape(origin)}" />'
            f'<button class="action-link secondary" type="submit">{escape(ui_text("server.public_share.revoke_share", app_language=app_language, fallback_text="Revoke share"))}</button>'
            '</form>'
        )
    extend_form = (
        f'<form class="inline extend-form" method="post" action="{escape(f"/app/public-shares/{share_id}/extend{form_suffix}")}">'
        f'<input type="hidden" name="origin" value="{escape(origin)}" />'
        f'<label><span>{escape(ui_text("server.public_share.expires_at", app_language=app_language, fallback_text="Expires"))}</span>'
        f'<input type="text" name="expires_at" value="{escape(str(current_expires_at or ""))}" placeholder="2026-04-30T00:00:00+00:00" /></label>'
        f'<button class="action-link secondary" type="submit">{escape(ui_text("server.public_share.extend_share", app_language=app_language, fallback_text="Extend share"))}</button>'
        '</form>'
    )
    archive_form = (
        f'<form class="inline" method="post" action="{escape(f"/app/public-shares/{share_id}/archive{form_suffix}")}">'
        f'<input type="hidden" name="origin" value="{escape(origin)}" />'
        f'<input type="hidden" name="archived" value="{escape(archive_target)}" />'
        f'<button class="action-link secondary" type="submit">{escape(archive_label)}</button>'
        '</form>'
    )
    delete_form = (
        f'<form class="inline" method="post" action="{escape(f"/app/public-shares/{share_id}/delete{form_suffix}")}">'
        f'<input type="hidden" name="origin" value="{escape(origin)}" />'
        f'<button class="action-link danger" type="submit">{escape(ui_text("server.public_share.delete_share", app_language=app_language, fallback_text="Delete share"))}</button>'
        '</form>'
    )
    return (
        '<section class="card management"><h2>'
        f'{escape(ui_text("server.public_share.manage_share", app_language=app_language, fallback_text="Manage share"))}'
        '</h2><div class="actions">'
        f'{revoke_form}{extend_form}{archive_form}{delete_form}'
        '</div></section>'
    )


def render_workspace_public_share_history_html(payload: Mapping[str, Any]) -> str:
    app_language = normalize_ui_language(payload.get("app_language") or "en")
    workspace_title = escape(str(payload.get("workspace_title") or ui_text("server.public_share.workspace_fallback", app_language=app_language, fallback_text="Workflow")))
    canonical_ref = escape(str(payload.get("canonical_ref") or ui_text("server.public_share.no_canonical_ref", app_language=app_language, fallback_text="Unavailable")))
    storage_role = escape(str(payload.get("storage_role") or ui_text("server.public_share.unknown_storage_role", app_language=app_language, fallback_text="unknown")))
    routes = dict(payload.get("routes") or {})
    create_action = escape(str(routes.get("workspace_share_create_page") or "#"))
    cards = []
    for entry in list(payload.get("entries") or []):
        cards.append(
            f"""
            <article class=\"share-card\">
              <div class=\"share-card-head\">
                <h2>{escape(str(entry.get('title') or entry.get('share_id') or ui_text('server.public_share.share_fallback', app_language=app_language, fallback_text='Public share')))}</h2>
                <span class=\"status-badge\">{escape(str(entry.get('state') or 'unknown'))}</span>
              </div>
              <p>{escape(str(entry.get('summary') or entry.get('share_path') or ''))}</p>
              <ul class=\"detail-list\">
                <li>{escape(ui_text('server.public_share.share_id', app_language=app_language, fallback_text='Share id'))}: <code>{escape(str(entry.get('share_id') or ''))}</code></li>
                <li>{escape(ui_text('server.public_share.audit_events', app_language=app_language, fallback_text='Audit events'))}: {escape(str(entry.get('audit_event_count') or 0))}</li>
                <li>{escape(ui_text('server.public_share.updated_at', app_language=app_language, fallback_text='Updated'))}: {escape(str(entry.get('updated_at') or ''))}</li>
              </ul>
              <div class=\"actions\">
                <a class=\"action-link\" href=\"{escape(str(entry.get('detail_href') or '#'))}\">{escape(ui_text('server.public_share.open_share', app_language=app_language, fallback_text='Open share'))}</a>
                <a class=\"action-link secondary\" href=\"{escape(str(entry.get('history_href') or '#'))}\">{escape(ui_text('server.public_share.open_history', app_language=app_language, fallback_text='Open history'))}</a>
                <a class=\"action-link secondary\" href=\"{escape(str(entry.get('artifact_href') or '#'))}\">{escape(ui_text('server.public_share.open_artifact', app_language=app_language, fallback_text='Open artifact'))}</a>
              </div>
            </article>
            """
        )
    cards_html = "".join(cards) or f"<article class=\"share-card empty\"><h2>{escape(ui_text('server.public_share.no_shares_title', app_language=app_language, fallback_text='No public shares yet'))}</h2><p>{escape(ui_text('server.public_share.no_shares_summary', app_language=app_language, fallback_text='Create a share from this workflow to start circuit sharing.'))}</p></article>"
    return f"""<!doctype html>
<html lang=\"{app_language}\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>{escape(ui_text('server.public_share.workspace_page_title', app_language=app_language, fallback_text='Workspace shares — {workspace}', workspace=workspace_title))}</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 0; padding: 24px; background: #f7f7f8; color: #111; }}
    .shell {{ max-width: 960px; margin: 0 auto; background: white; border-radius: 16px; padding: 24px; box-shadow: 0 10px 30px rgba(0,0,0,0.08); }}
    .share-card {{ border: 1px solid #e5e7eb; border-radius: 12px; padding: 16px; background: #fff; margin-top: 16px; }}
    .share-card-head {{ display: flex; justify-content: space-between; gap: 12px; align-items: center; }}
    .status-badge {{ background: #eff6ff; color: #1d4ed8; padding: 4px 8px; border-radius: 999px; font-size: 0.875rem; }}
    .actions {{ display: flex; gap: 12px; flex-wrap: wrap; margin-top: 16px; }}
    .action-link {{ display: inline-block; border-radius: 10px; padding: 10px 14px; text-decoration: none; background: #111827; color: white; }}
    .action-link.secondary {{ background: #374151; }}
    form.inline {{ display: inline; }}
    button.action-link {{ border: 0; cursor: pointer; }}
    code {{ background: #f3f4f6; padding: 2px 6px; border-radius: 6px; }}
  </style>
</head>
<body>
  <main class=\"shell\" role=\"main\" aria-labelledby=\"workspace-share-title\">
    <h1 id=\"workspace-share-title\">{escape(ui_text('server.public_share.workspace_share_history', app_language=app_language, fallback_text='Share history'))}</h1>
    <p><strong>{workspace_title}</strong></p>
    <p>{escape(ui_text('server.public_share.current_source', app_language=app_language, fallback_text='Current artifact'))}: <code>{canonical_ref}</code> — {escape(ui_text('server.public_share.storage_role', app_language=app_language, fallback_text='Storage role'))}: <code>{storage_role}</code></p>
    <div class=\"actions\">
      <form class=\"inline\" method=\"post\" action=\"{create_action}\"><button class=\"action-link\" type=\"submit\">{escape(ui_text('server.public_share.create_share', app_language=app_language, fallback_text='Create share'))}</button></form>
      <a class=\"action-link secondary\" href=\"{escape(str(routes.get('workspace_page') or '#'))}\">{escape(ui_text('server.public_share.back_to_workspace', app_language=app_language, fallback_text='Back to workflow'))}</a>
    </div>
    {_share_management_nav_html(routes, app_language=app_language)}
    {cards_html}
  </main>
</body>
</html>"""


def render_public_share_detail_html(payload: Mapping[str, Any], *, app_language: str | None = None, workspace_id: str | None = None) -> str:
    app_language = normalize_ui_language(app_language or payload.get("app_language") or "en")
    share_id = escape(str(payload.get("share_id") or ""))
    title = escape(str(payload.get("title") or payload.get("share_path") or ui_text("server.public_share.share_fallback", app_language=app_language, fallback_text="Public share")))
    summary = escape(str(payload.get("summary") or payload.get("share_path") or ""))
    lifecycle = dict(payload.get("lifecycle") or {})
    source = dict(payload.get("source_artifact") or {})
    links = dict(payload.get("links") or {})
    workspace_query = f"&workspace_id={workspace_id}" if workspace_id else ""
    back_to_workspace_shares = f"/app/workspaces/{workspace_id}/shares?app_language={app_language}" if workspace_id else "/app/library"
    history_page = f"/app/public-shares/{share_id}/history?app_language={app_language}{workspace_query}"
    artifact_href = escape(str(links.get("artifact") or f"/api/public-shares/{share_id}/artifact"))
    api_href = escape(str(links.get("self") or f"/api/public-shares/{share_id}"))
    share_path = escape(str(payload.get("share_path") or links.get("public_share_path") or ""))
    viewer_context = dict(payload.get("viewer_context") or {})
    notice = dict(payload.get("notice") or {})
    can_manage = bool(viewer_context.get("can_manage"))
    operation_capabilities = set(payload.get("operation_capabilities") or ())
    checkout_page = f"/app/public-shares/{share_id}/checkout?app_language={app_language}" + (f"&workspace_id={workspace_id}" if workspace_id else "")
    checkout_action_html = ""
    if "checkout_working_copy" in operation_capabilities:
        checkout_action_html = f'<a class="action-link" href="{escape(checkout_page)}">{escape(ui_text("server.public_share.checkout_submit", app_language=app_language, fallback_text="Restore to workspace"))}</a>'
    management_html = ""
    if can_manage:
        management_html = _public_share_management_controls_html(
            share_id=str(payload.get("share_id") or ""),
            lifecycle_state=str(lifecycle.get("state") or "unknown"),
            archived=bool(dict(payload.get("management") or {}).get("archived")),
            app_language=app_language,
            workspace_id=workspace_id,
            origin="detail",
            current_expires_at=str(lifecycle.get("expires_at") or "") or None,
        )
    notice_html = _public_share_notice_html(notice, app_language=app_language)
    return f"""<!doctype html>
<html lang=\"{app_language}\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>{escape(ui_text('server.public_share.detail_page_title', app_language=app_language, fallback_text='Public share — {share_id}', share_id=share_id or 'share'))}</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 0; padding: 24px; background: #f7f7f8; color: #111; }}
    .shell {{ max-width: 960px; margin: 0 auto; background: white; border-radius: 16px; padding: 24px; box-shadow: 0 10px 30px rgba(0,0,0,0.08); }}
    .card {{ border: 1px solid #e5e7eb; border-radius: 12px; padding: 16px; background: #fff; margin-top: 16px; }}
    .actions {{ display: flex; gap: 12px; flex-wrap: wrap; margin-top: 16px; }}
    .action-link {{ display: inline-block; border-radius: 10px; padding: 10px 14px; text-decoration: none; background: #111827; color: white; }}
    .action-link.secondary {{ background: #374151; }}
    code {{ background: #f3f4f6; padding: 2px 6px; border-radius: 6px; }}
  </style>
</head>
<body>
  <main class=\"shell\" role=\"main\" aria-labelledby=\"public-share-title\">
    <h1 id=\"public-share-title\">{title}</h1>
    <p>{summary}</p>
    <div class=\"actions\">
      <a class=\"action-link secondary\" href=\"{escape(back_to_workspace_shares)}\">{escape(ui_text('server.public_share.back_to_share_history', app_language=app_language, fallback_text='Back to share history'))}</a>
      <a class=\"action-link secondary\" href=\"{escape(history_page)}\">{escape(ui_text('server.public_share.open_history', app_language=app_language, fallback_text='Open history'))}</a>
      {checkout_action_html}
      <a class=\"action-link secondary\" href=\"{artifact_href}\">{escape(ui_text('server.public_share.open_artifact', app_language=app_language, fallback_text='Open artifact'))}</a>
      <a class=\"action-link secondary\" href=\"{api_href}\">{escape(ui_text('server.public_share.open_raw_share', app_language=app_language, fallback_text='Open raw share'))}</a>
    </div>
    <section class=\"card\"><h2>{escape(ui_text('server.public_share.share_identity', app_language=app_language, fallback_text='Share identity'))}</h2><ul>
      <li>{escape(ui_text('server.public_share.share_id', app_language=app_language, fallback_text='Share id'))}: <code>{share_id}</code></li>
      <li>{escape(ui_text('server.public_share.share_path_label', app_language=app_language, fallback_text='Share path'))}: <code>{share_path}</code></li>
      <li>{escape(ui_text('server.public_share.lifecycle_state', app_language=app_language, fallback_text='Lifecycle state'))}: <code>{escape(str(lifecycle.get('state') or 'unknown'))}</code></li>
      <li>{escape(ui_text('server.public_share.stored_state', app_language=app_language, fallback_text='Stored state'))}: <code>{escape(str(lifecycle.get('stored_state') or 'unknown'))}</code></li>
      <li>{escape(ui_text('server.public_share.created_at', app_language=app_language, fallback_text='Created'))}: {escape(str(lifecycle.get('created_at') or ''))}</li>
      <li>{escape(ui_text('server.public_share.updated_at', app_language=app_language, fallback_text='Updated'))}: {escape(str(lifecycle.get('updated_at') or ''))}</li>
      <li>{escape(ui_text('server.public_share.expires_at', app_language=app_language, fallback_text='Expires'))}: {escape(str(lifecycle.get('expires_at') or ui_text('server.public_share.not_set', app_language=app_language, fallback_text='Not set')))}</li>
    </ul></section>
    <section class=\"card\"><h2>{escape(ui_text('server.public_share.source_artifact', app_language=app_language, fallback_text='Source artifact'))}</h2><ul>
      <li>{escape(ui_text('server.public_share.storage_role', app_language=app_language, fallback_text='Storage role'))}: <code>{escape(str(source.get('storage_role') or 'unknown'))}</code></li>
      <li>{escape(ui_text('server.public_share.canonical_ref', app_language=app_language, fallback_text='Canonical ref'))}: <code>{escape(str(source.get('canonical_ref') or ''))}</code></li>
      <li>{escape(ui_text('server.public_share.artifact_family', app_language=app_language, fallback_text='Artifact family'))}: <code>{escape(str(source.get('artifact_format_family') or ''))}</code></li>
    </ul></section>
    {management_html}
  </main>
</body>
</html>"""


def render_public_share_checkout_html(payload: Mapping[str, Any], *, app_language: str | None = None, workspace_id: str | None = None) -> str:
    app_language = normalize_ui_language(app_language or payload.get("app_language") or "en")
    share_id = escape(str(payload.get("share_id") or ""))
    title = escape(str(payload.get("title") or payload.get("share_path") or ui_text("server.public_share.share_fallback", app_language=app_language, fallback_text="Public share")))
    summary = escape(str(payload.get("summary") or payload.get("share_path") or ""))
    lifecycle = dict(payload.get("lifecycle") or {})
    source = dict(payload.get("source_artifact") or {})
    viewer_context = dict(payload.get("viewer_context") or {})
    notice = dict(payload.get("notice") or {})
    links = dict(payload.get("links") or {})
    operation_capabilities = set(payload.get("operation_capabilities") or ())
    prefill_workspace_id = escape(str(payload.get("prefill_workspace_id") or workspace_id or ""))
    prefill_working_save_id = escape(str(payload.get("prefill_working_save_id") or ""))
    detail_page = f"/app/public-shares/{share_id}?app_language={app_language}" + (f"&workspace_id={workspace_id}" if workspace_id else "")
    history_page = f"/app/public-shares/{share_id}/history?app_language={app_language}" + (f"&workspace_id={workspace_id}" if workspace_id else "")
    checkout_action = f"/app/public-shares/{share_id}/checkout?app_language={app_language}" + (f"&workspace_id={workspace_id}" if workspace_id else "")
    can_checkout = "checkout_working_copy" in operation_capabilities
    notice_html = _public_share_notice_html(notice, app_language=app_language)
    capability_html = "<p><strong>Checkout available.</strong> This share can be restored into a workspace as a working copy.</p>" if can_checkout else f"<p><strong>{escape(ui_text('server.public_share.checkout_unavailable', app_language=app_language, fallback_text='Checkout unavailable.'))}</strong> {escape(ui_text('server.public_share.checkout_unavailable_summary', app_language=app_language, fallback_text='This share cannot currently be restored into a workspace.'))}</p>"
    disabled_attr = "" if can_checkout else " disabled"
    return f"""<!doctype html>
<html lang="{app_language}">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{escape(ui_text('server.public_share.checkout_page_title', app_language=app_language, fallback_text='Restore share to workspace — {share_id}', share_id=share_id or 'share'))}</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 0; padding: 24px; background: #f7f7f8; color: #111; }}
    .shell {{ max-width: 960px; margin: 0 auto; background: white; border-radius: 16px; padding: 24px; box-shadow: 0 10px 30px rgba(0,0,0,0.08); }}
    .card {{ border: 1px solid #e5e7eb; border-radius: 12px; padding: 16px; background: #fff; margin-top: 16px; }}
    .actions {{ display: flex; gap: 12px; flex-wrap: wrap; margin-top: 16px; }}
    .action-link {{ display: inline-block; border-radius: 10px; padding: 10px 14px; text-decoration: none; background: #111827; color: white; }}
    .action-link.secondary {{ background: #374151; }}
    form {{ display: grid; gap: 12px; margin-top: 16px; }}
    label {{ font-weight: 600; display: grid; gap: 6px; }}
    input, button {{ padding: 10px 12px; border-radius: 10px; border: 1px solid #d1d5db; font: inherit; }}
    button {{ background: #111827; color: white; border-color: #111827; cursor: pointer; }}
    button[disabled] {{ opacity: 0.45; cursor: not-allowed; }}
    code {{ background: #f3f4f6; padding: 2px 6px; border-radius: 6px; }}
  </style>
</head>
<body>
  <main class="shell" role="main" aria-labelledby="public-share-checkout-title">
    <h1 id="public-share-checkout-title">{escape(ui_text('server.public_share.checkout_heading', app_language=app_language, fallback_text='Restore share to workspace'))}</h1>
    <p>{title}</p>
    <p>{summary}</p>
    <div class="actions">
      <a class="action-link secondary" href="{escape(detail_page)}">{escape(ui_text('server.public_share.back_to_share', app_language=app_language, fallback_text='Back to share'))}</a>
      <a class="action-link secondary" href="{escape(history_page)}">{escape(ui_text('server.public_share.open_history', app_language=app_language, fallback_text='Open history'))}</a>
      <a class="action-link secondary" href="{escape(str(links.get('artifact') or f'/api/public-shares/{share_id}/artifact'))}">{escape(ui_text('server.public_share.open_artifact', app_language=app_language, fallback_text='Open artifact'))}</a>
    </div>
    <section class="card">
      <h2>{escape(ui_text('server.public_share.checkout_context', app_language=app_language, fallback_text='Checkout context'))}</h2>
      <ul>
        <li>{escape(ui_text('server.public_share.share_id', app_language=app_language, fallback_text='Share id'))}: <code>{share_id}</code></li>
        <li>{escape(ui_text('server.public_share.lifecycle_state', app_language=app_language, fallback_text='Lifecycle state'))}: <code>{escape(str(lifecycle.get('state') or 'unknown'))}</code></li>
        <li>{escape(ui_text('server.public_share.storage_role', app_language=app_language, fallback_text='Storage role'))}: <code>{escape(str(source.get('storage_role') or 'unknown'))}</code></li>
        <li>{escape(ui_text('server.public_share.canonical_ref', app_language=app_language, fallback_text='Canonical ref'))}: <code>{escape(str(source.get('canonical_ref') or ''))}</code></li>
      </ul>
      {capability_html}
    </section>
    <section class="card">
      <h2>{escape(ui_text('server.public_share.checkout_form_title', app_language=app_language, fallback_text='Restore as working copy'))}</h2>
      <p>{escape(ui_text('server.public_share.checkout_form_summary', app_language=app_language, fallback_text='Choose the workspace and optional working-save id to restore this shared commit snapshot into an editable workspace draft.'))}</p>
      <form method="post" action="{escape(checkout_action)}">
        <label>{escape(ui_text('server.public_share.checkout_workspace_id', app_language=app_language, fallback_text='Workspace id'))}
          <input name="workspace_id" value="{prefill_workspace_id}" placeholder="ws-001" required />
        </label>
        <label>{escape(ui_text('server.public_share.checkout_working_save_id', app_language=app_language, fallback_text='Working save id (optional)'))}
          <input name="working_save_id" value="{prefill_working_save_id}" placeholder="ws-restored-share" />
        </label>
        <button type="submit"{disabled_attr}>{escape(ui_text('server.public_share.checkout_submit', app_language=app_language, fallback_text='Restore to workspace'))}</button>
      </form>
      {notice_html}
    </section>
  </main>
</body>
</html>"""


def render_workspace_share_create_html(payload: Mapping[str, Any]) -> str:
    app_language = normalize_ui_language(payload.get("app_language") or "en")
    workspace_title = escape(str(payload.get("workspace_title") or ui_text("server.public_share.workspace_fallback", app_language=app_language, fallback_text="Workflow")))
    canonical_ref = escape(str(payload.get("canonical_ref") or ui_text("server.public_share.no_canonical_ref", app_language=app_language, fallback_text="Unavailable")))
    storage_role = escape(str(payload.get("storage_role") or ui_text("server.public_share.unknown_storage_role", app_language=app_language, fallback_text="unknown")))
    routes = dict(payload.get("routes") or {})
    title_value = escape(str(payload.get("prefill_title") or ""))
    summary_value = escape(str(payload.get("prefill_summary") or ""))
    expires_value = escape(str(payload.get("prefill_expires_at") or ""))
    share_count = escape(str(payload.get("share_count") or 0))
    form_action = escape(str(routes.get("workspace_share_create_page") or "#"))
    workspace_page = escape(str(routes.get("workspace_page") or "#"))
    share_history_page = escape(str(routes.get("workspace_share_history_page") or "#"))
    feedback_page = escape(str(routes.get("workspace_feedback_page") or "#"))
    starter_templates = escape(str(routes.get("starter_template_catalog_page") or "#"))
    library_page = escape(str(routes.get("library_page") or "#"))
    return f"""<!doctype html>
<html lang=\"{app_language}\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>{escape(ui_text('server.public_share.create_page_title', app_language=app_language, fallback_text='Create share — {workspace}', workspace=workspace_title))}</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 0; padding: 24px; background: #f7f7f8; color: #111; }}
    .shell {{ max-width: 960px; margin: 0 auto; background: white; border-radius: 16px; padding: 24px; box-shadow: 0 10px 30px rgba(0,0,0,0.08); }}
    .card {{ border: 1px solid #e5e7eb; border-radius: 12px; padding: 16px; background: #fff; margin-top: 16px; }}
    .actions {{ display: flex; gap: 12px; flex-wrap: wrap; margin-top: 16px; }}
    .action-link {{ display: inline-block; border-radius: 10px; padding: 10px 14px; text-decoration: none; background: #111827; color: white; }}
    .action-link.secondary {{ background: #374151; }}
    .form-grid {{ display: grid; gap: 16px; margin-top: 16px; }}
    label span {{ display: block; font-weight: 600; margin-bottom: 6px; }}
    input, textarea {{ width: 100%; box-sizing: border-box; border: 1px solid #d1d5db; border-radius: 10px; padding: 10px 12px; font: inherit; }}
    textarea {{ min-height: 120px; resize: vertical; }}
    button {{ border: 0; border-radius: 10px; padding: 12px 16px; cursor: pointer; background: #111827; color: white; }}
    code {{ background: #f3f4f6; padding: 2px 6px; border-radius: 6px; }}
  </style>
</head>
<body>
  <main class=\"shell\" role=\"main\" aria-labelledby=\"share-create-title\">
    <h1 id=\"share-create-title\">{escape(ui_text('server.public_share.create_share', app_language=app_language, fallback_text='Create share'))}</h1>
    <p><strong>{workspace_title}</strong></p>
    <p>{escape(ui_text('server.public_share.create_page_summary', app_language=app_language, fallback_text='Publish the current workflow artifact as a public share.'))}</p>
    <div class=\"actions\">
      <a class=\"action-link secondary\" href=\"{workspace_page}\">{escape(ui_text('server.public_share.back_to_workspace', app_language=app_language, fallback_text='Back to workflow'))}</a>
      <a class=\"action-link secondary\" href=\"{share_history_page}\">{escape(ui_text('server.public_share.back_to_share_history', app_language=app_language, fallback_text='Back to share history'))}</a>
      <a class=\"action-link secondary\" href=\"{library_page}\">{escape(ui_text('server.public_share.back_to_library', app_language=app_language, fallback_text='Back to library'))}</a>
      <a class=\"action-link secondary\" href=\"{starter_templates}\">{escape(ui_text('server.public_share.back_to_starter_templates', app_language=app_language, fallback_text='Back to starter templates'))}</a>
      <a class=\"action-link secondary\" href=\"{feedback_page}\">{escape(ui_text('server.public_share.send_feedback', app_language=app_language, fallback_text='Send feedback'))}</a>
    </div>
    <section class=\"card\">
      <h2>{escape(ui_text('server.public_share.source_artifact', app_language=app_language, fallback_text='Source artifact'))}</h2>
      <ul>
        <li>{escape(ui_text('server.public_share.canonical_ref', app_language=app_language, fallback_text='Canonical ref'))}: <code>{canonical_ref}</code></li>
        <li>{escape(ui_text('server.public_share.storage_role', app_language=app_language, fallback_text='Storage role'))}: <code>{storage_role}</code></li>
        <li>{escape(ui_text('server.public_share.share_count', app_language=app_language, fallback_text='Existing shares'))}: <code>{share_count}</code></li>
      </ul>
    </section>
    <section class=\"card\">
      <h2>{escape(ui_text('server.public_share.share_details', app_language=app_language, fallback_text='Share details'))}</h2>
      <form method=\"post\" action=\"{form_action}\">
        <div class=\"form-grid\">
          <label><span>{escape(ui_text('server.public_share.share_title', app_language=app_language, fallback_text='Title'))}</span><input type=\"text\" name=\"title\" value=\"{title_value}\" /></label>
          <label><span>{escape(ui_text('server.public_share.share_summary', app_language=app_language, fallback_text='Summary'))}</span><textarea name=\"summary\">{summary_value}</textarea></label>
          <label><span>{escape(ui_text('server.public_share.expires_at', app_language=app_language, fallback_text='Expires'))}</span><input type=\"text\" name=\"expires_at\" value=\"{expires_value}\" placeholder=\"2026-04-30T00:00:00+00:00\" /></label>
        </div>
        <div class=\"actions\">
          <button type=\"submit\">{escape(ui_text('server.public_share.create_share', app_language=app_language, fallback_text='Create share'))}</button>
        </div>
      </form>
    </section>
  </main>
</body>
</html>
"""


def render_public_share_history_html(payload: Mapping[str, Any], *, app_language: str | None = None, workspace_id: str | None = None) -> str:
    app_language = normalize_ui_language(app_language or payload.get("app_language") or "en")
    share_id = escape(str(payload.get("share_id") or ""))
    share_path = escape(str(payload.get("share_path") or ""))
    history = list(payload.get("history") or [])
    links = dict(payload.get("links") or {})
    detail_page = f"/app/public-shares/{share_id}?app_language={app_language}" + (f"&workspace_id={workspace_id}" if workspace_id else "")
    audit_items = []
    for entry in history:
        audit_items.append(
            f"<article class=\"event-card\"><h2>{escape(str(entry.get('event_type') or 'event'))}</h2><p>{escape(str(entry.get('timestamp') or ''))}</p><pre>{escape(str(entry.get('detail_payload') or ''))}</pre></article>"
        )
    audit_html = "".join(audit_items) or f"<article class=\"event-card empty\"><h2>{escape(ui_text('server.public_share.no_history_title', app_language=app_language, fallback_text='No audit history yet'))}</h2><p>{escape(ui_text('server.public_share.no_history_summary', app_language=app_language, fallback_text='Audit history will appear here after lifecycle events occur.'))}</p></article>"
    artifact_href = escape(str(links.get("artifact") or f"/api/public-shares/{share_id}/artifact"))
    viewer_context = dict(payload.get("viewer_context") or {})
    notice = dict(payload.get("notice") or {})
    operation_capabilities = set(payload.get("operation_capabilities") or ())
    checkout_page = f"/app/public-shares/{share_id}/checkout?app_language={app_language}" + (f"&workspace_id={workspace_id}" if workspace_id else "")
    checkout_action_html = ""
    if "checkout_working_copy" in operation_capabilities:
        checkout_action_html = f'<a class="action-link" href="{escape(checkout_page)}">{escape(ui_text("server.public_share.checkout_submit", app_language=app_language, fallback_text="Restore to workspace"))}</a>'
    can_manage = bool(viewer_context.get("can_manage"))
    management_html = ""
    if can_manage:
        lifecycle = dict(payload.get("lifecycle") or {})
        management_html = _public_share_management_controls_html(
            share_id=str(payload.get("share_id") or ""),
            lifecycle_state=str(lifecycle.get("state") or "unknown"),
            archived=bool(dict(payload.get("management") or {}).get("archived")),
            app_language=app_language,
            workspace_id=workspace_id,
            origin="history",
            current_expires_at=str(lifecycle.get("expires_at") or "") or None,
        )
    notice_html = _public_share_notice_html(notice, app_language=app_language)
    return f"""<!doctype html>
<html lang=\"{app_language}\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>{escape(ui_text('server.public_share.history_page_title', app_language=app_language, fallback_text='Share history — {share_id}', share_id=share_id or 'share'))}</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 0; padding: 24px; background: #f7f7f8; color: #111; }}
    .shell {{ max-width: 960px; margin: 0 auto; background: white; border-radius: 16px; padding: 24px; box-shadow: 0 10px 30px rgba(0,0,0,0.08); }}
    .event-card {{ border: 1px solid #e5e7eb; border-radius: 12px; padding: 16px; background: #fff; margin-top: 16px; }}
    .actions {{ display: flex; gap: 12px; flex-wrap: wrap; margin-top: 16px; }}
    .action-link {{ display: inline-block; border-radius: 10px; padding: 10px 14px; text-decoration: none; background: #111827; color: white; }}
    .action-link.secondary {{ background: #374151; }}
    pre {{ white-space: pre-wrap; word-break: break-word; background: #f9fafb; padding: 12px; border-radius: 10px; border: 1px solid #e5e7eb; }}
    code {{ background: #f3f4f6; padding: 2px 6px; border-radius: 6px; }}
  </style>
</head>
<body>
  <main class=\"shell\" role=\"main\" aria-labelledby=\"public-share-history-title\">
    <h1 id=\"public-share-history-title\">{escape(ui_text('server.public_share.open_history', app_language=app_language, fallback_text='Open history'))}</h1>
    <p><code>{share_id}</code> — {share_path}</p>
    <div class=\"actions\">
      <a class=\"action-link secondary\" href=\"{escape(detail_page)}\">{escape(ui_text('server.public_share.back_to_share', app_language=app_language, fallback_text='Back to share'))}</a>
      {checkout_action_html}
      <a class=\"action-link secondary\" href=\"{artifact_href}\">{escape(ui_text('server.public_share.open_artifact', app_language=app_language, fallback_text='Open artifact'))}</a>
    </div>
    {management_html}
    {audit_html}
  </main>
</body>
</html>"""


def _issuer_public_share_notice_html(notice: Mapping[str, Any] | None, *, app_language: str) -> str:
    if not notice:
        return ""
    status = str(notice.get("status") or "").strip().lower()
    action = str(notice.get("action") or "share action").strip()
    reason = str(notice.get("reason") or "").strip()
    action_label = action.replace("_", " ").title() or ui_text(
        "server.public_share.action_status_fallback",
        app_language=app_language,
        fallback_text="Share action",
    )
    if status == "done":
        message = ui_text(
            "server.public_share.action_status_done",
            app_language=app_language,
            fallback_text="{action} completed.",
            action=action_label,
        )
        css_class = "notice success"
    elif status == "error":
        message = ui_text(
            "server.public_share.action_status_error",
            app_language=app_language,
            fallback_text="{action} failed.",
            action=action_label,
        )
        if reason:
            message = f"{message} {reason}"
        css_class = "notice error"
    else:
        return ""
    return f'<section class="{css_class}" role="status"><p>{escape(message)}</p></section>'


def _issuer_public_share_nav_html(*, app_language: str) -> str:
    portfolio = escape(f"/app/users/me/public-shares?app_language={app_language}")
    summary = escape(f"/app/users/me/public-shares/summary?app_language={app_language}")
    reports = escape(f"/app/users/me/public-shares/action-reports?app_language={app_language}")
    return (
        '<nav class="actions">'
        f'<a class="action-link secondary" href="{portfolio}">{escape(ui_text("server.public_share.issuer_portfolio", app_language=app_language, fallback_text="My shares"))}</a>'
        f'<a class="action-link secondary" href="{summary}">{escape(ui_text("server.public_share.issuer_summary", app_language=app_language, fallback_text="Share summary"))}</a>'
        f'<a class="action-link secondary" href="{reports}">{escape(ui_text("server.public_share.issuer_reports", app_language=app_language, fallback_text="Action reports"))}</a>'
        '</nav>'
    )


def render_issuer_public_share_portfolio_html(payload: Mapping[str, Any], *, app_language: str | None = None) -> str:
    app_language = normalize_ui_language(app_language or payload.get("app_language") or "en")
    summary = dict(payload.get("summary") or {})
    governance = dict(payload.get("governance_summary") or {})
    shares = list(payload.get("shares") or [])
    notice_html = _issuer_public_share_notice_html(dict(payload.get("notice") or {}), app_language=app_language)
    bulk_action_empty = ui_text(
        "server.public_share.bulk_action_empty",
        app_language=app_language,
        fallback_text="Select at least one share first.",
    )
    bulk_selection_summary = ui_text(
        "server.public_share.bulk_selection_summary",
        app_language=app_language,
        fallback_text="Selected shares: {count}",
        count="0",
    )
    bulk_selection_template = ui_text(
        "server.public_share.bulk_selection_summary",
        app_language=app_language,
        fallback_text="Selected shares: {count}",
        count="__COUNT__",
    )
    bulk_toolbar_html = ""
    if shares:
        bulk_toolbar_html = f"""
    <section class="bulk-management" aria-labelledby="bulk-management-title">
      <h2 id="bulk-management-title">{escape(ui_text('server.public_share.bulk_manage_shares', app_language=app_language, fallback_text='Bulk manage shares'))}</h2>
      <p id="bulk-selection-summary">{escape(bulk_selection_summary)}</p>
      <div class="actions">
        <label class="select-all-toggle"><input type="checkbox" id="bulk-select-all" /> {escape(ui_text('server.public_share.select_all_shares', app_language=app_language, fallback_text='Select all shown shares'))}</label>
      </div>
      <div class="actions">
        <form class="inline" id="bulk-revoke-form" method="post" action="/app/users/me/public-shares/actions/revoke?app_language={app_language}">
          <input type="hidden" name="share_ids_csv" value="" />
          <button class="action-link secondary" type="submit">{escape(ui_text('server.public_share.bulk_revoke_shares', app_language=app_language, fallback_text='Revoke selected'))}</button>
        </form>
        <form class="inline" id="bulk-archive-form" method="post" action="/app/users/me/public-shares/actions/archive?app_language={app_language}">
          <input type="hidden" name="share_ids_csv" value="" />
          <input type="hidden" name="archived" value="true" />
          <button class="action-link secondary" type="submit">{escape(ui_text('server.public_share.bulk_archive_shares', app_language=app_language, fallback_text='Archive selected'))}</button>
        </form>
        <form class="inline extend-form" id="bulk-extend-form" method="post" action="/app/users/me/public-shares/actions/extend?app_language={app_language}">
          <input type="hidden" name="share_ids_csv" value="" />
          <input type="text" name="expires_at" value="" placeholder="2026-04-30T00:00:00+00:00" />
          <button class="action-link secondary" type="submit">{escape(ui_text('server.public_share.bulk_extend_shares', app_language=app_language, fallback_text='Extend selected'))}</button>
        </form>
        <form class="inline" id="bulk-delete-form" method="post" action="/app/users/me/public-shares/actions/delete?app_language={app_language}">
          <input type="hidden" name="share_ids_csv" value="" />
          <button class="action-link danger" type="submit">{escape(ui_text('server.public_share.bulk_delete_shares', app_language=app_language, fallback_text='Delete selected'))}</button>
        </form>
      </div>
    </section>
"""
    cards: list[str] = []
    for entry in shares:
        share_id = escape(str(entry.get("share_id") or ""))
        management = dict(entry.get("management") or {})
        lifecycle = dict(entry.get("lifecycle") or {})
        archived = bool(management.get("archived"))
        archive_target = "false" if archived else "true"
        archive_label = ui_text(
            "server.public_share.unarchive_share" if archived else "server.public_share.archive_share",
            app_language=app_language,
            fallback_text="Unarchive share" if archived else "Archive share",
        )
        cards.append(
            f"""
        <article class="share-card">
          <div class="share-card-head">
            <label class="share-selector"><input class="share-select" type="checkbox" value="{share_id}" data-share-id="{share_id}" /> {escape(ui_text('server.public_share.select_share', app_language=app_language, fallback_text='Select share'))}</label>
            <h2>{escape(str(entry.get('title') or entry.get('share_id') or ui_text('server.public_share.share_fallback', app_language=app_language, fallback_text='Public share')))}</h2>
            <span class="status-badge">{escape(str(lifecycle.get('state') or 'unknown'))}</span>
          </div>
          <p>{escape(str(entry.get('summary') or entry.get('share_path') or ''))}</p>
          <ul class="detail-list">
            <li>{escape(ui_text('server.public_share.share_id', app_language=app_language, fallback_text='Share id'))}: <code>{share_id}</code></li>
            <li>{escape(ui_text('server.public_share.storage_role', app_language=app_language, fallback_text='Storage role'))}: <code>{escape(str(entry.get('storage_role') or 'unknown'))}</code></li>
            <li>{escape(ui_text('server.public_share.audit_events', app_language=app_language, fallback_text='Audit events'))}: {escape(str(dict(entry.get('audit_summary') or {}).get('event_count') or 0))}</li>
          </ul>
          <div class="actions">
            <a class="action-link" href="/app/public-shares/{share_id}?app_language={app_language}">{escape(ui_text('server.public_share.open_share', app_language=app_language, fallback_text='Open share'))}</a>
            <a class="action-link secondary" href="/app/public-shares/{share_id}/history?app_language={app_language}">{escape(ui_text('server.public_share.open_history', app_language=app_language, fallback_text='Open history'))}</a>
            <form class="inline" method="post" action="/app/users/me/public-shares/actions/revoke?app_language={app_language}"><input type="hidden" name="share_id" value="{share_id}" /><button class="action-link secondary" type="submit">{escape(ui_text('server.public_share.revoke_share', app_language=app_language, fallback_text='Revoke share'))}</button></form>
            <form class="inline" method="post" action="/app/users/me/public-shares/actions/archive?app_language={app_language}"><input type="hidden" name="share_id" value="{share_id}" /><input type="hidden" name="archived" value="{archive_target}" /><button class="action-link secondary" type="submit">{escape(archive_label)}</button></form>
            <form class="inline extend-form" method="post" action="/app/users/me/public-shares/actions/extend?app_language={app_language}"><input type="hidden" name="share_id" value="{share_id}" /><input type="text" name="expires_at" value="{escape(str(lifecycle.get('expires_at') or ''))}" placeholder="2026-04-30T00:00:00+00:00" /><button class="action-link secondary" type="submit">{escape(ui_text('server.public_share.extend_share', app_language=app_language, fallback_text='Extend share'))}</button></form>
            <form class="inline" method="post" action="/app/users/me/public-shares/actions/delete?app_language={app_language}"><input type="hidden" name="share_id" value="{share_id}" /><button class="action-link danger" type="submit">{escape(ui_text('server.public_share.delete_share', app_language=app_language, fallback_text='Delete share'))}</button></form>
          </div>
        </article>
        """
        )
    cards_html = "".join(cards) or (
        f'<article class="share-card empty"><h2>{escape(ui_text("server.public_share.no_shares_title", app_language=app_language, fallback_text="No public shares yet"))}</h2>'
        f'<p>{escape(ui_text("server.public_share.no_shares_summary", app_language=app_language, fallback_text="Create a share from this workflow to start circuit sharing."))}</p></article>'
    )
    return f"""<!doctype html>
<html lang="{app_language}">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{escape(ui_text('server.public_share.issuer_portfolio_page_title', app_language=app_language, fallback_text='My public shares'))}</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 0; padding: 24px; background: #f7f7f8; color: #111; }}
    .shell {{ max-width: 1080px; margin: 0 auto; background: white; border-radius: 16px; padding: 24px; box-shadow: 0 10px 30px rgba(0,0,0,0.08); }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px,1fr)); gap: 12px; margin-top: 16px; }}
    .metric, .share-card, .notice, .bulk-management {{ border: 1px solid #e5e7eb; border-radius: 12px; padding: 16px; background: #fff; margin-top: 16px; }}
    .share-card-head {{ display:flex; justify-content: space-between; gap: 12px; align-items: center; flex-wrap: wrap; }}
    .status-badge {{ background: #eff6ff; color: #1d4ed8; padding: 4px 8px; border-radius: 999px; font-size: 0.875rem; }}
    .actions {{ display:flex; gap: 12px; flex-wrap: wrap; margin-top: 16px; }}
    .action-link {{ display:inline-block; border-radius: 10px; padding: 10px 14px; text-decoration:none; background:#111827; color:white; border:0; cursor:pointer; }}
    .action-link.secondary {{ background:#374151; }}
    .action-link.danger {{ background:#b91c1c; }}
    form.inline {{ display:inline-flex; gap: 8px; align-items: center; flex-wrap: wrap; }}
    .extend-form input[type=text] {{ border:1px solid #d1d5db; border-radius: 8px; padding: 8px 10px; min-width: 220px; }}
    .share-selector {{ display:inline-flex; gap: 8px; align-items:center; font-size: 0.9rem; }}
    .select-all-toggle {{ display:inline-flex; gap: 8px; align-items:center; }}
    code {{ background:#f3f4f6; padding:2px 6px; border-radius:6px; }}
  </style>
</head>
<body>
  <main class="shell" role="main" aria-labelledby="issuer-shares-title">
    <h1 id="issuer-shares-title">{escape(ui_text('server.public_share.issuer_portfolio', app_language=app_language, fallback_text='My public shares'))}</h1>
    <p>{escape(ui_text('server.public_share.issuer_portfolio_summary', app_language=app_language, fallback_text='Review and manage the shares you issued.'))}</p>
    {_issuer_public_share_nav_html(app_language=app_language)}
    {notice_html}
    <section class="grid">
      <article class="metric"><strong>{escape(ui_text('server.public_share.total_shares', app_language=app_language, fallback_text='Total shares'))}</strong><div>{escape(str(summary.get('total_share_count') or 0))}</div></article>
      <article class="metric"><strong>{escape(ui_text('server.public_share.active_shares', app_language=app_language, fallback_text='Active'))}</strong><div>{escape(str(summary.get('active_share_count') or 0))}</div></article>
      <article class="metric"><strong>{escape(ui_text('server.public_share.archived_shares', app_language=app_language, fallback_text='Archived'))}</strong><div>{escape(str(summary.get('archived_share_count') or 0))}</div></article>
      <article class="metric"><strong>{escape(ui_text('server.public_share.action_reports', app_language=app_language, fallback_text='Action reports'))}</strong><div>{escape(str(governance.get('total_action_report_count') or 0))}</div></article>
    </section>
    {bulk_toolbar_html}
    {cards_html}
  </main>
  <script>
    (() => {{
      const bulkMessage = {json.dumps(bulk_action_empty)};
      const checkboxes = Array.from(document.querySelectorAll('.share-select'));
      const selectAll = document.getElementById('bulk-select-all');
      const summary = document.getElementById('bulk-selection-summary');
      const forms = Array.from(document.querySelectorAll('form[id^="bulk-"]'));
      const updateSelection = () => {{
        const selected = checkboxes.filter((input) => input.checked).map((input) => input.value);
        forms.forEach((form) => {{
          const hidden = form.querySelector('input[name="share_ids_csv"]');
          if (hidden) hidden.value = selected.join(',');
        }});
        if (summary) summary.textContent = {json.dumps(bulk_selection_template)}.replace('__COUNT__', String(selected.length));
        if (selectAll) selectAll.checked = selected.length > 0 && selected.length === checkboxes.length;
      }};
      if (selectAll) {{
        selectAll.addEventListener('change', () => {{
          checkboxes.forEach((input) => {{ input.checked = selectAll.checked; }});
          updateSelection();
        }});
      }}
      checkboxes.forEach((input) => input.addEventListener('change', updateSelection));
      forms.forEach((form) => {{
        form.addEventListener('submit', (event) => {{
          const hidden = form.querySelector('input[name="share_ids_csv"]');
          if (!hidden || !hidden.value.trim()) {{
            event.preventDefault();
            window.alert(bulkMessage);
          }}
        }});
      }});
      updateSelection();
    }})();
  </script>
</body>
</html>"""

def render_issuer_public_share_summary_html(payload: Mapping[str, Any], *, app_language: str | None = None) -> str:
    app_language = normalize_ui_language(app_language or payload.get("app_language") or "en")
    summary = dict(payload.get("summary") or {})
    inventory = dict(payload.get("inventory_summary") or {})
    governance = dict(payload.get("governance_summary") or {})
    return f"""<!doctype html>
<html lang="{app_language}">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{escape(ui_text('server.public_share.issuer_summary_page_title', app_language=app_language, fallback_text='Public share summary'))}</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin:0; padding:24px; background:#f7f7f8; color:#111; }}
    .shell {{ max-width: 960px; margin:0 auto; background:white; border-radius:16px; padding:24px; box-shadow:0 10px 30px rgba(0,0,0,0.08); }}
    .grid {{ display:grid; grid-template-columns: repeat(auto-fit, minmax(180px,1fr)); gap:12px; margin-top:16px; }}
    .metric {{ border:1px solid #e5e7eb; border-radius:12px; padding:16px; background:#fff; }}
    .actions {{ display:flex; gap:12px; flex-wrap:wrap; margin-top:16px; }}
    .action-link {{ display:inline-block; border-radius:10px; padding:10px 14px; text-decoration:none; background:#111827; color:white; }}
  </style>
</head>
<body>
  <main class="shell" role="main" aria-labelledby="issuer-summary-title">
    <h1 id="issuer-summary-title">{escape(ui_text('server.public_share.issuer_summary', app_language=app_language, fallback_text='Share summary'))}</h1>
    {_issuer_public_share_nav_html(app_language=app_language)}
    <section class="grid">
      <article class="metric"><strong>{escape(ui_text('server.public_share.filtered_total', app_language=app_language, fallback_text='Filtered total'))}</strong><div>{escape(str(summary.get('total_share_count') or 0))}</div></article>
      <article class="metric"><strong>{escape(ui_text('server.public_share.inventory_total', app_language=app_language, fallback_text='Inventory total'))}</strong><div>{escape(str(inventory.get('total_share_count') or 0))}</div></article>
      <article class="metric"><strong>{escape(ui_text('server.public_share.latest_updated', app_language=app_language, fallback_text='Latest updated'))}</strong><div>{escape(str(summary.get('latest_updated_at') or ''))}</div></article>
      <article class="metric"><strong>{escape(ui_text('server.public_share.latest_action_report', app_language=app_language, fallback_text='Latest action report'))}</strong><div>{escape(str(governance.get('latest_action_report_at') or ''))}</div></article>
    </section>
  </main>
</body>
</html>"""


def render_issuer_public_share_action_reports_html(payload: Mapping[str, Any], *, app_language: str | None = None) -> str:
    app_language = normalize_ui_language(app_language or payload.get("app_language") or "en")
    reports = list(payload.get("reports") or [])
    notice_html = _issuer_public_share_notice_html(dict(payload.get("notice") or {}), app_language=app_language)
    cards = [
        (
            f'<article class="share-card"><h2>{escape(str(report.get("action") or "action").replace("_", " ").title())}</h2>'
            f'<p>{escape(str(report.get("created_at") or ""))}</p>'
            f'<p>{escape(ui_text("server.public_share.affected_shares", app_language=app_language, fallback_text="Affected shares"))}: '
            f'{escape(", ".join(str(v) for v in (report.get("affected_share_ids") or [])))}</p></article>'
        )
        for report in reports
    ]
    report_html = "".join(cards) or (
        f'<article class="share-card empty"><h2>{escape(ui_text("server.public_share.no_action_reports_title", app_language=app_language, fallback_text="No action reports yet"))}</h2>'
        f'<p>{escape(ui_text("server.public_share.no_action_reports_summary", app_language=app_language, fallback_text="Bulk share-management action reports will appear here."))}</p></article>'
    )
    return f"""<!doctype html>
<html lang="{app_language}">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{escape(ui_text('server.public_share.issuer_reports_page_title', app_language=app_language, fallback_text='Share action reports'))}</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin:0; padding:24px; background:#f7f7f8; color:#111; }}
    .shell {{ max-width:960px; margin:0 auto; background:white; border-radius:16px; padding:24px; box-shadow:0 10px 30px rgba(0,0,0,0.08); }}
    .share-card, .notice {{ border:1px solid #e5e7eb; border-radius:12px; padding:16px; background:#fff; margin-top:16px; }}
    .actions {{ display:flex; gap:12px; flex-wrap:wrap; margin-top:16px; }}
    .action-link {{ display:inline-block; border-radius:10px; padding:10px 14px; text-decoration:none; background:#111827; color:white; }}
  </style>
</head>
<body>
  <main class="shell" role="main" aria-labelledby="issuer-reports-title">
    <h1 id="issuer-reports-title">{escape(ui_text('server.public_share.issuer_reports', app_language=app_language, fallback_text='Action reports'))}</h1>
    {_issuer_public_share_nav_html(app_language=app_language)}
    {notice_html}
    {report_html}
  </main>
</body>
</html>"""
