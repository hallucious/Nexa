# Execution Model Specification
Version: 1.3.0
Status: Official Contract

---------------------------------------------------------------------
1) Minimal Execution Semantics (v1.1.0 유지)
---------------------------------------------------------------------
- Validation 성공 시 entry_node SUCCESS 마킹
- 나머지 노드 NOT_REACHED 유지

---------------------------------------------------------------------
2) DAG 상태 전파 규칙 (v1.2.0)
---------------------------------------------------------------------

다중 부모 노드(B)가 A1, A2, ... 을 부모로 가질 때:

1. ALL_SUCCESS:
   모든 부모 SUCCESS → B 실행

2. ANY_SUCCESS (v1.3.0):
   부모 중 하나라도 SUCCESS → B 실행
   (단, FAILURE가 하나라도 있으면 FAILURE 전파 규칙이 우선)

3. FIRST_SUCCESS (v1.3.0):
   부모 중 '최초로' SUCCESS가 관측되는 순간 B 실행
   v1 최소 구현에서는 deterministic 처리 위해 ANY_SUCCESS와 동일하게 동작한다.
   (비동기/병렬/대기 모델 도입 시 FIRST_SUCCESS는 별도 의미를 갖는다)

4. FAILURE 전파:
   부모 중 하나라도 FAILURE → B는 SKIPPED

5. NOT_REACHED:
   부모가 모두 NOT_REACHED(또는 실행 조건 미충족) → B는 NOT_REACHED

2. FAILURE 전파:
   부모 중 하나라도 FAILURE → B는 SKIPPED

3. NOT_REACHED:
   부모 중 하나라도 NOT_REACHED → B는 NOT_REACHED

이 규칙은 deterministic execution을 보장한다.
비동기/병렬/대기 모델은 v2 이후 단계에서 고려한다.


---

# Archived Initial Version (Preserved)

# Execution Model Specification
Version: v1.0.0
Status: Official Contract

Purpose:
This document defines how an Engine is executed at runtime.

All runtime behavior must comply with this model.

----------------------------------------------------------------------

1. Execution Type (v1 Constraint)

Execution Model: Sync-first

Rules:

- All Nodes execute synchronously.
- No parallel execution allowed in v1.
- No asynchronous execution allowed in v1.
- Execution order must be deterministic.

----------------------------------------------------------------------

2. Execution Initialization

When an Execution begins:

- A unique execution_id must be generated.
- Input snapshot must be recorded.
- Engine revision reference must be recorded.
- Execution metadata container must be initialized.

----------------------------------------------------------------------

3. Execution Order Determination

Execution order must be derived from:

- Flow rules
- Topological ordering (DAG constraint)

Rules:

- Entry Node executes first.
- Nodes execute only when all required inputs are available.
- No speculative execution allowed.
- No implicit parallel scheduling.

----------------------------------------------------------------------

4. Node Execution Lifecycle

For each Node:

1. Pre stage executes
2. Core stage executes
3. Post stage executes

If Pre fails:
- Core must not execute.
- Post must still record failure metadata.

If Core fails:
- Post must record failure metadata.
- Downstream Nodes must not execute.

----------------------------------------------------------------------

5. Failure Propagation

If a Node fails:

- All downstream dependent Nodes must be marked as skipped.
- Execution status must be marked as failed.
- Failure reason_code must be recorded.

Silent failure is forbidden.

----------------------------------------------------------------------

6. Skip Semantics

A Node is marked as skipped when:

- Upstream dependency failed.
- Flow condition evaluates to false.
- Structural validation prevents execution.

Skipped status must be explicitly recorded in Trace.

----------------------------------------------------------------------

7. Execution Completion

Execution completes when:

- All reachable Nodes have either:
  - Executed successfully
  - Failed
  - Been skipped

Completion must produce:

- Final status (success/failure)
- Final output (if defined)
- Full Trace snapshot

----------------------------------------------------------------------

8. Determinism Recording

For every Execution:

- Random seeds must be recorded (if applicable).
- AI model parameters must be recorded.
- Temperature or stochastic settings must be recorded.
- Runtime environment version must be recorded.

Execution must be reproducible given identical conditions.

----------------------------------------------------------------------

9. No Runtime Structural Mutation

During Execution:

- Structure must remain immutable.
- No dynamic Node insertion.
- No dynamic Flow alteration.
- No Channel rewiring.

Violation invalidates Execution.

----------------------------------------------------------------------

10. Execution Result Object

Execution must return a structured object containing:

- execution_id
- revision_id
- status
- final_output
- execution_time
- cost_metrics (if available)
- trace_reference

Raw primitive return values are forbidden.

----------------------------------------------------------------------

11. Validation Before Execution

Before starting execution:

- Structural validation must pass.
- Schema validation must pass.
- Entry validation must pass.
- Determinism configuration must be verified.

Execution without prior validation is forbidden.

----------------------------------------------------------------------

Contract Rule:

Any runtime behavior that deviates from this specification
is considered invalid and must be rejected.

End of Execution Model Specification v1.0.0

----------------------------------------------------------------------
Validation Mapping
----------------------------------------------------------------------
Enforced by rule_ids:
- NODE-004
- PIPE-001
- PIPE-002
- PIPE-003
- PIPE-004
- DET-001
- DET-002
- DET-003
- DET-004
- DET-005
