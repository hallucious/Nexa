from dataclasses import dataclass
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
            "metadata": audit_pack.metadata,
            "snapshot": audit_pack.snapshot,
            "diff": audit_pack.diff_report,
            "diff_text": audit_pack.diff_visualization,
            "regression": audit_pack.regression_report,
        }