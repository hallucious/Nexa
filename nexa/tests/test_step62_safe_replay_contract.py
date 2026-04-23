from src.engine.safe_replay import safe_replay

def base():
    return {
        "structural_fingerprint": "A",
        "validation_snapshot_hash": "B",
        "execution_fingerprint": "C",
    }

def test_safe_replay_pass():
    a = base()
    b = base()
    result = safe_replay(original=a, current=b)
    assert result["status"] == "PASS"

def test_safe_replay_structural_fail():
    a = base()
    b = base()
    b["structural_fingerprint"] = "X"
    result = safe_replay(original=a, current=b)
    assert result["status"] == "FAIL"

def test_safe_replay_validation_fail():
    a = base()
    b = base()
    b["validation_snapshot_hash"] = "X"
    result = safe_replay(original=a, current=b)
    assert result["status"] == "FAIL"

def test_safe_replay_environment_warn():
    a = base()
    b = base()
    b["execution_fingerprint"] = "X"
    result = safe_replay(original=a, current=b)
    assert result["status"] == "WARN"
