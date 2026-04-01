from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, Optional

from src.circuit.loader import load_legacy_nex_bundle
from src.circuit.runtime_adapter import (
    load_engine_from_legacy_nex_path,
    prepare_engine_from_legacy_nex_bundle,
)
from src.contracts.savefile_executor_aligned import SavefileExecutor
from src.contracts.savefile_loader import load_savefile_from_path
from src.contracts.savefile_provider_builder import build_provider_registry_from_savefile
from src.contracts.savefile_validator import validate_savefile
from src.engine.cli_policy_integration import apply_baseline_policy


def is_savefile_contract(circuit_path: str) -> bool:
    try:
        data = json.loads(Path(circuit_path).read_text(encoding="utf-8"))
    except Exception:
        return False

    if not isinstance(data, dict):
        return False

    required = {"meta", "circuit", "resources", "state", "ui"}
    return required.issubset(set(data.keys()))


def execute_savefile(
    circuit_path: str,
    *,
    input_overrides: Mapping[str, Any] | None = None,
    run_id: str = "cli",
):
    savefile = load_savefile_from_path(circuit_path)

    if input_overrides:
        savefile.state.input.update(dict(input_overrides))

    validate_savefile(savefile)
    provider_registry = build_provider_registry_from_savefile(savefile)
    executor = SavefileExecutor(provider_registry)
    trace = executor.execute(savefile, run_id=run_id)
    return savefile, trace


def build_savefile_trace_summary(savefile_name: str, trace: Any) -> dict[str, Any]:
    nodes: dict[str, dict[str, Any]] = {}
    any_failure = False

    for node_id, node_result in (getattr(trace, "node_results", {}) or {}).items():
        status = str(getattr(node_result, "status", "failure")).upper()
        nodes[node_id] = {
            "status": status,
            "attempts": 1 if status in ("SUCCESS", "FAILURE") else 0,
        }
        if status == "FAILURE":
            any_failure = True

    trace_status = str(getattr(trace, "status", "success")).upper()
    if trace_status == "FAILURE":
        any_failure = True

    return {
        "circuit_id": savefile_name,
        "status": "FAILURE" if any_failure else "SUCCESS",
        "nodes": nodes,
    }


def write_or_print_payload(payload: dict[str, Any], out_path: Optional[str]) -> None:
    if out_path:
        out_file = Path(out_path)
        out_file.parent.mkdir(parents=True, exist_ok=True)
        out_file.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    else:
        print(json.dumps(payload, indent=2, ensure_ascii=False))


def _emit_policy_wrapped_payload(
    payload: dict[str, Any],
    out_path: Optional[str],
    baseline_path: Optional[str],
    policy_config_path: Optional[str],
) -> int:
    payload, exit_code = apply_baseline_policy(payload, baseline_path, policy_config_path)
    write_or_print_payload(payload, out_path)
    return exit_code


def run_savefile_nex(
    circuit_path: str,
    out_path: Optional[str] = None,
    baseline_path: Optional[str] = None,
    policy_config_path: Optional[str] = None,
) -> int:
    savefile, trace = execute_savefile(circuit_path, run_id="cli")
    payload = build_savefile_trace_summary(savefile.meta.name, trace)
    return _emit_policy_wrapped_payload(payload, out_path, baseline_path, policy_config_path)


def build_legacy_trace_summary(circuit_id: str, trace: Any) -> dict[str, Any]:
    nodes: dict[str, dict[str, Any]] = {}
    any_failure = False

    for node_id, node_trace in trace.nodes.items():
        status = node_trace.node_status
        attempts = 1
        node_meta = getattr(node_trace, "meta", None)
        if node_meta and isinstance(node_meta.get("retry"), dict):
            retry_meta = node_meta["retry"]
            if isinstance(retry_meta.get("attempt_count"), int):
                attempts = retry_meta["attempt_count"]
        nodes[node_id] = {
            "status": status.value.upper(),
            "attempts": attempts if status.value.upper() in ("SUCCESS", "FAILURE") else 0,
        }
        if status.value.upper() == "FAILURE":
            any_failure = True

    return {
        "circuit_id": circuit_id,
        "status": "FAILURE" if any_failure else "SUCCESS",
        "nodes": nodes,
    }


def run_legacy_nex(
    circuit_path: str,
    out_path: Optional[str] = None,
    bundle_path: Optional[str] = None,
    baseline_path: Optional[str] = None,
    policy_config_path: Optional[str] = None,
) -> int:
    if is_savefile_contract(circuit_path):
        return run_savefile_nex(circuit_path, out_path, baseline_path, policy_config_path)

    circuit, engine = load_engine_from_legacy_nex_path(
        circuit_path,
        bundle_path=bundle_path,
    )
    trace = engine.execute(revision_id="cli")
    payload = build_legacy_trace_summary(circuit.circuit.circuit_id, trace)
    return _emit_policy_wrapped_payload(payload, out_path, baseline_path, policy_config_path)


def run_legacy_nex_bundle(
    bundle_path: str,
    out_path: Optional[str] = None,
    baseline_path: Optional[str] = None,
    policy_config_path: Optional[str] = None,
) -> int:
    bundle = load_legacy_nex_bundle(bundle_path, require_plugins=False)
    try:
        if is_savefile_contract(str(bundle.circuit_path)):
            return run_savefile_nex(
                str(bundle.circuit_path),
                out_path,
                baseline_path,
                policy_config_path,
            )

        circuit, engine = prepare_engine_from_legacy_nex_bundle(bundle)
        trace = engine.execute(revision_id="cli")
        payload = build_legacy_trace_summary(circuit.circuit.circuit_id, trace)
        return _emit_policy_wrapped_payload(payload, out_path, baseline_path, policy_config_path)
    finally:
        bundle.cleanup()
