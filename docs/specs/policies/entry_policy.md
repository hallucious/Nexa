Spec ID: entry_policy
Version: 1.0.0
Status: Partial
Category: policies
Depends On:

# Engine Entry Policy
Version: 1.0.0
Status: Official Contract

Purpose:
Engine의 입력 및 Entry 규칙을 정의한다.

## Policy (v1)
- Entry Node는 정확히 1개
- external input은 Entry input schema를 만족해야 한다
- default input은 명시 선언 + Trace에 기록

## Validation Mapping
Enforced by: ENT-001..005, ENG-001..002


---

# Archived Initial Version (Preserved)

# Engine Entry Policy Specification
Version: v1.0.0
Status: Official Contract

Purpose:
This document defines how an Engine receives its initial input
and how execution begins.

----------------------------------------------------------------------

1. Single Entry Principle

Every Engine must have exactly one Entry Node.

Rules:

- Only one Node may be designated as Entry.
- Execution must begin from this Node.
- Multiple entry Nodes are forbidden.
- Implicit entry resolution is forbidden.

----------------------------------------------------------------------

2. Entry Node Requirements

The Entry Node must:

- Define an explicit input schema.
- Define an explicit output schema.
- Follow full Pre/Core/Post execution stages.
- Obey side-effect policy.
- Obey determinism policy.

Entry Node is a regular Node with entry designation.

----------------------------------------------------------------------

3. External Input Handling

An Engine Execution may optionally receive external input.

Rules:

- External input must match Entry Node input schema.
- Input schema validation occurs in Entry Node Pre stage.
- Missing required fields cause immediate failure.
- Implicit input coercion is forbidden in v1.

----------------------------------------------------------------------

4. Default Input Support

An Entry Node may define default input values.

Rules:

- Defaults must be explicitly declared in schema.
- Defaults must be deterministic.
- Runtime implicit default injection is forbidden.
- Default values must be recorded in Trace input snapshot.

----------------------------------------------------------------------

5. Input Snapshot Recording

At Execution start:

- Full external input must be recorded.
- Resolved default values must be recorded.
- Final input snapshot must be immutable.
- Snapshot must be linked to execution_id.

Input mutation after snapshot is forbidden.

----------------------------------------------------------------------

6. Entry Validation Phase

Before execution begins:

- Structural validation must pass.
- Entry Node existence must be verified.
- Entry Node schema must be validated.
- External input must be validated.

Execution must not start without validation.

----------------------------------------------------------------------

7. Entry Failure Semantics

If Entry Node Pre stage fails:

- Execution status must be failure.
- No other Node may execute.
- Trace must record failure reason_code.

Entry failure terminates execution immediately.

----------------------------------------------------------------------

8. Flow Initialization

After Entry Node succeeds:

- Flow evaluation begins.
- Downstream Nodes may execute according to Flow rules.
- Data propagation must follow Channels.

Entry Node output becomes initial data source.

----------------------------------------------------------------------

9. Prohibited Behavior

- Implicit auto-generated Entry Node.
- Multiple Entry Nodes.
- Dynamic Entry switching.
- Execution without external input validation.
- Hidden input mutation.

----------------------------------------------------------------------

10. Contract Rule

Any Engine violating Entry Policy
is structurally invalid and must not execute.

End of Engine Entry Policy Specification v1.0.0

----------------------------------------------------------------------
Validation Mapping
----------------------------------------------------------------------
Enforced by rule_ids:
- ENT-001
- ENT-002
- ENT-003
- ENT-004
- ENT-005
- ENG-001
- ENG-002