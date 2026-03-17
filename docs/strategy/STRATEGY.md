# Nexa Strategy

Version: 1.1.0
Status: Official Strategy Direction

---

## 1. 제품 정체성

Nexa는 **구조적으로 검증 가능한 AI 실행 엔진**이다.

단순 자동화 도구가 아니라, **구조/제약/재현성/Trace**를 기반으로 실행을 통제한다.

핵심 차별화:
- 결정론적 실행 (deterministic, dependency-based execution)
- 전체 실행 추적 (full execution trace, per-node)
- 계약 기반 아키텍처 (contract-driven architecture)
- 회귀 감지 및 정책 게이팅 (regression detection + policy gating)

---

## 2. 1차 타겟

**기업 R&D 팀**을 1차 타겟으로 둔다.

이유: 재현성, 감사 로그, 실패 분석, 비용 통제 요구가 강함.

---

## 3. MVP 범위 (완료)

- 구조 설계: Engine / Node / Circuit / Channel / Flow
- 구조 검증: Validation Engine
- 실제 실행: Runtime (dependency-based scheduling)
- 전체 그래프 Trace 저장 (미실행 노드 포함)
- execution_id 기반 재현 가능성
- ExecutionConfig 기반 노드 행동 조합
- 회귀 감지 (typed reason codes + severity)
- 정책 평가 (PolicyDecision: PASS / WARN / FAIL)
- CLI (실행, diff, regression 명령)

---

## 4. 철학 / 우선순위

- Simple-first
- 우선순위: 구조 단순성 > 안정성 > 재현성 > 비용 > 성능
- 자동 적용 금지: 사용자 승인 후 새 Revision으로만 반영

---

## 5. UI 방향 (후순위)

- Guided → Builder → Advanced 단계로 확장
- 내부 모델은 유지하되, UX는 구조 안정화 이후 단계에서 진행

---

## 6. 다음 전략 목표

**Phase 3**: CLI 회귀 게이팅 — CI/CD에서 PASS/WARN/FAIL 기반 자동 차단

**Phase 4**: 설정 기반 정책 — 회귀 규칙을 circuit/run별로 커스터마이즈

**Phase 5**: Visual Circuit Builder — 개발자 생산성 향상

---

End of Strategy
