from typing import Callable, Dict, Any, Optional, Union
from .model import CircuitModel
from .condition_eval import evaluate
from .node_execution import run_node_stages, is_staged_handler
from src.utils.observability import is_observability_enabled, make_event, emit_event

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


    raw = getattr(model, "raw", {})
    obs_enabled = is_observability_enabled(raw)
    run_id = None
    try:
        if trace is not None:
            run_id = trace.run_id
    except Exception:
        run_id = None
    if run_id is None:
        run_id = str(raw.get("run_id") or "run-unknown")

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

        if obs_enabled:
            emit_event(make_event(run_id=run_id, circuit_id=model.circuit_id, node_id=current_id, stage=None, event='node.enter'))

        node = model.nodes[current_id]
        if is_staged_handler(engine_executor):
            last_result = run_node_stages(
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

        if obs_enabled:
            emit_event(make_event(run_id=run_id, circuit_id=model.circuit_id, node_id=current_id, stage=None, event='node.exit', success=True))

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
                if obs_enabled:
                    emit_event(make_event(run_id=run_id, circuit_id=model.circuit_id, node_id=None, stage=None, event='circuit.finish', success=True))
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

import json
from dataclasses import asdict
from pathlib import Path
from typing import List

from src.circuit.loader import (
    LegacyNexBundle,
    LegacyNexCircuit,
    load_legacy_nex_bundle,
    load_legacy_nex_file,
    validate_legacy_nex,
)
from src.engine.engine import Engine, RetryConfig as EngineRetryConfig
from src.engine.model import Channel, FlowRule as EngineFlowRule
from src.engine.types import FlowPolicy, NodeFailurePolicy
from src.platform.external_loader import validate_legacy_nex_plugins

_NEX_META_KEY = "_nex_adapter"


def _legacy_node_specs_map(circuit: LegacyNexCircuit) -> Dict[str, Dict[str, Any]]:
    return {
        node.node_id: {
            "kind": node.kind,
            "prompt_ref": node.prompt_ref,
            "provider_ref": node.provider_ref,
            "plugin_refs": list(node.plugin_refs),
        }
        for node in circuit.nodes
    }


def _legacy_engine_meta_from_nex(circuit: LegacyNexCircuit) -> Dict[str, Any]:
    return {
        _NEX_META_KEY: {
            "format": asdict(circuit.format),
            "circuit": {
                "circuit_id": circuit.circuit.circuit_id,
                "name": circuit.circuit.name,
                "description": circuit.circuit.description,
            },
            "node_specs": _legacy_node_specs_map(circuit),
            "resources": asdict(circuit.resources),
            "plugins": [asdict(plugin) for plugin in circuit.plugins],
            "strict_determinism": circuit.execution.strict_determinism,
        }
    }


def build_engine_from_legacy_nex(circuit: LegacyNexCircuit) -> Engine:
    validate_legacy_nex(circuit)

    channels: List[Channel] = [
        Channel(
            channel_id=edge.edge_id,
            src_node_id=edge.src_node_id,
            dst_node_id=edge.dst_node_id,
        )
        for edge in circuit.edges
    ]
    flow: List[EngineFlowRule] = [
        EngineFlowRule(
            rule_id=rule.rule_id,
            node_id=rule.node_id,
            policy=FlowPolicy(rule.policy),
        )
        for rule in circuit.flow
    ]
    node_failure_policies = {
        node_id: NodeFailurePolicy(policy)
        for node_id, policy in circuit.execution.node_failure_policies.items()
    }
    node_retry_policy = {
        node_id: EngineRetryConfig(max_attempts=retry.max_attempts)
        for node_id, retry in circuit.execution.node_retry_policy.items()
    }

    return Engine(
        entry_node_id=circuit.circuit.entry_node_id,
        node_ids=[node.node_id for node in circuit.nodes],
        channels=channels,
        flow=flow,
        meta=_legacy_engine_meta_from_nex(circuit),
        node_failure_policies=node_failure_policies,
        node_fallback_map=dict(circuit.execution.node_fallback_map),
        node_retry_policy=node_retry_policy,
    )


def load_engine_from_legacy_nex_path(
    circuit_path: str,
    *,
    bundle_path: Optional[str] = None,
) -> tuple[LegacyNexCircuit, Engine]:
    if bundle_path:
        raw_data = json.loads(Path(circuit_path).read_text(encoding="utf-8"))
        validate_legacy_nex_plugins(raw_data, bundle_path)

    circuit = load_legacy_nex_file(circuit_path)
    engine = build_engine_from_legacy_nex(circuit)
    return circuit, engine


def open_legacy_nex_bundle(bundle_path: str) -> LegacyNexBundle:
    return load_legacy_nex_bundle(bundle_path, require_plugins=False)


def prepare_engine_from_legacy_nex_bundle(
    bundle: LegacyNexBundle,
) -> tuple[LegacyNexCircuit, Engine]:
    if not bundle.plugins_dir.exists():
        raise RuntimeError("plugins/ missing in bundle")

    raw_data = json.loads(bundle.circuit_path.read_text(encoding="utf-8"))
    validate_legacy_nex_plugins(raw_data, str(bundle.temp_dir))
    circuit = load_legacy_nex_file(str(bundle.circuit_path))
    engine = build_engine_from_legacy_nex(circuit)
    return circuit, engine
