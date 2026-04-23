from typing import Any, Dict

from src.engine.execution_diff_visualizer import ExecutionDiffVisualizer
from src.engine.execution_regression_detector import ExecutionRegressionDetector
from src.engine.execution_snapshot_diff import ExecutionSnapshotDiffEngine


class RunComparator:
    @staticmethod
    def compare(run_a: Dict[str, Any], run_b: Dict[str, Any]):
        snapshot_a = run_a["snapshot"]
        snapshot_b = run_b["snapshot"]

        diff_report = ExecutionSnapshotDiffEngine.compare(snapshot_a, snapshot_b)
        diff_text = ExecutionDiffVisualizer.render(diff_report)
        regression_report = ExecutionRegressionDetector.detect(diff_report)

        return {
            "diff_report": diff_report,
            "diff_text": diff_text,
            "regression_report": regression_report,
        }