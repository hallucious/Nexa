# BLUEPRINT

Version: 1.4.1
## 1. Foundation Layer (Canonical Architecture Memory)

본 프로젝트의 기초 설계 문서는 다음 문서에 의해 계층적으로 관리된다:

-   docs/FOUNDATION_MAP.md

구조 변경 또는 계약 변경 작업 시 반드시 FOUNDATION_MAP을 참조하고,
영향받는 문서들의 상태 및 SemVer를 확인해야 한다.

## 2. Active Specifications

현재 코드와 1:1로 동기화되는 활성 spec 문서 목록:

-   docs/specs/execution_model.md
-   docs/specs/trace_model.md
-   docs/specs/validation_engine_contract.md
-   docs/specs/validation_rule_catalog.md


-   docs/specs/provider_contract.md
### 2.1 추가된 Active Specs (Step67~84 누적)

아래 항목들은 기존 목록에 **누적 추가**된 활성 spec(코드/테스트와 동기화)이다:

-   docs/specs/terminology.md
-   docs/specs/node_execution_contract.md  (NODE-EXEC v1.0.0)
-   docs/specs/docs_specs_circuit_trace_contract.md  (CT-TRACE v1.0.0, circuit trace contract)
-   docs/specs/plugin_contract.md  (PLUGIN-CONTRACT v1.0.0)
-   docs/specs/prompt_contract.md  (PROMPT-CONTRACT v1.0.0)
-   docs/specs/plugin_registry_contract.md  (PLUGIN-REGISTRY v1.0.0)
-   docs/specs/observability_metrics.md  (OBSERVABILITY, opt-in 이벤트/메트릭)

주의:
- **Active spec 목록의 Source-of-Truth는 본 문서(BLUEPRINT)이다.**
- `docs/FOUNDATION_MAP.md`는 문서 카탈로그/레이어링을 제공하지만, Active spec 결정 기준이 아니다.
- spec-version sync 계약 테스트는 BLUEPRINT의 Active spec 목록을 파싱해, 각 spec 문서의 `Version:`과 `src/contracts/spec_versions.py`의 매핑이 일치하는지 강제한다.


구조/계약 변경 시 위 문서들과 코드, 테스트는 반드시 동기화되어야 한다.

------------------------------------------------------------------------

# Archived Initial Version (Preserved)

# Hyper-AI BLUEPRINT

Version: v1.0.0 Status: Contract Snapshot

Purpose: This document is the authoritative contract snapshot for
Hyper-AI v1.

It defines: - Active specifications - System boundaries - Forbidden
capabilities (v1) - Document--Code synchronization rules

Any implementation must comply with this document.

====================================================================== 1.
System Identity
======================================================================

Hyper-AI is a:

"Structurally Verifiable AI Execution Engine"

Core Principles:

-   Structure-first
-   Constraint-enforced execution
-   Pure-first
-   Sync-first
-   Graph-based trace
-   Controlled non-determinism
-   Reproducibility mandatory

======================================================================
2. Active Specifications (v1 Set)
======================================================================

All following specifications are active and binding.

  Spec File                             Version   Status
  ------------------------------------- --------- --------
  specs/terminology.md                  v1.0.0    Active
  specs/node_abstraction.md             v1.0.0    Active
  specs/engine_constraints.md           v1.0.0    Active
  specs/execution_model.md              v1.0.0    Active
  specs/node_execution_pipeline.md      v1.0.0    Active
  specs/trace_model.md                  v1.0.0    Active
  specs/side_effect_policy.md           v1.0.0    Active
  specs/determinism_policy.md           v1.0.0    Active
  specs/entry_policy.md                 v1.0.0    Active
  specs/validation_engine_contract.md   v1.0.0    Active
  specs/validation_rule_catalog.md      v1.0.0    Active

These documents collectively define Hyper-AI v1.

======================================================================
3. v1 Structural Scope
======================================================================

v1 Engines must satisfy:

-   Single Entry
-   Directed Acyclic Graph (no cycles)
-   Synchronous execution only
-   No parallel execution
-   No async execution
-   No dynamic structural mutation
-   Full Pre/Core/Post pipeline
-   Graph-based trace recording
-   Immutable trace
-   Reproducibility metadata recording

======================================================================
4. v1 Forbidden Capabilities
======================================================================

The following are NOT allowed in v1:

-   Async execution
-   Parallel node execution
-   Loop constructs
-   Recursive Engine embedding
-   Dynamic Node insertion
-   Runtime Flow mutation
-   Side-effecting Nodes
-   Implicit schema coercion
-   Hidden execution logic
-   Silent failure
-   Partial trace generation

These may be introduced in future MAJOR versions only.

======================================================================
5. Execution Guarantees
======================================================================

Every Execution must guarantee:

-   Structural validation before execution
-   Determinism parameter recording
-   Full graph trace generation
-   Execution metadata recording
-   Failure propagation clarity
-   Immutability of results

Execution without these guarantees is invalid.

======================================================================
6. Document--Code Synchronization Rule
======================================================================

This project enforces strict synchronization:

1)  If any specification changes:
    -   Code must be updated.
    -   Tests must be updated.
    -   Version must be incremented.
2)  If code behavior changes:
    -   Relevant specification must be updated.
    -   Version must be incremented.
3)  A release is valid only when:
    -   Spec versions
    -   Code implementation
    -   Test coverage

    are fully aligned.

No divergence is allowed.

======================================================================
7. Versioning Model
======================================================================

Each spec document has independent SemVer.

BLUEPRINT version represents:

The active contract snapshot of all spec versions.

If any active spec version changes, BLUEPRINT version must be
incremented.

======================================================================
8. Trace Authority
======================================================================

Trace is the canonical execution evidence.

All:

-   Statistical analysis
-   Proposal generation
-   Debugging
-   Reproduction

must rely solely on Trace data.

No hidden runtime state may override Trace.

======================================================================
9. Contract Supremacy Rule
======================================================================

If any implementation contradicts a specification:

-   The specification prevails.
-   Implementation must be corrected.
-   Behavior must be considered invalid.

Specifications are authoritative.

======================================================================
End of Hyper-AI BLUEPRINT v1.0.0
======================================================================

======================================================================
10. Canonical Execution Enforcement (Added in v1.1.0)
======================================================================

1)  Canonical Core
    -   src.engine.\*
    -   src.platform.\* (orchestrator 제외)
    -   src.policy.\*
    -   src.contracts.\*
2)  Compatibility Shim Layer
    -   src.pipeline.\*
    -   src.gates.\*
    -   src.platform.orchestrator
3)  Dependency Direction Rule
    -   Canonical(Core) → Legacy 직접 import 금지
    -   Legacy → Canonical import 허용
    -   Shim → Legacy 위임 허용
4)  Legacy Removal
    -   Legacy 영역 제거는 MAJOR 버전에서만 허용된다.


## Validation Snapshot Layer

Validation execution produces a canonical snapshot of applied rules.
Snapshot is excluded from structural_fingerprint and serves forensic
and replay integrity purposes.


## ExecutionEnvironment v2

Environment is now part of execution identity.
execution_fingerprint determines semantic equality of runs.


## Circuit
See docs/specs/circuit_contract.md

## Active Specs
- CT-TRACE v1.0.0 (Circuit Trace Contract)

## Active Specs
- NODE-EXEC v1.0.0 (Node Execution Contract) — docs/specs/node_execution_contract.md
- PLUGIN-REGISTRY v1.0.0 (Plugin Registry Contract)
