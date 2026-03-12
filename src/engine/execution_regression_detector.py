from dataclasses import dataclass
from typing import List


@dataclass
class RegressionResult:
    type: str
    node_id: str
    severity: str
    description: str


@dataclass
class ExecutionRegressionReport:
    regressions: List[RegressionResult]
    total_regressions: int
    highest_severity: str


class ExecutionRegressionDetector:
    """
    Detect execution regressions from ExecutionSnapshotDiffReport.
    """

    SEVERITY_ORDER = ["LOW", "MEDIUM", "HIGH"]

    @staticmethod
    def detect(diff_report):

        regressions: List[RegressionResult] = []

        # Node removed regressions
        for node_id in diff_report.removed_nodes:
            regressions.append(
                RegressionResult(
                    type="NODE_REMOVED",
                    node_id=node_id,
                    severity="HIGH",
                    description="Node removed from execution",
                )
            )

        # Modified node regressions
        for node in diff_report.modified_nodes:

            if node.hash_changed:
                regressions.append(
                    RegressionResult(
                        type="HASH_MISMATCH",
                        node_id=node.node_id,
                        severity="HIGH",
                        description="Output hash changed",
                    )
                )

            elif node.output_changed:
                regressions.append(
                    RegressionResult(
                        type="OUTPUT_CHANGED",
                        node_id=node.node_id,
                        severity="MEDIUM",
                        description="Node output changed",
                    )
                )

            elif node.metadata_changed:
                regressions.append(
                    RegressionResult(
                        type="METADATA_CHANGED",
                        node_id=node.node_id,
                        severity="LOW",
                        description="Node metadata changed",
                    )
                )

        highest_severity = "LOW"

        for r in regressions:
            if ExecutionRegressionDetector.SEVERITY_ORDER.index(
                r.severity
            ) > ExecutionRegressionDetector.SEVERITY_ORDER.index(
                highest_severity
            ):
                highest_severity = r.severity

        return ExecutionRegressionReport(
            regressions=regressions,
            total_regressions=len(regressions),
            highest_severity=highest_severity,
        )