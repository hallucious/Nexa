Spec ID: observability_and_metrics
Version: 1.0.0
Status: Partial
Category: policies
Depends On:

======================================================================
Hyper-AI Observability & Metrics Specification v0.1
(관측성 및 메트릭 확장 – 복붙용 단일 블록)
======================================================================

목적:
Hyper-AI 실행을 완전 추적 가능하게 만들고,
성능, 비용, 실패 패턴을 분석 가능하게 한다.

관측성은 선택 기능이 아니라 기본 기능이다.

----------------------------------------------------------------------
1. 관측성 3계층 모델

1.1 Execution Level
- execution_id
- definition_version
- total_duration_ms
- final_status
- total_tokens (AI 사용량)
- total_cost (추정 비용)

1.2 Node Level
각 노드 실행마다 기록:

- node_id
- trace_id
- start_time
- end_time
- duration_ms
- status
- reason_code (실패 시)
- input_size (bytes or token count)
- output_size
- token_usage (AI 노드일 경우)
- retry_count

1.3 System Level
- 전체 동시 실행 수
- 평균 실행 시간
- 실패율
- retry 비율
- 병렬 실행 평균 수

----------------------------------------------------------------------
2. 로그 표준

모든 로그는 구조화된 JSON 형식으로 출력한다.

기본 로그 구조:

{
  "timestamp": "...",
  "execution_id": "...",
  "node_id": "...",
  "trace_id": "...",
  "level": "INFO|WARN|ERROR",
  "event": "node_start|node_end|retry|route|failure",
  "message": "...",
  "reason_code": "...",
  "duration_ms": ...
}

----------------------------------------------------------------------
3. AI 사용량 추적

AI 노드 실행 시 반드시 기록:

- model
- prompt_tokens
- completion_tokens
- total_tokens
- estimated_cost

AI 비용 계산은 설정된 provider 정책 기준.

----------------------------------------------------------------------
4. 실패 분석 모델

4.1 실패 카탈로그

reason_code 기반 통계 생성:

- FAIL_INVALID_INPUT
- FAIL_AI_TIMEOUT
- FAIL_PLUGIN_POLICY_BLOCK
- FAIL_SCHEMA_MISMATCH
- ...

4.2 상위 실패 유형 집계

- 스키마 오류 비율
- 외부 API 실패 비율
- 정책 차단 비율

----------------------------------------------------------------------
5. 성능 메트릭

5.1 실행 시간 분포
- 평균
- p50
- p95
- p99

5.2 병렬 효율성
- 병렬 블록별 평균 실행 시간
- 병합 대기 시간

5.3 재시도 영향
- retry 발생률
- retry 성공률

----------------------------------------------------------------------
6. 경로 추적 (Path Trace)

Execution 종료 시:

- 선택된 분기 기록
- 병렬 경로 기록
- route 변경 기록

예:

"path_trace": [
  {"node": "n1", "status": "success"},
  {"node": "n2", "branch": "then"},
  {"node": "n3", "retry": 1}
]

----------------------------------------------------------------------
7. Export 전략

v0.1 기준:

- 실행 종료 시 JSON report 생성 가능
- 파일 저장 또는 API 반환
- 향후 외부 모니터링 시스템 연동 가능

----------------------------------------------------------------------
8. 금지 규칙

- 실패 로그 누락 금지
- AI 토큰 사용량 누락 금지
- execution_id 없는 로그 금지
- 구조화되지 않은 로그 금지

----------------------------------------------------------------------
9. 철학 요약

1) 측정 없는 구조는 확장 불가.
2) 모든 실행은 분석 가능해야 한다.
3) 실패는 숨기지 않는다.
4) 비용은 추적 대상이다.
5) 관측성은 기본값이다.

======================================================================
End of Document
======================================================================