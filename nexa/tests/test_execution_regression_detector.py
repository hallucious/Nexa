"""
test_execution_regression_detector.py

Tests for execution_regression_detector module.

Coverage:
- Node regression detection
- Artifact regression detection
- Context regression detection
- Clean runs (no regressions)
- Deterministic output
- TypeError handling
"""
import pytest

from src.engine.execution_diff_model import (
    CHANGE_TYPE_ADDED,
    CHANGE_TYPE_MODIFIED,
    CHANGE_TYPE_REMOVED,
    CHANGE_TYPE_UNCHANGED,
    RUN_DIFF_STATUS_CHANGED,
    RUN_DIFF_STATUS_IDENTICAL,
    ArtifactDiff,
    ContextDiff,
    DiffSummary,
    NodeDiff,
    RunDiff,
)
from src.engine.execution_regression_detector import (
    ARTIFACT_HASH_CHANGED,
    ARTIFACT_REMOVED,
    CONTEXT_KEY_REMOVED,
    CONTEXT_VALUE_CHANGED,
    NODE_REMOVED_SUCCESS,
    NODE_SUCCESS_TO_FAILURE,
    NODE_SUCCESS_TO_SKIPPED,
    REGRESSION_STATUS_CLEAN,
    REGRESSION_STATUS_REGRESSION,
    detect_regressions,
)


def test_node_regression_success_to_failure():
    """Test detection of success -> failure node regression."""
    node_diffs = [
        NodeDiff(
            node_id="n1",
            change_type=CHANGE_TYPE_MODIFIED,
            left_status="success",
            right_status="failure",
        )
    ]
    
    diff = RunDiff(
        left_run_id="left",
        right_run_id="right",
        status=RUN_DIFF_STATUS_CHANGED,
        node_diffs=node_diffs,
    )
    
    result = detect_regressions(diff)
    
    assert result.status == REGRESSION_STATUS_REGRESSION
    assert result.summary.node_regressions == 1
    assert len(result.nodes) == 1
    assert result.nodes[0].node_id == "n1"
    assert result.nodes[0].reason_code == NODE_SUCCESS_TO_FAILURE
    assert result.nodes[0].reason == "success -> failure"


def test_node_regression_success_to_skipped():
    """Test detection of success -> skipped node regression."""
    node_diffs = [
        NodeDiff(
            node_id="n2",
            change_type=CHANGE_TYPE_MODIFIED,
            left_status="success",
            right_status="skipped",
        )
    ]
    
    diff = RunDiff(
        left_run_id="left",
        right_run_id="right",
        status=RUN_DIFF_STATUS_CHANGED,
        node_diffs=node_diffs,
    )
    
    result = detect_regressions(diff)
    
    assert result.status == REGRESSION_STATUS_REGRESSION
    assert result.summary.node_regressions == 1
    assert len(result.nodes) == 1
    assert result.nodes[0].node_id == "n2"
    assert result.nodes[0].reason_code == NODE_SUCCESS_TO_SKIPPED
    assert result.nodes[0].reason == "success -> skipped"


def test_node_regression_removed_successful():
    """Test detection of removed successful node regression."""
    node_diffs = [
        NodeDiff(
            node_id="n3",
            change_type=CHANGE_TYPE_REMOVED,
            left_status="success",
            right_status=None,
        )
    ]
    
    diff = RunDiff(
        left_run_id="left",
        right_run_id="right",
        status=RUN_DIFF_STATUS_CHANGED,
        node_diffs=node_diffs,
    )
    
    result = detect_regressions(diff)
    
    assert result.status == REGRESSION_STATUS_REGRESSION
    assert result.summary.node_regressions == 1
    assert len(result.nodes) == 1
    assert result.nodes[0].node_id == "n3"
    assert result.nodes[0].reason_code == NODE_REMOVED_SUCCESS
    assert result.nodes[0].reason == "removed successful node"
    assert result.nodes[0].left_status == "success"
    assert result.nodes[0].right_status is None


def test_artifact_regression_removed():
    """Test detection of artifact removed regression."""
    artifact_diffs = [
        ArtifactDiff(
            artifact_id="art_1",
            change_type=CHANGE_TYPE_REMOVED,
            left_hash="hash_abc",
        )
    ]
    
    diff = RunDiff(
        left_run_id="left",
        right_run_id="right",
        status=RUN_DIFF_STATUS_CHANGED,
        artifact_diffs=artifact_diffs,
    )
    
    result = detect_regressions(diff)
    
    assert result.status == REGRESSION_STATUS_REGRESSION
    assert result.summary.artifact_regressions == 1
    assert len(result.artifacts) == 1
    assert result.artifacts[0].artifact_id == "art_1"
    assert result.artifacts[0].reason_code == ARTIFACT_REMOVED
    assert result.artifacts[0].reason == "artifact removed"


def test_artifact_regression_hash_changed():
    """Test detection of artifact hash change regression."""
    artifact_diffs = [
        ArtifactDiff(
            artifact_id="art_2",
            change_type=CHANGE_TYPE_MODIFIED,
            left_hash="hash_old",
            right_hash="hash_new",
        )
    ]
    
    diff = RunDiff(
        left_run_id="left",
        right_run_id="right",
        status=RUN_DIFF_STATUS_CHANGED,
        artifact_diffs=artifact_diffs,
    )
    
    result = detect_regressions(diff)
    
    assert result.status == REGRESSION_STATUS_REGRESSION
    assert result.summary.artifact_regressions == 1
    assert len(result.artifacts) == 1
    assert result.artifacts[0].artifact_id == "art_2"
    assert result.artifacts[0].reason_code == ARTIFACT_HASH_CHANGED
    assert result.artifacts[0].reason == "hash changed"
    assert result.artifacts[0].left_hash == "hash_old"
    assert result.artifacts[0].right_hash == "hash_new"


def test_artifact_kind_only_change_is_not_regression():
    """Test that artifact kind-only change (no hash change) is NOT a regression."""
    artifact_diffs = [
        ArtifactDiff(
            artifact_id="art_3",
            change_type=CHANGE_TYPE_MODIFIED,
            left_hash="hash_same",
            right_hash="hash_same",
            left_kind="text",
            right_kind="json",
        )
    ]
    
    diff = RunDiff(
        left_run_id="left",
        right_run_id="right",
        status=RUN_DIFF_STATUS_CHANGED,
        artifact_diffs=artifact_diffs,
    )
    
    result = detect_regressions(diff)
    
    assert result.status == REGRESSION_STATUS_CLEAN
    assert result.summary.artifact_regressions == 0
    assert len(result.artifacts) == 0


def test_context_regression_removed():
    """Test detection of context key removed regression."""
    context_diffs = [
        ContextDiff(
            context_key="input.text.value",
            change_type=CHANGE_TYPE_REMOVED,
            left_value="some value",
        )
    ]
    
    diff = RunDiff(
        left_run_id="left",
        right_run_id="right",
        status=RUN_DIFF_STATUS_CHANGED,
        context_diffs=context_diffs,
    )
    
    result = detect_regressions(diff)
    
    assert result.status == REGRESSION_STATUS_REGRESSION
    assert result.summary.context_regressions == 1
    assert len(result.context) == 1
    assert result.context[0].context_key == "input.text.value"
    assert result.context[0].reason_code == CONTEXT_KEY_REMOVED
    assert result.context[0].reason == "context key removed"


def test_context_regression_modified():
    """Test detection of context key modified regression."""
    context_diffs = [
        ContextDiff(
            context_key="output.result",
            change_type=CHANGE_TYPE_MODIFIED,
            left_value="old_value",
            right_value="new_value",
        )
    ]
    
    diff = RunDiff(
        left_run_id="left",
        right_run_id="right",
        status=RUN_DIFF_STATUS_CHANGED,
        context_diffs=context_diffs,
    )
    
    result = detect_regressions(diff)
    
    assert result.status == REGRESSION_STATUS_REGRESSION
    assert result.summary.context_regressions == 1
    assert len(result.context) == 1
    assert result.context[0].context_key == "output.result"
    assert result.context[0].reason_code == CONTEXT_VALUE_CHANGED
    assert result.context[0].reason == "value changed"


def test_clean_diff_produces_clean_status():
    """Test that a clean diff produces clean regression status."""
    diff = RunDiff(
        left_run_id="left",
        right_run_id="right",
        status=RUN_DIFF_STATUS_IDENTICAL,
    )
    
    result = detect_regressions(diff)
    
    assert result.status == REGRESSION_STATUS_CLEAN
    assert result.summary.node_regressions == 0
    assert result.summary.artifact_regressions == 0
    assert result.summary.context_regressions == 0
    assert len(result.nodes) == 0
    assert len(result.artifacts) == 0
    assert len(result.context) == 0


def test_changed_diff_without_regressions():
    """Test that a changed diff without regressions produces clean status."""
    # Node added (not a regression)
    node_diffs = [
        NodeDiff(
            node_id="n_new",
            change_type=CHANGE_TYPE_ADDED,
            right_status="success",
        )
    ]
    
    # Artifact added (not a regression)
    artifact_diffs = [
        ArtifactDiff(
            artifact_id="art_new",
            change_type=CHANGE_TYPE_ADDED,
            right_hash="hash_new",
        )
    ]
    
    # Context added (not a regression)
    context_diffs = [
        ContextDiff(
            context_key="new.key",
            change_type=CHANGE_TYPE_ADDED,
            right_value="new_value",
        )
    ]
    
    diff = RunDiff(
        left_run_id="left",
        right_run_id="right",
        status=RUN_DIFF_STATUS_CHANGED,
        node_diffs=node_diffs,
        artifact_diffs=artifact_diffs,
        context_diffs=context_diffs,
    )
    
    result = detect_regressions(diff)
    
    assert result.status == REGRESSION_STATUS_CLEAN
    assert result.summary.node_regressions == 0
    assert result.summary.artifact_regressions == 0
    assert result.summary.context_regressions == 0


def test_deterministic_detector_output():
    """Test that detector produces deterministic output for same input."""
    node_diffs = [
        NodeDiff(
            node_id="n1",
            change_type=CHANGE_TYPE_MODIFIED,
            left_status="success",
            right_status="failure",
        )
    ]
    
    diff = RunDiff(
        left_run_id="left",
        right_run_id="right",
        status=RUN_DIFF_STATUS_CHANGED,
        node_diffs=node_diffs,
    )
    
    result1 = detect_regressions(diff)
    result2 = detect_regressions(diff)
    
    assert result1.status == result2.status
    assert result1.summary.node_regressions == result2.summary.node_regressions
    assert len(result1.nodes) == len(result2.nodes)
    assert result1.nodes[0].node_id == result2.nodes[0].node_id


def test_detect_regressions_type_error():
    """Test that detect_regressions raises TypeError for invalid input."""
    with pytest.raises(TypeError, match="diff must be a RunDiff"):
        detect_regressions({"invalid": "dict"})


def test_multiple_regressions_combined():
    """Test detection of multiple regression types in one diff."""
    node_diffs = [
        NodeDiff(
            node_id="n1",
            change_type=CHANGE_TYPE_MODIFIED,
            left_status="success",
            right_status="failure",
        ),
        NodeDiff(
            node_id="n2",
            change_type=CHANGE_TYPE_REMOVED,
            left_status="success",
        ),
    ]
    
    artifact_diffs = [
        ArtifactDiff(
            artifact_id="art_1",
            change_type=CHANGE_TYPE_REMOVED,
            left_hash="hash_abc",
        )
    ]
    
    context_diffs = [
        ContextDiff(
            context_key="ctx.key",
            change_type=CHANGE_TYPE_MODIFIED,
            left_value="old",
            right_value="new",
        )
    ]
    
    diff = RunDiff(
        left_run_id="left",
        right_run_id="right",
        status=RUN_DIFF_STATUS_CHANGED,
        node_diffs=node_diffs,
        artifact_diffs=artifact_diffs,
        context_diffs=context_diffs,
    )
    
    result = detect_regressions(diff)
    
    assert result.status == REGRESSION_STATUS_REGRESSION
    assert result.summary.node_regressions == 2
    assert result.summary.artifact_regressions == 1
    assert result.summary.context_regressions == 1
    assert len(result.nodes) == 2
    assert len(result.artifacts) == 1
    assert len(result.context) == 1


# ---------------------------------------------------------------------------
# Reason code validation tests
# ---------------------------------------------------------------------------

def test_node_regression_invalid_reason_code_raises_error():
    """Test that NodeRegression raises ValueError for invalid reason_code."""
    from src.engine.execution_regression_detector import NodeRegression
    
    with pytest.raises(ValueError) as exc_info:
        NodeRegression(
            node_id="n1",
            reason_code="INVALID_CODE",
            left_status="success",
            right_status="failure",
        )
    
    assert "Invalid reason_code 'INVALID_CODE'" in str(exc_info.value)
    assert "NodeRegression" in str(exc_info.value)


def test_artifact_regression_invalid_reason_code_raises_error():
    """Test that ArtifactRegression raises ValueError for invalid reason_code."""
    from src.engine.execution_regression_detector import ArtifactRegression
    
    with pytest.raises(ValueError) as exc_info:
        ArtifactRegression(
            artifact_id="art_1",
            reason_code="INVALID_CODE",
        )
    
    assert "Invalid reason_code 'INVALID_CODE'" in str(exc_info.value)
    assert "ArtifactRegression" in str(exc_info.value)


def test_context_regression_invalid_reason_code_raises_error():
    """Test that ContextRegression raises ValueError for invalid reason_code."""
    from src.engine.execution_regression_detector import ContextRegression
    
    with pytest.raises(ValueError) as exc_info:
        ContextRegression(
            context_key="ctx.key",
            reason_code="INVALID_CODE",
        )
    
    assert "Invalid reason_code 'INVALID_CODE'" in str(exc_info.value)
    assert "ContextRegression" in str(exc_info.value)


def test_valid_reason_codes_still_work():
    """Test that valid reason_codes continue to work unchanged."""
    from src.engine.execution_regression_detector import (
        NodeRegression,
        ArtifactRegression,
        ContextRegression,
    )
    
    # Should not raise
    node_reg = NodeRegression(
        node_id="n1",
        reason_code=NODE_SUCCESS_TO_FAILURE,
        left_status="success",
        right_status="failure",
    )
    assert node_reg.reason_code == NODE_SUCCESS_TO_FAILURE
    assert node_reg.reason == "success -> failure"
    
    # Should not raise
    artifact_reg = ArtifactRegression(
        artifact_id="art_1",
        reason_code=ARTIFACT_REMOVED,
    )
    assert artifact_reg.reason_code == ARTIFACT_REMOVED
    assert artifact_reg.reason == "artifact removed"
    
    # Should not raise
    context_reg = ContextRegression(
        context_key="ctx.key",
        reason_code=CONTEXT_VALUE_CHANGED,
    )
    assert context_reg.reason_code == CONTEXT_VALUE_CHANGED
    assert context_reg.reason == "value changed"


def test_detect_regressions_output_unchanged():
    """Test that detect_regressions output remains unchanged after validation."""
    # This verifies that the validation doesn't break the normal detection path
    node_diffs = [
        NodeDiff(
            node_id="n1",
            change_type=CHANGE_TYPE_MODIFIED,
            left_status="success",
            right_status="failure",
        )
    ]
    
    diff = RunDiff(
        left_run_id="left",
        right_run_id="right",
        status=RUN_DIFF_STATUS_CHANGED,
        node_diffs=node_diffs,
    )
    
    # Should work exactly as before
    result = detect_regressions(diff)
    
    assert result.status == REGRESSION_STATUS_REGRESSION
    assert result.summary.node_regressions == 1
    assert len(result.nodes) == 1
    assert result.nodes[0].reason_code == NODE_SUCCESS_TO_FAILURE
    assert result.nodes[0].reason == "success -> failure"


# ---------------------------------------------------------------------------
# Severity modeling tests
# ---------------------------------------------------------------------------

def test_node_success_to_failure_severity_is_high():
    """Test NODE_SUCCESS_TO_FAILURE maps to HIGH severity."""
    from src.engine.execution_regression_detector import (
        NodeRegression,
        REGRESSION_SEVERITY_HIGH,
    )
    
    reg = NodeRegression(
        node_id="n1",
        reason_code=NODE_SUCCESS_TO_FAILURE,
        left_status="success",
        right_status="failure",
    )
    
    assert reg.severity == REGRESSION_SEVERITY_HIGH


def test_node_removed_success_severity_is_high():
    """Test NODE_REMOVED_SUCCESS maps to HIGH severity."""
    from src.engine.execution_regression_detector import (
        NodeRegression,
        REGRESSION_SEVERITY_HIGH,
    )
    
    reg = NodeRegression(
        node_id="n1",
        reason_code=NODE_REMOVED_SUCCESS,
        left_status="success",
        right_status=None,
    )
    
    assert reg.severity == REGRESSION_SEVERITY_HIGH


def test_node_success_to_skipped_severity_is_medium():
    """Test NODE_SUCCESS_TO_SKIPPED maps to MEDIUM severity."""
    from src.engine.execution_regression_detector import (
        NodeRegression,
        REGRESSION_SEVERITY_MEDIUM,
    )
    
    reg = NodeRegression(
        node_id="n1",
        reason_code=NODE_SUCCESS_TO_SKIPPED,
        left_status="success",
        right_status="skipped",
    )
    
    assert reg.severity == REGRESSION_SEVERITY_MEDIUM


def test_artifact_removed_severity_is_high():
    """Test ARTIFACT_REMOVED maps to HIGH severity."""
    from src.engine.execution_regression_detector import (
        ArtifactRegression,
        REGRESSION_SEVERITY_HIGH,
        ARTIFACT_REMOVED,
    )
    
    reg = ArtifactRegression(
        artifact_id="art_1",
        reason_code=ARTIFACT_REMOVED,
    )
    
    assert reg.severity == REGRESSION_SEVERITY_HIGH


def test_artifact_hash_changed_severity_is_medium():
    """Test ARTIFACT_HASH_CHANGED maps to MEDIUM severity."""
    from src.engine.execution_regression_detector import (
        ArtifactRegression,
        REGRESSION_SEVERITY_MEDIUM,
        ARTIFACT_HASH_CHANGED,
    )
    
    reg = ArtifactRegression(
        artifact_id="art_1",
        reason_code=ARTIFACT_HASH_CHANGED,
        left_hash="old",
        right_hash="new",
    )
    
    assert reg.severity == REGRESSION_SEVERITY_MEDIUM


def test_context_key_removed_severity_is_medium():
    """Test CONTEXT_KEY_REMOVED maps to MEDIUM severity."""
    from src.engine.execution_regression_detector import (
        ContextRegression,
        REGRESSION_SEVERITY_MEDIUM,
        CONTEXT_KEY_REMOVED,
    )
    
    reg = ContextRegression(
        context_key="ctx.key",
        reason_code=CONTEXT_KEY_REMOVED,
    )
    
    assert reg.severity == REGRESSION_SEVERITY_MEDIUM


def test_context_value_changed_severity_is_low():
    """Test CONTEXT_VALUE_CHANGED maps to LOW severity."""
    from src.engine.execution_regression_detector import (
        ContextRegression,
        REGRESSION_SEVERITY_LOW,
        CONTEXT_VALUE_CHANGED,
    )
    
    reg = ContextRegression(
        context_key="ctx.key",
        reason_code=CONTEXT_VALUE_CHANGED,
        left_value="old",
        right_value="new",
    )
    
    assert reg.severity == REGRESSION_SEVERITY_LOW


def test_severity_counts_in_summary():
    """Test that severity counts are correctly calculated in RegressionSummary."""
    from src.engine.execution_regression_detector import (
        REGRESSION_SEVERITY_HIGH,
        REGRESSION_SEVERITY_MEDIUM,
        REGRESSION_SEVERITY_LOW,
    )
    
    # Create a diff with multiple regressions of different severities
    node_diffs = [
        NodeDiff(
            node_id="n1",
            change_type=CHANGE_TYPE_MODIFIED,
            left_status="success",
            right_status="failure",  # HIGH
        ),
        NodeDiff(
            node_id="n2",
            change_type=CHANGE_TYPE_MODIFIED,
            left_status="success",
            right_status="skipped",  # MEDIUM
        ),
    ]
    
    artifact_diffs = [
        ArtifactDiff(
            artifact_id="art_1",
            change_type=CHANGE_TYPE_REMOVED,
            left_hash="hash_abc",  # HIGH
        ),
        ArtifactDiff(
            artifact_id="art_2",
            change_type=CHANGE_TYPE_MODIFIED,
            left_hash="old_hash",
            right_hash="new_hash",  # MEDIUM
        ),
    ]
    
    context_diffs = [
        ContextDiff(
            context_key="ctx.key1",
            change_type=CHANGE_TYPE_MODIFIED,
            left_value="old",
            right_value="new",  # LOW
        ),
    ]
    
    diff = RunDiff(
        left_run_id="left",
        right_run_id="right",
        status=RUN_DIFF_STATUS_CHANGED,
        node_diffs=node_diffs,
        artifact_diffs=artifact_diffs,
        context_diffs=context_diffs,
    )
    
    result = detect_regressions(diff)
    
    # Verify severity counts
    assert result.summary.high_regressions == 2  # n1, art_1
    assert result.summary.medium_regressions == 2  # n2, art_2
    assert result.summary.low_regressions == 1  # ctx.key1
    
    # Verify individual severities
    assert result.nodes[0].severity == REGRESSION_SEVERITY_HIGH
    assert result.nodes[1].severity == REGRESSION_SEVERITY_MEDIUM
    assert result.artifacts[0].severity == REGRESSION_SEVERITY_HIGH
    assert result.artifacts[1].severity == REGRESSION_SEVERITY_MEDIUM
    assert result.context[0].severity == REGRESSION_SEVERITY_LOW


def test_clean_result_has_zero_severity_counts():
    """Test that clean results have zero severity counts."""
    diff = RunDiff(
        left_run_id="left",
        right_run_id="right",
        status=RUN_DIFF_STATUS_IDENTICAL,
    )
    
    result = detect_regressions(diff)
    
    assert result.summary.high_regressions == 0
    assert result.summary.medium_regressions == 0
    assert result.summary.low_regressions == 0


def test_severity_deterministic_output():
    """Test that severity assignment is deterministic."""
    from src.engine.execution_regression_detector import REGRESSION_SEVERITY_HIGH
    
    # Run detection twice
    node_diffs = [
        NodeDiff(
            node_id="n1",
            change_type=CHANGE_TYPE_MODIFIED,
            left_status="success",
            right_status="failure",
        )
    ]
    
    diff = RunDiff(
        left_run_id="left",
        right_run_id="right",
        status=RUN_DIFF_STATUS_CHANGED,
        node_diffs=node_diffs,
    )
    
    result1 = detect_regressions(diff)
    result2 = detect_regressions(diff)
    
    # Severity should be consistent
    assert result1.nodes[0].severity == result2.nodes[0].severity
    assert result1.nodes[0].severity == REGRESSION_SEVERITY_HIGH
    assert result1.summary.high_regressions == result2.summary.high_regressions
    assert result1.summary.high_regressions == 1


# ---------------------------------------------------------------------------
# Category-specific reason_code validation tests (Step186.2.1)
# ---------------------------------------------------------------------------

def test_node_regression_rejects_artifact_reason_code():
    """Test NodeRegression rejects artifact reason codes."""
    from src.engine.execution_regression_detector import (
        NodeRegression,
        ARTIFACT_REMOVED,
    )
    
    with pytest.raises(ValueError) as exc_info:
        NodeRegression(
            node_id="n1",
            reason_code=ARTIFACT_REMOVED,
            left_status="success",
            right_status="failure",
        )
    
    assert "Invalid reason_code" in str(exc_info.value)
    assert "NodeRegression" in str(exc_info.value)
    assert ARTIFACT_REMOVED in str(exc_info.value)


def test_node_regression_rejects_context_reason_code():
    """Test NodeRegression rejects context reason codes."""
    from src.engine.execution_regression_detector import (
        NodeRegression,
        CONTEXT_KEY_REMOVED,
    )
    
    with pytest.raises(ValueError) as exc_info:
        NodeRegression(
            node_id="n1",
            reason_code=CONTEXT_KEY_REMOVED,
            left_status="success",
            right_status="failure",
        )
    
    assert "Invalid reason_code" in str(exc_info.value)
    assert "NodeRegression" in str(exc_info.value)
    assert CONTEXT_KEY_REMOVED in str(exc_info.value)


def test_artifact_regression_rejects_node_reason_code():
    """Test ArtifactRegression rejects node reason codes."""
    from src.engine.execution_regression_detector import (
        ArtifactRegression,
        NODE_SUCCESS_TO_FAILURE,
    )
    
    with pytest.raises(ValueError) as exc_info:
        ArtifactRegression(
            artifact_id="art_1",
            reason_code=NODE_SUCCESS_TO_FAILURE,
        )
    
    assert "Invalid reason_code" in str(exc_info.value)
    assert "ArtifactRegression" in str(exc_info.value)
    assert NODE_SUCCESS_TO_FAILURE in str(exc_info.value)


def test_artifact_regression_rejects_context_reason_code():
    """Test ArtifactRegression rejects context reason codes."""
    from src.engine.execution_regression_detector import (
        ArtifactRegression,
        CONTEXT_VALUE_CHANGED,
    )
    
    with pytest.raises(ValueError) as exc_info:
        ArtifactRegression(
            artifact_id="art_1",
            reason_code=CONTEXT_VALUE_CHANGED,
        )
    
    assert "Invalid reason_code" in str(exc_info.value)
    assert "ArtifactRegression" in str(exc_info.value)
    assert CONTEXT_VALUE_CHANGED in str(exc_info.value)


def test_context_regression_rejects_node_reason_code():
    """Test ContextRegression rejects node reason codes."""
    from src.engine.execution_regression_detector import (
        ContextRegression,
        NODE_REMOVED_SUCCESS,
    )
    
    with pytest.raises(ValueError) as exc_info:
        ContextRegression(
            context_key="ctx.key",
            reason_code=NODE_REMOVED_SUCCESS,
        )
    
    assert "Invalid reason_code" in str(exc_info.value)
    assert "ContextRegression" in str(exc_info.value)
    assert NODE_REMOVED_SUCCESS in str(exc_info.value)


def test_context_regression_rejects_artifact_reason_code():
    """Test ContextRegression rejects artifact reason codes."""
    from src.engine.execution_regression_detector import (
        ContextRegression,
        ARTIFACT_HASH_CHANGED,
    )
    
    with pytest.raises(ValueError) as exc_info:
        ContextRegression(
            context_key="ctx.key",
            reason_code=ARTIFACT_HASH_CHANGED,
        )
    
    assert "Invalid reason_code" in str(exc_info.value)
    assert "ContextRegression" in str(exc_info.value)
    assert ARTIFACT_HASH_CHANGED in str(exc_info.value)


def test_valid_category_specific_codes_still_work():
    """Test that valid category-specific codes continue to work."""
    from src.engine.execution_regression_detector import (
        NodeRegression,
        ArtifactRegression,
        ContextRegression,
        NODE_SUCCESS_TO_FAILURE,
        ARTIFACT_REMOVED,
        CONTEXT_KEY_REMOVED,
    )
    
    # Node regression with node code
    node_reg = NodeRegression(
        node_id="n1",
        reason_code=NODE_SUCCESS_TO_FAILURE,
        left_status="success",
        right_status="failure",
    )
    assert node_reg.reason_code == NODE_SUCCESS_TO_FAILURE
    
    # Artifact regression with artifact code
    artifact_reg = ArtifactRegression(
        artifact_id="art_1",
        reason_code=ARTIFACT_REMOVED,
    )
    assert artifact_reg.reason_code == ARTIFACT_REMOVED
    
    # Context regression with context code
    context_reg = ContextRegression(
        context_key="ctx.key",
        reason_code=CONTEXT_KEY_REMOVED,
    )
    assert context_reg.reason_code == CONTEXT_KEY_REMOVED


def test_detect_regressions_unchanged_with_category_validation():
    """Test that detect_regressions behavior is unchanged after category validation."""
    # This verifies that category-specific validation doesn't break normal detection
    node_diffs = [
        NodeDiff(
            node_id="n1",
            change_type=CHANGE_TYPE_MODIFIED,
            left_status="success",
            right_status="failure",
        )
    ]
    
    artifact_diffs = [
        ArtifactDiff(
            artifact_id="art_1",
            change_type=CHANGE_TYPE_REMOVED,
            left_hash="hash_abc",
        )
    ]
    
    context_diffs = [
        ContextDiff(
            context_key="ctx.key",
            change_type=CHANGE_TYPE_MODIFIED,
            left_value="old",
            right_value="new",
        )
    ]
    
    diff = RunDiff(
        left_run_id="left",
        right_run_id="right",
        status=RUN_DIFF_STATUS_CHANGED,
        node_diffs=node_diffs,
        artifact_diffs=artifact_diffs,
        context_diffs=context_diffs,
    )
    
    result = detect_regressions(diff)
    
    # Should work exactly as before
    assert result.status == REGRESSION_STATUS_REGRESSION
    assert result.summary.node_regressions == 1
    assert result.summary.artifact_regressions == 1
    assert result.summary.context_regressions == 1
    assert len(result.nodes) == 1
    assert len(result.artifacts) == 1
    assert len(result.context) == 1
    assert result.nodes[0].reason_code == NODE_SUCCESS_TO_FAILURE
    assert result.artifacts[0].reason_code == ARTIFACT_REMOVED
    assert result.context[0].reason_code == CONTEXT_VALUE_CHANGED
