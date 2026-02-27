# Side Effect Policy (Pure-first)
Version: 1.0.0
Status: Official Contract

Purpose:
v1에서 side effect를 금지하여 재현성을 확보한다.

## Policy (v1)
- 파일/네트워크/DB 등 외부 상태 변화 금지
- 공유 mutable state 변경 금지
- Action Node는 v1 범위 밖(Reserved)

## Validation Mapping
Enforced by: SIDE-001..003
