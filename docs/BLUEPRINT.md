# HYPER-AI BLUEPRINT

Version: 3.5.0
Status: Step41-B2 Design: Injection Registry Contract v1 (Option B)
Last Updated: 2026-02-26
Doc Versioning: SemVer (MAJOR=structure, MINOR=rule add, PATCH=text fix)

---

## 0) One-liner 목적
AI 협업으로 버그 발생 확률을 구조적으로 최소화(안정성 우선).

## 1) 품질 우선순위
재현성 > 계약 안정성 > 테스트 증명 > 확장성.

---

## Step36: Policy trace (reason_trace)
- 모든 정책 결정은 사람이 읽을 수 있는 `reason_trace`를 포함한다.

## Step37: Policy isolation layer
- Gate는 정책 판단만, Runner/CLI는 실행/IO/아티팩트만 담당한다.

## Step38: Baseline-aware policy diff
- 두 run 사이의 정책 스냅샷을 비교하는 deterministic diff를 제공한다.

## Step39: Baseline Drift Detector + Hard drift block
- `--baseline <run_id>` 지정 시 baseline vs current drift 비교를 수행한다.
- Hard drift(decision/reason_code 변화) 발생 시 `--fail-on-hard-drift`로 non-zero exit(2) 가능.

## Step40: Plugin System v1 (Formal Manifest Contract)
- in-tree 플러그인(`src/platform/*_plugin.py`)은 `PLUGIN_MANIFEST`를 노출한다.
- Discovery == Registry를 테스트로 강제한다.
- injection target/key 충돌은 에러로 처리한다.
- `PLATFORM_API_VERSION` 호환성 검증을 수행한다.

## Step41: Capability Negotiation v1
### 목적
Gate별 “필요 기능(capability)”과 “선택 우선순위(priority chain)”를 선언하고,
플랫폼이 단일 negotiation 모듈에서 deterministic하게 plugin/provider를 선택한다.

### Canonical injection keys (Normative)
- ctx.providers: gpt, gemini, perplexity, g6_counterfactual, g7_final_review
- ctx.plugins: exec
- ctx.context["plugins"]: fact_check (override)

### Observability (Normative)
- negotiation마다 `CAPABILITY_NEGOTIATED` 이벤트를 OBSERVABILITY.jsonl에 기록한다.

---

## Step41-B: Required Promotion (Phase B) — **All gates unified**, required is policy table

### 핵심 결론(정본)
- 모듈화의 핵심은 “required를 모두 true로”가 아니다.
- **모든 gate가 동일한 방식으로 negotiation을 거치도록 통일**하는 것이 모듈화의 본질이다.
- required/optional은 **정책 테이블**로 분리하며, gate/기능별로 다를 수 있다.

### B의 목적
1) 모든 Gate가 **항상** negotiation 모듈을 통해 capability를 해석/선택하도록 통일한다.
2) 그 위에 required 승격을 “정책 테이블”로 관리하여, 안정성 강화를 단계적으로 적용한다.

### Gate ↔ Capability 표준 형태(형식 통일)
각 Gate는 최소 다음을 선언한다:
- gate_id
- capability (string)
- required (bool)
- priority_chain (시도 순서)

그리고 플랫폼은:
- negotiate(...) → NegotiationResult 반환(선택/미싱/사유코드/priority_chain 포함)

### Required 정책 테이블 (v1)
초기(Phase B1)에는 required 승격을 최소화한다. (확장 안정성 확보 우선)
- G5: exec_tool = REQUIRED (1차 승격)
- 나머지 Gate capability는 OPTIONAL 유지(외부 provider 환경 의존성 때문)

> 이후 승격은 “운영 환경에서 항상 공급 가능한지”와 “없을 때 품질 붕괴 정도”를 기준으로 진행한다.

### Required Missing Policy (Normative)
REQUIRED capability가 미싱이면:
- Gate MUST return FAIL (안전 실패)
- reason_code MUST be CAPABILITY_REQUIRED_MISSING
- Pipeline status MUST be FAIL
- 관측/드리프트(후처리)는 가능한 범위에서 계속 수행

---

## Out of scope (명시)
- 외부 플러그인 패키지 로딩(다음 단계 A에서 다룸)
- override priority(정책 확정 전 도입 금지)

---

# Step42: External Plugin Loading v1 (In-Repo Plugins Directory)

## Objective
Enable loading plugins from an external, local directory (default: `./plugins/`) while preserving:
- allowlist control
- manifest validation (Step40)
- deterministic negotiation (Step41/41-B)
- conflict rejection (no overrides in v1)

External loading is **disabled by default** and must be explicitly enabled.

---

## Activation (Normative)
- CLI flag: `--enable-external-plugins`
- Optional path: `--plugins-dir <path>` (default: `./plugins`)

If not enabled, the system behaves exactly as Step40/41-B (in-tree only).

---

## External Plugin Layout (v1)
Directory:
- `plugins/<plugin_id>/plugin.py`
- `plugins/<plugin_id>/manifest.json`

`manifest.json` MUST match the Step40 manifest schema (manifest_version 1.0) and include:
- `id`
- `type`
- `entrypoint`
- `inject.target`, `inject.key`
- `requires.platform_api` range
- `determinism.required`

---

## Loading Policy (Normative)
1) Scan plugins directory for `manifest.json`
2) Validate manifest schema and version constraints
3) Import entrypoint from `plugin.py` using module isolation (local import path only)
4) Register injection mapping into the same internal structures as in-tree plugins
5) Run the same conflict checks:
   - duplicate `(target, key)` → FAIL
   - registry/discovery mismatch is not used for external plugins (separate allowlist applies)

---

## Allowlist (Normative)
External plugins require explicit allowlist:
- `plugins/ALLOWLIST.json` (checked into repo) OR
- CLI: `--allow-plugin <id>` repeated

Default policy: deny-all.

---

## Conflict / Override Policy (v1)
- If an external plugin claims an injection key already used by an in-tree plugin: **FAIL**
- If two external plugins conflict: **FAIL**
Override/priority is deferred to v2+.

---

## Observability (Normative)
On external loading attempt, append events to `OBSERVABILITY.jsonl`:
- `EXTERNAL_PLUGIN_SCAN_STARTED`
- `EXTERNAL_PLUGIN_LOADED` (per plugin id)
- `EXTERNAL_PLUGIN_REJECTED` (per plugin id, with reason)
- `EXTERNAL_PLUGIN_SCAN_DONE` (counts)

---

## Scope (Explicit Non-Goals)
- Remote download / marketplace
- Signed plugins
- Sandboxed filesystem/network (beyond existing timeouts)
- Override priority rules

---

# Step43: External Plugin Sandbox v1 (Process Isolation)

## Objective
Enable **safe execution** of external plugins loaded from `./plugins/` by introducing an explicit sandbox boundary.
The sandbox MUST reduce blast radius for:
- hangs/timeouts
- filesystem damage
- unintended network calls
- runaway CPU/memory usage

This step focuses on **external plugins only**. In-tree plugins remain unchanged.

## Scope (v1)
### In scope
- A *sandbox runner* that executes external plugin entrypoints out-of-process
- Hard timeouts (wall-clock)
- Minimal allowlist of environment variables
- Structured error mapping back to `WorkerResult` / `PolicyDecision` meta
- Deterministic behavior requirements preserved

### Out of scope
- Full VM/container orchestration
- Cross-platform perfect parity (Windows/Linux differences allowed but documented)
- Signed plugins / trust store
- Marketplace

## Sandbox Boundary (Normative)
External plugin execution MUST occur in a separate process:
- Parent process: pipeline/runner
- Child process: plugin sandbox worker

If the child process:
- exceeds timeout -> killed, returns `CAPABILITY_TIMEOUT`
- exits non-zero -> returns `PLUGIN_RUNTIME_ERROR`
- writes invalid JSON contract -> returns `PLUGIN_INVALID_OUTPUT`

## Safety Policy (Normative)
External plugins are executed with:
- Working directory: a dedicated temp dir under the current run directory
- Filesystem:
  - Read-only access to repo is NOT guaranteed in v1; instead:
  - Provide explicit input files via temp dir copy (minimal surface)
- Network:
  - Default: **disabled** (best-effort). If not enforceable on the host, record `network_policy="unrestricted"` in meta.
- Environment:
  - Strip all variables except an allowlist (PATH, PYTHONPATH as needed)

## Observability (Normative)
For each external plugin execution, append to `OBSERVABILITY.jsonl`:
- `event`: `EXTERNAL_PLUGIN_SANDBOX_RUN`
- `plugin_id`, `entrypoint`, `timeout_ms`
- `status`: `success|timeout|error|invalid_output`
- `latency_ms`
- `reason_code` (if failed)

## Determinism (Normative)
Sandbox must not introduce nondeterminism:
- No timestamps in returned artifacts
- Stable JSON serialization rules
- All randomness must be explicitly seeded by the parent and passed into the sandbox
---
## Step41-B2: Injection Registry Contract v1 (Option B: 완전 계약화)

### 목적
Injection(주입) 레이어를 “기반층 계약”으로 고정하여 Gate/Plugin/Runner 전반의 호출·오류·관측성을 완전히 통일한다.

### 범위(이번 단계에서 반드시 고정)
1) **InjectionSpec(version 포함)**: target/key 단위의 계약 버전 고정
2) **Registry load-time validator**: 충돌/불일치/로드 실패를 *runtime 이전*에 즉시 실패
3) **InjectionHandle.call() 표준 반환**: `(WorkerResult, value)` 고정
4) **WorkerResult.error_code 표준화**: timeout/crash/contract_error 등 enum 고정
5) **Observability 이벤트 통일**: 모든 주입 호출은 동일 JSONL 포맷으로 기록

### InjectionSpec (Normative)
- 필드:
  - `target: str` (예: "providers", "plugins", "tools")
  - `key: str` (예: "openai", "p_ok")
  - `version: str` (SemVer, 예: "1.0.0")
  - `determinism_required: bool` (기본 False)
  - `timeout_ms: int` (기본값은 정책 테이블에서 결정)
- 규칙:
  - 동일 `(target, key)`는 **중복 등록 금지**
  - 동일 `(target, key)`에 대해 `version` 불일치 발생 시 **load 단계 즉시 실패**
  - `determinism_required=True`인 spec은 호출 결과 `success=False`일 때 **Gate는 반드시 FAIL**

### WorkerResult (Normative)
- 불변 구조:
  - `success: bool`
  - `error: Optional[str]`  (표준 error_code만 허용)
  - `meta: Dict[str, Any]`
- 표준 error_code (enum):
  - `"timeout"`: 시간 초과
  - `"crash"`: 프로세스/런타임 크래시
  - `"contract_error"`: 반환 스키마/타입/필드 불일치 등 계약 위반
  - `"load_error"`: 플러그인/모듈 로드 실패
  - `"security_violation"`: 보안 정책 위반(금지 import/경로 탈출 시도 등)
  - `"unknown_error"`: 위 케이스로 분류 불가

### Registry validation (Normative)
Registry는 “사용 직전”이 아니라 **로드 시점**에 전수 검증한다:
- 중복 키: 즉시 예외
- spec version mismatch: 즉시 예외
- 필수 필드 누락/타입 불일치: 즉시 예외
- 엔트리포인트 실행 전 preflight 실패(예: 파일 없음): 즉시 예외

### Observability: Injection Call (Normative)
모든 Injection 호출은 `OBSERVABILITY.jsonl`에 다음 이벤트를 기록한다:

- `event`: `INJECTION_CALL`
- `target`, `key`, `spec_version`
- `success` (bool)
- `error` (표준 error_code 또는 null)
- `duration_ms`
- `determinism_required`
- `reason_code` (Gate 정책이 실패 처리한 경우)

※ 기존 `EXTERNAL_PLUGIN_SANDBOX_RUN` 이벤트는 “sandbox 실행” 관측이고,
`INJECTION_CALL`은 “주입 인터페이스 호출” 관측이다. 둘 다 유지하되 스키마는 각각 고정한다.

### Gate 규칙(강제)
- Gate는 직접 플러그인을 import/exec 하지 않는다.
- Gate는 **오직 InjectionRegistry + InjectionHandle.call()**을 통해서만 외부 실행/텍스트 생성 등을 요청한다.
- Gate의 실패 판단은 `WorkerResult.success` + 정책 테이블(예: determinism.required)로만 결정한다.
