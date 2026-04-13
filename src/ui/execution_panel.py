from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Sequence

from src.storage.models.commit_snapshot_model import CommitSnapshotModel
from src.storage.models.execution_record_model import ExecutionRecordModel, NodeTimingCard, OutputResultCard
from src.storage.models.loaded_nex_artifact import LoadedNexArtifact
from src.storage.models.working_save_model import WorkingSaveModel
from src.engine.execution_event import ExecutionEvent
from src.contracts.status_taxonomy import lookup_reason_code_record
from src.ui.i18n import ui_language_from_sources, ui_text
from src.ui.friendly_error_messages import FriendlyErrorView, friendly_error_from_candidates


@dataclass(frozen=True)
class RunIdentityView:
    run_id: str | None = None
    execution_id: str | None = None
    commit_id: str | None = None
    working_save_id: str | None = None
    trigger_type: str | None = None
    title: str | None = None
    description: str | None = None


@dataclass(frozen=True)
class ExecutionProgressView:
    progress_mode: str = "unknown"
    percent: float | None = None
    completed_units: int | None = None
    total_units: int | None = None
    current_stage_label: str | None = None
    eta_seconds: float | None = None
    indeterminate_message: str | None = None


@dataclass(frozen=True)
class ActiveExecutionContextView:
    active_node_id: str | None = None
    active_node_label: str | None = None
    active_resource_type: str | None = None
    active_resource_id: str | None = None
    active_stage: str | None = None
    status_message: str | None = None


@dataclass(frozen=True)
class ExecutionEventView:
    event_id: str
    event_type: str
    timestamp: str
    node_id: str | None = None
    severity: str = "info"
    short_message: str = ""
    details_preview: str | None = None


@dataclass(frozen=True)
class OutputSummaryView:
    output_ref: str
    source_node: str | None = None
    value_summary: str = ""
    value_type: str | None = None
    full_value: str | None = None
    is_copyable: bool = False
    streaming_in_progress: bool = False
    display_mode: str = "text"
    preview_items: list[str] = field(default_factory=list)
    item_count: int | None = None
    copy_action_label: str | None = None
    artifact_ref: str | None = None
    open_artifact_action_label: str | None = None


@dataclass(frozen=True)
class ExecutionDiagnosticsSummary:
    warning_count: int = 0
    error_count: int = 0
    failure_point: str | None = None
    termination_reason: str | None = None
    last_error_label: str | None = None


@dataclass(frozen=True)
class ExecutionTimingView:
    started_at: str | None = None
    finished_at: str | None = None
    total_duration_ms: int | None = None
    event_count: int | None = None


@dataclass(frozen=True)
class ExecutionMetricsView:
    total_nodes: int = 0
    completed_nodes: int = 0
    failed_nodes: int = 0
    artifact_count: int = 0
    provider_call_count: int | None = None
    plugin_call_count: int | None = None


@dataclass(frozen=True)
class ExecutionControlActionView:
    action_id: str
    label: str
    enabled: bool
    reason_disabled: str | None = None


@dataclass(frozen=True)
class ExecutionControlStateView:
    can_run: bool = False
    can_cancel: bool = False
    can_pause: bool = False
    can_resume: bool = False
    can_replay: bool = False
    available_actions: list[ExecutionControlActionView] = field(default_factory=list)


@dataclass(frozen=True)
class ExecutionFindingRefView:
    finding_type: str
    location_ref: str | None = None
    message: str = ""


@dataclass(frozen=True)
class GovernanceSignalView:
    family: str
    status: str
    reason_code: str | None = None
    severity: str = "info"
    label: str | None = None
    summary: str | None = None


@dataclass(frozen=True)
class DeliveryOutcomeView:
    status: str
    destination_ref: str | None = None
    reason_code: str | None = None
    summary: str | None = None


@dataclass(frozen=True)
class ExecutionPanelViewModel:
    source_mode: str
    storage_role: str
    execution_status: str
    friendly_error: FriendlyErrorView = field(default_factory=FriendlyErrorView)
    run_identity: RunIdentityView = field(default_factory=RunIdentityView)
    progress: ExecutionProgressView = field(default_factory=ExecutionProgressView)
    active_context: ActiveExecutionContextView = field(default_factory=ActiveExecutionContextView)
    recent_events: list[ExecutionEventView] = field(default_factory=list)
    latest_outputs: list[OutputSummaryView] = field(default_factory=list)
    diagnostics: ExecutionDiagnosticsSummary = field(default_factory=ExecutionDiagnosticsSummary)
    timing: ExecutionTimingView = field(default_factory=ExecutionTimingView)
    metrics: ExecutionMetricsView = field(default_factory=ExecutionMetricsView)
    control_state: ExecutionControlStateView = field(default_factory=ExecutionControlStateView)
    related_findings: list[ExecutionFindingRefView] = field(default_factory=list)
    governance_signals: list[GovernanceSignalView] = field(default_factory=list)
    delivery_outcome: DeliveryOutcomeView | None = None
    explanation: str | None = None


def _unwrap(source: WorkingSaveModel | CommitSnapshotModel | ExecutionRecordModel | LoadedNexArtifact | None):
    if isinstance(source, LoadedNexArtifact):
        return source.parsed_model
    return source


def _iso_from_ms(timestamp_ms: int) -> str:
    return f"ms:{timestamp_ms}"


def _severity_for_event(event_type: str, payload: Mapping[str, Any] | None) -> str:
    payload = payload or {}
    if event_type in {"execution_failed", "node_failed"}:
        return "error"
    if event_type in {"warning", "execution_warning", "node_warning"}:
        return "warning"
    if payload.get("status") in {"failed", "partial", "cancelled"}:
        return "warning"
    return "info"


def _message_for_event(event_type: str, node_id: str | None, payload: Mapping[str, Any] | None, *, app_language: str) -> str:
    payload = payload or {}
    human_event_type = event_type.replace("_", " ")
    if node_id:
        base = ui_text("execution.event.base_node", app_language=app_language, fallback_text="{event_type} ({node_id})", event_type=human_event_type, node_id=node_id)
    else:
        base = ui_text("execution.event.base", app_language=app_language, fallback_text="{event_type}", event_type=human_event_type)
    if payload.get("status"):
        return ui_text("execution.event.status_suffix", app_language=app_language, fallback_text="{base}: {status}", base=base, status=payload["status"])
    if payload.get("error"):
        return ui_text("execution.event.error_suffix", app_language=app_language, fallback_text="{base}: {error}", base=base, error=payload["error"])
    return base


def _event_views_from_live_events(events: Sequence[ExecutionEvent], *, app_language: str) -> list[ExecutionEventView]:
    views: list[ExecutionEventView] = []
    for index, event in enumerate(events, start=1):
        details = None
        if event.payload:
            details = ", ".join(f"{k}={v}" for k, v in list(event.payload.items())[:3])
        views.append(
            ExecutionEventView(
                event_id=f"event-{index}",
                event_type=event.type,
                timestamp=_iso_from_ms(event.timestamp_ms),
                node_id=event.node_id,
                severity=_severity_for_event(event.type, event.payload),
                short_message=_message_for_event(event.type, event.node_id, event.payload, app_language=app_language),
                details_preview=details,
            )
        )
    return views


def _event_views_from_record(record: ExecutionRecordModel, *, app_language: str) -> list[ExecutionEventView]:
    views: list[ExecutionEventView] = []
    sequence = 1
    views.append(
        ExecutionEventView(
            event_id=f"event-{sequence}",
            event_type="execution_started",
            timestamp=record.meta.started_at,
            severity="info",
            short_message=ui_text("execution.event.execution_started", app_language=app_language),
        )
    )
    sequence += 1
    for card in record.timeline.started_nodes:
        views.append(
            ExecutionEventView(
                event_id=f"event-{sequence}",
                event_type="node_started",
                timestamp=card.started_at or record.meta.started_at,
                node_id=card.node_id,
                severity="info",
                short_message=ui_text("execution.event.node_started", app_language=app_language, node_id=card.node_id),
            )
        )
        sequence += 1
    for card in record.timeline.completed_nodes:
        severity = "error" if card.outcome == "failed" else "info"
        views.append(
            ExecutionEventView(
                event_id=f"event-{sequence}",
                event_type="node_completed",
                timestamp=card.finished_at or record.meta.finished_at or record.meta.started_at,
                node_id=card.node_id,
                severity=severity,
                short_message=ui_text("execution.event.node_completed", app_language=app_language, node_id=card.node_id, outcome=card.outcome),
                details_preview=getattr(card, "error", None),
            )
        )
        sequence += 1
    terminal_type = {
        "completed": "execution_completed",
        "failed": "execution_failed",
        "partial": "execution_completed",
        "cancelled": "execution_completed",
        "paused": "execution_paused",
        "running": "execution_running",
    }.get(record.meta.status, "execution_completed")
    views.append(
        ExecutionEventView(
            event_id=f"event-{sequence}",
            event_type=terminal_type,
            timestamp=record.meta.finished_at or record.meta.started_at,
            severity="error" if record.meta.status == "failed" else "info",
            short_message=ui_text("execution.event.execution_terminal", app_language=app_language, status=record.meta.status),
        )
    )
    return views


def _progress_from_record(record: ExecutionRecordModel, active_context: ActiveExecutionContextView, *, app_language: str) -> ExecutionProgressView:
    total_units = len(record.timeline.node_order) or len(record.node_results.results) or None
    completed_units = len(record.timeline.completed_nodes) or None
    percent = None
    if total_units and completed_units is not None and total_units > 0:
        percent = round((completed_units / total_units) * 100.0, 2)
    mode = "node_count" if total_units else "indeterminate"
    return ExecutionProgressView(
        progress_mode=mode,
        percent=percent,
        completed_units=completed_units,
        total_units=total_units,
        current_stage_label=active_context.active_stage,
        indeterminate_message=None if total_units else ui_text("execution.progress.no_node_count", app_language=app_language),
    )


def _metrics_from_record(record: ExecutionRecordModel) -> ExecutionMetricsView:
    completed = sum(1 for result in record.node_results.results if result.status == "success")
    failed = sum(1 for result in record.node_results.results if result.status == "failed")
    provider_calls = None
    plugin_calls = None
    if record.observability.provider_usage_summary:
        provider_calls = sum(int(v) for v in record.observability.provider_usage_summary.values() if isinstance(v, (int, float)))
    if record.observability.plugin_usage_summary:
        plugin_calls = sum(int(v) for v in record.observability.plugin_usage_summary.values() if isinstance(v, (int, float)))
    return ExecutionMetricsView(
        total_nodes=len(record.timeline.node_order) or len(record.node_results.results),
        completed_nodes=completed,
        failed_nodes=failed,
        artifact_count=record.artifacts.artifact_count or len(record.artifacts.artifact_refs),
        provider_call_count=provider_calls,
        plugin_call_count=plugin_calls,
    )


def _stringify_output_value(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, (int, float, bool)):
        return str(value)
    try:
        import json
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    except TypeError:
        return str(value)


def _pretty_output_value(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, (int, float, bool)):
        return str(value)
    try:
        import json
        return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2)
    except TypeError:
        return str(value)


def _preview_items_for_value(value: Any) -> tuple[str, list[str], int | None]:
    if isinstance(value, Mapping):
        items = []
        for key, item_value in list(value.items())[:3]:
            items.append(f"{key}: {_truncate_summary(_stringify_output_value(item_value), limit=60)}")
        return "structured", items, len(value)
    if isinstance(value, (list, tuple)):
        items = [_truncate_summary(_stringify_output_value(item), limit=60) for item in list(value)[:3]]
        return "list", items, len(value)
    if isinstance(value, str):
        lines = [line.strip() for line in value.splitlines() if line.strip()]
        if len(lines) > 1:
            return "multiline_text", lines[:3], len(lines)
        return "text", ([] if not value else [value]), None
    if isinstance(value, (int, float, bool)):
        return "scalar", [str(value)], None
    if value is None:
        return "empty", [], 0
    stringified = _stringify_output_value(value)
    return (("text" if stringified else "empty"), ([stringified] if stringified else []), None)


def _truncate_summary(text: str | None, *, limit: int = 120) -> str:
    if not text:
        return ""
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "…"


def _artifact_ref_for_output(record: ExecutionRecordModel, source_node: str | None) -> str | None:
    if source_node is None:
        return None
    for artifact in record.artifacts.artifact_refs:
        if artifact.producer_node == source_node and artifact.artifact_type in {"final_output", "output", "text_output", "json_output"}:
            return artifact.ref or artifact.artifact_id
    return None


def _latest_outputs_from_record(record: ExecutionRecordModel, *, app_language: str) -> list[OutputSummaryView]:
    outputs: list[OutputSummaryView] = []
    for output in record.outputs.final_outputs:
        full_value = _pretty_output_value(output.value_payload)
        display_mode, preview_items, item_count = _preview_items_for_value(output.value_payload if output.value_payload is not None else output.value_summary)
        artifact_ref = _artifact_ref_for_output(record, output.source_node)
        outputs.append(
            OutputSummaryView(
                output_ref=output.output_ref,
                source_node=output.source_node,
                value_summary=output.value_summary or _truncate_summary(full_value),
                value_type=output.value_type,
                full_value=full_value,
                is_copyable=bool(full_value),
                streaming_in_progress=False,
                display_mode=display_mode,
                preview_items=preview_items,
                item_count=item_count,
                copy_action_label=(ui_text("execution.output.copy", app_language=app_language) if full_value else None),
                artifact_ref=artifact_ref,
                open_artifact_action_label=(ui_text("execution.output.open_artifact", app_language=app_language) if artifact_ref else None),
            )
        )
    if not outputs and record.outputs.output_summary:
        display_mode, preview_items, item_count = _preview_items_for_value(record.outputs.output_summary)
        outputs.append(
            OutputSummaryView(
                output_ref="output_summary",
                value_summary=record.outputs.output_summary,
                value_type=None,
                full_value=record.outputs.output_summary,
                is_copyable=True,
                streaming_in_progress=False,
                display_mode=display_mode,
                preview_items=preview_items,
                item_count=item_count,
                copy_action_label=ui_text("execution.output.copy", app_language=app_language),
            )
        )
    return outputs


def _latest_outputs_from_live_events(
    events: Sequence[ExecutionEvent],
    *,
    fallback_record: ExecutionRecordModel | None = None,
    app_language: str,
) -> list[OutputSummaryView]:
    tracked: dict[str, OutputSummaryView] = {}
    stream_chunks: dict[str, str] = {}
    for event in events:
        payload = event.payload if isinstance(event.payload, Mapping) else {}
        if event.type == "token_chunk":
            chunk = payload.get("chunk") or payload.get("text") or payload.get("token")
            if not isinstance(chunk, str) or not chunk:
                continue
            output_ref = str(payload.get("output_ref") or payload.get("stream_id") or event.node_id or "live_stream")
            stream_chunks[output_ref] = stream_chunks.get(output_ref, "") + chunk
            full_value = stream_chunks[output_ref]
            tracked[output_ref] = OutputSummaryView(
                output_ref=output_ref,
                source_node=event.node_id,
                value_summary=_truncate_summary(full_value),
                value_type=str(payload.get("value_type") or "text"),
                full_value=full_value,
                is_copyable=True,
                streaming_in_progress=True,
                display_mode="text",
                preview_items=[_truncate_summary(full_value, limit=60)],
                item_count=None,
                copy_action_label=ui_text("execution.output.copy", app_language=app_language),
                artifact_ref=(_artifact_ref_for_output(fallback_record, event.node_id) if fallback_record is not None else None),
                open_artifact_action_label=(ui_text("execution.output.open_artifact", app_language=app_language) if fallback_record is not None and _artifact_ref_for_output(fallback_record, event.node_id) else None),
            )
            continue
        if event.type not in {"partial_output", "final_output"}:
            continue
        output_ref = str(payload.get("output_ref") or payload.get("name") or event.node_id or ("final_output" if event.type == "final_output" else "partial_output"))
        value = payload.get("value", payload.get("full_value"))
        full_value = _stringify_output_value(value)
        summary = payload.get("value_summary") or payload.get("summary") or _truncate_summary(full_value)
        value_type = payload.get("value_type")
        if not isinstance(value_type, str):
            value_type = "text" if isinstance(value, str) else (type(value).__name__ if value is not None else None)
        source_node = str(payload.get("source_node") or event.node_id) if (payload.get("source_node") is not None or event.node_id is not None) else None
        display_mode, preview_items, item_count = _preview_items_for_value(value if value is not None else summary)
        artifact_ref = _artifact_ref_for_output(fallback_record, source_node) if fallback_record is not None else None
        tracked[output_ref] = OutputSummaryView(
            output_ref=output_ref,
            source_node=source_node,
            value_summary=str(summary or ""),
            value_type=value_type,
            full_value=full_value,
            is_copyable=bool(full_value),
            streaming_in_progress=event.type == "partial_output",
            display_mode=display_mode,
            preview_items=preview_items,
            item_count=item_count,
            copy_action_label=(ui_text("execution.output.copy", app_language=app_language) if full_value else None),
            artifact_ref=artifact_ref,
            open_artifact_action_label=(ui_text("execution.output.open_artifact", app_language=app_language) if artifact_ref else None),
        )
    if tracked:
        return list(tracked.values())
    if fallback_record is not None:
        return _latest_outputs_from_record(fallback_record, app_language=app_language)
    return []


def _diagnostics_from_record(record: ExecutionRecordModel) -> ExecutionDiagnosticsSummary:
    last_error = None
    if record.diagnostics.errors:
        issue = record.diagnostics.errors[-1]
        last_error = issue.message or issue.issue_code
    return ExecutionDiagnosticsSummary(
        warning_count=len(record.diagnostics.warnings),
        error_count=len(record.diagnostics.errors),
        failure_point=record.diagnostics.failure_point,
        termination_reason=record.diagnostics.termination_reason,
        last_error_label=last_error,
    )


def _control_state_for_record(record: ExecutionRecordModel, *, app_language: str) -> ExecutionControlStateView:
    status = record.meta.status
    can_cancel = status == "running"
    can_pause = status == "running"
    can_resume = status == "paused"
    can_replay = status in {"completed", "failed", "partial", "cancelled", "paused"}
    actions = [
        ExecutionControlActionView("run", ui_text("execution.control.run", app_language=app_language), False, reason_disabled=ui_text("execution.control.historical_disabled", app_language=app_language)),
        ExecutionControlActionView("cancel", ui_text("execution.control.cancel", app_language=app_language), can_cancel, None if can_cancel else ui_text("execution.control.run_not_active", app_language=app_language)),
        ExecutionControlActionView("pause", ui_text("execution.control.pause", app_language=app_language), can_pause, None if can_pause else ui_text("execution.control.run_not_active", app_language=app_language)),
        ExecutionControlActionView("resume", ui_text("execution.control.resume", app_language=app_language), can_resume, None if can_resume else ui_text("execution.control.run_not_paused", app_language=app_language)),
        ExecutionControlActionView("replay", ui_text("execution.control.replay", app_language=app_language), can_replay, None if can_replay else ui_text("execution.control.replay_unavailable", app_language=app_language)),
    ]
    return ExecutionControlStateView(
        can_run=False,
        can_cancel=can_cancel,
        can_pause=can_pause,
        can_resume=can_resume,
        can_replay=can_replay,
        available_actions=actions,
    )


def _active_context_from_live_events(events: Sequence[ExecutionEvent], *, app_language: str) -> ActiveExecutionContextView:
    active_node: str | None = None
    active_stage: str | None = None
    for event in events:
        if event.type == "node_started" and event.node_id:
            active_node = event.node_id
            active_stage = str(event.payload.get("stage")) if isinstance(event.payload, Mapping) and event.payload.get("stage") else "node_started"
        elif event.type == "node_completed" and event.node_id == active_node:
            active_node = None
            active_stage = None
    if active_node is None:
        return ActiveExecutionContextView(status_message=ui_text("execution.context.no_active_node", app_language=app_language))
    return ActiveExecutionContextView(
        active_node_id=active_node,
        active_node_label=active_node,
        active_resource_type="runtime",
        active_stage=active_stage,
        status_message=ui_text("execution.context.executing_node", app_language=app_language, node_id=active_node),
    )


def _active_context_from_record(record: ExecutionRecordModel, *, app_language: str) -> ActiveExecutionContextView:
    if record.meta.status == "running":
        completed_ids = {card.node_id for card in record.timeline.completed_nodes}
        for node_id in record.timeline.node_order:
            if node_id not in completed_ids:
                return ActiveExecutionContextView(
                    active_node_id=node_id,
                    active_node_label=node_id,
                    active_resource_type="runtime",
                    active_stage="running",
                    status_message=ui_text("execution.context.executing_node", app_language=app_language, node_id=node_id),
                )
    return ActiveExecutionContextView(status_message=ui_text("execution.context.no_active_node", app_language=app_language))


def _status_from_source(source: WorkingSaveModel | CommitSnapshotModel | ExecutionRecordModel | None, execution_record: ExecutionRecordModel | None) -> tuple[str, str, str]:
    if execution_record is not None:
        source_mode = {
            "replay_run": "replay_session",
            "designer_test_run": "designer_test_run",
        }.get(execution_record.source.trigger_type, "execution_record")
        storage_role = "execution_record"
        return source_mode, storage_role, execution_record.meta.status

    if isinstance(source, WorkingSaveModel):
        last_run = source.runtime.last_run if isinstance(source.runtime.last_run, dict) else {}
        last_status = last_run.get("status") or last_run.get("semantic_status")
        if isinstance(last_status, str) and last_status:
            return "working_save_last_run", "working_save", last_status
        return "unknown", "working_save", "idle"
    if isinstance(source, CommitSnapshotModel):
        return "unknown", "commit_snapshot", "idle"
    return "unknown", "none", "unknown"


def _run_identity_for_record(record: ExecutionRecordModel) -> RunIdentityView:
    return RunIdentityView(
        run_id=record.meta.run_id,
        execution_id=record.meta.run_id,
        commit_id=record.source.commit_id,
        working_save_id=record.source.working_save_id,
        trigger_type=record.source.trigger_type,
        title=record.meta.title,
        description=record.meta.description,
    )


def _run_identity_for_idle_source(source: WorkingSaveModel | CommitSnapshotModel | None) -> RunIdentityView:
    if isinstance(source, WorkingSaveModel):
        last_run = source.runtime.last_run if isinstance(source.runtime.last_run, dict) else {}
        return RunIdentityView(
            run_id=(str(last_run.get("run_id")) if last_run.get("run_id") is not None else None),
            execution_id=(str(last_run.get("run_id")) if last_run.get("run_id") is not None else None),
            commit_id=(str(last_run.get("commit_id")) if last_run.get("commit_id") is not None else None),
            working_save_id=source.meta.working_save_id,
            trigger_type=(str(last_run.get("trigger_type")) if last_run.get("trigger_type") is not None else None),
            title=source.meta.name,
        )
    if isinstance(source, CommitSnapshotModel):
        return RunIdentityView(commit_id=source.meta.commit_id, working_save_id=source.meta.source_working_save_id, title=source.meta.name)
    return RunIdentityView()


def _control_state_for_idle_source(source: WorkingSaveModel | CommitSnapshotModel | None, *, app_language: str) -> ExecutionControlStateView:
    can_run = isinstance(source, (WorkingSaveModel, CommitSnapshotModel))
    if isinstance(source, CommitSnapshotModel):
        can_run = bool(source.approval.approval_completed)
    actions = [
        ExecutionControlActionView("run", ui_text("execution.control.run", app_language=app_language), can_run, None if can_run else ui_text("execution.control.target_not_runnable", app_language=app_language)),
        ExecutionControlActionView("cancel", ui_text("execution.control.cancel", app_language=app_language), False, ui_text("execution.control.no_active_run", app_language=app_language)),
        ExecutionControlActionView("pause", ui_text("execution.control.pause", app_language=app_language), False, ui_text("execution.control.no_active_run", app_language=app_language)),
        ExecutionControlActionView("resume", ui_text("execution.control.resume", app_language=app_language), False, ui_text("execution.control.no_paused_run", app_language=app_language)),
        ExecutionControlActionView("replay", ui_text("execution.control.replay", app_language=app_language), False, ui_text("execution.control.no_execution_record", app_language=app_language)),
    ]
    return ExecutionControlStateView(can_run=can_run, available_actions=actions)


def _severity_from_governance_status(status: str) -> str:
    lowered = status.lower()
    if "blocked" in lowered or lowered in {"failed", "terminated"}:
        return "error"
    if "warning" in lowered or "near" in lowered or "confirmation" in lowered:
        return "warning"
    return "info"


def _governance_summary_from_sources(source: WorkingSaveModel | CommitSnapshotModel | ExecutionRecordModel | None, execution_record: ExecutionRecordModel | None) -> dict[str, Any]:
    if execution_record is not None:
        metrics = execution_record.observability.metrics if isinstance(execution_record.observability.metrics, dict) else {}
        governance = metrics.get("governance") if isinstance(metrics.get("governance"), Mapping) else None
        recovery = metrics.get("recovery") if isinstance(metrics.get("recovery"), Mapping) else None
        policy_validation = recovery.get("policy_validation") if isinstance(recovery, Mapping) and isinstance(recovery.get("policy_validation"), Mapping) else None
        if governance is not None or policy_validation is not None:
            projected = dict(governance) if governance is not None else {}
            if policy_validation is not None:
                projected["policy_validation"] = dict(policy_validation)
            return projected
    if isinstance(source, WorkingSaveModel):
        last_run = source.runtime.last_run if isinstance(source.runtime.last_run, dict) else {}
        governance = last_run.get("governance") if isinstance(last_run.get("governance"), Mapping) else None
        if governance is not None:
            projected = dict(governance)
            policy_validation = last_run.get("policy_validation") if isinstance(last_run.get("policy_validation"), Mapping) else None
            if policy_validation is not None:
                projected["policy_validation"] = dict(policy_validation)
            return projected
        projected: dict[str, Any] = {}
        for key in (
            "launch_status",
            "safety_status",
            "safety_reason_code",
            "quota_status",
            "quota_reason_code",
            "delivery_status",
            "delivery_reason_code",
            "delivery_destination_ref",
            "reason_codes",
            "top_reason_code",
        ):
            value = last_run.get(key)
            if value is not None and value != "" and value != []:
                projected[key] = value
        policy_validation = last_run.get("policy_validation") if isinstance(last_run.get("policy_validation"), Mapping) else None
        if policy_validation is not None:
            projected["policy_validation"] = dict(policy_validation)
        return projected
    return {}


def _governance_views(summary: Mapping[str, Any], *, app_language: str) -> tuple[list[GovernanceSignalView], DeliveryOutcomeView | None]:
    signals: list[GovernanceSignalView] = []
    delivery_outcome: DeliveryOutcomeView | None = None
    for family in ("launch_status", "safety_status", "quota_status", "streaming_status", "delivery_status"):
        status = summary.get(family)
        if not isinstance(status, str) or not status:
            continue
        family_prefix = family.replace("_status", "")
        reason_code = summary.get(f"{family_prefix}_reason_code") if isinstance(summary.get(f"{family_prefix}_reason_code"), str) else None
        record = lookup_reason_code_record(reason_code) if isinstance(reason_code, str) else None
        signals.append(
            GovernanceSignalView(
                family=family,
                status=status,
                reason_code=reason_code,
                severity=(record.severity if record is not None else _severity_from_governance_status(status)),
                label=family_prefix.replace("_", " ").title(),
                summary=(record.human_summary if record is not None else None),
            )
        )
        if family == "delivery_status":
            delivery_outcome = DeliveryOutcomeView(
                status=status,
                destination_ref=(str(summary.get("delivery_destination_ref")) if summary.get("delivery_destination_ref") is not None else None),
                reason_code=reason_code,
                summary=(record.human_summary if record is not None else None),
            )
    policy_validation = summary.get("policy_validation") if isinstance(summary.get("policy_validation"), Mapping) else None
    if policy_validation is not None:
        status = str(policy_validation.get("status") or "invalid")
        reason = str(policy_validation.get("reason") or "invalid_policy")
        fallback_applied = bool(policy_validation.get("fallback_applied"))
        summary_text = ui_text(
            "execution.governance.policy_validation_invalid",
            app_language=app_language,
            fallback_text=(
                "Fallback scoring policy was invalid ({reason}). Safe defaults were applied."
                if fallback_applied
                else "Fallback scoring policy was invalid ({reason})."
            ),
            reason=reason,
        )
        signals.append(
            GovernanceSignalView(
                family="policy_validation",
                status=status,
                reason_code=reason,
                severity="warning",
                label=ui_text(
                    "execution.governance.policy_validation_label",
                    app_language=app_language,
                    fallback_text="Policy validation",
                ),
                summary=summary_text,
            )
        )
    return signals, delivery_outcome




def _friendly_error_for_execution(
    source: WorkingSaveModel | CommitSnapshotModel | ExecutionRecordModel | None,
    execution_record: ExecutionRecordModel | None,
    governance_summary: Mapping[str, Any],
    *,
    app_language: str,
) -> FriendlyErrorView:
    candidates: list[dict[str, Any]] = []

    for family_prefix in ("launch", "safety", "quota", "delivery", "streaming"):
        reason_key = f"{family_prefix}_reason_code"
        status_key = f"{family_prefix}_status"
        if isinstance(governance_summary.get(reason_key), str):
            candidates.append({
                "source_kind": family_prefix,
                "reason_code": governance_summary.get(reason_key),
                "issue_code": governance_summary.get(status_key),
                "message": governance_summary.get("summary_message") if isinstance(governance_summary.get("summary_message"), str) else None,
            })

    if execution_record is not None:
        for issue in [*execution_record.diagnostics.errors, *execution_record.diagnostics.warnings]:
            candidates.append({
                "source_kind": issue.category,
                "issue_code": issue.issue_code,
                "message": issue.message or issue.reason or issue.fix_hint,
            })
        if execution_record.diagnostics.termination_reason:
            candidates.append({
                "source_kind": "termination",
                "message": execution_record.diagnostics.termination_reason,
            })

    if isinstance(source, WorkingSaveModel):
        for error in source.runtime.errors:
            if isinstance(error, Mapping):
                candidates.append({
                    "source_kind": "runtime",
                    "issue_code": error.get("issue_code") if isinstance(error.get("issue_code"), str) else None,
                    "reason_code": error.get("reason_code") if isinstance(error.get("reason_code"), str) else None,
                    "message": error.get("message") if isinstance(error.get("message"), str) else str(error),
                })
            else:
                candidates.append({"source_kind": "runtime", "message": str(error)})

    return friendly_error_from_candidates(app_language=app_language, candidates=candidates)
def read_execution_panel_view_model(
    source: WorkingSaveModel | CommitSnapshotModel | ExecutionRecordModel | LoadedNexArtifact | None,
    *,
    execution_record: ExecutionRecordModel | None = None,
    live_events: Sequence[ExecutionEvent] | None = None,
    explanation: str | None = None,
) -> ExecutionPanelViewModel:
    """Build a UI-facing execution projection from engine-owned truth."""

    source = _unwrap(source)
    app_language = ui_language_from_sources(source, execution_record)
    if isinstance(source, ExecutionRecordModel):
        execution_record = source

    source_mode, storage_role, execution_status = _status_from_source(source, execution_record)
    if live_events:
        source_mode = "live_execution"
        if execution_status in {"idle", "unknown"}:
            execution_status = "running"

    governance_summary = _governance_summary_from_sources(source, execution_record)
    governance_signals, delivery_outcome = _governance_views(governance_summary, app_language=app_language)
    friendly_error = _friendly_error_for_execution(source, execution_record, governance_summary, app_language=app_language)

    if execution_record is not None:
        recent_events = _event_views_from_live_events(live_events, app_language=app_language) if live_events else _event_views_from_record(execution_record, app_language=app_language)
        active_context = _active_context_from_live_events(live_events, app_language=app_language) if live_events else _active_context_from_record(execution_record, app_language=app_language)
        progress = _progress_from_record(execution_record, active_context, app_language=app_language)
        return ExecutionPanelViewModel(
            source_mode=source_mode,
            storage_role=storage_role,
            execution_status=execution_status,
            friendly_error=friendly_error,
            run_identity=_run_identity_for_record(execution_record),
            progress=progress,
            active_context=active_context,
            recent_events=recent_events,
            latest_outputs=_latest_outputs_from_live_events(live_events, fallback_record=execution_record, app_language=app_language) if live_events else _latest_outputs_from_record(execution_record, app_language=app_language),
            diagnostics=_diagnostics_from_record(execution_record),
            timing=ExecutionTimingView(
                started_at=execution_record.meta.started_at,
                finished_at=execution_record.meta.finished_at,
                total_duration_ms=execution_record.timeline.total_duration_ms,
                event_count=execution_record.timeline.event_count or len(recent_events),
            ),
            metrics=_metrics_from_record(execution_record),
            control_state=_control_state_for_record(execution_record, app_language=app_language),
            related_findings=[],
            governance_signals=governance_signals,
            delivery_outcome=delivery_outcome,
            explanation=explanation,
        )

    return ExecutionPanelViewModel(
        source_mode=source_mode,
        storage_role=storage_role,
        execution_status=execution_status,
        friendly_error=friendly_error,
        run_identity=_run_identity_for_idle_source(source),
        progress=ExecutionProgressView(progress_mode="indeterminate", indeterminate_message=ui_text("execution.panel.no_execution_record", app_language=app_language)),
        active_context=ActiveExecutionContextView(status_message=ui_text("execution.panel.no_active_execution", app_language=app_language)),
        diagnostics=ExecutionDiagnosticsSummary(),
        control_state=_control_state_for_idle_source(source, app_language=app_language),
        governance_signals=governance_signals,
        delivery_outcome=delivery_outcome,
        explanation=explanation,
    )


__all__ = [
    "RunIdentityView",
    "ExecutionProgressView",
    "ActiveExecutionContextView",
    "ExecutionEventView",
    "OutputSummaryView",
    "ExecutionDiagnosticsSummary",
    "ExecutionTimingView",
    "ExecutionMetricsView",
    "ExecutionControlActionView",
    "ExecutionControlStateView",
    "ExecutionFindingRefView",
    "GovernanceSignalView",
    "DeliveryOutcomeView",
    "ExecutionPanelViewModel",
    "read_execution_panel_view_model",
]
