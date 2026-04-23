from typing import Dict, Any
from src.engine.drift_detector import detect_drift

def safe_replay(*, original: Dict[str, Any], current: Dict[str, Any]) -> Dict[str, Any]:
    drift = detect_drift(a=original, b=current)

    status = "PASS"

    if "STRUCTURAL_DRIFT" in drift["reasons"]:
        status = "FAIL"
    elif "VALIDATION_DRIFT" in drift["reasons"]:
        status = "FAIL"
    elif "ENVIRONMENT_DRIFT" in drift["reasons"]:
        status = "WARN"

    return {
        "replayed": True,
        "status": status,
        "drifted": drift["drifted"],
        "reasons": drift["reasons"],
    }
