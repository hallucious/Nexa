# HYPER-AI CODING PLAN

Version: 3.4.0
Status: Step43 Design: External Plugin Sandbox v1
Last Updated: 2026-02-26
Doc Versioning: SemVer

---

## Step41-B: Implement Plan (B) — Gate unification first, required as policy

### Goal
B를 “G5만 required 구현”으로 축소하지 않는다.
- **모든 gate가 negotiation을 동일한 패턴으로 사용**하도록 통일(모듈화 핵심)
- required 승격은 **정책 테이블**로 관리(초기에는 최소 승격)

---

## Deliverables

### B1) Gate integration unification (모든 gate 동일 패턴)
1) 각 gate/plugin의 “선택 로직”을 capability_negotiation 모듈 호출로 통일
2) 기존 동작(우선순위/폴백)은 유지(회귀 최소화)
3) Observability: CAPABILITY_NEGOTIATED 이벤트가 일관되게 기록되는지 확인

대상(최소):
- g1_design_plugin
- g2_continuity_plugin
- g4_self_check_plugin
- g5_implement_test_plugin
- g6_counterfactual_plugin (이미 적용됨)
- g7_final_review_plugin
- fact_check_plugin / g3_fact_audit_plugin (이미 적용됨)

### B2) Required promotion policy (정책 테이블 적용)
초기 정책:
- G5 exec_tool = REQUIRED
- others OPTIONAL

구현:
- G5에서 negotiate(..., required=True) 적용
- REQUIRED missing → FAIL + CAPABILITY_REQUIRED_MISSING

### B3) Tests
- Negotiation unit tests(이미 Step41로 일부 확보)
- New tests:
  - G5: exec_tool missing → FAIL + reason_code CAPABILITY_REQUIRED_MISSING
  - 기타 gate들은 provider missing 시 OPTIONAL 정책대로 스킵/폴백 유지
- Regression:
  - Step37 timeout test 유지
  - Step39 drift tests 유지
  - Step40 manifest tests 유지

---

## Acceptance Criteria
- 모든 gate가 negotiation을 거치는 “형식 통일” 완료
- required 정책 테이블이 명시적으로 적용됨(초기: G5만 REQUIRED)
- pytest 전체 통과
- 동작 회귀(결정/사유코드/아티팩트) 최소화

---

## Non-goals (B 단계에서 하지 않음)
- External plugin directory loading (A 단계에서 수행)
- override priority/weighting
- UI/UX

---

## Implementation Order (must)
1) B1: 남은 gate들 negotiation 통일(작은 단위로, 테스트 선행)
2) B2: G5 exec_tool REQUIRED 승격
3) pytest pass
4) GitHub main backup
5) Obsidian note (1:1 with commit)

---

# Step42: External Plugin Loading v1 — Implementation Plan

## Goal
Load plugins from a local `./plugins/` directory when explicitly enabled, using the same manifest contract and negotiation pipeline.

---

## Deliverables

1) CLI flags
- `--enable-external-plugins` (default False)
- `--plugins-dir <path>` (default `./plugins`)
- allowlist control:
  - `--allow-plugin <id>` (repeatable)
  - and/or `plugins/ALLOWLIST.json`

2) Loader module
- Add `src/platform/external_plugin_loader.py`
- Responsibilities:
  - discover manifests (`manifest.json`)
  - validate schema + platform_api range
  - load entrypoint from `plugin.py`
  - register into platform injection maps
  - enforce conflicts (duplicate target/key → error)

3) Integration point
- Hook into platform initialization before gates run so negotiation sees external plugins.

4) Tests
- external plugin loaded when enabled + allowlisted
- denied when not allowlisted
- conflict with in-tree injection key → fail
- invalid manifest_version → fail
- version constraint mismatch → fail

---

## Acceptance Criteria
- With flag enabled and allowlisted plugin present, negotiation can select it.
- Without flag, behavior is unchanged.
- Conflicts are rejected deterministically.
- pytest fully passes.

---

## Implementation Order
1) Add loader + minimal schema validation
2) Add CLI wiring
3) Add allowlist mechanism
4) Add tests
5) pytest pass
6) GitHub backup (main)
7) Obsidian note (1:1 with commit)

---

## Step43: External Plugin Sandbox v1 — Implementation Plan

### Goal
Execute external plugins in an isolated process with hard timeout and strict IO contracts.

### Deliverables
1) Sandbox worker protocol (JSON over stdio)
- Parent sends:
  - `plugin_id`, `entrypoint`, `args`, `timeout_ms`, `seed`, `io_paths`
- Child returns:
  - `success`, `result`, `error`, `reason_code`, `latency_ms`

2) New modules
- `src/platform/sandbox_protocol.py` (types + encode/decode)
- `src/platform/external_sandbox_runner.py` (parent-side)
- `src/platform/external_sandbox_worker.py` (child-side CLI entry)

3) Integration points
- `external_loader` marks plugins as `origin="external"`
- Negotiation returns selected plugin + origin
- When origin is external:
  - execution goes through sandbox runner
- In-tree plugins bypass sandbox

4) Reason codes (add if missing)
- `CAPABILITY_TIMEOUT`
- `PLUGIN_RUNTIME_ERROR`
- `PLUGIN_INVALID_OUTPUT`
- `SANDBOX_POLICY_UNAVAILABLE` (if host cannot enforce network/file policy)

5) Tests
- Unit: protocol round-trip, deterministic ordering
- Integration:
  - external plugin that sleeps -> timeout triggers
  - external plugin that raises -> runtime error triggers
  - external plugin returns malformed output -> invalid_output triggers
  - external plugin normal -> success

### Acceptance Criteria
- External plugin execution is out-of-process.
- Timeout is enforced (hard kill).
- Failures are mapped to reason codes deterministically.
- All existing tests continue to pass + new Step43 tests pass.

### Non-Goals
- Containerization
- Signed plugins
- Advanced policy engine

