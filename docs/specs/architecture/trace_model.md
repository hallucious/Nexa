Spec ID: trace_model
Version: 1.4.0
Status: Official Contract
Category: architecture
Depends On:

# Trace Model Specification

Purpose:
Execution의 증거(Trace) 형식을 정의한다.
Trace는 Nexa의 **유일한 실행 증거**이며, 디버깅/재현/감사/통계를 위한 정본이다.

----------------------------------------------------------------------
1) Core Requirements (v1)
----------------------------------------------------------------------

Trace는 반드시 다음을 만족해야 한다.

- Graph-based: Engine 그래프의 **모든 노드**에 대해 기록이 존재해야 한다(미실행 포함).
- Immutable: Trace는 생성 후 변경 불가(불변).
- Complete: Pre/Core/Post 상태를 노드별로 기록한다.
- Identified:
  - execution_id (고유)
  - revision_id (구조 버전)
  - structural_fingerprint (구조 동일성 해시)

----------------------------------------------------------------------
2) ExecutionTrace (Top-level)
----------------------------------------------------------------------

ExecutionTrace는 최소 아래 필드를 포함한다.

- execution_id: str
- revision_id: str
- structural_fingerprint: str

- started_at: datetime
- finished_at: datetime | null
- duration_ms: int | null

- validation_success: bool | null
- validation_violations: list[(rule_id, message)] | null  (최소 참조 포맷)

- nodes: Mapping[node_id -> NodeTrace]  (모든 node_id 포함 필수)
- meta: dict (선택)

----------------------------------------------------------------------
3) NodeTrace (Per-node)
----------------------------------------------------------------------

NodeTrace는 최소 아래 필드를 포함한다.

- node_id: str

- node_status: NodeStatus
  - not_reached | success | failure | skipped

- pre_status: StageStatus
- core_status: StageStatus
- post_status: StageStatus
  - success | failure | skipped

- reason_code: str | null
- message: str | null

- input_snapshot: dict | null (선택)
- output_snapshot: dict | null (선택)
- meta: dict | null (선택)

----------------------------------------------------------------------
4) Node Coverage Rule (Hard Requirement)
----------------------------------------------------------------------

Trace는 반드시 Engine의 node_ids 전체를 포함해야 한다.

- 누락된 node_id가 1개라도 있으면 Trace는 무효이며,
  Validation/Execution은 실패로 처리되어야 한다.

----------------------------------------------------------------------
5) Failure Semantics (v1)
----------------------------------------------------------------------

- 어떤 노드가 실패하면 downstream 노드는 node_status=skipped로 기록될 수 있다.
- 단, skipped와 not_reached는 의미가 다르다:
  - not_reached: 그래프/Flow 상 도달 자체가 없었음(예: 분기 미선택)
  - skipped: 도달 가능했으나 upstream 실패/정책으로 실행이 생략됨

----------------------------------------------------------------------
6) Immutability Rule
----------------------------------------------------------------------

Trace/NodeTrace는 생성 후 변경이 불가능해야 한다.
(Python 구현에서는 dataclass(frozen=True) 수준을 기본으로 사용한다.)

----------------------------------------------------------------------
7) Validation Mapping
----------------------------------------------------------------------

Enforced by rule_ids:
- TRACE-001
- TRACE-002
- TRACE-003
- TRACE-004


---

# Archived Initial Version (Preserved)

# Trace Model Specification
Archived-Version: v1.0.0
Status: Official Contract

Purpose:
This document defines how execution results are recorded.
Trace is the canonical runtime record of an Engine execution.

Trace is immutable once finalized.

----------------------------------------------------------------------

1. Trace Definition

Trace is a complete graph-based snapshot of an Execution.

It must include:

- Engine revision reference
- execution_id
- input snapshot
- full Node state graph
- execution metadata
- final status

Trace is not a linear log.
Trace preserves structural topology.

----------------------------------------------------------------------

2. Graph Preservation Rule

Trace must preserve:

- All Nodes in the Engine (executed or not)
- All Channels
- Flow rules (reference)
- Structural fingerprint reference

Linear-only trace storage is forbidden.

----------------------------------------------------------------------

3. Node State Recording

For every Node in the Engine,
Trace must record:

- node_id
- execution status (success / failure / skipped / not_reached)
- Pre/Core/Post stage status
- start_time
- end_time
- duration
- output snapshot (if allowed by policy)
- error reason_code (if failure)

Nodes that never executed must still appear in Trace.

----------------------------------------------------------------------

4. Execution Status Model

Allowed Node statuses:

- success
- failure
- skipped
- not_reached

Allowed Execution statuses:

- success
- failure

Partial success state is forbidden in v1.

----------------------------------------------------------------------

5. Skip and Failure Semantics

If a Node fails:

- Downstream Nodes must be marked as skipped.
- Failure propagation must be traceable.

If Flow condition prevents execution:

- Node must be marked as skipped.
- Condition reference must be recorded.

----------------------------------------------------------------------

6. Metadata Recording

Trace must include:

- execution_id
- revision_id
- structural fingerprint
- execution start timestamp
- execution end timestamp
- total duration
- cost metrics (if applicable)
- environment version
- determinism parameters

Missing metadata invalidates Trace.

----------------------------------------------------------------------

7. Immutability Rule

Once Execution completes:

- Trace must become immutable.
- No modification allowed.
- No patching allowed.
- Corrections require new Execution.

----------------------------------------------------------------------

8. Trace Integrity Rule

Trace must:

- Be internally consistent.
- Match the Engine revision used.
- Match structural fingerprint.
- Preserve Node execution ordering.

Trace inconsistency invalidates execution record.

----------------------------------------------------------------------

9. Trace as Canonical Evidence

Trace is:

- The source of statistical analysis.
- The source of proposal generation.
- The source of audit and reproducibility.
- The source of debugging.

Any analysis must rely only on Trace.

----------------------------------------------------------------------

10. Storage Independence

Trace format must:

- Be serializable.
- Be exportable.
- Be storage backend independent.

Persistence mechanism is implementation detail,
but Trace schema must remain stable per version.

----------------------------------------------------------------------

Contract Rule:

Execution without full Trace generation is forbidden.

Trace is mandatory for every Execution.

End of Trace Model Specification v1.0.0

----------------------------------------------------------------------
Validation Mapping
----------------------------------------------------------------------
Enforced by rule_ids:
- TRACE-001
- TRACE-002
- TRACE-003
- TRACE-004

================================================================================
8) Serialization Contract (Added in v1.2.0)
================================================================================

1) Purpose
- ExecutionTrace must provide a deterministic serialization API suitable for:
  - artifact storage
  - diffing
  - replay/audit
  - policy comparison

2) Required APIs
- ExecutionTrace.to_dict(stable: bool = True) -> dict
- ExecutionTrace.to_json(stable: bool = True, ensure_ascii: bool = False, indent: int | None = None) -> str

3) Determinism Requirements (stable=True)
- Repeated calls MUST produce identical output for the same trace instance.
- nodes MUST be emitted in deterministic order (node_id sorted).
- datetime values MUST be emitted as ISO-8601 strings (datetime.isoformat()).
- enum values MUST be emitted as their .value string.
- meta / input_snapshot / output_snapshot MUST be JSON-safe:
  - allowed: dict (string keys only), list/tuple, str, int, float, bool, None
  - any non-JSON-safe type MUST raise TypeError (contract violation).

4) Scope
- This contract constrains *output determinism*, not internal storage.
- The specific JSON string formatting is not mandated, but stable=True MUST be deterministic.

----------------------------------------------------------------------
8) Validation Snapshot (Optional)
----------------------------------------------------------------------

Location:
trace.meta.validation.snapshot

Structure:
{
  "snapshot_version": "1",
  "applied_rules": ["<RULE_ID>", ...]
}

Rules:
- applied_rules MUST be lexicographically sorted.
- applied_rules MUST NOT contain duplicates.
- snapshot MUST NOT be included in structural_fingerprint calculation.
- snapshot is immutable once trace is finalized.


----------------------------------------------------------------------
9) Execution Fingerprint
----------------------------------------------------------------------

trace.execution_fingerprint MUST exist.

Definition:
execution_fingerprint =
SHA256(structural_fingerprint + ":" + environment_fingerprint)

Rules:
- structural_fingerprint MUST remain environment invariant.
- execution_fingerprint MUST change if environment_fingerprint changes.
