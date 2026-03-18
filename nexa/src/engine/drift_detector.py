from typing import Dict, List, Any

def detect_drift(*, a: Dict[str, Any], b: Dict[str, Any]) -> Dict[str, Any]:
    reasons: List[str] = []

    if a.get("structural_fingerprint") != b.get("structural_fingerprint"):
        reasons.append("STRUCTURAL_DRIFT")

    if a.get("validation_snapshot_hash") != b.get("validation_snapshot_hash"):
        reasons.append("VALIDATION_DRIFT")

    if a.get("execution_fingerprint") != b.get("execution_fingerprint"):
        reasons.append("ENVIRONMENT_DRIFT")

    return {
        "drifted": len(reasons) > 0,
        "reasons": reasons,
        "diff_summary": {
            "structural_changed": "STRUCTURAL_DRIFT" in reasons,
            "validation_changed": "VALIDATION_DRIFT" in reasons,
            "environment_changed": "ENVIRONMENT_DRIFT" in reasons,
        },
    }
