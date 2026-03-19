
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
