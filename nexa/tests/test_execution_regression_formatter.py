"""
test_execution_regression_formatter.py

Tests for execution_regression_formatter module.

Coverage:
- Summary formatting
- Detailed formatting with sections
- Clean result formatting
- JSON formatter structure
- JSON formatter deterministic output
"""
import json

from src.engine.execution_regression_detector import (
    ARTIFACT_HASH_CHANGED,
    ARTIFACT_REMOVED,
    CONTEXT_KEY_REMOVED,
    CONTEXT_VALUE_CHANGED,
    NODE_REMOVED_SUCCESS,
    NODE_SUCCESS_TO_FAILURE,
    NODE_SUCCESS_TO_SKIPPED,
    REGRESSION_SEVERITY_HIGH,
    REGRESSION_SEVERITY_MEDIUM,
    REGRESSION_SEVERITY_LOW,
    REGRESSION_STATUS_CLEAN,
    REGRESSION_STATUS_REGRESSION,
    ArtifactRegression,
    ContextRegression,
    NodeRegression,
    RegressionResult,
    RegressionSummary,
)
from src.engine.execution_regression_formatter import (
    format_regression,
    format_regression_json,
    format_regression_summary,
)


def test_format_regression_summary_with_regressions():
    """Test summary formatting with regressions present."""
    result = RegressionResult(
        status=REGRESSION_STATUS_REGRESSION,
        summary=RegressionSummary(
            node_regressions=2,
            artifact_regressions=1,
            context_regressions=3,
        ),
    )
    
    output = format_regression_summary(result)
    
    assert "Execution Regression" in output
    assert "status: regression" in output
    assert "nodes: 2" in output
    assert "artifacts: 1" in output
    assert "context: 3" in output


def test_format_regression_summary_clean():
    """Test summary formatting for clean result."""
    result = RegressionResult(
        status=REGRESSION_STATUS_CLEAN,
        summary=RegressionSummary(
            node_regressions=0,
            artifact_regressions=0,
            context_regressions=0,
        ),
    )
    
    output = format_regression_summary(result)
    
    assert "Execution Regression" in output
    assert "status: clean" in output
    assert "nodes: 0" in output
    assert "artifacts: 0" in output
    assert "context: 0" in output


def test_format_regression_clean_no_detail_sections():
    """Test that clean result has no detail sections."""
    result = RegressionResult(
        status=REGRESSION_STATUS_CLEAN,
        summary=RegressionSummary(),
    )
    
    output = format_regression(result)
    
    # Should have summary
    assert "Execution Regression" in output
    assert "status: clean" in output
    
    # Should NOT have detail sections
    assert "Node Regressions" not in output
    assert "Artifact Regressions" not in output
    assert "Context Regressions" not in output


def test_format_regression_with_node_regressions():
    """Test detailed formatting with node regressions."""
    result = RegressionResult(
        status=REGRESSION_STATUS_REGRESSION,
        summary=RegressionSummary(node_regressions=2),
        nodes=[
            NodeRegression(
                node_id="n1",
                reason_code=NODE_SUCCESS_TO_FAILURE,
                left_status="success",
                right_status="failure",
            ),
            NodeRegression(
                node_id="n2",
                reason_code=NODE_REMOVED_SUCCESS,
                left_status="success",
                right_status=None,
            ),
        ],
    )
    
    output = format_regression(result)
    
    assert "Node Regressions" in output
    assert "n1: success -> failure" in output
    assert "n2: removed (was success)" in output


def test_format_regression_with_artifact_regressions():
    """Test detailed formatting with artifact regressions."""
    result = RegressionResult(
        status=REGRESSION_STATUS_REGRESSION,
        summary=RegressionSummary(artifact_regressions=1),
        artifacts=[
            ArtifactRegression(
                artifact_id="art_1",
                reason_code=ARTIFACT_HASH_CHANGED,
                left_hash="old_hash",
                right_hash="new_hash",
            ),
        ],
    )
    
    output = format_regression(result)
    
    assert "Artifact Regressions" in output
    assert "art_1: hash changed" in output


def test_format_regression_with_context_regressions():
    """Test detailed formatting with context regressions."""
    result = RegressionResult(
        status=REGRESSION_STATUS_REGRESSION,
        summary=RegressionSummary(context_regressions=1),
        context=[
            ContextRegression(
                context_key="input.text.value",
                reason_code=CONTEXT_VALUE_CHANGED,
                left_value="old",
                right_value="new",
            ),
        ],
    )
    
    output = format_regression(result)
    
    assert "Context Regressions" in output
    assert "input.text.value: value changed" in output


def test_format_regression_all_sections():
    """Test formatting with all regression types present."""
    result = RegressionResult(
        status=REGRESSION_STATUS_REGRESSION,
        summary=RegressionSummary(
            node_regressions=1,
            artifact_regressions=1,
            context_regressions=1,
        ),
        nodes=[
            NodeRegression(
                node_id="n1",
                reason_code=NODE_SUCCESS_TO_FAILURE,
                left_status="success",
                right_status="failure",
            ),
        ],
        artifacts=[
            ArtifactRegression(
                artifact_id="art_1",
                reason_code=ARTIFACT_REMOVED,
            ),
        ],
        context=[
            ContextRegression(
                context_key="ctx.key",
                reason_code=CONTEXT_KEY_REMOVED,
            ),
        ],
    )
    
    output = format_regression(result)
    
    # Summary
    assert "Execution Regression" in output
    assert "status: regression" in output
    
    # All sections
    assert "Node Regressions" in output
    assert "Artifact Regressions" in output
    assert "Context Regressions" in output


def test_format_regression_json_structure():
    """Test JSON formatter produces correct structure."""
    result = RegressionResult(
        status=REGRESSION_STATUS_REGRESSION,
        summary=RegressionSummary(
            node_regressions=1,
            artifact_regressions=1,
            context_regressions=1,
        ),
        nodes=[
            NodeRegression(
                node_id="n1",
                reason_code=NODE_SUCCESS_TO_FAILURE,
                left_status="success",
                right_status="failure",
            ),
        ],
        artifacts=[
            ArtifactRegression(
                artifact_id="art_1",
                reason_code=ARTIFACT_HASH_CHANGED,
                left_hash="old",
                right_hash="new",
            ),
        ],
        context=[
            ContextRegression(
                context_key="ctx.key",
                reason_code=CONTEXT_VALUE_CHANGED,
                left_value="old_val",
                right_value="new_val",
            ),
        ],
    )
    
    output = format_regression_json(result)
    
    # Verify structure
    assert output["status"] == REGRESSION_STATUS_REGRESSION
    assert output["summary"]["node_regressions"] == 1
    assert output["summary"]["artifact_regressions"] == 1
    assert output["summary"]["context_regressions"] == 1
    
    assert len(output["nodes"]) == 1
    assert output["nodes"][0]["node_id"] == "n1"
    assert output["nodes"][0]["reason_code"] == NODE_SUCCESS_TO_FAILURE
    assert output["nodes"][0]["reason"] == "success -> failure"
    assert output["nodes"][0]["left_status"] == "success"
    assert output["nodes"][0]["right_status"] == "failure"
    
    assert len(output["artifacts"]) == 1
    assert output["artifacts"][0]["artifact_id"] == "art_1"
    assert output["artifacts"][0]["reason_code"] == ARTIFACT_HASH_CHANGED
    assert output["artifacts"][0]["reason"] == "hash changed"
    assert output["artifacts"][0]["left_hash"] == "old"
    assert output["artifacts"][0]["right_hash"] == "new"
    
    assert len(output["context"]) == 1
    assert output["context"][0]["context_key"] == "ctx.key"
    assert output["context"][0]["reason_code"] == CONTEXT_VALUE_CHANGED
    assert output["context"][0]["reason"] == "value changed"
    assert output["context"][0]["left_value"] == "old_val"
    assert output["context"][0]["right_value"] == "new_val"


def test_format_regression_json_clean():
    """Test JSON formatter for clean result."""
    result = RegressionResult(
        status=REGRESSION_STATUS_CLEAN,
        summary=RegressionSummary(),
    )
    
    output = format_regression_json(result)
    
    assert output["status"] == REGRESSION_STATUS_CLEAN
    assert output["summary"]["node_regressions"] == 0
    assert output["summary"]["artifact_regressions"] == 0
    assert output["summary"]["context_regressions"] == 0
    assert output["nodes"] == []
    assert output["artifacts"] == []
    assert output["context"] == []


def test_format_regression_json_deterministic():
    """Test that JSON formatter produces deterministic output."""
    result = RegressionResult(
        status=REGRESSION_STATUS_REGRESSION,
        summary=RegressionSummary(node_regressions=1),
        nodes=[
            NodeRegression(
                node_id="n1",
                reason_code=NODE_SUCCESS_TO_FAILURE,
                left_status="success",
                right_status="failure",
            ),
        ],
    )
    
    output1 = format_regression_json(result)
    output2 = format_regression_json(result)
    
    # JSON should be identical
    json_str1 = json.dumps(output1, sort_keys=True)
    json_str2 = json.dumps(output2, sort_keys=True)
    
    assert json_str1 == json_str2


def test_format_regression_json_serializable():
    """Test that JSON formatter output is json.dumps compatible."""
    result = RegressionResult(
        status=REGRESSION_STATUS_REGRESSION,
        summary=RegressionSummary(node_regressions=1),
        nodes=[
            NodeRegression(
                node_id="n1",
                reason_code=NODE_SUCCESS_TO_FAILURE,
                left_status="success",
                right_status="failure",
            ),
        ],
    )
    
    output = format_regression_json(result)
    
    # Should not raise
    json_str = json.dumps(output, indent=2)
    
    # Should be parseable
    parsed = json.loads(json_str)
    assert parsed["status"] == REGRESSION_STATUS_REGRESSION


# ---------------------------------------------------------------------------
# Severity formatting tests
# ---------------------------------------------------------------------------

def test_format_regression_summary_includes_severity_counts():
    """Test that summary includes severity counts."""
    from src.engine.execution_regression_detector import REGRESSION_SEVERITY_HIGH
    
    result = RegressionResult(
        status=REGRESSION_STATUS_REGRESSION,
        summary=RegressionSummary(
            node_regressions=1,
            high_regressions=1,
            medium_regressions=0,
            low_regressions=0,
        ),
        nodes=[
            NodeRegression(
                node_id="n1",
                reason_code=NODE_SUCCESS_TO_FAILURE,
                left_status="success",
                right_status="failure",
            ),
        ],
    )
    
    output = format_regression_summary(result)
    
    assert "severity: high=1 medium=0 low=0" in output


def test_format_regression_text_shows_severity_labels():
    """Test that detailed text formatter shows severity labels."""
    from src.engine.execution_regression_detector import (
        REGRESSION_SEVERITY_HIGH,
        REGRESSION_SEVERITY_MEDIUM,
        REGRESSION_SEVERITY_LOW,
    )
    
    result = RegressionResult(
        status=REGRESSION_STATUS_REGRESSION,
        summary=RegressionSummary(
            node_regressions=1,
            artifact_regressions=1,
            context_regressions=1,
            high_regressions=2,
            medium_regressions=0,
            low_regressions=1,
        ),
        nodes=[
            NodeRegression(
                node_id="n1",
                reason_code=NODE_SUCCESS_TO_FAILURE,
                left_status="success",
                right_status="failure",
            ),
        ],
        artifacts=[
            ArtifactRegression(
                artifact_id="art_1",
                reason_code=ARTIFACT_REMOVED,
            ),
        ],
        context=[
            ContextRegression(
                context_key="ctx.key",
                reason_code=CONTEXT_VALUE_CHANGED,
            ),
        ],
    )
    
    output = format_regression(result)
    
    # Check that severity labels appear
    assert "[HIGH]" in output
    assert "[LOW]" in output
    assert "n1: success -> failure [HIGH]" in output
    assert "art_1: artifact removed [HIGH]" in output
    assert "ctx.key: value changed [LOW]" in output


def test_format_regression_json_includes_severity():
    """Test that JSON formatter includes severity for each regression."""
    from src.engine.execution_regression_detector import (
        REGRESSION_SEVERITY_HIGH,
        REGRESSION_SEVERITY_MEDIUM,
        REGRESSION_SEVERITY_LOW,
    )
    
    result = RegressionResult(
        status=REGRESSION_STATUS_REGRESSION,
        summary=RegressionSummary(
            node_regressions=1,
            artifact_regressions=1,
            context_regressions=1,
            high_regressions=2,
            medium_regressions=0,
            low_regressions=1,
        ),
        nodes=[
            NodeRegression(
                node_id="n1",
                reason_code=NODE_SUCCESS_TO_FAILURE,
                left_status="success",
                right_status="failure",
            ),
        ],
        artifacts=[
            ArtifactRegression(
                artifact_id="art_1",
                reason_code=ARTIFACT_REMOVED,
            ),
        ],
        context=[
            ContextRegression(
                context_key="ctx.key",
                reason_code=CONTEXT_VALUE_CHANGED,
            ),
        ],
    )
    
    output = format_regression_json(result)
    
    # Check summary severity counts
    assert output["summary"]["high_regressions"] == 2
    assert output["summary"]["medium_regressions"] == 0
    assert output["summary"]["low_regressions"] == 1
    
    # Check individual regression severities
    assert output["nodes"][0]["severity"] == REGRESSION_SEVERITY_HIGH
    assert output["artifacts"][0]["severity"] == REGRESSION_SEVERITY_HIGH
    assert output["context"][0]["severity"] == REGRESSION_SEVERITY_LOW


def test_format_regression_json_clean_has_zero_severity_counts():
    """Test that clean result JSON has zero severity counts."""
    result = RegressionResult(
        status=REGRESSION_STATUS_CLEAN,
        summary=RegressionSummary(
            high_regressions=0,
            medium_regressions=0,
            low_regressions=0,
        ),
    )
    
    output = format_regression_json(result)
    
    assert output["summary"]["high_regressions"] == 0
    assert output["summary"]["medium_regressions"] == 0
    assert output["summary"]["low_regressions"] == 0


def test_format_regression_severity_deterministic():
    """Test that severity formatting is deterministic."""
    from src.engine.execution_regression_detector import REGRESSION_SEVERITY_HIGH
    
    result = RegressionResult(
        status=REGRESSION_STATUS_REGRESSION,
        summary=RegressionSummary(
            node_regressions=1,
            high_regressions=1,
            medium_regressions=0,
            low_regressions=0,
        ),
        nodes=[
            NodeRegression(
                node_id="n1",
                reason_code=NODE_SUCCESS_TO_FAILURE,
                left_status="success",
                right_status="failure",
            ),
        ],
    )
    
    # Format multiple times
    output1 = format_regression(result)
    output2 = format_regression(result)
    
    assert output1 == output2
    assert "[HIGH]" in output1
