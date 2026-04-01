
from __future__ import annotations

import json
import tempfile
import zipfile
from dataclasses import asdict, dataclass, is_dataclass
from pathlib import Path
from typing import Any, Dict


@dataclass
class ExecutionAuditPack:
    metadata: Dict[str, Any]
    snapshot: Any
    diff_report: Any
    diff_visualization: str
    regression_report: Any




def _synthesize_execution_record_reference_contract(payload: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        return {}

    existing = payload.get("execution_record_reference_contract")
    if isinstance(existing, dict) and existing:
        return existing

    replay_payload = payload.get("replay_payload")
    if not isinstance(replay_payload, dict) or not replay_payload:
        return {}

    execution_id = str(replay_payload.get("execution_id") or payload.get("run_id") or "unknown-execution")
    trace = payload.get("trace") or payload.get("execution_trace")
    has_trace = isinstance(trace, dict) and bool(trace)
    has_events = bool(isinstance(trace, dict) and trace.get("events"))

    trace_ref = f"trace://{execution_id}" if has_trace else None
    event_stream_ref = f"events://{execution_id}" if has_events else None
    primary_trace_ref = event_stream_ref or trace_ref

    node_order = replay_payload.get("node_order") if isinstance(replay_payload, dict) else []
    if not isinstance(node_order, list):
        node_order = []
    node_trace_refs = {
        str(node_id): f"{primary_trace_ref}#node:{node_id}"
        for node_id in node_order
        if isinstance(node_id, str) and primary_trace_ref
    }

    expected_outputs = replay_payload.get("expected_outputs") if isinstance(replay_payload, dict) else {}
    if not isinstance(expected_outputs, dict):
        expected_outputs = {}
    output_value_refs = {
        str(output_ref): f"{primary_trace_ref}#output:{output_ref}"
        for output_ref in expected_outputs.keys()
        if primary_trace_ref
    }
    unresolved_output_refs = [] if primary_trace_ref else [str(output_ref) for output_ref in expected_outputs.keys()]

    artifacts = payload.get("artifacts")
    if not isinstance(artifacts, list):
        artifacts = []
    artifact_refs = {
        f"artifact_{index}": f"artifact://{execution_id}/{index}"
        for index, _ in enumerate(artifacts, start=1)
    }

    contract = {
        "run_id": execution_id,
        "commit_id": replay_payload.get("commit_id"),
        "primary_trace_ref": primary_trace_ref,
        "trace_ref": trace_ref,
        "event_stream_ref": event_stream_ref,
        "node_trace_refs": node_trace_refs,
        "output_value_refs": output_value_refs,
        "artifact_refs": artifact_refs,
        "unresolved_output_refs": unresolved_output_refs,
        "unresolved_artifact_refs": [],
        "observability_refs": [item for item in [primary_trace_ref] if item],
        "is_replay_ready": bool(primary_trace_ref and expected_outputs),
        "is_audit_ready": bool(primary_trace_ref),
    }
    payload["execution_record_reference_contract"] = contract
    return contract
class ExecutionAuditPackBuilder:
    """
    Build an execution audit pack that aggregates
    snapshot, diff, visualization and regression results.
    """

    @staticmethod
    def build(
        snapshot,
        diff_report,
        diff_text,
        regression_report,
        metadata: Dict[str, Any],
    ) -> ExecutionAuditPack:

        return ExecutionAuditPack(
            metadata=metadata,
            snapshot=snapshot,
            diff_report=diff_report,
            diff_visualization=diff_text,
            regression_report=regression_report,
        )

    @staticmethod
    def to_dict(audit_pack: ExecutionAuditPack) -> Dict[str, Any]:
        return {
            "metadata": ExecutionAuditPackBuilder._normalize(audit_pack.metadata),
            "snapshot": ExecutionAuditPackBuilder._normalize(audit_pack.snapshot),
            "diff": ExecutionAuditPackBuilder._normalize(audit_pack.diff_report),
            "diff_text": audit_pack.diff_visualization,
            "regression": ExecutionAuditPackBuilder._normalize(audit_pack.regression_report),
        }

    @staticmethod
    def export(payload: Dict[str, Any], output_path: str) -> Path:
        """
        Export a deterministic audit pack zip from a run result payload.

        The payload is expected to be the JSON object emitted by `nexa run`.
        Missing sections are represented with stable empty defaults.
        """
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)

        with tempfile.TemporaryDirectory(prefix='nexa_audit_pack_') as tmp:
            root = Path(tmp) / 'audit_pack'
            artifacts_dir = root / 'artifacts'
            root.mkdir(parents=True, exist_ok=True)
            artifacts_dir.mkdir(parents=True, exist_ok=True)

            result = payload.get('result', {}) if isinstance(payload, dict) else {}
            state = result.get('state', {}) if isinstance(result, dict) else {}
            summary = payload.get('summary', {}) if isinstance(payload, dict) else {}
            artifacts = payload.get('artifacts', []) if isinstance(payload, dict) else []
            trace = payload.get('trace', payload.get('execution_trace', {})) if isinstance(payload, dict) else {}

            metadata = {
                'format': 'nexa.audit_pack',
                'version': '1.0.0',
                'artifact_count': len(artifacts) if isinstance(artifacts, list) else 0,
                'state_key_count': len(state) if isinstance(state, dict) else 0,
            }

            execution_trace_payload = {
                'trace': ExecutionAuditPackBuilder._normalize(trace),
                'state': ExecutionAuditPackBuilder._normalize(state),
            }
            summary_payload = {
                'summary': ExecutionAuditPackBuilder._normalize(summary),
            }
            replay_payload = ExecutionAuditPackBuilder._normalize(
                payload.get('replay_payload', {}) if isinstance(payload, dict) else {}
            )
            synthesized_contract = _synthesize_execution_record_reference_contract(payload if isinstance(payload, dict) else {})
            execution_record_reference_contract = ExecutionAuditPackBuilder._normalize(synthesized_contract)

            if isinstance(execution_record_reference_contract, dict) and execution_record_reference_contract:
                metadata['replay_ready'] = bool(execution_record_reference_contract.get('is_replay_ready'))
                metadata['audit_ready'] = bool(execution_record_reference_contract.get('is_audit_ready'))
                metadata['primary_trace_ref'] = execution_record_reference_contract.get('primary_trace_ref')

            (root / 'execution_trace.json').write_text(
                json.dumps(execution_trace_payload, indent=2, ensure_ascii=False, sort_keys=True),
                encoding='utf-8',
            )
            (root / 'metadata.json').write_text(
                json.dumps(metadata, indent=2, ensure_ascii=False, sort_keys=True),
                encoding='utf-8',
            )
            (root / 'summary.json').write_text(
                json.dumps(summary_payload, indent=2, ensure_ascii=False, sort_keys=True),
                encoding='utf-8',
            )
            (root / 'replay_payload.json').write_text(
                json.dumps(replay_payload, indent=2, ensure_ascii=False, sort_keys=True),
                encoding='utf-8',
            )
            if isinstance(execution_record_reference_contract, dict) and execution_record_reference_contract:
                (root / 'execution_record_reference_contract.json').write_text(
                    json.dumps(execution_record_reference_contract, indent=2, ensure_ascii=False, sort_keys=True),
                    encoding='utf-8',
                )

            if isinstance(artifacts, list):
                for index, artifact in enumerate(artifacts, start=1):
                    artifact_path = artifacts_dir / f'artifact_{index}.json'
                    artifact_path.write_text(
                        json.dumps(ExecutionAuditPackBuilder._normalize(artifact), indent=2, ensure_ascii=False, sort_keys=True),
                        encoding='utf-8',
                    )

            with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
                for file_path in sorted(root.rglob('*')):
                    if file_path.is_file():
                        arcname = file_path.relative_to(root)
                        info = zipfile.ZipInfo(str(arcname))
                        info.date_time = (1980, 1, 1, 0, 0, 0)
                        info.compress_type = zipfile.ZIP_DEFLATED
                        zf.writestr(info, file_path.read_bytes())

        return output

    @staticmethod
    def _normalize(value: Any) -> Any:
        if is_dataclass(value) and not isinstance(value, type):
            return {k: ExecutionAuditPackBuilder._normalize(v) for k, v in asdict(value).items()}
        if isinstance(value, dict):
            return {str(k): ExecutionAuditPackBuilder._normalize(v) for k, v in value.items()}
        if isinstance(value, (list, tuple)):
            return [ExecutionAuditPackBuilder._normalize(v) for v in value]
        if isinstance(value, (str, int, float, bool)) or value is None:
            return value
        return repr(value)
