from __future__ import annotations

import json
import shutil
import tempfile
import zipfile
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from src.cli.savefile_runtime import is_savefile_contract
from src.engine.cli_legacy_nex_plugins import validate_plugins_from_nex
from src.engine.engine import Engine, RetryConfig as EngineRetryConfig
from src.engine.model import Channel, FlowRule as EngineFlowRule
from src.engine.types import FlowPolicy, NodeFailurePolicy, NodeStatus



@dataclass
class NexFormat:
    kind: str
    version: str


@dataclass
class CircuitMeta:
    circuit_id: str
    name: str
    entry_node_id: str
    description: Optional[str] = None


@dataclass
class NodeSpec:
    node_id: str
    kind: str
    prompt_ref: Optional[str] = None
    provider_ref: Optional[str] = None
    plugin_refs: List[str] = field(default_factory=list)


@dataclass
class EdgeSpec:
    edge_id: str
    src_node_id: str
    dst_node_id: str


@dataclass
class NexFlowRule:
    rule_id: str
    node_id: str
    policy: str


@dataclass
class NexRetryConfig:
    max_attempts: int


@dataclass
class ExecutionConfig:
    strict_determinism: bool = False
    node_failure_policies: Dict[str, str] = field(default_factory=dict)
    node_fallback_map: Dict[str, str] = field(default_factory=dict)
    node_retry_policy: Dict[str, NexRetryConfig] = field(default_factory=dict)


@dataclass
class PromptResource:
    template: str


@dataclass
class ProviderResource:
    provider_type: str
    model: str
    config: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ResourceSpec:
    prompts: Dict[str, PromptResource] = field(default_factory=dict)
    providers: Dict[str, ProviderResource] = field(default_factory=dict)


@dataclass
class PluginSpec:
    plugin_id: str
    version: Optional[str] = None
    required: bool = True


@dataclass
class NexCircuit:
    format: NexFormat
    circuit: CircuitMeta
    nodes: List[NodeSpec]
    edges: List[EdgeSpec]
    flow: List[NexFlowRule]
    execution: ExecutionConfig
    resources: ResourceSpec
    plugins: List[PluginSpec]


class NexValidationError(Exception):
    pass


def validate_nex(circuit: NexCircuit) -> List[str]:
    warnings: List[str] = []

    if circuit.format.kind != "nexa.circuit":
        raise NexValidationError("Invalid format.kind")

    if circuit.format.version != "1.0.0":
        warnings.append("Unknown format version")

    node_ids = {node.node_id for node in circuit.nodes}
    if circuit.circuit.entry_node_id not in node_ids:
        raise NexValidationError("entry_node_id not found in nodes")

    for edge in circuit.edges:
        if edge.src_node_id not in node_ids:
            raise NexValidationError(f"Edge src not found: {edge.src_node_id}")
        if edge.dst_node_id not in node_ids:
            raise NexValidationError(f"Edge dst not found: {edge.dst_node_id}")

    for node_id, retry in circuit.execution.node_retry_policy.items():
        if retry.max_attempts < 1:
            raise NexValidationError(f"Invalid retry config for {node_id}")

    plugin_ids = {p.plugin_id for p in circuit.plugins}
    for node in circuit.nodes:
        for ref in node.plugin_refs:
            if ref not in plugin_ids:
                warnings.append(f"Plugin not declared: {ref}")

    return warnings


def serialize_nex(circuit: NexCircuit) -> Dict[str, Any]:
    return asdict(circuit)


def save_nex_file(circuit: NexCircuit, file_path: str) -> None:
    path = Path(file_path)
    if path.suffix != ".nex":
        raise ValueError("legacy NexCircuit files must use .nex extension")

    data = serialize_nex(circuit)

    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


ApplyBaselinePolicy = Callable[[Dict[str, Any], Optional[str], Optional[str]], tuple[Dict[str, Any], int]]
WritePayload = Callable[[Dict[str, Any], Optional[str]], None]
RunSavefile = Callable[[str, Optional[str], Optional[str], Optional[str]], int]

_NEX_META_KEY = "_nex_adapter"


class NexBundle:
    def __init__(self, temp_dir: Path):
        self.temp_dir = temp_dir
        self.circuit_path = temp_dir / "circuit.nex"
        self.plugins_dir = temp_dir / "plugins"

    def cleanup(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)


def _load_retry_policy(raw: Dict[str, Any]) -> Dict[str, NexRetryConfig]:
    return {
        node_id: NexRetryConfig(max_attempts=value["max_attempts"])
        for node_id, value in raw.items()
    }


def _load_resources(raw: Dict[str, Any]) -> ResourceSpec:
    prompts = {
        key: PromptResource(template=value["template"])
        for key, value in raw.get("prompts", {}).items()
    }
    providers = {
        key: ProviderResource(
            provider_type=value["provider_type"],
            model=value["model"],
            config=value.get("config", {}),
        )
        for key, value in raw.get("providers", {}).items()
    }
    return ResourceSpec(prompts=prompts, providers=providers)


def deserialize_nex(data: Dict[str, Any]) -> NexCircuit:
    """Convert dict data into NexCircuit dataclass tree."""
    return NexCircuit(
        format=NexFormat(**data["format"]),
        circuit=CircuitMeta(**data["circuit"]),
        nodes=[NodeSpec(**item) for item in data.get("nodes", [])],
        edges=[EdgeSpec(**item) for item in data.get("edges", [])],
        flow=[NexFlowRule(**item) for item in data.get("flow", [])],
        execution=ExecutionConfig(
            strict_determinism=data.get("execution", {}).get("strict_determinism", False),
            node_failure_policies=data.get("execution", {}).get("node_failure_policies", {}),
            node_fallback_map=data.get("execution", {}).get("node_fallback_map", {}),
            node_retry_policy=_load_retry_policy(
                data.get("execution", {}).get("node_retry_policy", {})
            ),
        ),
        resources=_load_resources(data.get("resources", {})),
        plugins=[PluginSpec(**item) for item in data.get("plugins", [])],
    )


def load_nex_file(file_path: str) -> NexCircuit:
    """Load a .nex JSON file and convert it into NexCircuit."""
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return deserialize_nex(data)


def _node_specs_map(circuit: NexCircuit) -> Dict[str, Dict[str, Any]]:
    return {
        node.node_id: {
            "kind": node.kind,
            "prompt_ref": node.prompt_ref,
            "provider_ref": node.provider_ref,
            "plugin_refs": list(node.plugin_refs),
        }
        for node in circuit.nodes
    }


def _engine_meta_from_nex(circuit: NexCircuit) -> Dict[str, Any]:
    return {
        _NEX_META_KEY: {
            "format": asdict(circuit.format),
            "circuit": {
                "circuit_id": circuit.circuit.circuit_id,
                "name": circuit.circuit.name,
                "description": circuit.circuit.description,
            },
            "node_specs": _node_specs_map(circuit),
            "resources": asdict(circuit.resources),
            "plugins": [asdict(plugin) for plugin in circuit.plugins],
            "strict_determinism": circuit.execution.strict_determinism,
        }
    }


def build_engine_from_nex(circuit: NexCircuit) -> Engine:
    """Convert NexCircuit into Engine.

    This adapter intentionally reconstructs only the structural/runtime state that
    the current Engine datamodel can represent. Prompt/provider/plugin resources
    are preserved in engine.meta for reverse conversion.
    """
    validate_nex(circuit)

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
        meta=_engine_meta_from_nex(circuit),
        node_failure_policies=node_failure_policies,
        node_fallback_map=dict(circuit.execution.node_fallback_map),
        node_retry_policy=node_retry_policy,
    )


def build_nex_from_engine(engine: Engine) -> NexCircuit:
    """Convert Engine back into NexCircuit.

    If the Engine originated from a NexCircuit, rich metadata is restored from
    engine.meta[_NEX_META_KEY]. Otherwise, sane defaults are used.
    """
    adapter_meta: Dict[str, Any] = dict(engine.meta.get(_NEX_META_KEY, {}))

    format_meta = adapter_meta.get("format", {"kind": "nexa.circuit", "version": "1.0.0"})
    circuit_meta = adapter_meta.get("circuit", {})
    node_specs_map = adapter_meta.get("node_specs", {})
    resources_raw = adapter_meta.get("resources", {})
    plugins_raw = adapter_meta.get("plugins", [])
    strict_determinism = bool(adapter_meta.get("strict_determinism", False))

    nodes = []
    for node_id in engine.node_ids:
        spec = node_specs_map.get(node_id, {})
        nodes.append(
            NodeSpec(
                node_id=node_id,
                kind=spec.get("kind", "execution"),
                prompt_ref=spec.get("prompt_ref"),
                provider_ref=spec.get("provider_ref"),
                plugin_refs=list(spec.get("plugin_refs", [])),
            )
        )

    edges = [
        EdgeSpec(
            edge_id=channel.channel_id,
            src_node_id=channel.src_node_id,
            dst_node_id=channel.dst_node_id,
        )
        for channel in engine.channels
    ]

    flow = [
        NexFlowRule(
            rule_id=rule.rule_id,
            node_id=rule.node_id,
            policy=rule.policy.value,
        )
        for rule in engine.flow
    ]

    execution = ExecutionConfig(
        strict_determinism=strict_determinism,
        node_failure_policies={
            node_id: policy.value for node_id, policy in engine.node_failure_policies.items()
        },
        node_fallback_map=dict(engine.node_fallback_map),
        node_retry_policy={
            node_id: NexRetryConfig(max_attempts=retry.max_attempts)
            for node_id, retry in engine.node_retry_policy.items()
        },
    )

    resources = ResourceSpec(
        prompts={
            key: PromptResource(**value)
            for key, value in resources_raw.get("prompts", {}).items()
        },
        providers={
            key: ProviderResource(**value)
            for key, value in resources_raw.get("providers", {}).items()
        },
    )

    plugins = [PluginSpec(**plugin) for plugin in plugins_raw]

    return NexCircuit(
        format=NexFormat(**format_meta),
        circuit=CircuitMeta(
            circuit_id=circuit_meta.get("circuit_id", engine.entry_node_id),
            name=circuit_meta.get("name", engine.entry_node_id),
            entry_node_id=engine.entry_node_id,
            description=circuit_meta.get("description"),
        ),
        nodes=nodes,
        edges=edges,
        flow=flow,
        execution=execution,
        resources=resources,
        plugins=plugins,
    )


def load_nex_bundle(bundle_path: str, *, require_plugins: bool = True) -> NexBundle:
    bundle_file = Path(bundle_path)

    if not bundle_file.exists():
        raise RuntimeError(f"Bundle not found: {bundle_path}")

    temp_dir = Path(tempfile.mkdtemp(prefix="nexa_bundle_"))

    with zipfile.ZipFile(bundle_file, "r") as zf:
        zf.extractall(temp_dir)

    circuit = temp_dir / "circuit.nex"
    plugins = temp_dir / "plugins"

    if not circuit.exists():
        raise RuntimeError("circuit.nex missing in bundle")

    if require_plugins and not plugins.exists():
        raise RuntimeError("plugins/ missing in bundle")

    return NexBundle(temp_dir)


def _node_attempts(node_meta: Optional[Dict[str, Any]], status: NodeStatus) -> int:
    if node_meta and isinstance(node_meta.get("retry"), dict):
        retry_meta = node_meta["retry"]
        if isinstance(retry_meta.get("attempt_count"), int):
            return retry_meta["attempt_count"]
    if status in (NodeStatus.SUCCESS, NodeStatus.FAILURE):
        return 1
    return 0


def build_trace_summary(circuit_id: str, trace) -> Dict[str, Any]:
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


def run_legacy_nex(
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
        validate_plugins_from_nex(raw_data, bundle_path)

    circuit = load_nex_file(circuit_path)
    engine = build_engine_from_nex(circuit)
    trace = engine.execute(revision_id="cli")
    payload = build_trace_summary(circuit.circuit.circuit_id, trace)
    payload, exit_code = apply_baseline_policy(payload, baseline_path, policy_config_path)
    write_or_print_payload(payload, out_path)
    return exit_code


def run_legacy_nex_bundle(
    bundle_path: str,
    *,
    out_path: Optional[str] = None,
    baseline_path: Optional[str] = None,
    policy_config_path: Optional[str] = None,
    run_savefile_nex: RunSavefile,
    apply_baseline_policy: ApplyBaselinePolicy,
    write_or_print_payload: WritePayload,
) -> int:
    bundle = load_nex_bundle(bundle_path, require_plugins=False)
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
        validate_plugins_from_nex(raw_data, str(bundle.temp_dir))

        circuit = load_nex_file(str(bundle.circuit_path))
        engine = build_engine_from_nex(circuit)
        trace = engine.execute(revision_id="cli")
        payload = build_trace_summary(circuit.circuit.circuit_id, trace)
        payload, exit_code = apply_baseline_policy(payload, baseline_path, policy_config_path)
        write_or_print_payload(payload, out_path)
        return exit_code
    finally:
        bundle.cleanup()
