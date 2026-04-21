from __future__ import annotations

from dataclasses import replace

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Optional

from src.circuit.loader import load_legacy_nex_bundle
from src.circuit.runtime_adapter import (
    load_engine_from_legacy_nex_path,
    prepare_engine_from_legacy_nex_bundle,
)
from src.contracts.nex_contract import ALLOWED_STORAGE_ROLES
from src.contracts.savefile_executor_aligned import SavefileExecutor
from src.contracts.savefile_loader import load_savefile_from_path
from src.storage.nex_api import load_nex, resolve_public_nex_execution_target
from src.storage.share_api import (
    ensure_public_nex_link_share_operation_allowed,
    load_public_nex_link_share,
    load_public_nex_link_share_artifact_context,
    is_public_nex_link_share_payload,
)
from src.storage.execution_savefile_adapter import execution_savefile_from_loaded_nex_artifact
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

    if is_public_nex_link_share_payload(data):
        return True

    meta = data.get("meta", {}) if isinstance(data.get("meta"), dict) else {}
    if meta.get("storage_role") in ALLOWED_STORAGE_ROLES:
        return True

    required = {"meta", "circuit", "resources", "state", "ui"}
    return required.issubset(set(data.keys()))


@dataclass(frozen=True)
class SavefileExecutionContext:
    savefile: Any
    storage_role: str | None = None
    canonical_ref: str | None = None
    public_load_status: str | None = None
    working_save_id: str | None = None
    commit_id: str | None = None
    share_id: str | None = None


def _load_execution_context(circuit_path: str) -> SavefileExecutionContext:
    try:
        data = json.loads(Path(circuit_path).read_text(encoding="utf-8"))
    except Exception:
        data = None

    if isinstance(data, dict):
        share_id = None
        loaded = None
        if is_public_nex_link_share_payload(data):
            share_payload, loaded = load_public_nex_link_share_artifact_context(circuit_path)
            ensure_public_nex_link_share_operation_allowed(share_payload, "run_artifact")
            share = share_payload.get("share", {}) if isinstance(share_payload.get("share"), dict) else {}
            share_id = share.get("share_id") if isinstance(share.get("share_id"), str) else None
            target = resolve_public_nex_execution_target(share_payload["artifact"])
        else:
            meta = data.get("meta", {}) if isinstance(data.get("meta"), dict) else {}
            storage_role = meta.get("storage_role")
            if storage_role in ALLOWED_STORAGE_ROLES:
                loaded = load_nex(circuit_path)

        if loaded is not None:
            if loaded.parsed_model is None:
                blocking_messages = [finding.message for finding in loaded.findings if getattr(finding, "blocking", False)]
                detail = blocking_messages[0] if blocking_messages else f"public .nex artifact could not be loaded ({loaded.load_status})"
                raise ValueError(detail)
            canonical_ref = None
            working_save_id = None
            commit_id = None
            if share_id is not None:
                canonical_ref = target.target_ref
                working_save_id = target.target_ref if target.target_type == "working_save" else target.source_working_save_id
                commit_id = target.target_ref if target.target_type == "commit_snapshot" else None
            parsed_meta = getattr(loaded.parsed_model, "meta", None)
            if share_id is None and parsed_meta is not None:
                working_save_id = getattr(parsed_meta, "working_save_id", None)
                commit_id = getattr(parsed_meta, "commit_id", None)
                canonical_ref = working_save_id or commit_id
            if share_id is None and working_save_id is None:
                lineage = getattr(loaded.parsed_model, "lineage", None)
                if lineage is not None:
                    working_save_id = getattr(lineage, "source_working_save_id", None)
            return SavefileExecutionContext(
                savefile=execution_savefile_from_loaded_nex_artifact(loaded),
                storage_role=loaded.storage_role,
                canonical_ref=canonical_ref,
                public_load_status=loaded.load_status,
                working_save_id=working_save_id,
                commit_id=commit_id,
                share_id=share_id,
            )

    return SavefileExecutionContext(savefile=load_savefile_from_path(circuit_path))


def execute_savefile(
    circuit_path: str,
    *,
    input_overrides: Mapping[str, Any] | None = None,
    run_id: str = "cli",
):
    context = _load_execution_context(circuit_path)
    savefile = context.savefile

    if input_overrides:
        merged_input = dict(savefile.state.input)
        merged_input.update(dict(input_overrides))
        savefile = replace(savefile, state=replace(savefile.state, input=merged_input))

    validate_savefile(savefile)
    provider_registry = build_provider_registry_from_savefile(savefile)
    executor = SavefileExecutor(provider_registry)
    trace = executor.execute(savefile, run_id=run_id)
    return context, trace


def build_savefile_trace_summary(savefile_name: str, trace: Any, *, storage_role: str | None = None, canonical_ref: str | None = None) -> dict[str, Any]:
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

    payload = {
        "circuit_id": savefile_name,
        "status": "FAILURE" if any_failure else "SUCCESS",
        "nodes": nodes,
    }
    if storage_role is not None:
        payload["storage_role"] = storage_role
    if canonical_ref is not None:
        payload["canonical_ref"] = canonical_ref
    return payload


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
    context, trace = execute_savefile(circuit_path, run_id="cli")
    payload = build_savefile_trace_summary(
        context.savefile.meta.name,
        trace,
        storage_role=context.storage_role,
        canonical_ref=context.canonical_ref,
    )
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
