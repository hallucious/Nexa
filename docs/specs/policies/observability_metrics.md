Spec ID: observability_metrics
Version: 1.0.0
Status: Partial
Category: policies
Depends On:

# observability_metrics
Version: 1.0.0
Status: Partial (opt-in observability implemented; contract surface still evolving)

## 1. 목적
이 문서는 Hyper-AI에서 “관측성(Observability)”을 **옵션으로 켜고 끌 수 있는 형태**로 제공하기 위한 최소 계약을 정의한다.
핵심 목표는 다음이다:
1) 기본 동작(API/출력)을 깨지 않으면서 이벤트를 기록한다.
2) 테스트로 이벤트 스키마/발생 조건을 방어한다.
3) 추후 파일/로그/외부 수집기로 확장 가능하도록 이벤트 구조를 안정화한다.

## 2. 현재 구현 범위(코드 기준)
- 모듈: `src/utils/observability.py`
- 엔진/런타임에서 opt-in:
  - node 실행 단계(Pre/Core/Post) 이벤트
  - prompt 관련 이벤트(가능한 범위에서)
- “기본값 off”를 원칙으로 하며, 켜졌을 때만 이벤트를 emit 한다.

## 3. 이벤트(최소 스키마)
모든 이벤트는 아래 공통 필드를 가진다:
- `ts`: ISO8601 timestamp(UTC)
- `event`: 이벤트 타입 문자열
- `gate_id`: Gate 식별자(없으면 None)
- `circuit_id`: 회로 식별자(없으면 None)
- `node_id`: 노드 식별자(없으면 None)
- `stage`: pre/core/post(해당 없으면 None)
- `prompt_id`: prompt 식별자(해당 없으면 None)

## 4. 이벤트 타입(현재)
- `node.stage.enter`
- `node.stage.exit`
- `prompt.used` (가능한 컨텍스트에서)

## 5. 비목표(지금은 하지 않음)
- 런타임 상태 스냅샷 저장(세이브파일)
- 외부 로그 수집기/분산 트레이싱 연동
- 퍼포먼스/비용 자동 최적화

## 6. 테스트 기준(권장)
- opt-in on/off에 따른 이벤트 발생 여부가 결정적이어야 한다.
- 이벤트 필드 누락/타입 변경 시 테스트가 깨져야 한다.
