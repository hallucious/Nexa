# Baseline Packet

이 문서는 Gate 2가 “의미 연속성”을 판단할 때 참조하는 기준 묶음이다.
(장기 프로젝트 기본 모드: 기준 문서가 파일로 존재해야 함)

## 포함 규칙 (우선순위)
1) PIC (baseline/PIC.md) : 최우선
2) BLUEPRINT / CODING_PLAN : 설계/계획 기준
3) (선택) BASELINE_G1_OUTPUT.json : 구조 비교용(있으면 사용)

## 운영 규칙
- 테스트에서는 외부 호출 금지. (Gemini/Perplexity는 mock/stub)
- 실사용(수동 실행)에서는 .env 키가 있으면 실제 호출 가능
- Gate 2는 “의미 연속성”을 존속 조건으로 취급하며,
  DRIFT/VIOLATION이면 FAIL을 집행할 수 있다.

## 파일 목록(현 시점)
- baseline/PIC.md
- (선택) baseline/BASELINE_G1_OUTPUT.json
- (참조) BLUEPRINT.md / CODING_PLAN.md
