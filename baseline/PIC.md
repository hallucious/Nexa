# Project Identity Contract (PIC)

## 1) Project (this project)
- Name: HAI (Hyper-AI Gate Pipeline)
- One-liner: AI 협업을 통해 버그 발생 확률을 구조적으로 낮추는 코딩 프레임워크

## 2) Non-negotiables (존속 조건)
- 의미(방향성) 연속성이 없으면 프로젝트는 중단/되돌림 대상이다.
- 테스트는 결정적(deterministic)이어야 한다. (동일 입력 → 동일 결과)
- 테스트 중 외부 API/네트워크 호출 금지. (필요 시 mock/stub로 대체)

## 3) Target workflow (요약)
- Gate 기반 파이프라인으로 설계→일관성→팩트감사→자기검증→구현/테스트→대안/반례→최종리뷰
- 각 Gate는 파일 기반 artifact를 남기며, PASS/FAIL + (필요 시) 입력 변형 출력 가능

## 4) Gate 2 continuity principle (핵심)
- Gate 2의 목적은 “작업 연속성(의미/방향)” 보장이다.
- 의미 판단 주체: Gemini (PIC 기준)
- Gate 2는 Gemini 판정을 집행(PASS/FAIL)한다.
- 구조(JSON diff)는 audit/debug 용이며, 의미 판정을 대체하지 않는다.

## 5) Drift/Violation 기준(요약)
- SAME: PIC의 목적/방향과 동일선상
- DRIFT: 목적은 유지하나 우선순위/범위가 눈에 띄게 이동
- VIOLATION: 목적/방향을 위반(다른 프로젝트가 됨)
