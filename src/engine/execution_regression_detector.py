"""
execution_regression_detector.py

Regression detection layer on top of RunDiff.

This module consumes RunDiff and applies deterministic rule-based regression
logic to identify execution regressions.

IMPORTANT: This is a pure analysis layer.
- Consumes RunDiff only
- No file I/O
- No CLI imports
- No formatter imports
- Deterministic output
- No mutation of RunDiff
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List

from src.contracts.regression_reason_codes import (
    ARTIFACT_HASH_CHANGED,
    ARTIFACT_REMOVED,
    ARTIFACT_VALIDATION_INCONCLUSIVE_TO_FAIL,
    ARTIFACT_VALIDATION_PASS_TO_FAIL,
    ARTIFACT_VALIDATION_PASS_TO_INCONCLUSIVE,
    ARTIFACT_VALIDATION_PASS_TO_WARNING,
    ARTIFACT_VALIDATION_WARNING_TO_FAIL,
    CONTEXT_KEY_REMOVED,
    CONTEXT_VALUE_CHANGED,
    NODE_REMOVED_SUCCESS,
    NODE_SUCCESS_TO_FAILURE,
    NODE_SUCCESS_TO_SKIPPED,
    NODE_VERIFIER_INCONCLUSIVE_TO_FAIL,
    NODE_VERIFIER_PASS_TO_FAIL,
    NODE_VERIFIER_PASS_TO_INCONCLUSIVE,
    NODE_VERIFIER_PASS_TO_WARNING,
    NODE_VERIFIER_WARNING_TO_FAIL,
    VALID_ARTIFACT_REASON_CODES,
    VALID_CONTEXT_REASON_CODES,
    VALID_NODE_REASON_CODES,
    VALID_VERIFICATION_REASON_CODES,
)
from src.engine.execution_diff_model import CHANGE_TYPE_MODIFIED, CHANGE_TYPE_REMOVED, RunDiff

REGRESSION_STATUS_CLEAN = "clean"
REGRESSION_STATUS_REGRESSION = "regression"

VALID_REGRESSION_STATUSES = frozenset({
    REGRESSION_STATUS_CLEAN,
    REGRESSION_STATUS_REGRESSION,
})

REGRESSION_SEVERITY_HIGH = "HIGH"
REGRESSION_SEVERITY_MEDIUM = "MEDIUM"
REGRESSION_SEVERITY_LOW = "LOW"

VALID_REGRESSION_SEVERITIES = frozenset({
    REGRESSION_SEVERITY_HIGH,
    REGRESSION_SEVERITY_MEDIUM,
    REGRESSION_SEVERITY_LOW,
})

_REASON_CODE_TO_SEVERITY = {
    NODE_SUCCESS_TO_FAILURE: REGRESSION_SEVERITY_HIGH,
    NODE_REMOVED_SUCCESS: REGRESSION_SEVERITY_HIGH,
    NODE_SUCCESS_TO_SKIPPED: REGRESSION_SEVERITY_MEDIUM,
    ARTIFACT_REMOVED: REGRESSION_SEVERITY_HIGH,
    ARTIFACT_HASH_CHANGED: REGRESSION_SEVERITY_MEDIUM,
    CONTEXT_KEY_REMOVED: REGRESSION_SEVERITY_MEDIUM,
    CONTEXT_VALUE_CHANGED: REGRESSION_SEVERITY_LOW,
    NODE_VERIFIER_PASS_TO_FAIL: REGRESSION_SEVERITY_HIGH,
    ARTIFACT_VALIDATION_PASS_TO_FAIL: REGRESSION_SEVERITY_HIGH,
    NODE_VERIFIER_PASS_TO_WARNING: REGRESSION_SEVERITY_MEDIUM,
    NODE_VERIFIER_PASS_TO_INCONCLUSIVE: REGRESSION_SEVERITY_MEDIUM,
    NODE_VERIFIER_WARNING_TO_FAIL: REGRESSION_SEVERITY_MEDIUM,
    NODE_VERIFIER_INCONCLUSIVE_TO_FAIL: REGRESSION_SEVERITY_MEDIUM,
    ARTIFACT_VALIDATION_PASS_TO_WARNING: REGRESSION_SEVERITY_MEDIUM,
    ARTIFACT_VALIDATION_PASS_TO_INCONCLUSIVE: REGRESSION_SEVERITY_MEDIUM,
    ARTIFACT_VALIDATION_WARNING_TO_FAIL: REGRESSION_SEVERITY_MEDIUM,
    ARTIFACT_VALIDATION_INCONCLUSIVE_TO_FAIL: REGRESSION_SEVERITY_MEDIUM,
}

_REASON_CODE_DESCRIPTIONS = {
    NODE_SUCCESS_TO_FAILURE: "success -> failure",
    NODE_SUCCESS_TO_SKIPPED: "success -> skipped",
    NODE_REMOVED_SUCCESS: "removed successful node",
    ARTIFACT_REMOVED: "artifact removed",
    ARTIFACT_HASH_CHANGED: "hash changed",
    CONTEXT_KEY_REMOVED: "context key removed",
    CONTEXT_VALUE_CHANGED: "value changed",
    NODE_VERIFIER_PASS_TO_FAIL: "verifier pass -> fail",
    NODE_VERIFIER_PASS_TO_WARNING: "verifier pass -> warning",
    NODE_VERIFIER_PASS_TO_INCONCLUSIVE: "verifier pass -> inconclusive",
    NODE_VERIFIER_WARNING_TO_FAIL: "verifier warning -> fail",
    NODE_VERIFIER_INCONCLUSIVE_TO_FAIL: "verifier inconclusive -> fail",
    ARTIFACT_VALIDATION_PASS_TO_FAIL: "artifact validation pass -> fail",
    ARTIFACT_VALIDATION_PASS_TO_WARNING: "artifact validation pass -> warning",
    ARTIFACT_VALIDATION_PASS_TO_INCONCLUSIVE: "artifact validation pass -> inconclusive",
    ARTIFACT_VALIDATION_WARNING_TO_FAIL: "artifact validation warning -> fail",
    ARTIFACT_VALIDATION_INCONCLUSIVE_TO_FAIL: "artifact validation inconclusive -> fail",
}


def _get_severity(reason_code: str) -> str:
    return _REASON_CODE_TO_SEVERITY[reason_code]


def _get_reason_description(reason_code: str) -> str:
    return _REASON_CODE_DESCRIPTIONS.get(reason_code, reason_code)


@dataclass
class RegressionSummary:
    node_regressions: int = 0
    artifact_regressions: int = 0
    context_regressions: int = 0
    verification_regressions: int = 0
    high_regressions: int = 0
    medium_regressions: int = 0
    low_regressions: int = 0


@dataclass
class NodeRegression:
    node_id: str
    reason_code: str
    left_status: str | None
    right_status: str | None
    severity: str = field(init=False)

    def __post_init__(self):
        if self.reason_code not in VALID_NODE_REASON_CODES:
            raise ValueError(
                f"Invalid reason_code '{self.reason_code}' for NodeRegression. "
                f"Must be one of: {', '.join(sorted(VALID_NODE_REASON_CODES))}"
            )
        self.severity = _get_severity(self.reason_code)
        if self.severity not in VALID_REGRESSION_SEVERITIES:
            raise ValueError(
                f"Invalid severity '{self.severity}' for NodeRegression. "
                f"Must be one of: {', '.join(sorted(VALID_REGRESSION_SEVERITIES))}"
            )

    @property
    def reason(self) -> str:
        return _get_reason_description(self.reason_code)


@dataclass
class ArtifactRegression:
    artifact_id: str
    reason_code: str
    left_hash: str | None = None
    right_hash: str | None = None
    severity: str = field(init=False)

    def __post_init__(self):
        if self.reason_code not in VALID_ARTIFACT_REASON_CODES:
            raise ValueError(
                f"Invalid reason_code '{self.reason_code}' for ArtifactRegression. "
                f"Must be one of: {', '.join(sorted(VALID_ARTIFACT_REASON_CODES))}"
            )
        self.severity = _get_severity(self.reason_code)
        if self.severity not in VALID_REGRESSION_SEVERITIES:
            raise ValueError(
                f"Invalid severity '{self.severity}' for ArtifactRegression. "
                f"Must be one of: {', '.join(sorted(VALID_REGRESSION_SEVERITIES))}"
            )

    @property
    def reason(self) -> str:
        return _get_reason_description(self.reason_code)


@dataclass
class ContextRegression:
    context_key: str
    reason_code: str
    left_value: Any = None
    right_value: Any = None
    severity: str = field(init=False)

    def __post_init__(self):
        if self.reason_code not in VALID_CONTEXT_REASON_CODES:
            raise ValueError(
                f"Invalid reason_code '{self.reason_code}' for ContextRegression. "
                f"Must be one of: {', '.join(sorted(VALID_CONTEXT_REASON_CODES))}"
            )
        self.severity = _get_severity(self.reason_code)
        if self.severity not in VALID_REGRESSION_SEVERITIES:
            raise ValueError(
                f"Invalid severity '{self.severity}' for ContextRegression. "
                f"Must be one of: {', '.join(sorted(VALID_REGRESSION_SEVERITIES))}"
            )

    @property
    def reason(self) -> str:
        return _get_reason_description(self.reason_code)


@dataclass
class VerificationRegression:
    target_type: str
    target_id: str
    reason_code: str
    left_status: str | None = None
    right_status: str | None = None
    left_reason_codes: List[str] = field(default_factory=list)
    right_reason_codes: List[str] = field(default_factory=list)
    severity: str = field(init=False)

    def __post_init__(self):
        if self.reason_code not in VALID_VERIFICATION_REASON_CODES:
            raise ValueError(
                f"Invalid reason_code '{self.reason_code}' for VerificationRegression. "
                f"Must be one of: {', '.join(sorted(VALID_VERIFICATION_REASON_CODES))}"
            )
        self.severity = _get_severity(self.reason_code)
        if self.severity not in VALID_REGRESSION_SEVERITIES:
            raise ValueError(
                f"Invalid severity '{self.severity}' for VerificationRegression. "
                f"Must be one of: {', '.join(sorted(VALID_REGRESSION_SEVERITIES))}"
            )
        if self.target_type not in {"node", "artifact"}:
            raise ValueError("VerificationRegression.target_type must be 'node' or 'artifact'")
        if not self.target_id:
            raise ValueError("VerificationRegression.target_id must be non-empty")

    @property
    def reason(self) -> str:
        return _get_reason_description(self.reason_code)


@dataclass
class RegressionResult:
    status: str
    summary: RegressionSummary = field(default_factory=RegressionSummary)
    nodes: List[NodeRegression] = field(default_factory=list)
    artifacts: List[ArtifactRegression] = field(default_factory=list)
    context: List[ContextRegression] = field(default_factory=list)
    verification: List[VerificationRegression] = field(default_factory=list)


def _detect_node_regressions(diff: RunDiff) -> List[NodeRegression]:
    regressions: List[NodeRegression] = []
    for node_diff in diff.node_diffs:
        node_id = node_diff.node_id
        left_status = node_diff.left_status
        right_status = node_diff.right_status
        change_type = node_diff.change_type
        if left_status == "success" and right_status == "failure":
            regressions.append(NodeRegression(node_id=node_id, reason_code=NODE_SUCCESS_TO_FAILURE, left_status=left_status, right_status=right_status))
        if left_status == "success" and right_status == "skipped":
            regressions.append(NodeRegression(node_id=node_id, reason_code=NODE_SUCCESS_TO_SKIPPED, left_status=left_status, right_status=right_status))
        if change_type == CHANGE_TYPE_REMOVED and left_status == "success":
            regressions.append(NodeRegression(node_id=node_id, reason_code=NODE_REMOVED_SUCCESS, left_status=left_status, right_status=None))
    return regressions


def _detect_artifact_regressions(diff: RunDiff) -> List[ArtifactRegression]:
    regressions: List[ArtifactRegression] = []
    for art_diff in diff.artifact_diffs:
        if art_diff.change_type == CHANGE_TYPE_REMOVED:
            regressions.append(ArtifactRegression(artifact_id=art_diff.artifact_id, reason_code=ARTIFACT_REMOVED, left_hash=art_diff.left_hash))
        if art_diff.change_type == CHANGE_TYPE_MODIFIED and art_diff.left_hash != art_diff.right_hash:
            regressions.append(ArtifactRegression(artifact_id=art_diff.artifact_id, reason_code=ARTIFACT_HASH_CHANGED, left_hash=art_diff.left_hash, right_hash=art_diff.right_hash))
    return regressions


def _detect_context_regressions(diff: RunDiff) -> List[ContextRegression]:
    regressions: List[ContextRegression] = []
    for ctx_diff in diff.context_diffs:
        if ctx_diff.change_type == CHANGE_TYPE_REMOVED:
            regressions.append(ContextRegression(context_key=ctx_diff.context_key, reason_code=CONTEXT_KEY_REMOVED, left_value=ctx_diff.left_value))
        if ctx_diff.change_type == CHANGE_TYPE_MODIFIED:
            regressions.append(ContextRegression(context_key=ctx_diff.context_key, reason_code=CONTEXT_VALUE_CHANGED, left_value=ctx_diff.left_value, right_value=ctx_diff.right_value))
    return regressions


def _verification_node_reason(left_status: str | None, right_status: str | None) -> str | None:
    return {
        ("pass", "fail"): NODE_VERIFIER_PASS_TO_FAIL,
        ("pass", "warning"): NODE_VERIFIER_PASS_TO_WARNING,
        ("pass", "inconclusive"): NODE_VERIFIER_PASS_TO_INCONCLUSIVE,
        ("warning", "fail"): NODE_VERIFIER_WARNING_TO_FAIL,
        ("inconclusive", "fail"): NODE_VERIFIER_INCONCLUSIVE_TO_FAIL,
    }.get((left_status, right_status))


def _verification_artifact_reason(left_status: str | None, right_status: str | None) -> str | None:
    return {
        ("pass", "fail"): ARTIFACT_VALIDATION_PASS_TO_FAIL,
        ("pass", "warning"): ARTIFACT_VALIDATION_PASS_TO_WARNING,
        ("pass", "inconclusive"): ARTIFACT_VALIDATION_PASS_TO_INCONCLUSIVE,
        ("warning", "fail"): ARTIFACT_VALIDATION_WARNING_TO_FAIL,
        ("inconclusive", "fail"): ARTIFACT_VALIDATION_INCONCLUSIVE_TO_FAIL,
    }.get((left_status, right_status))


def _detect_verification_regressions(diff: RunDiff) -> List[VerificationRegression]:
    regressions: List[VerificationRegression] = []
    for node_diff in diff.node_diffs:
        reason_code = _verification_node_reason(node_diff.left_verifier_status, node_diff.right_verifier_status)
        if reason_code is not None:
            regressions.append(
                VerificationRegression(
                    target_type="node",
                    target_id=node_diff.node_id,
                    reason_code=reason_code,
                    left_status=node_diff.left_verifier_status,
                    right_status=node_diff.right_verifier_status,
                    left_reason_codes=list(node_diff.left_verifier_reason_codes),
                    right_reason_codes=list(node_diff.right_verifier_reason_codes),
                )
            )
    for artifact_diff in diff.artifact_diffs:
        reason_code = _verification_artifact_reason(artifact_diff.left_validation_status, artifact_diff.right_validation_status)
        if reason_code is not None:
            regressions.append(
                VerificationRegression(
                    target_type="artifact",
                    target_id=artifact_diff.artifact_id,
                    reason_code=reason_code,
                    left_status=artifact_diff.left_validation_status,
                    right_status=artifact_diff.right_validation_status,
                )
            )
    return regressions


def detect_regressions(diff: RunDiff) -> RegressionResult:
    if not isinstance(diff, RunDiff):
        raise TypeError(f"diff must be a RunDiff, got {type(diff).__name__}")

    node_regressions = _detect_node_regressions(diff)
    artifact_regressions = _detect_artifact_regressions(diff)
    context_regressions = _detect_context_regressions(diff)
    verification_regressions = _detect_verification_regressions(diff)

    all_regressions = node_regressions + artifact_regressions + context_regressions + verification_regressions
    high_count = sum(1 for r in all_regressions if r.severity == REGRESSION_SEVERITY_HIGH)
    medium_count = sum(1 for r in all_regressions if r.severity == REGRESSION_SEVERITY_MEDIUM)
    low_count = sum(1 for r in all_regressions if r.severity == REGRESSION_SEVERITY_LOW)

    summary = RegressionSummary(
        node_regressions=len(node_regressions),
        artifact_regressions=len(artifact_regressions),
        context_regressions=len(context_regressions),
        verification_regressions=len(verification_regressions),
        high_regressions=high_count,
        medium_regressions=medium_count,
        low_regressions=low_count,
    )

    status = REGRESSION_STATUS_REGRESSION if all_regressions else REGRESSION_STATUS_CLEAN
    return RegressionResult(
        status=status,
        summary=summary,
        nodes=node_regressions,
        artifacts=artifact_regressions,
        context=context_regressions,
        verification=verification_regressions,
    )


@dataclass
class LegacyRegressionResult:
    type: str
    node_id: str
    severity: str
    description: str


@dataclass
class ExecutionRegressionReport:
    regressions: List[LegacyRegressionResult] = field(default_factory=list)
    total_regressions: int = 0
    highest_severity: str = "LOW"


class ExecutionRegressionDetector:
    SEVERITY_ORDER = ["LOW", "MEDIUM", "HIGH"]

    @staticmethod
    def detect(diff_report) -> ExecutionRegressionReport:
        regressions: List[LegacyRegressionResult] = []

        for node_id in getattr(diff_report, 'removed_nodes', []):
            regressions.append(LegacyRegressionResult(type="NODE_REMOVED", node_id=node_id, severity="HIGH", description="Node removed from execution"))

        for node in getattr(diff_report, 'modified_nodes', []):
            if getattr(node, 'hash_changed', False):
                regressions.append(LegacyRegressionResult(type="HASH_MISMATCH", node_id=node.node_id, severity="HIGH", description="Output hash changed"))
            elif getattr(node, 'output_changed', False):
                regressions.append(LegacyRegressionResult(type="OUTPUT_CHANGED", node_id=node.node_id, severity="MEDIUM", description="Node output changed"))
            elif getattr(node, 'metadata_changed', False):
                regressions.append(LegacyRegressionResult(type="METADATA_CHANGED", node_id=node.node_id, severity="LOW", description="Node metadata changed"))
            elif getattr(node, 'verifier_changed', False):
                regressions.append(LegacyRegressionResult(type="VERIFIER_CHANGED", node_id=node.node_id, severity="MEDIUM", description="Verifier result changed"))

        highest_severity = "LOW"
        for regression in regressions:
            if ExecutionRegressionDetector.SEVERITY_ORDER.index(regression.severity) > ExecutionRegressionDetector.SEVERITY_ORDER.index(highest_severity):
                highest_severity = regression.severity

        return ExecutionRegressionReport(regressions=regressions, total_regressions=len(regressions), highest_severity=highest_severity)
