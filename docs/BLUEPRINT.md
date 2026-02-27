# Hyper-AI BLUEPRINT
Version: 1.4.0
Status: Official Architecture Contract

---------------------------------------------------------------------
Step45: DAG 기반 상태 전파 규칙 확정 (ALL_SUCCESS 정책)
---------------------------------------------------------------------

목적:
Engine의 DAG 구조에서 다중 부모(merge) 노드 실행 조건을 공식 계약으로 고정한다.

다중 부모 노드 실행 규칙:

1. 모든 upstream이 SUCCESS → 실행 대상
2. 하나라도 FAILURE → SKIPPED
3. 하나라도 NOT_REACHED → NOT_REACHED

이 규칙은 안정성 우선 철학에 기반한다.
예측 가능성 / 재현성 / 디버깅 단순화를 목표로 한다.

정본 계약:
- docs/specs/execution_model.md v1.2.0
