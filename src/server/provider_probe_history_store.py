from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace
from typing import Any, Optional

from src.server.fastapi_binding_models import FastApiRouteDependencies
from src.server.provider_probe_history_models import ProviderProbeHistoryRecord


@dataclass
class InMemoryProviderProbeHistoryStore:
    _rows_by_event_id: dict[str, dict[str, Any]] = field(default_factory=dict)

    @classmethod
    def from_rows(cls, rows: Sequence[Mapping[str, Any]] = ()) -> "InMemoryProviderProbeHistoryStore":
        store = cls()
        for row in rows:
            store.write(row)
        return store

    def write(self, row: Mapping[str, Any]) -> dict[str, Any]:
        record = ProviderProbeHistoryRecord.from_mapping(row)
        if record is None:
            raise ValueError("provider_probe_history_store.row_invalid")
        normalized = record.to_mapping()
        self._rows_by_event_id[record.probe_event_id] = normalized
        return dict(normalized)

    def list_workspace_rows(self, workspace_id: str) -> tuple[dict[str, Any], ...]:
        normalized_workspace_id = str(workspace_id or "").strip()
        rows = [dict(row) for row in self._rows_by_event_id.values() if str(row.get("workspace_id") or "").strip() == normalized_workspace_id]
        rows.sort(key=lambda item: (str(item.get("occurred_at") or ""), str(item.get("probe_event_id") or "")), reverse=True)
        return tuple(rows)

    def list_recent_rows(self, limit: Optional[int] = None) -> tuple[dict[str, Any], ...]:
        rows = [dict(row) for row in self._rows_by_event_id.values()]
        rows.sort(key=lambda item: (str(item.get("occurred_at") or ""), str(item.get("probe_event_id") or "")), reverse=True)
        if limit is not None:
            limited = max(int(limit), 0)
            rows = rows[:limited]
        return tuple(rows)


def bind_probe_history_store(
    *,
    dependencies: FastApiRouteDependencies,
    store: InMemoryProviderProbeHistoryStore,
) -> FastApiRouteDependencies:
    return replace(
        dependencies,
        workspace_provider_probe_rows_provider=store.list_workspace_rows,
        recent_provider_probe_rows_provider=store.list_recent_rows,
        provider_probe_history_writer=store.write,
    )
