"""Compatibility wrapper for the legacy engine CLI surface.

The canonical public CLI entrypoint is ``src.cli.nexa_cli:main`` as exposed
through ``pyproject.toml`` and ``nexa.py``. This module remains only as a
bounded compatibility surface for engine-specific tests and old callers that
still import ``src.engine.cli`` directly.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence

from src.cli.savefile_runtime import execute_savefile_summary, is_savefile_contract
from src.circuit.runtime_adapter import (
    load_engine_from_legacy_nex_path,
    open_legacy_nex_bundle,
    prepare_engine_from_legacy_nex_bundle,
)
from src.contracts.regression_reason_codes import (
    NODE_REMOVED_SUCCESS,
    NODE_SUCCESS_TO_FAILURE,
    NODE_SUCCESS_TO_SKIPPED,
)
from src.engine.engine import Engine
from src.engine.execution_regression_detector import NodeRegression, RegressionResult
from src.engine.execution_regression_policy import (
    POLICY_STATUS_FAIL,
    POLICY_STATUS_WARN,
    evaluate_regression_policy,
)
from src.engine.types import NodeStatus

CANONICAL_PUBLIC_CLI = "src.cli.nexa_cli:main"

ApplyBaselinePolicy = Callable[[Dict[str, Any], Optional[str], Optional[str]], tuple[Dict[str, Any], int]]
WritePayload = Callable[[Dict[str, Any], Optional[str]], None]
RunSavefile = Callable[[str, Optional[str], Optional[str], Optional[str]], int]


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
    circuit, engine = load_engine_from_legacy_nex_path(
        circuit_path,
        bundle_path=bundle_path,
    )
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
    bundle = open_legacy_nex_bundle(bundle_path)
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
