from src.engine.drift_detector import detect_drift

def base():
    return {
        "structural_fingerprint": "A",
        "validation_snapshot_hash": "B",
        "execution_fingerprint": "C",
    }

def test_no_drift():
    a = base()
    b = base()
    result = detect_drift(a=a, b=b)
    assert result["drifted"] is False
    assert result["reasons"] == []

def test_structural_drift():
    a = base()
    b = base()
    b["structural_fingerprint"] = "X"
    result = detect_drift(a=a, b=b)
    assert "STRUCTURAL_DRIFT" in result["reasons"]

def test_validation_drift():
    a = base()
    b = base()
    b["validation_snapshot_hash"] = "Y"
    result = detect_drift(a=a, b=b)
    assert "VALIDATION_DRIFT" in result["reasons"]

def test_environment_drift():
    a = base()
    b = base()
    b["execution_fingerprint"] = "Z"
    result = detect_drift(a=a, b=b)
    assert "ENVIRONMENT_DRIFT" in result["reasons"]
