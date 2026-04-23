[Nexa_SaaS_Completion_Plan_Practical_Execution_Order]

1. P0 구현 완료 및 green 유지
- `phase45_p0_implementation_brief_v1.0.md` 기준 구현 완료
- 전체 테스트 green
- 최소 9개 route 수직 슬라이스 검증 완료

2. S1 + S9 병렬 시작
- S1: async queue / worker / Redis / non-blocking run path
- S9: CI/CD / staging auto-deploy / smoke tests
- 이유: 제품 병목과 배포 신뢰성 둘 다 초기에 필요

3. S-PROV 확정 구현
- canonical provider catalog
- server-managed key model
- `provider_cost_catalog`
- pricing resolver 연결
- 이유: 이후 quota, billing, UX 모두 이 결정 위에 올라감

4. S2 구현
- presigned upload
- quarantine state machine
- ClamAV scan
- extraction limits
- file upload persistence
- 이유: 실제 문서 업로드가 가능해져야 킬러 UC 진행 가능

5. S3 구현
- contract review circuit
- prompt files
- starter template registration
- result shape 고정
- 이유: 첫 PMF 후보 UC를 실제로 실행 가능하게 만들어야 함

6. S4 skeleton → polished 순서 구현
- skeleton: sign-in, workspace, upload, submit, result
- polished: quarantine UX, clause UI, trace/result viewer
- 이유: 실제 사용자 사용 가능 상태 확보

7. S7 basic 먼저
- Sentry
- 최소 에러 관측
- redaction baseline
- 이유: 외부 사용자 붙기 전에 에러 가시성 필요

8. S8 핵심 보안 먼저
- rate limiting
- explicit CORS
- input safety boundary enforcement
- security headers
- 이유: 공개 노출 전 최소 안전선 확보

9. 여기까지 오면 MVP SaaS 판정
- 브라우저에서 계약서 업로드
- 안전 스캔
- 실행
- 결과 확인
- 기본 모니터링/보안 확보

10. S5 구현
- Stripe
- run-count quota
- estimated/actual cost quota
- free/pro/team enforcement
- 이유: 수익화와 비용 통제 시작점

11. S6 구현
- run completed / failed
- quota warning
- payment failed
- file rejected
- 이유: 비동기 UX 완성도 상승

12. S-OPS 구현
- backup
- restore runbooks
- lifecycle
- cleanup jobs
- archive index flow
- 이유: 운영 내구성 확보

13. S-ADMIN 구현
- failed run diagnosis
- stuck job retry/reset
- quota/subscription inspect
- webhook replay
- upload review
- 이유: 운영자가 SQL 없이 다룰 수 있어야 함

14. 여기까지 오면 운영 성숙 구간
- revenue-generating
- observable
- supportable
- recoverable

15. S10 진행
- capability bundle activation
- public surface 점진 확대
- 이유: 기능 확장을 route count가 아니라 capability 기준으로 수행

16. S11, S12는 뒤로
- S11 모바일: browser PMF 확인 후
- S12 MCP: 운영 안정화 후

[요약]
최우선 흐름:
P0 → (S1+S9) → S-PROV → S2 → S3 → S4 → S7 basic → S8 core → MVP SaaS
그 다음:
S5 → S6 → S-OPS → S-ADMIN → 운영 성숙
그 이후:
S10 → S11 → S12