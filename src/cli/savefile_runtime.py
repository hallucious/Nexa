from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, Optional

from src.circuit.runtime_adapter import (
    execute_legacy_nex_bundle_summary,
    execute_legacy_nex_summary,
    open_legacy_nex_bundle,
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


def execute_savefile_summary(
    circuit_path: str,
    *,
    input_overrides: Mapping[str, Any] | None = None,
    run_id: str = "cli",
) -> tuple[Any, Any, dict[str, Any]]:
    savefile, trace = execute_savefile(
        circuit_path,
        input_overrides=input_overrides,
        run_id=run_id,
    )
    payload = build_savefile_trace_summary(savefile.meta.name, trace)
    return savefile, trace, payload


def write_or_print_payload(payload: dict[str, Any], out_path: Optional[str]) -> None:
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
    payload, exit_code = apply_baseline_policy(payload, baseline_path, policy_config_path)
    write_or_print_payload(payload, out_path)
    return exit_code


def run_legacy_nex(
    circuit_path: str,
    out_path: Optional[str] = None,
    bundle_path: Optional[str] = None,
    baseline_path: Optional[str] = None,
    policy_config_path: Optional[str] = None,
) -> int:
    if is_savefile_contract(circuit_path):
        return run_savefile_nex(circuit_path, out_path, baseline_path, policy_config_path)

    payload = execute_legacy_nex_summary(
        circuit_path,
        bundle_path=bundle_path,
        run_id="cli",
    )
    payload, exit_code = apply_baseline_policy(payload, baseline_path, policy_config_path)
    write_or_print_payload(payload, out_path)
    return exit_code


def run_legacy_nex_bundle(
    bundle_path: str,
    out_path: Optional[str] = None,
    baseline_path: Optional[str] = None,
    policy_config_path: Optional[str] = None,
) -> int:
    bundle = open_legacy_nex_bundle(bundle_path)
    try:
        if is_savefile_contract(str(bundle.circuit_path)):
            return run_savefile_nex(
                str(bundle.circuit_path),
                out_path,
                baseline_path,
                policy_config_path,
            )

        payload = execute_legacy_nex_bundle_summary(bundle, run_id="cli")
        payload, exit_code = apply_baseline_policy(payload, baseline_path, policy_config_path)
        write_or_print_payload(payload, out_path)
        return exit_code
    finally:
        bundle.cleanup()
