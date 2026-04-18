from __future__ import annotations

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
    return (
        '<nav class="actions">'
        f'<a class="action-link secondary" href="{workspace_page}">{escape(ui_text("server.public_share.back_to_workspace", app_language=app_language, fallback_text="Back to workflow"))}</a>'
        f'<a class="action-link secondary" href="{library_page}">{escape(ui_text("server.public_share.back_to_library", app_language=app_language, fallback_text="Back to library"))}</a>'
        f'<a class="action-link secondary" href="{result_page}">{escape(ui_text("server.public_share.back_to_results", app_language=app_language, fallback_text="Back to results"))}</a>'
        f'<a class="action-link secondary" href="{starter_templates}">{escape(ui_text("server.public_share.back_to_starter_templates", app_language=app_language, fallback_text="Back to starter templates"))}</a>'
        f'<a class="action-link secondary" href="{feedback_page}">{escape(ui_text("server.public_share.send_feedback", app_language=app_language, fallback_text="Send feedback"))}</a>'
        '</nav>'
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
  </main>
</body>
</html>"""


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
      <a class=\"action-link secondary\" href=\"{artifact_href}\">{escape(ui_text('server.public_share.open_artifact', app_language=app_language, fallback_text='Open artifact'))}</a>
    </div>
    {audit_html}
  </main>
</body>
</html>"""
