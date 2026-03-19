from __future__ import annotations

import json
import tempfile
import zipfile
from pathlib import Path
from typing import Any, Dict

from src.circuit.circuit_runner import CircuitRunner
from src.engine.execution_determinism_validator import ExecutionDeterminismValidator
from src.engine.execution_replay import ExecutionReplayEngine, ReplayPlanner
from src.engine.execution_timeline import ExecutionTimeline, NodeExecutionSpan


class AuditReplayError(Exception):
    pass


class _InlineRegistry:
    def __init__(self, configs: Dict[str, Dict[str, Any]]):
        self._configs = configs

    def get(self, config_id: str):
        return self._configs[config_id]


class _InlineRuntime:
    def __init__(self, outputs: Dict[str, Any]):
        self._outputs = outputs

    def execute_by_config_id(self, registry, config_id: str, state: Dict[str, Any]):
        class Result:
            def __init__(self, output: Any):
                self.output = output

        if config_id not in self._outputs:
            raise KeyError(f"missing replay output for config: {config_id}")
        return Result(self._outputs[config_id])


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise AuditReplayError(f"missing required file in audit pack: {path.name}") from exc
    except json.JSONDecodeError as exc:
        raise AuditReplayError(f"invalid JSON in audit pack file: {path.name}") from exc


def _build_timeline(payload: Dict[str, Any]) -> ExecutionTimeline:
    try:
        spans = [
            NodeExecutionSpan(
                node_id=str(item["node_id"]),
                start_ms=int(item["start_ms"]),
                end_ms=int(item["end_ms"]),
                duration_ms=int(item["duration_ms"]),
                status=str(item.get("status", "success")),
                error=item.get("error"),
            )
            for item in payload["node_spans"]
        ]
        return ExecutionTimeline(
            execution_id=str(payload["execution_id"]),
            start_ms=int(payload["start_ms"]),
            end_ms=int(payload["end_ms"]),
            duration_ms=int(payload["duration_ms"]),
            node_spans=spans,
        )
    except KeyError as exc:
        raise AuditReplayError(f"timeline payload missing field: {exc.args[0]}") from exc


def replay_audit_pack(audit_zip_path: str) -> Dict[str, Any]:
    audit_path = Path(audit_zip_path)
    if not audit_path.exists():
        raise AuditReplayError(f"audit pack not found: {audit_zip_path}")

    with tempfile.TemporaryDirectory(prefix="nexa_audit_replay_") as tmp:
        tmp_root = Path(tmp)
        try:
            with zipfile.ZipFile(audit_path, "r") as zf:
                zf.extractall(tmp_root)
        except zipfile.BadZipFile as exc:
            raise AuditReplayError(f"invalid audit pack zip: {audit_zip_path}") from exc

        # Always require core files from export path.
        _load_json(tmp_root / "execution_trace.json")
        _load_json(tmp_root / "metadata.json")
        _load_json(tmp_root / "summary.json")

        replay_payload_path = tmp_root / "replay_payload.json"
        replay_payload = _load_json(replay_payload_path)
        if not isinstance(replay_payload, dict):
            raise AuditReplayError("replay_payload.json must contain a JSON object")

        required = ["timeline", "circuit", "input_state", "expected_outputs", "configs", "replay_outputs"]
        missing = [key for key in required if key not in replay_payload]
        if missing:
            raise AuditReplayError("replay_payload.json missing required fields: " + ", ".join(missing))

        timeline = _build_timeline(replay_payload["timeline"])
        planner = ReplayPlanner()
        plan = planner.build_plan(timeline)

        runtime = _InlineRuntime(outputs=dict(replay_payload["replay_outputs"]))
        registry = _InlineRegistry(configs=dict(replay_payload["configs"]))
        runner = CircuitRunner(runtime, registry)

        replay_result = ExecutionReplayEngine().replay(
            plan=plan,
            circuit_runner=runner,
            circuit=dict(replay_payload["circuit"]),
            input_state=dict(replay_payload["input_state"]),
            expected_outputs=dict(replay_payload["expected_outputs"]),
        )

        report = ExecutionDeterminismValidator().validate(
            execution_id=plan.execution_id,
            expected_outputs=dict(replay_payload["expected_outputs"]),
            replay_result=replay_result,
        )

        differences = []
        for node_result in report.node_results:
            if not node_result.deterministic:
                differences.append({
                    "node_id": node_result.node_id,
                    "reason": node_result.reason,
                    "expected_output": node_result.expected_output,
                    "replay_output": node_result.replay_output,
                })

        return {
            "status": "PASS" if report.deterministic else "FAIL",
            "execution_id": report.execution_id,
            "differences": differences,
        }
