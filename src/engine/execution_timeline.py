from dataclasses import dataclass
from typing import List, Optional, Dict

from src.engine.execution_event import ExecutionEvent


@dataclass
class NodeExecutionSpan:
    node_id: str
    start_ms: int
    end_ms: int
    duration_ms: int
    status: str
    error: Optional[str] = None


@dataclass
class ExecutionTimeline:
    execution_id: str
    start_ms: int
    end_ms: int
    duration_ms: int
    node_spans: List[NodeExecutionSpan]


@dataclass
class ExecutionProfile:
    execution_id: str
    total_duration_ms: int
    total_nodes: int
    succeeded_nodes: int
    failed_nodes: int
    slowest_node_id: Optional[str]
    slowest_node_duration_ms: Optional[int]


@dataclass
class ExecutionTimelineBundle:
    timeline: ExecutionTimeline
    profile: ExecutionProfile


class ExecutionTimelineBuilder:

    def build(self, events: List[ExecutionEvent]) -> ExecutionTimelineBundle:
        execution_id: Optional[str] = None
        execution_start: Optional[int] = None
        execution_end: Optional[int] = None

        node_start_times: Dict[str, int] = {}
        node_spans: List[NodeExecutionSpan] = []

        for event in events:

            if execution_id is None:
                execution_id = event.execution_id

            if event.type == "execution_started":
                execution_start = event.timestamp_ms

            elif event.type in {"execution_completed", "execution_failed", "execution_paused"}:
                execution_end = event.timestamp_ms

            elif event.type == "execution_resumed":
                # Resume is an informational run-linking event; start/end remain anchored
                # to execution_started / terminal execution_* events.
                continue

            elif event.type == "node_started":
                if event.node_id:
                    node_start_times[event.node_id] = event.timestamp_ms

            elif event.type == "node_completed":
                if event.node_id is None:
                    continue

                start = node_start_times.get(event.node_id)
                if start is None:
                    continue

                end = event.timestamp_ms
                duration = end - start

                payload = event.payload or {}

                status = payload.get("status", "success")
                error = payload.get("error")

                span = NodeExecutionSpan(
                    node_id=event.node_id,
                    start_ms=start,
                    end_ms=end,
                    duration_ms=duration,
                    status=status,
                    error=error,
                )

                node_spans.append(span)

        if execution_start is None or execution_end is None or execution_id is None:
            raise ValueError("Invalid event sequence: missing execution start/end")

        execution_duration = execution_end - execution_start

        # ---- profiler calculation ----

        total_nodes = len(node_spans)
        succeeded_nodes = sum(1 for s in node_spans if s.status == "success")
        failed_nodes = sum(1 for s in node_spans if s.status == "failed")

        slowest_node_id: Optional[str] = None
        slowest_node_duration: Optional[int] = None

        if node_spans:
            slowest = max(node_spans, key=lambda s: s.duration_ms)
            slowest_node_id = slowest.node_id
            slowest_node_duration = slowest.duration_ms

        timeline = ExecutionTimeline(
            execution_id=execution_id,
            start_ms=execution_start,
            end_ms=execution_end,
            duration_ms=execution_duration,
            node_spans=node_spans,
        )

        profile = ExecutionProfile(
            execution_id=execution_id,
            total_duration_ms=execution_duration,
            total_nodes=total_nodes,
            succeeded_nodes=succeeded_nodes,
            failed_nodes=failed_nodes,
            slowest_node_id=slowest_node_id,
            slowest_node_duration_ms=slowest_node_duration,
        )

        return ExecutionTimelineBundle(
            timeline=timeline,
            profile=profile,
        )