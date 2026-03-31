from __future__ import annotations

import json
import shutil
import tempfile
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from .model import CircuitModel, EdgeModel, NodeModel
from .validator import validate_circuit


SUPPORTED_SCHEMA = "hyper-ai.definition_language"
SUPPORTED_VERSION = "1.0.0"


@dataclass
class LegacyNexFormat:
    kind: str
    version: str


@dataclass
class LegacyCircuitMeta:
    circuit_id: str
    name: str
    entry_node_id: str
    description: Optional[str] = None


@dataclass
class LegacyNodeSpec:
    node_id: str
    kind: str
    prompt_ref: Optional[str] = None
    provider_ref: Optional[str] = None
    plugin_refs: List[str] = field(default_factory=list)


@dataclass
class LegacyEdgeSpec:
    edge_id: str
    src_node_id: str
    dst_node_id: str


@dataclass
class LegacyFlowRule:
    rule_id: str
    node_id: str
    policy: str


@dataclass
class LegacyRetryConfig:
    max_attempts: int


@dataclass
class LegacyExecutionConfig:
    strict_determinism: bool = False
    node_failure_policies: Dict[str, str] = field(default_factory=dict)
    node_fallback_map: Dict[str, str] = field(default_factory=dict)
    node_retry_policy: Dict[str, LegacyRetryConfig] = field(default_factory=dict)


@dataclass
class LegacyPromptResource:
    template: str


@dataclass
class LegacyProviderResource:
    provider_type: str
    model: str
    config: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LegacyResourceSpec:
    prompts: Dict[str, LegacyPromptResource] = field(default_factory=dict)
    providers: Dict[str, LegacyProviderResource] = field(default_factory=dict)


@dataclass
class LegacyPluginSpec:
    plugin_id: str
    version: Optional[str] = None
    required: bool = True


@dataclass
class LegacyNexCircuit:
    format: LegacyNexFormat
    circuit: LegacyCircuitMeta
    nodes: List[LegacyNodeSpec]
    edges: List[LegacyEdgeSpec]
    flow: List[LegacyFlowRule]
    execution: LegacyExecutionConfig
    resources: LegacyResourceSpec
    plugins: List[LegacyPluginSpec]


class LegacyNexValidationError(Exception):
    pass


class LegacyNexBundle:
    def __init__(self, temp_dir: Path):
        self.temp_dir = temp_dir
        self.circuit_path = temp_dir / "circuit.nex"
        self.plugins_dir = temp_dir / "plugins"

    def cleanup(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)


def load_definition(path: Path) -> CircuitModel:
    data: Dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))

    if data.get("schema") != SUPPORTED_SCHEMA:
        raise ValueError("Invalid schema")

    if data.get("schema_version") != SUPPORTED_VERSION:
        raise ValueError("Unsupported schema_version")

    validate_circuit(data)

    nodes = {n["id"]: NodeModel(id=n["id"], raw=n) for n in data["nodes"]}

    edges = [
        EdgeModel(
            from_id=e["from"],
            to_id=e["to"],
            kind=e["kind"],
            raw=e,
        )
        for e in data["edges"]
    ]

    return CircuitModel(
        circuit_id=data["circuit_id"],
        nodes=nodes,
        edges=edges,
        entry_node_id=data["entry_node_id"],
        raw=data,
    )


def validate_legacy_nex(circuit: LegacyNexCircuit) -> None:
    if circuit.format.kind != "nexa.circuit":
        raise LegacyNexValidationError("Invalid format.kind")

    node_ids = {node.node_id for node in circuit.nodes}
    if circuit.circuit.entry_node_id not in node_ids:
        raise LegacyNexValidationError("entry_node_id not found in nodes")

    for edge in circuit.edges:
        if edge.src_node_id not in node_ids:
            raise LegacyNexValidationError(f"Edge src not found: {edge.src_node_id}")
        if edge.dst_node_id not in node_ids:
            raise LegacyNexValidationError(f"Edge dst not found: {edge.dst_node_id}")

    for node_id, retry in circuit.execution.node_retry_policy.items():
        if retry.max_attempts < 1:
            raise LegacyNexValidationError(f"Invalid retry config for {node_id}")


def _load_legacy_retry_policy(raw: Dict[str, Any]) -> Dict[str, LegacyRetryConfig]:
    return {
        node_id: LegacyRetryConfig(max_attempts=value["max_attempts"])
        for node_id, value in raw.items()
    }


def _load_legacy_resources(raw: Dict[str, Any]) -> LegacyResourceSpec:
    prompts = {
        key: LegacyPromptResource(template=value["template"])
        for key, value in raw.get("prompts", {}).items()
    }
    providers = {
        key: LegacyProviderResource(
            provider_type=value["provider_type"],
            model=value["model"],
            config=value.get("config", {}),
        )
        for key, value in raw.get("providers", {}).items()
    }
    return LegacyResourceSpec(prompts=prompts, providers=providers)


def deserialize_legacy_nex(data: Dict[str, Any]) -> LegacyNexCircuit:
    return LegacyNexCircuit(
        format=LegacyNexFormat(**data["format"]),
        circuit=LegacyCircuitMeta(**data["circuit"]),
        nodes=[LegacyNodeSpec(**item) for item in data.get("nodes", [])],
        edges=[LegacyEdgeSpec(**item) for item in data.get("edges", [])],
        flow=[LegacyFlowRule(**item) for item in data.get("flow", [])],
        execution=LegacyExecutionConfig(
            strict_determinism=data.get("execution", {}).get("strict_determinism", False),
            node_failure_policies=data.get("execution", {}).get("node_failure_policies", {}),
            node_fallback_map=data.get("execution", {}).get("node_fallback_map", {}),
            node_retry_policy=_load_legacy_retry_policy(
                data.get("execution", {}).get("node_retry_policy", {})
            ),
        ),
        resources=_load_legacy_resources(data.get("resources", {})),
        plugins=[LegacyPluginSpec(**item) for item in data.get("plugins", [])],
    )


def load_legacy_nex_file(file_path: str) -> LegacyNexCircuit:
    return deserialize_legacy_nex(json.loads(Path(file_path).read_text(encoding="utf-8")))


def load_legacy_nex_bundle(bundle_path: str, *, require_plugins: bool = True) -> LegacyNexBundle:
    bundle_file = Path(bundle_path)
    if not bundle_file.exists():
        raise RuntimeError(f"Bundle not found: {bundle_path}")

    temp_dir = Path(tempfile.mkdtemp(prefix="nexa_bundle_"))
    with zipfile.ZipFile(bundle_file, "r") as zf:
        zf.extractall(temp_dir)

    bundle = LegacyNexBundle(temp_dir)
    if not bundle.circuit_path.exists():
        bundle.cleanup()
        raise RuntimeError("circuit.nex missing in bundle")
    if require_plugins and not bundle.plugins_dir.exists():
        bundle.cleanup()
        raise RuntimeError("plugins/ missing in bundle")
    return bundle
