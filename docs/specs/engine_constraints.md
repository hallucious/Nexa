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
