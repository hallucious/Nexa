"""Compatibility wrapper for the legacy engine CLI surface.

The canonical public CLI entrypoint is ``src.cli.nexa_cli:main`` as exposed
through ``pyproject.toml`` and ``nexa.py``. This module remains only as a
bounded compatibility surface for engine-specific tests and old callers that
still import ``src.engine.cli`` directly.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
import zipfile
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence

from src.cli.savefile_runtime import execute_savefile_summary, is_savefile_contract
from src.contracts.regression_reason_codes import (
    NODE_REMOVED_SUCCESS,
    NODE_SUCCESS_TO_FAILURE,
    NODE_SUCCESS_TO_SKIPPED,
)
from src.engine.engine import Engine, RetryConfig as EngineRetryConfig
from src.engine.execution_regression_detector import NodeRegression, RegressionResult
from src.engine.execution_regression_policy import (
    POLICY_STATUS_FAIL,
    POLICY_STATUS_WARN,
    evaluate_regression_policy,
)
from src.engine.model import Channel, FlowRule as EngineFlowRule
from src.engine.types import FlowPolicy, NodeFailurePolicy, NodeStatus

CANONICAL_PUBLIC_CLI = "src.cli.nexa_cli:main"
_NEX_META_KEY = "_nex_adapter"

ApplyBaselinePolicy = Callable[[Dict[str, Any], Optional[str], Optional[str]], tuple[Dict[str, Any], int]]
WritePayload = Callable[[Dict[str, Any], Optional[str]], None]
RunSavefile = Callable[[str, Optional[str], Optional[str], Optional[str]], int]


@dataclass
class _LegacyPluginResolutionResult:
    found: List[str]
    missing_required: List[str]
    missing_optional: List[str]
    version_mismatch: List[str]


@dataclass
class _LegacyNexFormat:
    kind: str
    version: str


@dataclass
class _LegacyCircuitMeta:
    circuit_id: str
    name: str
    entry_node_id: str
    description: Optional[str] = None


@dataclass
class _LegacyNodeSpec:
    node_id: str
    kind: str
    prompt_ref: Optional[str] = None
    provider_ref: Optional[str] = None
    plugin_refs: List[str] = field(default_factory=list)


@dataclass
class _LegacyEdgeSpec:
    edge_id: str
    src_node_id: str
    dst_node_id: str


@dataclass
class _LegacyFlowRule:
    rule_id: str
    node_id: str
    policy: str


@dataclass
class _LegacyRetryConfig:
    max_attempts: int


@dataclass
class _LegacyExecutionConfig:
    strict_determinism: bool = False
    node_failure_policies: Dict[str, str] = field(default_factory=dict)
    node_fallback_map: Dict[str, str] = field(default_factory=dict)
    node_retry_policy: Dict[str, _LegacyRetryConfig] = field(default_factory=dict)


@dataclass
class _LegacyPromptResource:
    template: str


@dataclass
class _LegacyProviderResource:
    provider_type: str
    model: str
    config: Dict[str, Any] = field(default_factory=dict)


@dataclass
class _LegacyResourceSpec:
    prompts: Dict[str, _LegacyPromptResource] = field(default_factory=dict)
    providers: Dict[str, _LegacyProviderResource] = field(default_factory=dict)


@dataclass
class _LegacyPluginSpec:
    plugin_id: str
    version: Optional[str] = None
    required: bool = True


@dataclass
class _LegacyNexCircuit:
    format: _LegacyNexFormat
    circuit: _LegacyCircuitMeta
    nodes: List[_LegacyNodeSpec]
    edges: List[_LegacyEdgeSpec]
    flow: List[_LegacyFlowRule]
    execution: _LegacyExecutionConfig
    resources: _LegacyResourceSpec
    plugins: List[_LegacyPluginSpec]


class _LegacyNexValidationError(Exception):
    pass


class _LegacyNexBundle:
    def __init__(self, temp_dir: Path):
        self.temp_dir = temp_dir
        self.circuit_path = temp_dir / "circuit.nex"
        self.plugins_dir = temp_dir / "plugins"

    def cleanup(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="hai-engine",
        description="Hyper-AI Engine CLI (Engine-native execution)",
    )

    subparsers = parser.add_subparsers(dest="command")

    run_parser = subparsers.add_parser("run", help="Execute a .nex circuit file")
    run_parser.add_argument("circuit", type=str, help="Path to .nex circuit file")
    run_parser.add_argument(
        "--out",
        type=str,
        required=False,
        help="Write execution summary JSON to file",
    )
    run_parser.add_argument(
        "--bundle",
        type=str,
        required=False,
        help="Path to bundle root that contains plugins/",
    )
    run_parser.add_argument(
        "--baseline",
        type=str,
        required=False,
        help="Path to baseline execution summary JSON for regression gating",
    )
    run_parser.add_argument(
        "--policy-config",
        type=str,
        required=False,
        help="Path to policy config JSON",
    )

    parser.add_argument("--input", type=str, required=False)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--entry-node-id", type=str, required=False)
    parser.add_argument("--node-ids", type=str, required=False)

    return parser


def _parse_node_ids(node_ids_csv: Optional[str]) -> Optional[List[str]]:
    if not node_ids_csv:
        return None
    items = [s.strip() for s in node_ids_csv.split(",")]
    items = [s for s in items if s]
    return items or None


def _load_legacy_plugin_metadata(plugin_dir: Path) -> Optional[Dict[str, Any]]:
    meta_file = plugin_dir / "plugin.json"
    if not meta_file.exists():
        return None

    data = json.loads(meta_file.read_text(encoding="utf-8"))
    required_fields = ["plugin_id", "version", "entrypoint", "type"]
    for field_name in required_fields:
        if field_name not in data:
            raise RuntimeError(f"Missing field '{field_name}' in {meta_file}")

    if data["plugin_id"] != plugin_dir.name:
        raise RuntimeError(f"plugin_id mismatch: {data['plugin_id']} != {plugin_dir.name}")

    return data


def _scan_legacy_plugins_dir(plugins_dir: Path) -> Dict[str, Dict[str, Any]]:
    if not plugins_dir.exists():
        return {}

    result: Dict[str, Dict[str, Any]] = {}
    for plugin_dir in plugins_dir.iterdir():
        if not plugin_dir.is_dir():
            continue

        metadata = _load_legacy_plugin_metadata(plugin_dir)
        if metadata is None:
            metadata = {
                "plugin_id": plugin_dir.name,
                "version": None,
                "entrypoint": None,
                "type": "legacy",
            }

        result[plugin_dir.name] = metadata

    return result


def _resolve_legacy_plugins(
    plugin_refs: List[Dict[str, Any]],
    plugins_dir: Path,
) -> _LegacyPluginResolutionResult:
    available = _scan_legacy_plugins_dir(plugins_dir)

    found: List[str] = []
    missing_required: List[str] = []
    missing_optional: List[str] = []
    version_mismatch: List[str] = []

    for ref in plugin_refs:
        plugin_id = ref.get("plugin_id")
        required = ref.get("required", True)
        expected_version = ref.get("version")

        if plugin_id not in available:
            if required:
                missing_required.append(plugin_id)
            else:
                missing_optional.append(plugin_id)
            continue

        actual_version = available[plugin_id].get("version")
        if expected_version and actual_version is not None and expected_version != actual_version:
            version_mismatch.append(f"{plugin_id}:{expected_version}!={actual_version}")
            continue

        found.append(plugin_id)

    return _LegacyPluginResolutionResult(
        found=found,
        missing_required=missing_required,
        missing_optional=missing_optional,
        version_mismatch=version_mismatch,
    )


def _validate_plugins_from_nex(nex_data: Dict[str, Any], bundle_path: str) -> None:
    plugin_refs = nex_data.get("plugins")
    if not isinstance(plugin_refs, list):
        plugin_refs = nex_data.get("plugin_refs", [])
    result = _resolve_legacy_plugins(plugin_refs, Path(bundle_path) / "plugins")
    if result.missing_required:
        raise RuntimeError(f"Missing required plugins: {result.missing_required}")
    if result.version_mismatch:
        raise RuntimeError(f"Plugin version mismatch: {result.version_mismatch}")


def _validate_legacy_nex(circuit: _LegacyNexCircuit) -> None:
    if circuit.format.kind != "nexa.circuit":
        raise _LegacyNexValidationError("Invalid format.kind")

    node_ids = {node.node_id for node in circuit.nodes}
    if circuit.circuit.entry_node_id not in node_ids:
        raise _LegacyNexValidationError("entry_node_id not found in nodes")

    for edge in circuit.edges:
        if edge.src_node_id not in node_ids:
            raise _LegacyNexValidationError(f"Edge src not found: {edge.src_node_id}")
        if edge.dst_node_id not in node_ids:
            raise _LegacyNexValidationError(f"Edge dst not found: {edge.dst_node_id}")

    for node_id, retry in circuit.execution.node_retry_policy.items():
        if retry.max_attempts < 1:
            raise _LegacyNexValidationError(f"Invalid retry config for {node_id}")


def _load_legacy_retry_policy(raw: Dict[str, Any]) -> Dict[str, _LegacyRetryConfig]:
    return {
        node_id: _LegacyRetryConfig(max_attempts=value["max_attempts"])
        for node_id, value in raw.items()
    }


def _load_legacy_resources(raw: Dict[str, Any]) -> _LegacyResourceSpec:
    prompts = {
        key: _LegacyPromptResource(template=value["template"])
        for key, value in raw.get("prompts", {}).items()
    }
    providers = {
        key: _LegacyProviderResource(
            provider_type=value["provider_type"],
            model=value["model"],
            config=value.get("config", {}),
        )
        for key, value in raw.get("providers", {}).items()
    }
    return _LegacyResourceSpec(prompts=prompts, providers=providers)


def _deserialize_legacy_nex(data: Dict[str, Any]) -> _LegacyNexCircuit:
    return _LegacyNexCircuit(
        format=_LegacyNexFormat(**data["format"]),
        circuit=_LegacyCircuitMeta(**data["circuit"]),
        nodes=[_LegacyNodeSpec(**item) for item in data.get("nodes", [])],
        edges=[_LegacyEdgeSpec(**item) for item in data.get("edges", [])],
        flow=[_LegacyFlowRule(**item) for item in data.get("flow", [])],
        execution=_LegacyExecutionConfig(
            strict_determinism=data.get("execution", {}).get("strict_determinism", False),
            node_failure_policies=data.get("execution", {}).get("node_failure_policies", {}),
            node_fallback_map=data.get("execution", {}).get("node_fallback_map", {}),
            node_retry_policy=_load_legacy_retry_policy(
                data.get("execution", {}).get("node_retry_policy", {})
            ),
        ),
        resources=_load_legacy_resources(data.get("resources", {})),
        plugins=[_LegacyPluginSpec(**item) for item in data.get("plugins", [])],
    )


def _load_legacy_nex_file(file_path: str) -> _LegacyNexCircuit:
    return _deserialize_legacy_nex(json.loads(Path(file_path).read_text(encoding="utf-8")))


def _legacy_node_specs_map(circuit: _LegacyNexCircuit) -> Dict[str, Dict[str, Any]]:
    return {
        node.node_id: {
            "kind": node.kind,
            "prompt_ref": node.prompt_ref,
            "provider_ref": node.provider_ref,
            "plugin_refs": list(node.plugin_refs),
        }
        for node in circuit.nodes
    }


def _legacy_engine_meta_from_nex(circuit: _LegacyNexCircuit) -> Dict[str, Any]:
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


def _build_engine_from_legacy_nex(circuit: _LegacyNexCircuit) -> Engine:
    _validate_legacy_nex(circuit)

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


def _load_legacy_nex_bundle(bundle_path: str, *, require_plugins: bool = True) -> _LegacyNexBundle:
    bundle_file = Path(bundle_path)
    if not bundle_file.exists():
        raise RuntimeError(f"Bundle not found: {bundle_path}")

    temp_dir = Path(tempfile.mkdtemp(prefix="nexa_bundle_"))
    with zipfile.ZipFile(bundle_file, "r") as zf:
        zf.extractall(temp_dir)

    bundle = _LegacyNexBundle(temp_dir)
    if not bundle.circuit_path.exists():
        bundle.cleanup()
        raise RuntimeError("circuit.nex missing in bundle")
    if require_plugins and not bundle.plugins_dir.exists():
        bundle.cleanup()
        raise RuntimeError("plugins/ missing in bundle")
    return bundle


def _node_attempts(node_meta: Optional[Dict[str, Any]], status: NodeStatus) -> int:
    if node_meta and isinstance(node_meta.get("retry"), dict):
        retry_meta = node_meta["retry"]
        if isinstance(retry_meta.get("attempt_count"), int):
            return retry_meta["attempt_count"]
    if status in (NodeStatus.SUCCESS, NodeStatus.FAILURE):
        return 1
    return 0


def _build_trace_summary(circuit_id: str, trace: Any) -> Dict[str, Any]:
    nodes: Dict[str, Dict[str, Any]] = {}
    any_failure = False

    for node_id, node_trace in trace.nodes.items():
        status = node_trace.node_status
        nodes[node_id] = {
            "status": status.value.upper(),
            "attempts": _node_attempts(getattr(node_trace, "meta", None), status),
        }
        if status == NodeStatus.FAILURE:
            any_failure = True

    return {
        "circuit_id": circuit_id,
        "status": "FAILURE" if any_failure else "SUCCESS",
        "nodes": nodes,
    }


def _run_legacy_nex(
    circuit_path: str,
    *,
    out_path: Optional[str] = None,
    bundle_path: Optional[str] = None,
    baseline_path: Optional[str] = None,
    policy_config_path: Optional[str] = None,
    apply_baseline_policy: ApplyBaselinePolicy,
    write_or_print_payload: WritePayload,
) -> int:
    if bundle_path:
        raw_data = json.loads(Path(circuit_path).read_text(encoding="utf-8"))
        _validate_plugins_from_nex(raw_data, bundle_path)

    circuit = _load_legacy_nex_file(circuit_path)
    engine = _build_engine_from_legacy_nex(circuit)
    trace = engine.execute(revision_id="cli")
    payload = _build_trace_summary(circuit.circuit.circuit_id, trace)
    payload, exit_code = apply_baseline_policy(payload, baseline_path, policy_config_path)
    write_or_print_payload(payload, out_path)
    return exit_code


def _run_legacy_nex_bundle(
    bundle_path: str,
    *,
    out_path: Optional[str] = None,
    baseline_path: Optional[str] = None,
    policy_config_path: Optional[str] = None,
    run_savefile_nex: RunSavefile,
    apply_baseline_policy: ApplyBaselinePolicy,
    write_or_print_payload: WritePayload,
) -> int:
    bundle = _load_legacy_nex_bundle(bundle_path, require_plugins=False)
    try:
        if is_savefile_contract(str(bundle.circuit_path)):
            return run_savefile_nex(
                str(bundle.circuit_path),
                out_path,
                baseline_path,
                policy_config_path,
            )

        if not bundle.plugins_dir.exists():
            raise RuntimeError("plugins/ missing in bundle")

        raw_data = json.loads(bundle.circuit_path.read_text(encoding="utf-8"))
        _validate_plugins_from_nex(raw_data, str(bundle.temp_dir))

        circuit = _load_legacy_nex_file(str(bundle.circuit_path))
        engine = _build_engine_from_legacy_nex(circuit)
        trace = engine.execute(revision_id="cli")
        payload = _build_trace_summary(circuit.circuit.circuit_id, trace)
        payload, exit_code = apply_baseline_policy(payload, baseline_path, policy_config_path)
        write_or_print_payload(payload, out_path)
        return exit_code
    finally:
        bundle.cleanup()


def _build_regression_result_from_summaries(
    baseline_payload: Dict[str, Any],
    current_payload: Dict[str, Any],
) -> RegressionResult:
    baseline_nodes = baseline_payload.get("nodes") or {}
    current_nodes = current_payload.get("nodes") or {}

    regressions: List[NodeRegression] = []

    for node_id in sorted(set(baseline_nodes) | set(current_nodes)):
        left = baseline_nodes.get(node_id)
        right = current_nodes.get(node_id)

        left_status = (left or {}).get("status")
        right_status = (right or {}).get("status")

        if left_status == "SUCCESS" and right_status == "FAILURE":
            regressions.append(
                NodeRegression(
                    node_id=node_id,
                    reason_code=NODE_SUCCESS_TO_FAILURE,
                    left_status="success",
                    right_status="failure",
                )
            )
        elif left_status == "SUCCESS" and right_status == "SKIPPED":
            regressions.append(
                NodeRegression(
                    node_id=node_id,
                    reason_code=NODE_SUCCESS_TO_SKIPPED,
                    left_status="success",
                    right_status="skipped",
                )
            )
        elif left_status == "SUCCESS" and right is None:
            regressions.append(
                NodeRegression(
                    node_id=node_id,
                    reason_code=NODE_REMOVED_SUCCESS,
                    left_status="success",
                    right_status=None,
                )
            )

    if regressions:
        return RegressionResult(status="regression", nodes=regressions)
    return RegressionResult(status="clean")


def _load_policy_overrides(policy_config_path: Optional[str]) -> Optional[Dict[str, str]]:
    if not policy_config_path:
        return None
    payload = json.loads(Path(policy_config_path).read_text(encoding="utf-8"))
    overrides = payload.get("overrides")
    if overrides is None:
        return None
    if not isinstance(overrides, dict):
        raise ValueError("policy config 'overrides' must be an object")

    normalized: Dict[str, str] = {}
    for reason_code, severity in overrides.items():
        if not isinstance(reason_code, str) or not isinstance(severity, str):
            raise ValueError("policy config overrides must map strings to strings")
        normalized[reason_code] = severity
    return normalized


def _render_policy_output(policy_result: Any) -> str:
    status = getattr(policy_result, "status", None)
    reasons = list(getattr(policy_result, "reasons", []) or [])

    lines: List[str] = []
    if status is not None:
        lines.append(f"Status: {status}")
    if reasons:
        lines.extend(reasons)
    return "\n".join(lines) if lines else str(policy_result)


def _apply_baseline_policy(
    payload: Dict[str, Any],
    baseline_path: Optional[str],
    policy_config_path: Optional[str] = None,
) -> tuple[Dict[str, Any], int]:
    if not baseline_path:
        return payload, 0

    baseline_payload = json.loads(Path(baseline_path).read_text(encoding="utf-8"))
    regression_result = _build_regression_result_from_summaries(baseline_payload, payload)
    overrides = _load_policy_overrides(policy_config_path)
    decision = evaluate_regression_policy(regression_result, overrides)

    enriched = dict(payload)
    enriched["policy"] = {
        "status": decision.status,
        "reasons": list(decision.reasons),
        "display": _render_policy_output(decision),
    }

    if decision.status == POLICY_STATUS_FAIL:
        return enriched, 2
    if decision.status == POLICY_STATUS_WARN:
        return enriched, 1
    return enriched, 0


def _write_or_print_payload(payload: Dict[str, Any], out_path: Optional[str]) -> None:
    if out_path:
        out_file = Path(out_path)
        out_file.parent.mkdir(parents=True, exist_ok=True)
        out_file.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    else:
        print(json.dumps(payload, indent=2, ensure_ascii=False))


def run_savefile_nex(
    circuit_path: str,
    out_path: Optional[str] = None,
    baseline_path: Optional[str] = None,
    policy_config_path: Optional[str] = None,
) -> int:
    _, _, payload = execute_savefile_summary(circuit_path, run_id="cli")
    payload, exit_code = _apply_baseline_policy(payload, baseline_path, policy_config_path)
    _write_or_print_payload(payload, out_path)
    return exit_code


def run_nex(
    circuit_path: str,
    out_path: Optional[str] = None,
    bundle_path: Optional[str] = None,
    baseline_path: Optional[str] = None,
    policy_config_path: Optional[str] = None,
) -> int:
    if is_savefile_contract(circuit_path):
        return run_savefile_nex(circuit_path, out_path, baseline_path, policy_config_path)

    return _run_legacy_nex(
        circuit_path,
        out_path=out_path,
        bundle_path=bundle_path,
        baseline_path=baseline_path,
        policy_config_path=policy_config_path,
        apply_baseline_policy=_apply_baseline_policy,
        write_or_print_payload=_write_or_print_payload,
    )


def run_nex_bundle(
    bundle_path: str,
    out_path: Optional[str] = None,
    baseline_path: Optional[str] = None,
    policy_config_path: Optional[str] = None,
) -> int:
    return _run_legacy_nex_bundle(
        bundle_path,
        out_path=out_path,
        baseline_path=baseline_path,
        policy_config_path=policy_config_path,
        run_savefile_nex=run_savefile_nex,
        apply_baseline_policy=_apply_baseline_policy,
        write_or_print_payload=_write_or_print_payload,
    )


def run_engine(
    input_path: Optional[str],
    dry_run: bool,
    entry_node_id: Optional[str],
    node_ids: Optional[List[str]],
) -> int:
    if dry_run:
        print("[Engine CLI] Dry run successful.")
        return 0

    if not entry_node_id or not node_ids:
        print("[Engine CLI] Execution placeholder.")
        return 0

    engine = Engine(entry_node_id=entry_node_id, node_ids=node_ids)
    trace = engine.execute(revision_id="cli")
    has_failure = any(node.node_status == NodeStatus.FAILURE for node in trace.nodes.values())

    if not has_failure:
        print("[Engine CLI] Execution completed.")
        return 0

    print("[Engine CLI] Execution failed.")
    return 1


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.command == "run":
        if str(args.circuit).endswith(".nexb"):
            return run_nex_bundle(
                args.circuit,
                getattr(args, "out", None),
                getattr(args, "baseline", None),
                getattr(args, "policy_config", None),
            )
        return run_nex(
            args.circuit,
            getattr(args, "out", None),
            getattr(args, "bundle", None),
            getattr(args, "baseline", None),
            getattr(args, "policy_config", None),
        )

    node_ids = _parse_node_ids(args.node_ids)
    return run_engine(args.input, args.dry_run, args.entry_node_id, node_ids)


if __name__ == "__main__":
    sys.exit(main())
