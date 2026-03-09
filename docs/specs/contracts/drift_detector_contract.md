# Drift Detector Contract
Version: 1.0.0

Purpose:
Detect drift between two execution traces.

Inputs:
- structural_fingerprint
- validation_snapshot_hash
- execution_fingerprint

Output:
{
  "drifted": bool,
  "reasons": [reason_code],
  "diff_summary": dict
}

Reason Codes:
- STRUCTURAL_DRIFT
- VALIDATION_DRIFT
- ENVIRONMENT_DRIFT
