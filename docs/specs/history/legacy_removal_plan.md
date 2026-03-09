# legacy_removal_plan
Version: 0.1.1
Status: Planned

## 1. 목적
본 문서는 **pipeline/gates/orchestrator(legacy)** 를 안전하게 제거하고, Hyper-AI를 **Engine 중심 구조**로 단일화하기 위한 설계(계획) 문서다.

핵심 목표:
1) Engine은 legacy 모듈을 **절대 import 하지 않는다**(계약 테스트로 강제).
2) 사용자/실행 진입점(특히 CLI)이 Engine 기반으로 전환된다.
3) legacy 삭제 이후에도 **계약 테스트/기능 테스트가 동일하게 통과**한다.

## 2. 배경(현재 상태 스냅샷)
현재 레포에는 다음이 공존한다:
1) Engine 코어: `src/engine/*` (현재 중심)
2) Legacy pipeline: `src/pipeline/*`
3) Legacy gates: `src/gates/*`
4) Legacy orchestrator: `src/platform/orchestrator.py`

현재 계약(이미 존재):
- Engine import 시 legacy 로딩 금지 계약: `tests/test_engine_legacy_isolation_contract.py`

## 3. 범위
### 3.1 제거 대상(legacy)
1) `src/pipeline/*`
2) `src/gates/*`
3) `src/platform/orchestrator.py`

### 3.2 비범위
1) Engine 내부 실행 의미(Execution Model) 변경
2) Validation Engine/Rule Catalog 계약 변경
3) 외부 플러그인 기능 확장

## 4. 핵심 위험(Risk Register)
1) 간접 import 잔존
2) 테스트 의존성(pipeline/gates/orchestrator에 묶임)
3) 표준 CLI 부재(진입점이 legacy에 묶임)

## 5. 삭제 전략(원칙)
1) 대체 경로를 먼저 만든다.
2) legacy 사용 지점을 모두 제거한다.
3) 마지막에 legacy 파일/테스트를 물리 삭제한다.
4) 각 단계는 “계약 테스트 추가 → 코드 변경 → pytest 통과” 순서로 진행한다.

## 6. 단계별 계획(Plan of Record)
Note:
- Engine CLI contract established: `src/engine/cli.py` + `tests/test_engine_cli_contract.py`
- Legacy pipeline entry deprecated: `scripts/run_pipeline.py`
- Next: migrate pipeline-based tests → Engine-based tests (see `docs/specs/pipeline_test_migration_plan.md`)

### 6.1 Phase A — Legacy 사용 지점 식별/차단 강화
- 레포 전수 조사(legacy 참조 목록 작성)
- 필요 시 “legacy 사용 금지” 계약을 확장

### 6.2 Phase B — Engine 기반 CLI 구축
- Engine CLI 표면/계약 테스트 고정
- 표준 실행 경로 승격(진입점 전환)

### 6.3 Phase C — Orchestrator 대체/삭제
- 필요 시 Engine graph builder로 치환
- 의존 0 달성 후 제거

### 6.4 Phase D — gates 제거(Engine node로 대체)
- gates regression을 Engine 기반으로 전환 후 삭제

### 6.5 Phase E — pipeline 제거
- runner/state/contracts 역할을 Engine/Platform으로 이관 후 삭제

## 7. 삭제 전 필수 체크리스트(Pre-Delete Checklist)
1) Engine import legacy 금지 계약: PASS
2) Engine CLI(표준 실행 경로): PASS
3) legacy 참조(직접/간접) 0: PASS
4) pytest 전체 통과: PASS

## 8. 완료 정의(DoD)
1) `src/pipeline/*`, `src/gates/*`, `src/platform/orchestrator.py` 삭제 완료
2) pytest 전체 통과
3) 문서와 코드 상태가 일치
