"""
execution_regression_detector.py

Regression detection layer on top of RunDiff.

This module consumes RunDiff and applies deterministic rule-based regression
detection logic to identify execution regressions.

IMPORTANT: This is a pure analysis layer.
- Consumes RunDiff only
- No file I/O
- No CLI imports
- No formatter imports
- Deterministic output
- No mutation of RunDiff

Regression rules:
A. Node regressions:
   1. left_status == "success" and right_status == "failure"
   2. left_status == "success" and right_status == "skipped"
   3. node removed where left_status == "success"

B. Artifact regressions:
   1. artifact removed
   2. artifact hash changed (modified)

C. Context regressions:
   1. context key removed
   2. context key modified (value changed)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List

from src.engine.execution_diff_model import (
    CHANGE_TYPE_MODIFIED,
    CHANGE_TYPE_REMOVED,
    RunDiff,
)


# ---------------------------------------------------------------------------
# Status constants
# ---------------------------------------------------------------------------

REGRESSION_STATUS_CLEAN = "clean"
REGRESSION_STATUS_REGRESSION = "regression"

VALID_REGRESSION_STATUSES = frozenset({
    REGRESSION_STATUS_CLEAN,
    REGRESSION_STATUS_REGRESSION,
})


# ---------------------------------------------------------------------------
# Reason code constants
# ---------------------------------------------------------------------------

# Node regression reason codes
NODE_SUCCESS_TO_FAILURE = "NODE_SUCCESS_TO_FAILURE"
NODE_SUCCESS_TO_SKIPPED = "NODE_SUCCESS_TO_SKIPPED"
NODE_REMOVED_SUCCESS = "NODE_REMOVED_SUCCESS"

# Artifact regression reason codes
ARTIFACT_REMOVED = "ARTIFACT_REMOVED"
ARTIFACT_HASH_CHANGED = "ARTIFACT_HASH_CHANGED"

# Context regression reason codes
CONTEXT_KEY_REMOVED = "CONTEXT_KEY_REMOVED"
CONTEXT_VALUE_CHANGED = "CONTEXT_VALUE_CHANGED"

# All valid reason codes
VALID_REASON_CODES = frozenset({
    NODE_SUCCESS_TO_FAILURE,
    NODE_SUCCESS_TO_SKIPPED,
    NODE_REMOVED_SUCCESS,
    ARTIFACT_REMOVED,
    ARTIFACT_HASH_CHANGED,
    CONTEXT_KEY_REMOVED,
    CONTEXT_VALUE_CHANGED,
})


# ---------------------------------------------------------------------------
# Reason code to human-readable mapping
# ---------------------------------------------------------------------------

_REASON_CODE_DESCRIPTIONS = {
    NODE_SUCCESS_TO_FAILURE: "success -> failure",
    NODE_SUCCESS_TO_SKIPPED: "success -> skipped",
    NODE_REMOVED_SUCCESS: "removed successful node",
    ARTIFACT_REMOVED: "artifact removed",
    ARTIFACT_HASH_CHANGED: "hash changed",
    CONTEXT_KEY_REMOVED: "context key removed",
    CONTEXT_VALUE_CHANGED: "value changed",
}


def _get_reason_description(reason_code: str) -> str:
    """Get human-readable description for a reason code."""
    return _REASON_CODE_DESCRIPTIONS.get(reason_code, reason_code)


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class RegressionSummary:
    """Summary counts of detected regressions."""
    node_regressions: int = 0
    artifact_regressions: int = 0
    context_regressions: int = 0


@dataclass
class NodeRegression:
    """Records a single node regression."""
    node_id: str
    reason_code: str
    left_status: str | None
    right_status: str | None
    
    def __post_init__(self):
        """Validate reason_code on construction."""
        if self.reason_code not in VALID_REASON_CODES:
            raise ValueError(
                f"Invalid reason_code '{self.reason_code}' for NodeRegression. "
                f"Must be one of: {', '.join(sorted(VALID_REASON_CODES))}"
            )
    
    @property
    def reason(self) -> str:
        """Human-readable reason (backward compatibility)."""
        return _get_reason_description(self.reason_code)


@dataclass
class ArtifactRegression:
    """Records a single artifact regression."""
    artifact_id: str
    reason_code: str
    left_hash: str | None = None
    right_hash: str | None = None
    
    def __post_init__(self):
        """Validate reason_code on construction."""
        if self.reason_code not in VALID_REASON_CODES:
            raise ValueError(
                f"Invalid reason_code '{self.reason_code}' for ArtifactRegression. "
                f"Must be one of: {', '.join(sorted(VALID_REASON_CODES))}"
            )
    
    @property
    def reason(self) -> str:
        """Human-readable reason (backward compatibility)."""
        return _get_reason_description(self.reason_code)


@dataclass
class ContextRegression:
    """Records a single context key regression."""
    context_key: str
    reason_code: str
    left_value: Any = None
    right_value: Any = None
    
    def __post_init__(self):
        """Validate reason_code on construction."""
        if self.reason_code not in VALID_REASON_CODES:
            raise ValueError(
                f"Invalid reason_code '{self.reason_code}' for ContextRegression. "
                f"Must be one of: {', '.join(sorted(VALID_REASON_CODES))}"
            )
    
    @property
    def reason(self) -> str:
        """Human-readable reason (backward compatibility)."""
        return _get_reason_description(self.reason_code)


@dataclass
class RegressionResult:
    """Top-level result from regression detection.
    
    status:
        "regression" - at least one regression detected
        "clean"      - no regressions detected
    """
    status: str
    summary: RegressionSummary = field(default_factory=RegressionSummary)
    nodes: List[NodeRegression] = field(default_factory=list)
    artifacts: List[ArtifactRegression] = field(default_factory=list)
    context: List[ContextRegression] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Regression detection logic
# ---------------------------------------------------------------------------

def _detect_node_regressions(diff: RunDiff) -> List[NodeRegression]:
    """Detect node regressions from RunDiff.
    
    Regression rules:
    1. success -> failure
    2. success -> skipped
    3. removed node that was successful
    """
    regressions: List[NodeRegression] = []
    
    for node_diff in diff.node_diffs:
        node_id = node_diff.node_id
        left_status = node_diff.left_status
        right_status = node_diff.right_status
        change_type = node_diff.change_type
        
        # Rule 1: success -> failure
        if left_status == "success" and right_status == "failure":
            regressions.append(NodeRegression(
                node_id=node_id,
                reason_code=NODE_SUCCESS_TO_FAILURE,
                left_status=left_status,
                right_status=right_status,
            ))
            continue
        
        # Rule 2: success -> skipped
        if left_status == "success" and right_status == "skipped":
            regressions.append(NodeRegression(
                node_id=node_id,
                reason_code=NODE_SUCCESS_TO_SKIPPED,
                left_status=left_status,
                right_status=right_status,
            ))
            continue
        
        # Rule 3: removed successful node
        if change_type == CHANGE_TYPE_REMOVED and left_status == "success":
            regressions.append(NodeRegression(
                node_id=node_id,
                reason_code=NODE_REMOVED_SUCCESS,
                left_status=left_status,
                right_status=None,
            ))
            continue
    
    return regressions


def _detect_artifact_regressions(diff: RunDiff) -> List[ArtifactRegression]:
    """Detect artifact regressions from RunDiff.
    
    Regression rules:
    1. artifact removed
    2. artifact hash changed
    """
    regressions: List[ArtifactRegression] = []
    
    for art_diff in diff.artifact_diffs:
        artifact_id = art_diff.artifact_id
        change_type = art_diff.change_type
        left_hash = art_diff.left_hash
        right_hash = art_diff.right_hash
        
        # Rule 1: artifact removed
        if change_type == CHANGE_TYPE_REMOVED:
            regressions.append(ArtifactRegression(
                artifact_id=artifact_id,
                reason_code=ARTIFACT_REMOVED,
                left_hash=left_hash,
            ))
            continue
        
        # Rule 2: artifact hash changed
        if change_type == CHANGE_TYPE_MODIFIED and left_hash != right_hash:
            regressions.append(ArtifactRegression(
                artifact_id=artifact_id,
                reason_code=ARTIFACT_HASH_CHANGED,
                left_hash=left_hash,
                right_hash=right_hash,
            ))
            continue
    
    return regressions


def _detect_context_regressions(diff: RunDiff) -> List[ContextRegression]:
    """Detect context regressions from RunDiff.
    
    Regression rules:
    1. context key removed
    2. context key modified
    """
    regressions: List[ContextRegression] = []
    
    for ctx_diff in diff.context_diffs:
        context_key = ctx_diff.context_key
        change_type = ctx_diff.change_type
        left_value = ctx_diff.left_value
        right_value = ctx_diff.right_value
        
        # Rule 1: context key removed
        if change_type == CHANGE_TYPE_REMOVED:
            regressions.append(ContextRegression(
                context_key=context_key,
                reason_code=CONTEXT_KEY_REMOVED,
                left_value=left_value,
            ))
            continue
        
        # Rule 2: context key modified
        if change_type == CHANGE_TYPE_MODIFIED:
            regressions.append(ContextRegression(
                context_key=context_key,
                reason_code=CONTEXT_VALUE_CHANGED,
                left_value=left_value,
                right_value=right_value,
            ))
            continue
    
    return regressions


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def detect_regressions(diff: RunDiff) -> RegressionResult:
    """Detect regressions from a RunDiff.
    
    Args:
        diff: RunDiff output from compare_runs
    
    Returns:
        RegressionResult with detected regressions
    
    Raises:
        TypeError: if diff is not a RunDiff instance
    """
    if not isinstance(diff, RunDiff):
        raise TypeError(f"diff must be a RunDiff, got {type(diff).__name__}")
    
    node_regressions = _detect_node_regressions(diff)
    artifact_regressions = _detect_artifact_regressions(diff)
    context_regressions = _detect_context_regressions(diff)
    
    summary = RegressionSummary(
        node_regressions=len(node_regressions),
        artifact_regressions=len(artifact_regressions),
        context_regressions=len(context_regressions),
    )
    
    has_regression = bool(
        node_regressions or artifact_regressions or context_regressions
    )
    
    status = REGRESSION_STATUS_REGRESSION if has_regression else REGRESSION_STATUS_CLEAN
    
    return RegressionResult(
        status=status,
        summary=summary,
        nodes=node_regressions,
        artifacts=artifact_regressions,
        context=context_regressions,
    )


# ---------------------------------------------------------------------------
# Backward compatibility for legacy RunComparator
# ---------------------------------------------------------------------------

@dataclass
class LegacyRegressionResult:
    """Legacy compatibility result class."""
    type: str
    node_id: str
    severity: str
    description: str


@dataclass
class ExecutionRegressionReport:
    """Legacy compatibility class for RunComparator.
    
    This provides backward compatibility with the old API.
    """
    regressions: List[LegacyRegressionResult] = field(default_factory=list)
    total_regressions: int = 0
    highest_severity: str = "LOW"


class ExecutionRegressionDetector:
    """Legacy compatibility class for RunComparator.
    
    This class provides backward compatibility with the old ExecutionRegressionDetector
    API while maintaining the legacy behavior for Step166 tests.
    
    This is a thin wrapper that should eventually be phased out.
    """
    
    SEVERITY_ORDER = ["LOW", "MEDIUM", "HIGH"]
    
    @staticmethod
    def detect(diff_report) -> ExecutionRegressionReport:
        """Legacy detect method for backward compatibility.
        
        Note: This is a compatibility shim for the old ExecutionSnapshotDiffReport API.
        New code should use detect_regressions() with RunDiff.
        """
        regressions: List[LegacyRegressionResult] = []
        
        # Handle old ExecutionSnapshotDiffReport format
        # Node removed regressions
        removed_nodes = getattr(diff_report, 'removed_nodes', [])
        for node_id in removed_nodes:
            regressions.append(
                LegacyRegressionResult(
                    type="NODE_REMOVED",
                    node_id=node_id,
                    severity="HIGH",
                    description="Node removed from execution",
                )
            )
        
        # Modified node regressions
        modified_nodes = getattr(diff_report, 'modified_nodes', [])
        for node in modified_nodes:
            if getattr(node, 'hash_changed', False):
                regressions.append(
                    LegacyRegressionResult(
                        type="HASH_MISMATCH",
                        node_id=node.node_id,
                        severity="HIGH",
                        description="Output hash changed",
                    )
                )
            elif getattr(node, 'output_changed', False):
                regressions.append(
                    LegacyRegressionResult(
                        type="OUTPUT_CHANGED",
                        node_id=node.node_id,
                        severity="MEDIUM",
                        description="Node output changed",
                    )
                )
            elif getattr(node, 'metadata_changed', False):
                regressions.append(
                    LegacyRegressionResult(
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
            ) > ExecutionRegressionDetector.SEVERITY_ORDER.index(highest_severity):
                highest_severity = r.severity
        
        return ExecutionRegressionReport(
            regressions=regressions,
            total_regressions=len(regressions),
            highest_severity=highest_severity,
        )
