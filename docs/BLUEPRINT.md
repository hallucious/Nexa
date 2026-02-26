# HYPER-AI BLUEPRINT

Version: 3.3.0
Status: Step42 Design: External Plugin Loading v1
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
