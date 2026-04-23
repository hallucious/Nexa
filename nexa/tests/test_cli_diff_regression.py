"""
test_cli_diff_regression.py

Tests for CLI diff --regression mode integration.

Coverage:
- --regression text output path
- --regression --json output path
- Clean regression output
- Changed diff with regressions
- Parser registration for --regression
- Subprocess execution path
- Ensure legacy diff output still works
"""
import json
import subprocess
import tempfile
from pathlib import Path

import pytest


def _write_json_file(path, data):
    """Helper to write JSON data to file."""
    with open(path, "w") as f:
        json.dump(data, f)


def test_regression_flag_registered():
    """Test that --regression flag is registered in parser."""
    result = subprocess.run(
        ["python", "-m", "src.cli.nexa_cli", "diff", "--help"],
        capture_output=True,
        text=True,
    )
    
    assert result.returncode == 0
    assert "--regression" in result.stdout


def test_regression_text_output():
    """Test --regression produces text regression output."""
    # Create test snapshots
    left_run = {
        "run_id": "left",
        "nodes": {
            "n1": {"status": "success"},
        },
    }
    
    right_run = {
        "run_id": "right",
        "nodes": {
            "n1": {"status": "failure"},
        },
    }
    
    with tempfile.TemporaryDirectory() as tmpdir:
        left_path = Path(tmpdir) / "left.json"
        right_path = Path(tmpdir) / "right.json"
        
        _write_json_file(left_path, left_run)
        _write_json_file(right_path, right_run)
        
        result = subprocess.run(
            [
                "python", "-m", "src.cli.nexa_cli",
                "diff",
                str(left_path),
                str(right_path),
                "--regression",
            ],
            capture_output=True,
            text=True,
        )
        
        assert result.returncode == 0
        assert "Execution Regression" in result.stdout
        assert "status: regression" in result.stdout
        assert "nodes: 1" in result.stdout
        assert "Node Regressions" in result.stdout
        assert "n1: success -> failure" in result.stdout


def test_regression_json_output():
    """Test --regression --json produces JSON regression output."""
    left_run = {
        "run_id": "left",
        "nodes": {
            "n1": {"status": "success"},
        },
        "artifacts": {
            "art_1": {"hash": "hash_old"},
        },
    }
    
    right_run = {
        "run_id": "right",
        "nodes": {
            "n1": {"status": "success"},
        },
        "artifacts": {
            "art_1": {"hash": "hash_new"},
        },
    }
    
    with tempfile.TemporaryDirectory() as tmpdir:
        left_path = Path(tmpdir) / "left.json"
        right_path = Path(tmpdir) / "right.json"
        
        _write_json_file(left_path, left_run)
        _write_json_file(right_path, right_run)
        
        result = subprocess.run(
            [
                "python", "-m", "src.cli.nexa_cli",
                "diff",
                str(left_path),
                str(right_path),
                "--regression",
                "--json",
            ],
            capture_output=True,
            text=True,
        )
        
        assert result.returncode == 0
        
        output = json.loads(result.stdout)
        assert output["status"] == "regression"
        assert output["summary"]["artifact_regressions"] == 1
        assert len(output["artifacts"]) == 1
        assert output["artifacts"][0]["artifact_id"] == "art_1"


def test_regression_clean_output():
    """Test --regression with clean (no regression) diff."""
    left_run = {
        "run_id": "left",
        "nodes": {
            "n1": {"status": "success"},
        },
    }
    
    right_run = {
        "run_id": "right",
        "nodes": {
            "n1": {"status": "success"},
        },
    }
    
    with tempfile.TemporaryDirectory() as tmpdir:
        left_path = Path(tmpdir) / "left.json"
        right_path = Path(tmpdir) / "right.json"
        
        _write_json_file(left_path, left_run)
        _write_json_file(right_path, right_run)
        
        result = subprocess.run(
            [
                "python", "-m", "src.cli.nexa_cli",
                "diff",
                str(left_path),
                str(right_path),
                "--regression",
            ],
            capture_output=True,
            text=True,
        )
        
        assert result.returncode == 0
        assert "status: clean" in result.stdout
        assert "nodes: 0" in result.stdout
        # Should not have detail sections
        assert "Node Regressions" not in result.stdout


def test_regression_multiple_regressions():
    """Test --regression with multiple regression types."""
    left_run = {
        "run_id": "left",
        "nodes": {
            "n1": {"status": "success"},
            "n2": {"status": "success"},
        },
        "artifacts": {
            "art_1": {"hash": "hash_abc"},
        },
        "context": {
            "input.text": "value_old",
        },
    }
    
    right_run = {
        "run_id": "right",
        "nodes": {
            "n1": {"status": "failure"},
            # n2 removed
        },
        "artifacts": {
            # art_1 removed
        },
        "context": {
            "input.text": "value_new",
        },
    }
    
    with tempfile.TemporaryDirectory() as tmpdir:
        left_path = Path(tmpdir) / "left.json"
        right_path = Path(tmpdir) / "right.json"
        
        _write_json_file(left_path, left_run)
        _write_json_file(right_path, right_run)
        
        result = subprocess.run(
            [
                "python", "-m", "src.cli.nexa_cli",
                "diff",
                str(left_path),
                str(right_path),
                "--regression",
            ],
            capture_output=True,
            text=True,
        )
        
        assert result.returncode == 0
        assert "nodes: 2" in result.stdout
        assert "artifacts: 1" in result.stdout
        assert "context: 1" in result.stdout
        assert "Node Regressions" in result.stdout
        assert "Artifact Regressions" in result.stdout
        assert "Context Regressions" in result.stdout


def test_legacy_diff_still_works():
    """Test that legacy diff mode (without --regression) still works."""
    left_run = {
        "run_id": "left",
        "nodes": {
            "n1": {"status": "success"},
        },
    }
    
    right_run = {
        "run_id": "right",
        "nodes": {
            "n1": {"status": "failure"},
        },
    }
    
    with tempfile.TemporaryDirectory() as tmpdir:
        left_path = Path(tmpdir) / "left.json"
        right_path = Path(tmpdir) / "right.json"
        
        _write_json_file(left_path, left_run)
        _write_json_file(right_path, right_run)
        
        result = subprocess.run(
            [
                "python", "-m", "src.cli.nexa_cli",
                "diff",
                str(left_path),
                str(right_path),
            ],
            capture_output=True,
            text=True,
        )
        
        assert result.returncode == 0
        # Should use normal diff formatter
        assert "Execution Diff" in result.stdout
        # Should NOT use regression formatter
        assert "Execution Regression" not in result.stdout


def test_legacy_diff_json_still_works():
    """Test that legacy diff --json mode still works."""
    left_run = {
        "run_id": "left",
        "nodes": {
            "n1": {"status": "success"},
        },
    }
    
    right_run = {
        "run_id": "right",
        "nodes": {
            "n1": {"status": "failure"},
        },
    }
    
    with tempfile.TemporaryDirectory() as tmpdir:
        left_path = Path(tmpdir) / "left.json"
        right_path = Path(tmpdir) / "right.json"
        
        _write_json_file(left_path, left_run)
        _write_json_file(right_path, right_run)
        
        result = subprocess.run(
            [
                "python", "-m", "src.cli.nexa_cli",
                "diff",
                str(left_path),
                str(right_path),
                "--json",
            ],
            capture_output=True,
            text=True,
        )
        
        assert result.returncode == 0
        
        output = json.loads(result.stdout)
        # Should be normal diff output
        assert "status" in output
        assert "summary" in output
        assert "nodes" in output
        # Should have diff-specific summary fields (not regression fields)
        assert "nodes_added" in output["summary"]
        assert "nodes_changed" in output["summary"]
        # Should NOT have regression-specific summary fields
        assert "node_regressions" not in output.get("summary", {})


def test_subprocess_execution_path():
    """Test subprocess execution of --regression mode."""
    left_run = {
        "run_id": "left",
        "nodes": {
            "n1": {"status": "success"},
        },
    }
    
    right_run = {
        "run_id": "right",
        "nodes": {
            "n1": {"status": "skipped"},
        },
    }
    
    with tempfile.TemporaryDirectory() as tmpdir:
        left_path = Path(tmpdir) / "left.json"
        right_path = Path(tmpdir) / "right.json"
        
        _write_json_file(left_path, left_run)
        _write_json_file(right_path, right_run)
        
        result = subprocess.run(
            [
                "python", "-m", "src.cli.nexa_cli",
                "diff",
                str(left_path),
                str(right_path),
                "--regression",
            ],
            capture_output=True,
            text=True,
            cwd=".",
        )
        
        assert result.returncode == 0
        assert "success -> skipped" in result.stdout
