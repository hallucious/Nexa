
from __future__ import annotations

import json
import tempfile
import zipfile
from dataclasses import asdict, dataclass, is_dataclass
from pathlib import Path
from typing import Any, Dict

from src.storage.lifecycle_api import create_serialized_audit_export_payload


@dataclass
class ExecutionAuditPack:
    metadata: Dict[str, Any]
    snapshot: Any
    diff_report: Any
    diff_visualization: str
    regression_report: Any



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

            audit_payload = create_serialized_audit_export_payload(payload if isinstance(payload, dict) else {})
            metadata = ExecutionAuditPackBuilder._normalize(audit_payload.get('metadata', {}))
            execution_trace_payload = ExecutionAuditPackBuilder._normalize(audit_payload.get('execution_trace_payload', {}))
            summary_payload = ExecutionAuditPackBuilder._normalize(audit_payload.get('summary_payload', {}))
            replay_payload = ExecutionAuditPackBuilder._normalize(audit_payload.get('replay_payload', {}))
            execution_record = ExecutionAuditPackBuilder._normalize(audit_payload.get('execution_record', {}))
            execution_record_reference_contract = ExecutionAuditPackBuilder._normalize(
                audit_payload.get('execution_record_reference_contract', {})
            )
            artifacts = ExecutionAuditPackBuilder._normalize(audit_payload.get('artifacts', []))

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
            if isinstance(execution_record, dict) and execution_record:
                (root / 'execution_record.json').write_text(
                    json.dumps(execution_record, indent=2, ensure_ascii=False, sort_keys=True),
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
