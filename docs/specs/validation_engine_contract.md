# Validation Engine Contract
Version: 1.0.0
Status: Official Contract

Purpose:
Structural Validation Engine의 출력 및 강제 책임을 정의한다.
Validation은 Execution 전에 필수이며, 실패 시 실행은 금지된다.

## Output Contract
Validation 결과는 아래를 포함해야 한다:
- success (bool)
- engine_revision (str)
- structural_fingerprint (str)
- violations[] (rule_id, severity, location, message)

success=true 조건:
- severity=error 위반이 0개일 때만 true

## Execution Dependency
- validation.success == false 이면 execute()는 거부해야 한다
- validation 결과는 Trace에 참조로 기록되어야 한다


---

# Archived Initial Version (Preserved)

# Validation Engine Contract
Version: v1.0.0
Status: Official Contract

Purpose:
Defines the output contract and enforcement responsibilities of the Structural Validation Engine.
Validation must occur before any Execution. Execution without successful validation is forbidden.

======================================================================
1. Validation Scope
======================================================================

Validation Engine must verify:
- Engine Structural Constraints
- Entry Policy
- Node Abstraction compliance
- Channel type compatibility
- DAG constraint
- Side-effect policy (static level)
- Determinism configuration presence
- Trace schema/requirements declared for v1

======================================================================
2. Validation Result Object
======================================================================

Validation must return a structured object:

{
  "success": bool,
  "engine_revision": str,
  "structural_fingerprint": str,
  "violations": [
      {
          "rule_id": str,
          "rule_name": str,
          "severity": "error" | "warning",
          "location_type": "engine" | "node" | "channel" | "flow",
          "location_id": str | null,
          "message": str
      }
  ]
}

Primitive boolean return values are forbidden.

======================================================================
3. Success Rule
======================================================================

success = true ONLY IF:
- violations contains no item with severity = "error"

Warnings do not block execution.
Errors must block execution.

======================================================================
4. Rule Identification
======================================================================

Every violation must include:
- rule_id (stable identifier)
- rule_name (human readable name)

Rule IDs must be stable across versions unless rule semantics change.

======================================================================
5. Severity Levels
======================================================================

error:
- Execution must be blocked.

warning:
- Execution allowed.
- Must be logged.
- May generate Proposal.

Silent violations are forbidden.

======================================================================
6. Location Semantics
======================================================================

location_type must specify scope:
- engine → entire Engine structure
- node → specific Node
- channel → specific Channel
- flow → specific Flow rule

location_id must reference exact identifier or be null if global.

======================================================================
7. Determinism Requirement
======================================================================

Validation must ensure determinism metadata configuration exists and required recording fields are declared.
Missing configuration = error.

======================================================================
8. Immutability Rule
======================================================================

Validation result must be immutable after generation.
Any post-generation mutation invalidates validation.

======================================================================
9. Execution Dependency Rule
======================================================================

Execution must:
- Reject if validation.success == false
- Store validation result reference in Trace
- Record validation timestamp

======================================================================
10. Contract Supremacy
======================================================================

Validation Engine enforces BLUEPRINT contract.
If validation detects a violation:
- Engine must not execute.
- Revision must not be published.
- Proposal may be generated.

End of Validation Engine Contract v1.0.0