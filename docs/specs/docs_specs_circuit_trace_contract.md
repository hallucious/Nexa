# circuit_trace_contract.md
- Spec ID: CT-TRACE
- Version: 1.0.0
- Status: Active
- Location: docs/specs/circuit_trace_contract.md

## 1. 목적
Circuit 실행 과정에서 “무슨 노드가, 어떤 조건으로, 어떤 순서로, 왜 선택되었는지”를 **재현 가능**하게 기록하기 위한 Trace(추적) 구조 및 동작 계약을 정의한다.

본 스펙의 최우선 제약은 다음과 같다.
- `execute_circuit()`의 **반환 계약을 깨지 않는다.**
- Trace는 **엔진의 의미론(실행 결과)에 영향을 주지 않는다**(읽기 전용 기록).

## 2. 범위
### 2.1 포함
- Trace 데이터 모델(구조)
- Trace 기록 시점(이벤트 경계)
- 기본 활성화 정책(기본 OFF)
- 확장 지점(향후 JSON export, observability 연동 등)

### 2.2 비포함(명시적 제외)
- 시각화(UI), CLI 옵션
- 파일 저장/로드(Trace persistence)
- 성능 최적화(단, 최소 성능 원칙은 적용)
- 조건 평가기(Condition Evaluator) 내부 세부 단계 로깅(결과만 기록)

## 3. 용어 정의
- **Circuit**: 노드와 엣지(조건부 포함)로 구성된 실행 그래프
- **Node**: 실행 단위
- **Edge**: 다음 노드 선택을 위한 연결(조건부 가능)
- **Trace**: 실행 과정 기록(읽기 전용)
- **Run**: `execute_circuit()` 1회 호출 단위

## 4. 핵심 불변식(Contract Invariants)
1. Trace는 실행 결과를 변경하지 않는다.
2. Trace는 기본적으로 비활성화(OFF)이며, 활성화 여부는 **명시적 설정**으로만 결정된다.
3. Trace 활성화 시에도 `execute_circuit()`의 반환 타입/구조는 변경하지 않는다.
4. Trace는 “선택된 엣지/조건 결과/노드 상태”를 최소 단위로 기록한다.
5. Trace는 테스트/디버깅에서 실행 순서를 재현하는 데 충분해야 한다(완전성 기준은 7장 참조).

## 5. 데이터 모델
### 5.1 CircuitTrace
`CircuitTrace`는 Run 전체를 대표하는 최상위 기록 구조체다.

**필수 필드**
- `circuit_id: str`
- `run_id: str` (유니크)
- `started_at: str` (ISO-8601 권장)
- `finished_at: str | None`
- `final_status: str` (예: success/fail)
- `nodes: list[NodeTrace]`

**선택 필드**
- `meta: dict[str, Any]` (환경/버전/옵션 등)

### 5.2 NodeTrace
`NodeTrace`는 노드 1회 실행(또는 스킵)을 기록한다.

**필수 필드**
- `node_id: str`
- `entered_at: str`
- `exited_at: str | None`
- `status: str` (success/fail/skipped)
- `selected_edge: SelectedEdge | None` (스킵 포함)
- `condition_result: ConditionResult | None` (조건부 엣지 선택 시)
- `input_snapshot: SnapshotRef | None`
- `output_snapshot: SnapshotRef | None`

### 5.3 SelectedEdge
- `from_node_id: str`
- `to_node_id: str`
- `edge_id: str | None` (있으면 기록, 없으면 None)
- `priority: int | None` (조건부 우선순위 존재 시)

### 5.4 ConditionResult
조건 평가 결과를 최소 단위로 기록한다.

- `expression: str | None` (가능하면 기록, 불가능하면 None)
- `value: bool | None` (평가 결과)
- `error: str | None` (평가 실패 시)

### 5.5 SnapshotRef
스냅샷은 “실데이터 복사”가 아니라 **참조/요약**를 기본으로 한다(메모리/성능 리스크 완화).

- `kind: str` (예: shallow, summary, none)
- `data: dict[str, Any] | None` (summary일 때)
- `note: str | None`

## 6. 기록 시점(이벤트 경계)
Trace는 다음 경계에서만 기록한다.

1. **노드 진입 직전**: `NodeTrace.entered_at` 기록, `input_snapshot` 생성(옵션)
2. **노드 실행 종료 직후**: `NodeTrace.exited_at`, `status`, `output_snapshot` 기록
3. **엣지 선택 직후**: `selected_edge` 기록, 조건부면 `condition_result` 기록
4. **Circuit 종료 시점**: `CircuitTrace.finished_at`, `final_status` 기록

조건 평가기의 내부 단계(토큰화/파싱/중간식 등)는 기록 대상이 아니다.

## 7. 완전성 기준(Design Done)
Trace ON 상태에서 아래가 가능해야 한다.
- 노드 실행 순서 재구성
- 각 단계에서 “왜 다음 노드가 선택되었는지” 추적(조건 결과 + 우선순위)
- 실패가 발생한 노드/시점 식별
- 스킵/분기 경로 구분

## 8. 활성화 정책
- 기본: Trace OFF
- 활성화는 다음 중 하나로만 허용(구현에서 선택)
  - (권장) `ExecutionContext` 내부 플래그 및 `trace_sink` 존재 여부로 결정
  - (대안) `execute_circuit(..., trace_collector=...)` 같은 optional 인자

본 스펙 v1.0.0의 기본 권장안은 “**함수 시그니처 불변(대안 A)**”이다.

## 9. 오류 처리
- Trace 기록 실패는 원칙적으로 **Circuit 실행 실패로 전파하지 않는다**(best-effort).
- 단, 개발/디버그 모드에서만 “Trace 기록 실패를 실패로 승격”하는 옵션을 둘 수 있다(스펙 외 확장).

## 10. 보안/개인정보/민감정보
- 스냅샷(summary)은 민감정보를 포함하지 않도록 최소화한다.
- 원본 입력/출력을 그대로 덤프하지 않는다(필요 시 별도 opt-in 확장으로 처리).

## 11. 스펙-코드 동기화 규칙(프로젝트 불변식 준수)
이 스펙을 “정식 적용(IMPLEMENT)” 단계에서 수행해야 할 동기화 작업:
- `src/contracts/spec_versions.py`에 CT-TRACE 1.0.0 등록
- BLUEPRINT의 활성 spec 목록/FOUNDATION_MAP 갱신(해당 시스템 규칙에 따름)
- 계약 테스트(스펙 버전 동기화) 통과 확인

(본 문서는 DESIGN 산출물이며, 위 동기화는 구현 단계에서 수행한다.)
