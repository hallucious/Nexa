from typing import Callable, Dict, Any, Optional, Union
from .model import CircuitModel
from .condition_eval import evaluate
from .node_execution import run_node_pipeline, is_pipeline_handler

# --- CT-TRACE v1.0.0: minimal integration (signature unchanged) ---
# Trace is stored in model.raw to avoid changing execute_circuit() signature.
# Enable by setting: model.raw["trace_enabled"] = True
#
# When enabled, this function will create (or reuse) a CircuitTrace instance
# under: model.raw["trace"]


def _trace_enabled(model: CircuitModel) -> bool:
    try:
        return bool(getattr(model, "raw", {}).get("trace_enabled") is True)
    except Exception:
        return False


def execute_circuit(model: CircuitModel, engine_executor: Union[Callable[[str, Dict[str, Any]], Dict[str, Any]], Dict[str, Any]]) -> Dict[str, Any]:
    trace = None
    NodeTrace = SelectedEdge = ConditionResult = None  # type: ignore
    if _trace_enabled(model):
        from .trace import CircuitTrace, NodeTrace, SelectedEdge, ConditionResult, now_iso  # local import
        trace = model.raw.get("trace")
        if trace is None:
            trace = CircuitTrace(circuit_id=model.circuit_id)
            model.raw["trace"] = trace

    current_id = model.entry_node_id
    visited = set()
    last_result: Dict[str, Any] = {}

    while True:
        if current_id in visited:
            raise ValueError("Unexpected cycle during execution")
        visited.add(current_id)

        node_trace = None
        if trace is not None:
            node_trace = NodeTrace(node_id=current_id, entered_at=now_iso())
            trace.nodes.append(node_trace)

        node = model.nodes[current_id]
        if is_pipeline_handler(engine_executor):
            last_result = run_node_pipeline(
                node_id=current_id,
                node_raw=node.raw,
                input_payload=last_result,
                handler=engine_executor,
            )
        else:
            # Backward compatible: callable treated as CORE handler
            last_result = engine_executor(current_id, node.raw)  # type: ignore[misc]


        if node_trace is not None:
            node_trace.exited_at = now_iso()
            node_trace.status = "success"

        edges_from = [e for e in model.edges if e.from_id == current_id]

        next_edges = [e for e in edges_from if e.kind == "next"]
        conditional_edges = [e for e in edges_from if e.kind == "conditional"]
        other_edges = [e for e in edges_from if e.kind not in {"next", "conditional"}]

        if other_edges:
            raise ValueError("Unsupported edge type in Phase2")

        if len(next_edges) > 1:
            raise ValueError("Multiple next edges not supported")

        if next_edges:
            if node_trace is not None:
                node_trace.selected_edge = SelectedEdge(
                    from_node_id=current_id,
                    to_node_id=next_edges[0].to_id,
                    edge_id=None,
                    priority=None,
                )
            current_id = next_edges[0].to_id
            continue

        if conditional_edges:
            # priority required
            for e in conditional_edges:
                if "priority" not in e.raw:
                    raise ValueError("Conditional edge missing priority")

            conditional_edges = sorted(conditional_edges, key=lambda e: e.raw["priority"])

            chosen = None
            for e in conditional_edges:
                cond = e.raw.get("condition", {})
                expr = cond.get("expr")
                if expr is None:
                    raise ValueError("Conditional edge missing expr")

                ok: Optional[bool] = None
                err: Optional[str] = None
                try:
                    ok = evaluate(expr, last_result)
                except Exception as ex:
                    err = str(ex)
                    # record best-effort, then re-raise to preserve existing behavior
                    if node_trace is not None:
                        node_trace.condition_result = ConditionResult(expression=expr, value=ok, error=err)
                    raise
                else:
                    if node_trace is not None:
                        node_trace.condition_result = ConditionResult(expression=expr, value=ok, error=err)

                if ok:
                    chosen = e
                    break

            if chosen is None:
                if trace is not None:
                    trace.final_status = "success"
                    trace.finished_at = now_iso()
                return last_result

            if node_trace is not None:
                node_trace.selected_edge = SelectedEdge(
                    from_node_id=current_id,
                    to_node_id=chosen.to_id,
                    edge_id=None,
                    priority=chosen.raw.get("priority"),
                )
            current_id = chosen.to_id
            continue

        if trace is not None:
            trace.final_status = "success"
            trace.finished_at = now_iso()
        return last_result
