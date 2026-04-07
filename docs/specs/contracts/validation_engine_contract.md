Spec ID: validation_engine_contract
Version: 1.2.0
Status: Partial
Category: contracts
Depends On:

# Validation Engine Contract
Version: 1.2.0
Status: Official Contract

Purpose:
Defines the output and enforcement responsibilities of the Structural Validation Engine.
Validation is mandatory before Execution, and execution is forbidden on failure.

## Output Contract
Validation results must include the following:
- success (bool)
- engine_revision (str)
- structural_fingerprint (str)
- violations[] (rule_id, severity, location, message)

Condition for success=true:
- true only when the number of severity=error violations is zero

## Execution Dependency
- if validation.success == false, execute() must be rejected
- validation results must be recorded in Trace by reference


---

# Archived Initial Version (Preserved)

# Validation Engine Contract
Archived-Version: v1.0.0
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

================================================================================
11) Execution Behavior Clarification (Added in v1.1.0)
================================================================================

Background:
- In v1, Engine.execute() must always record Validation results in Trace.
- "Execution forbidden" means "node execution forbidden."
  (It does not mean that Trace creation/return is itself forbidden.)

Rules:
1) If validation.success == false:
   - The Engine must not execute any node.
   - All Trace.nodes[*].node_status values must be NOT_REACHED.
   - Trace.validation_success = false
   - Trace.validation_violations must record violations[] *as-is* (schema below).
2) Validation timestamp recording:
   - It must be recorded as an ISO-8601 string in Trace.meta.validation.at.

Trace.validation_violations schema (enforced from v1.1.0):
- violations: [
    {
      "rule_id": str,
      "rule_name": str,
      "severity": "error" | "warning",
      "location_type": "engine" | "node" | "channel" | "flow",
      "location_id": str | null,
      "message": str
    }
  ]

Compatibility:
- Tuple-form (rule_id, message) records are no longer allowed.


## Validation Snapshot Obligation

If validation is executed,
engine MUST populate:

trace.meta.validation.snapshot

Engine MUST:
- Deduplicate rule ids
- Sort rule ids lexicographically
- Produce stable JSON structure

## Precision Addendum (v1.1.0)
The validation engine is the canonical home for the evaluation / verifier layer.
Verifier semantics MUST therefore include the following precision rules:

1. execution success and quality success are separate states
2. verification remains structured, machine-actionable, and traceable
3. structural / logical / requirement / policy / evidence verification modes may coexist
4. composite verification MUST preserve blocking reason codes and aggregate confidence
5. verifier outcomes MAY drive retry / reroute / branch / escalate decisions, but MUST NOT silently rewrite node truth
6. missing evidence or strong disagreement MUST lower aggregate confidence rather than being hidden behind PASS-only semantics

