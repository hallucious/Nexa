# Safe Replay Contract
Version: 1.0.0

Policy:
STRUCTURAL_DRIFT -> FAIL
VALIDATION_DRIFT -> FAIL
ENVIRONMENT_DRIFT -> WARN (default)

Output:
{
  "replayed": true,
  "status": "PASS" | "WARN" | "FAIL",
  "drifted": bool,
  "reasons": [reason_code]
}
