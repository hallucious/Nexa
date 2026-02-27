# Trace Model Specification
Version: 1.1.0
Status: Official Contract

Purpose:
Execution의 증거(Trace) 형식을 정의한다.
Trace는 Hyper-AI의 **유일한 실행 증거**이며, 디버깅/재현/감사/통계를 위한 정본이다.

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
