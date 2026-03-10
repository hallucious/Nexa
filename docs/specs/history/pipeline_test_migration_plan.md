Spec ID: pipeline_test_migration_plan
Version: 1.0.0
Status: Partial
Category: history
Depends On:

# pipeline_test_migration_plan
Version: 0.1.0
Status: Planned

## 1. 목적
본 문서는 `tests/`에 남아있는 **legacy(pipeline/gates/orchestrator) 의존 테스트**를
Engine 중심 구조로 점진 전환하기 위한 계획 문서다.

## 2. 전환 원칙
1) 테스트를 제거해서 통과시키지 않는다.
2) Engine CLI/Engine Core를 기준으로 **동등한 의미의 계약/회귀 테스트**로 대체한다.
3) 전환은 작은 단위로 수행한다: (1) 대체 테스트 추가 → (2) 기존 테스트 deprecate → (3) 마지막에 삭제
4) 각 단계마다 `python -m pytest -q` 전체 통과를 유지한다.

## 3. 현황: legacy import 포함 테스트 목록
- 발견된 legacy import 라인 수: 146
- 영향받는 테스트 파일 수: 47

| 분류 | 테스트 파일 | 대표 legacy import 예시(라인) | 전환 방향 |
|---|---|---|---|
| Misc legacy dependency | `tests/test_contract_invariance.py` | L6: `from src.pipeline.runner import PipelineRunner, GateContext` | 개별 분석 후 Engine 계약/기능 테스트로 치환 |
| Misc legacy dependency | `tests/test_engine_legacy_isolation_contract.py` | L26: `legacy_prefixes = ("src.pipeline", "src.gates", "src.platform.orchestrator")` | 개별 분석 후 Engine 계약/기능 테스트로 치환 |
| Gate behavior/step regression (legacy gates) | `tests/test_g6_output_schema_snapshot.py` | L5: `from src.gates.g6_counterfactual import gate_g6_counterfactual_review` | Engine node handler 기반 regression으로 치환 |
| Gate behavior/step regression (legacy gates) | `tests/test_gate_result_contract.py` | L5: `from src.pipeline.runner import GateResult` | Engine node handler 기반 regression으로 치환 |
| Observability contract (legacy runner) | `tests/test_observability_contract.py` | L6: `from src.pipeline.runner import PipelineRunner, GateContext` | Engine Observability 이벤트/레코드 계약으로 치환 |
| Orchestrator contract (legacy) | `tests/test_orchestrator_contract.py` | L8: `from src.pipeline.runner import GateContext` | Engine 실행 그래프/빌더 계약으로 치환 (orchestrator 제거 전까지 유지) |
| Runner/state/policy invariants (legacy runner) | `tests/test_policy_invariants_stabilization.py` | L8: `from src.pipeline.runner import PipelineRunner, GateContext` | Engine run result/state 모델 기반 invariants로 치환 |
| Runner/state/policy invariants (legacy runner) | `tests/test_runner_meta_snapshot.py` | L6: `from src.pipeline.runner import PipelineRunner` | Engine run result/state 모델 기반 invariants로 치환 |
| Runner/state/policy invariants (legacy runner) | `tests/test_runner_policy_invariants.py` | L7: `from src.pipeline.runner import PipelineRunner, GateContext` | Engine run result/state 모델 기반 invariants로 치환 |
| Runner/state/policy invariants (legacy runner) | `tests/test_stable_core_repeatability.py` | L5: `from src.pipeline.runner import PipelineRunner` | Engine run result/state 모델 기반 invariants로 치환 |
| Gate behavior/step regression (legacy gates) | `tests/test_step10_g7.py` | L7: `from src.pipeline.runner import PipelineRunner` | Engine node handler 기반 regression으로 치환 |
| Gate behavior/step regression (legacy gates) | `tests/test_step11_3_g2_pic_priority.py` | L7: `from src.pipeline.state import RunMeta, GateId` | Engine node handler 기반 regression으로 치환 |
| Gate behavior/step regression (legacy gates) | `tests/test_step12_g4_self_check_execution.py` | L6: `from src.gates.g4_self_check import gate_g4_self_check` | Engine node handler 기반 regression으로 치환 |
| Gate behavior/step regression (legacy gates) | `tests/test_step15_gate_context_injection.py` | L3: `from src.pipeline.runner import PipelineRunner, GateContext` | Engine node handler 기반 regression으로 치환 |
| Gate behavior/step regression (legacy gates) | `tests/test_step16_gate_registry.py` | L3: `from src.pipeline.runner import PipelineRunner` | Engine node handler 기반 regression으로 치환 |
| Gate behavior/step regression (legacy gates) | `tests/test_step17_cli_module.py` | L5: `from src.pipeline.cli import build_default_runner` | Engine node handler 기반 regression으로 치환 |
| Gate behavior/step regression (legacy gates) | `tests/test_step18_cli_request_text.py` | L3: `from src.pipeline.cli import parse_args` | Engine node handler 기반 regression으로 치환 |
| Gate behavior/step regression (legacy gates) | `tests/test_step19_cli_load_dotenv.py` | L6: `from src.pipeline import cli` | Engine node handler 기반 regression으로 치환 |
| Gate behavior/step regression (legacy gates) | `tests/test_step1_init.py` | L6: `from src.pipeline.artifacts import Artifacts` | Engine node handler 기반 regression으로 치환 |
| Runner/state/policy invariants (legacy runner) | `tests/test_step20_meta_json_written.py` | L6: `from src.pipeline.runner import PipelineRunner` | Engine run result/state 모델 기반 invariants로 치환 |
| Gate behavior/step regression (legacy gates) | `tests/test_step21_provider_injection.py` | L3: `from src.pipeline.runner import PipelineRunner, GateContext` | Engine node handler 기반 regression으로 치환 |
| Gate behavior/step regression (legacy gates) | `tests/test_step22_g1_provider_injection.py` | L3: `from src.pipeline.runner import GateContext` | Engine node handler 기반 regression으로 치환 |
| Gate behavior/step regression (legacy gates) | `tests/test_step23_g3_provider_injection.py` | L3: `from src.pipeline.state import RunMeta` | Engine node handler 기반 regression으로 치환 |
| Gate behavior/step regression (legacy gates) | `tests/test_step24_g4_provider_injection.py` | L3: `from src.pipeline.state import RunMeta` | Engine node handler 기반 regression으로 치환 |
| Gate behavior/step regression (legacy gates) | `tests/test_step25_g7_provider_injection.py` | L3: `from src.gates.g7_final_review import gate_g7_final_review` | Engine node handler 기반 regression으로 치환 |
| Gate behavior/step regression (legacy gates) | `tests/test_step26_g6_provider_injection.py` | L3: `from src.gates.g6_counterfactual import gate_g6_counterfactual_review` | Engine node handler 기반 regression으로 치환 |
| Gate behavior/step regression (legacy gates) | `tests/test_step27_g2_provider_injection.py` | L3: `from src.pipeline.state import RunMeta` | Engine node handler 기반 regression으로 치환 |
| Runner/state/policy invariants (legacy runner) | `tests/test_step28_g2_unknown_stop_policy.py` | L4: `from src.pipeline.state import RunMeta` | Engine run result/state 모델 기반 invariants로 치환 |
| Gate behavior/step regression (legacy gates) | `tests/test_step29_platform_unified_resolve.py` | L3: `from src.pipeline.runner import GateContext` | Engine node handler 기반 regression으로 치환 |
| Runner/state/policy invariants (legacy runner) | `tests/test_step2_runner.py` | L3: `from src.pipeline.runner import PipelineRunner` | Engine run result/state 모델 기반 invariants로 치환 |
| Runner/state/policy invariants (legacy runner) | `tests/test_step30_plugin_meta_contract.py` | L8: `from src.pipeline.runner import GateContext` | Engine run result/state 모델 기반 invariants로 치환 |
| Observability contract (legacy runner) | `tests/test_step34_observability_run_dir_artifact.py` | L6: `from src.pipeline.runner import PipelineRunner, GateContext` | Engine Observability 이벤트/레코드 계약으로 치환 |
| Observability contract (legacy runner) | `tests/test_step35_observability_report.py` | L6: `from src.pipeline.observability_report import summarize_run` | Engine Observability 이벤트/레코드 계약으로 치환 |
| Runner/state/policy invariants (legacy runner) | `tests/test_step36_policy_trace_written.py` | L6: `from src.pipeline.runner import PipelineRunner, GateContext` | Engine run result/state 모델 기반 invariants로 치환 |
| Runner/state/policy invariants (legacy runner) | `tests/test_step38_policy_diff_report.py` | L6: `from src.pipeline.policy_diff import diff_policy_between_runs` | Engine run result/state 모델 기반 invariants로 치환 |
| Gate behavior/step regression (legacy gates) | `tests/test_step39_drift_detector_phase2.py` | L6: `from src.pipeline.drift_detector import run_drift_detector` | Engine node handler 기반 regression으로 치환 |
| Gate behavior/step regression (legacy gates) | `tests/test_step39_fail_on_hard_drift.py` | L5: `from src.pipeline.cli import _exit_code_after_drift` | Engine node handler 기반 regression으로 치환 |
| Gate behavior/step regression (legacy gates) | `tests/test_step3_contracts.py` | L5: `from src.pipeline.runner import PipelineRunner` | Engine node handler 기반 regression으로 치환 |
| Gate behavior/step regression (legacy gates) | `tests/test_step41_capability_negotiation.py` | L5: `from src.pipeline.runner import GateContext` | Engine node handler 기반 regression으로 치환 |
| Gate behavior/step regression (legacy gates) | `tests/test_step41b2_injection_registry_contract.py` | L13: `from src.pipeline.observability import read_observability_events` | Engine node handler 기반 regression으로 치환 |
| Gate behavior/step regression (legacy gates) | `tests/test_step41b_gate_negotiation_coverage.py` | L6: `from src.pipeline.runner import GateContext, RunMeta` | Engine node handler 기반 regression으로 치환 |
| Gate behavior/step regression (legacy gates) | `tests/test_step4_g1.py` | L5: `from src.pipeline.runner import PipelineRunner` | Engine node handler 기반 regression으로 치환 |
| Gate behavior/step regression (legacy gates) | `tests/test_step5_g2_continuity.py` | L6: `from src.pipeline.runner import PipelineRunner` | Engine node handler 기반 regression으로 치환 |
| Gate behavior/step regression (legacy gates) | `tests/test_step6_g3_fact_audit.py` | L6: `from src.pipeline.runner import PipelineRunner` | Engine node handler 기반 regression으로 치환 |
| Gate behavior/step regression (legacy gates) | `tests/test_step7_g4_self_check.py` | L6: `from src.pipeline.runner import PipelineRunner` | Engine node handler 기반 regression으로 치환 |
| Gate behavior/step regression (legacy gates) | `tests/test_step8_g5.py` | L7: `from src.pipeline.runner import PipelineRunner` | Engine node handler 기반 regression으로 치환 |
| Gate behavior/step regression (legacy gates) | `tests/test_step9_g6.py` | L7: `from src.pipeline.runner import PipelineRunner` | Engine node handler 기반 regression으로 치환 |

## 4. 단계별 전환 계획(권장 순서)
### 4.1 Phase T1 — Runner/State/Policy invariants 전환
- 목표: `PipelineRunner/RunMeta/RunStatus` 기반 계약을 Engine 결과 모델 기반으로 치환
- 산출물: Engine run 메타/정책 불변조건 테스트 세트

### 4.2 Phase T2 — Observability 계약 전환
- 목표: runner 단위 관측성 계약을 Engine 관측성 이벤트/스팬/레코드 계약으로 치환

### 4.3 Phase T3 — Orchestrator 계약 전환
- 목표: orchestrator가 필요하다면 Engine graph builder로 치환, 불필요하면 삭제

### 4.4 Phase T4 — Gate(step) 회귀 테스트 전환
- 목표: legacy gates regression을 Engine node 기반 regression으로 재작성

## 5. 완료 정의(DoD)
1) `tests/`에서 `src.pipeline`, `src.gates`, `src.platform.orchestrator` import가 0
2) 동등 의미의 Engine 기반 테스트로 커버리지 보존
3) pytest 전체 통과 유지
