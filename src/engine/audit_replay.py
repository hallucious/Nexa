
from __future__ import annotations

import json
import tempfile
import zipfile
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any, Dict

from src.circuit.circuit_runner import CircuitRunner
from src.engine.execution_determinism_validator import ExecutionDeterminismValidator
from src.engine.execution_replay import ExecutionReplayEngine, ReplayPlan
from src.engine.node_execution_runtime import NodeExecutionRuntime
from src.platform.provider_executor import ProviderExecutor
from src.platform.provider_registry import ProviderRegistry
from src.contracts.provider_contract import ProviderRequest, ProviderResult


class _EchoProvider:
    def execute(self, request: ProviderRequest) -> ProviderResult:
        return ProviderResult(
            output=request.prompt,
            raw_text=request.prompt,
            structured=None,
            artifacts=[],
            trace={"provider": "echo"},
            error=None,
        )


class _ReplayRegistry:
    def __init__(self, configs: Dict[str, dict]):
        self._configs = dict(configs)

    def get(self, config_id: str) -> dict:
        if config_id not in self._configs:
            raise KeyError(f"execution config not found: {config_id}")
        return self._configs[config_id]


def _normalize(value: Any) -> Any:
    if is_dataclass(value) and not isinstance(value, type):
        return {k: _normalize(v) for k, v in asdict(value).items()}
    if isinstance(value, dict):
        return {str(k): _normalize(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_normalize(v) for v in value]
    return value


def replay_audit_pack(audit_zip_path: str) -> dict:
    audit_path = Path(audit_zip_path)
    if not audit_path.exists():
        raise FileNotFoundError(f"file not found: {audit_zip_path}")

    with tempfile.TemporaryDirectory(prefix="nexa_audit_replay_") as tmp:
        root = Path(tmp)
        with zipfile.ZipFile(audit_path, "r") as zf:
            zf.extractall(root)

        replay_file = root / "replay_payload.json"
        if not replay_file.exists():
            raise ValueError("audit pack missing replay_payload.json")

        try:
            replay_payload = json.loads(replay_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid replay_payload.json: {exc}") from exc

        if not isinstance(replay_payload, dict):
            raise ValueError("replay_payload.json must contain a JSON object")

        execution_id = replay_payload.get("execution_id", "unknown-execution")
        node_order = replay_payload.get("node_order", [])
        circuit = replay_payload.get("circuit", {})
        configs = replay_payload.get("execution_configs", {})
        input_state = replay_payload.get("input_state", {})
        expected_outputs = replay_payload.get("expected_outputs", {})

        if not isinstance(node_order, list) or not all(isinstance(n, str) for n in node_order) or not node_order:
            raise ValueError("replay payload node_order must be a non-empty list of strings")
        if not isinstance(circuit, dict) or not circuit:
            raise ValueError("replay payload circuit must be a non-empty object")
        if not isinstance(configs, dict) or not configs:
            raise ValueError("replay payload execution_configs must be a non-empty object")
        if not isinstance(input_state, dict):
            raise ValueError("replay payload input_state must be an object")
        if not isinstance(expected_outputs, dict) or not expected_outputs:
            raise ValueError("replay payload expected_outputs must be a non-empty object")

        provider_registry = ProviderRegistry()
        provider_registry.register("echo", _EchoProvider())
        executor = ProviderExecutor(provider_registry)
        runtime = NodeExecutionRuntime(provider_executor=executor)
        runner = CircuitRunner(runtime, _ReplayRegistry(configs))

        replay_engine = ExecutionReplayEngine()
        replay_result = replay_engine.replay(
            plan=ReplayPlan(execution_id=execution_id, node_order=node_order),
            circuit_runner=runner,
            circuit=circuit,
            input_state=input_state,
            expected_outputs=expected_outputs,
        )

        validator = ExecutionDeterminismValidator()
        report = validator.validate(
            execution_id=execution_id,
            expected_outputs=expected_outputs,
            replay_result=replay_result,
        )

        differences = []
        for node_result in report.node_results:
            if not node_result.deterministic:
                reason = node_result.reason or "unknown difference"
                differences.append(f"node {node_result.node_id}: {reason}")

        return {
            "status": "PASS" if report.deterministic else "FAIL",
            "execution_id": execution_id,
            "differences": differences,
            "report": _normalize(report),
        }
