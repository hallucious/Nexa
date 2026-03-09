# Engine Structural Constraints
Version: 1.0.0
Status: Official Contract

Purpose:
Engine이 실행되기 위한 구조 제약을 정의한다.

## Constraints (v1)
- Single Entry 필수(0개/2개 이상 금지)
- DAG 필수(사이클 금지)
- Channel 타입 호환 필수(암묵 변환 금지)
- Flow/Channel 분리(Flow는 제어, Channel은 데이터)
- 실행 중 구조 변경 금지
- Revision 불변성(구조 변경은 새 Revision)

## Validation Mapping
Enforced by: ENG-001..008, CH-001..004, FLOW-001..003


---

# Archived Initial Version (Preserved)

# Engine Structural Constraints
Version: v1.0.0
Status: Official Contract

Purpose:
This document defines mandatory structural rules
that every Engine must satisfy before execution.

Violation of any constraint renders the Engine invalid.

----------------------------------------------------------------------

1. Single Entry Rule

An Engine must have exactly one entry point.

Rules:

- Only one Node may be marked as Entry.
- Execution must begin from this Node.
- Multiple entry points are forbidden.
- Zero entry point is forbidden.

----------------------------------------------------------------------

2. Directed Graph Rule

The Engine structure must form a directed graph.

Rules:

- Nodes are vertices.
- Channels define directed edges.
- Channels must connect output → input.
- Reverse connection is forbidden.

----------------------------------------------------------------------

3. Channel Type Compatibility

For every Channel:

- Output schema of source Node must match
  input schema of destination Node.
- Partial compatibility is forbidden unless explicitly defined.
- Implicit type coercion is forbidden in v1.

----------------------------------------------------------------------

4. Flow / Channel Separation

Data flow and control flow must be separated.

Rules:

- Channels carry data only.
- Flow defines execution order only.
- Channels must not encode conditional logic.
- Flow must not mutate data.

----------------------------------------------------------------------

5. No Dynamic Structural Mutation

During execution:

- Nodes cannot be added.
- Nodes cannot be removed.
- Channels cannot be modified.
- Flow rules cannot be modified.

Structure is immutable during execution.

----------------------------------------------------------------------

6. No Hidden Execution

All executable logic must be inside Nodes.

Forbidden:

- Inline logic at Engine level.
- Hidden implicit execution steps.
- Implicit fallback execution.

Execution must be fully traceable.

----------------------------------------------------------------------

7. Revision Integrity

Any structural modification must:

- Generate a new Revision.
- Preserve immutability of previous Revision.
- Maintain revision linkage.

In-place structural mutation is forbidden.

----------------------------------------------------------------------

8. Cycle Rule (v1 Constraint)

Cycles are forbidden in v1.

The Engine must form a Directed Acyclic Graph (DAG).

Loop constructs may be introduced in future versions
under a dedicated Loop Specification.

----------------------------------------------------------------------

9. Deterministic Structural Identity

The structural fingerprint must:

- Be derived solely from Nodes, Channels, and Flow.
- Exclude execution data.
- Be stable across identical structures.

Fingerprint inconsistency invalidates revision comparison.

----------------------------------------------------------------------

10. Validation Before Execution

Before any Execution:

- All structural constraints must pass.
- Schema compatibility must be verified.
- Entry rule must be verified.
- Cycle rule must be verified.

Execution without validation is forbidden.

----------------------------------------------------------------------

Contract Rule:

An Engine that violates any structural constraint
must not execute.

End of Engine Structural Constraints v1.0.0

----------------------------------------------------------------------
Validation Mapping
----------------------------------------------------------------------
Enforced by rule_ids:
- ENG-001
- ENG-002
- ENG-003
- ENG-004
- ENG-005
- ENG-006
- ENG-007
- ENG-008
- CH-001
- CH-002
- CH-003
- CH-004
- FLOW-001
- FLOW-002
- FLOW-003