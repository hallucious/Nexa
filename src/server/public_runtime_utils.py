from __future__ import annotations

from html import escape
from typing import Mapping


def resolve_app_route(
    routes: Mapping[str, object],
    route_key: str,
    fallback: str,
    *,
    app_language: str | None = None,
    workspace_id: str | None = None,
) -> str:
    route = str(routes.get(route_key) or fallback).strip() or fallback
    query_parts: list[str] = []
    if app_language and "app_language=" not in route:
        query_parts.append(f"app_language={app_language}")
    if workspace_id and "workspace_id=" not in route:
        query_parts.append(f"workspace_id={workspace_id}")
    if query_parts:
        joiner = "&" if "?" in route else "?"
        route = f"{route}{joiner}{'&'.join(query_parts)}"
    return route


def escaped_app_route(
    routes: Mapping[str, object],
    route_key: str,
    fallback: str,
    *,
    app_language: str | None = None,
    workspace_id: str | None = None,
) -> str:
    return escape(
        resolve_app_route(
            routes,
            route_key,
            fallback,
            app_language=app_language,
            workspace_id=workspace_id,
        )
    )


__all__ = ["resolve_app_route", "escaped_app_route"]
