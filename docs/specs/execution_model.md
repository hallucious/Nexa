# Execution Model Specification
Version: 1.2.0
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

2. FAILURE 전파:
   부모 중 하나라도 FAILURE → B는 SKIPPED

3. NOT_REACHED:
   부모 중 하나라도 NOT_REACHED → B는 NOT_REACHED

이 규칙은 deterministic execution을 보장한다.
비동기/병렬/대기 모델은 v2 이후 단계에서 고려한다.
