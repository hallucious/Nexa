# Node Execution Pipeline Specification (Pre/Core/Post)
Version: 1.0.0
Status: Official Contract

Purpose:
모든 Node가 따라야 하는 Pre/Core/Post 파이프라인을 정의한다.

## Rules
- Pre: 입력/정책/환경 검증
- Core: 주 기능 실행(부작용 금지)
- Post: 출력 검증 + 메타데이터/Trace 기록(실패 시에도 실행)

## Validation Mapping
Enforced by: PIPE-001..005


---

# Archived Initial Version (Preserved)

# Node Execution Pipeline Specification
Version: v1.0.0
Status: Official Contract

Purpose:
This document defines the mandatory execution stages
for every Node.

All Node executions must follow Pre → Core → Post sequence.

----------------------------------------------------------------------

1. Mandatory Three-Stage Model

Every Node execution must include:

1) Pre Stage
2) Core Stage
3) Post Stage

Skipping any stage is forbidden.

----------------------------------------------------------------------

2. Pre Stage

Purpose:
Validate and prepare execution.

Responsibilities:

- Input schema validation
- Required field presence check
- Type verification
- Policy compliance check
- Environment validation (if applicable)
- Determinism configuration validation

If Pre fails:

- Core must NOT execute.
- Post must record failure.
- Node status becomes failure.

Pre must not mutate input.

----------------------------------------------------------------------

3. Core Stage

Purpose:
Perform main functional computation.

Responsibilities:

- Execute Node logic
- Produce output
- Respect side-effect policy
- Follow determinism recording rule

Core must:

- Not modify Engine structure
- Not modify Flow rules
- Not perform hidden execution
- Not swallow exceptions

If Core throws an error:

- Failure must be structured.
- reason_code must be recorded.
- Post must execute for recording.

----------------------------------------------------------------------

4. Post Stage

Purpose:
Finalize and record execution result.

Responsibilities:

- Output schema validation
- Metadata collection
- Duration calculation
- Status determination
- Trace update
- Determinism parameter recording

Post must always execute,
even if Pre or Core failed.

----------------------------------------------------------------------

5. Status Resolution Rules

Allowed Node status outcomes:

- success
- failure

Skipped status is assigned at Engine level,
not inside Node.

Status must be determined in Post stage.

----------------------------------------------------------------------

6. Error Handling Model

Node execution must never:

- Return unstructured error
- Raise unhandled exception
- Fail silently

All failures must produce:

- success flag (false)
- reason_code
- optional diagnostic metadata

----------------------------------------------------------------------

7. Determinism Recording

If stochastic behavior exists in Core:

- Random seed must be captured
- AI parameters must be recorded
- Model version must be recorded

Recording must occur in Post stage.

----------------------------------------------------------------------

8. Time Measurement

Node execution must record:

- start_time (Pre start)
- end_time (Post end)
- duration (end_time - start_time)

Missing timing invalidates Trace.

----------------------------------------------------------------------

9. Prohibited Behavior

Within any stage, Node must NOT:

- Modify Engine structure
- Modify Channels
- Modify Flow
- Access external mutable state (v1)
- Dynamically insert new Nodes

----------------------------------------------------------------------

10. Contract Rule

Any Node execution not following
Pre → Core → Post strictly
is considered structurally invalid.

End of Node Execution Pipeline Specification v1.0.0

----------------------------------------------------------------------
Validation Mapping
----------------------------------------------------------------------
Enforced by rule_ids:
- PIPE-001
- PIPE-002
- PIPE-003
- PIPE-004
- PIPE-005