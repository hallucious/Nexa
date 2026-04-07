from src.designer.models.circuit_patch_plan import (
    ChangeScope,
    CircuitPatchPlan,
    PatchOperation,
    PreviewRequirements,
    ReversibilitySpec,
    ValidationRequirements,
)
from src.designer.models.designer_intent import ActionSpec, DesignerIntent, ObjectiveSpec, TargetScope
from src.designer.proposal_flow import DesignerProposalFlow
from src.engine.node_execution_runtime import NodeExecutionRuntime
from src.engine.outcome_memory import OutcomeMemoryStore, record_success_pattern
from src.platform.provider_executor import ProviderExecutor
from src.platform.provider_registry import ProviderRegistry
from src.storage.execution_record_api import create_serialized_execution_record_from_circuit_run


class RecordingProvider:
    def __init__(self, name: str):
        self.name = name
        self.requests = []

    def execute(self, request):
        self.requests.append(request)
        return {
            "output": f"{self.name}:{request.prompt or 'empty'}",
            "trace": {"provider": self.name},
        }


class FixedIntentNormalizer:
    def normalize(self, request_text, *, context=None):
        return DesignerIntent(
            intent_id="intent-constraint",
            category="MODIFY_CIRCUIT",
            user_request_text=request_text,
            target_scope=TargetScope(mode="existing_circuit", savefile_ref="ws-1"),
            objective=ObjectiveSpec(primary_goal="Modify the working circuit"),
            proposed_actions=(
                ActionSpec(
                    action_type="create_node",
                    target_ref="pipeline_node",
                    parameters={"kind": "pipeline_step"},
                    rationale="Create a legacy pipeline node",
                ),
            ),
            explanation="fixed intent for constraint integration test",
        )


class ForbiddenPatchBuilder:
    def build(self, intent):
        return CircuitPatchPlan(
            patch_id="patch-constraint",
            patch_mode="modify_existing",
            summary="Introduce a forbidden legacy pipeline node",
            intent_ref=intent.intent_id,
            target_savefile_ref="ws-1",
            change_scope=ChangeScope(scope_level="bounded", touch_mode="structural_edit", touched_nodes=("pipeline_node",)),
            operations=(
                PatchOperation(
                    op_id="op-create-pipeline",
                    op_type="create_node",
                    target_ref="pipeline_node",
                    payload={"kind": "pipeline_step", "risk_level": "low"},
                    rationale="Create a forbidden pipeline node for constraint lint coverage",
                ),
            ),
            reversibility=ReversibilitySpec(reversible=True),
            preview_requirements=PreviewRequirements(required_preview_areas=("summary",)),
            validation_requirements=ValidationRequirements(required_checks=("designer_constraints",)),
        )


def _runtime(tmp_path, providers, *, outcome_memory_store=None):
    registry = ProviderRegistry()
    for provider_id, provider in providers.items():
        registry.register(provider_id, provider)
    return NodeExecutionRuntime(
        provider_executor=ProviderExecutor(registry),
        observability_file=str(tmp_path / "obs.jsonl"),
        outcome_memory_store=outcome_memory_store,
    )


def test_step227_outcome_memory_guides_route_tier_and_records_success(tmp_path):
    store = OutcomeMemoryStore()
    record_success_pattern(
        store,
        route_tier="high_quality",
        provider_id="hq",
        task_types=["analysis"],
        confidence_score=0.91,
        verifier_ids=["output_verifier"],
        trace_refs=["trace://history/n1"],
        notes="historical successful analysis run",
    )

    cheap = RecordingProvider("cheap")
    hq = RecordingProvider("hq")
    runtime = _runtime(tmp_path, {"cheap": cheap, "hq": hq}, outcome_memory_store=store)

    config = {
        "config_id": "ec_outcome_memory_runtime",
        "node_id": "n1",
        "provider": {
            "provider_id": "cheap",
            "provider_candidates": ["hq", "cheap"],
            "allowed_models": ["hq-model", "cheap-model"],
            "model": "cheap-model",
            "task_type": "analysis",
        },
        "runtime_config": {
            "return_raw_output": True,
            "budget_routing": {
                "current_budget": 25.0,
                "allowed_providers": ["hq", "cheap"],
                "allowed_models": ["hq-model", "cheap-model"],
                "task_type": "analysis",
            },
            "safety_gate": {
                "allowed_actions": ["provider_execute"],
            },
        },
    }

    result = runtime.execute(config, {"question": "which provider wins"})

    assert result.trace.precision["outcome_memory"]["suggested_route_tier"] == "high_quality"
    assert result.trace.precision["routing"][0]["route_decision"]["selected_route_tier"] == "high_quality"
    assert result.trace.precision["outcome_memory"]["recorded_success_pattern_id"]
    assert store.total_entries() == 2



def test_step227_execution_record_projects_trace_intelligence_summary():
    payload = create_serialized_execution_record_from_circuit_run(
        {"id": "trace-intel-circuit", "nodes": [{"id": "n1"}, {"id": "n2"}]},
        {"n1": {"value": "ok"}, "n2": {"value": "retry"}},
        execution_id="trace-intel-exec",
        trace={
            "events": ["started", "completed"],
            "node_results": {
                "n1": {
                    "status": "success",
                    "trace": {"timings_ms": {"provider_execute": 10.0}},
                },
                "n2": {
                    "status": "failed",
                    "error": {"type": "provider_timeout", "message": "provider timed out"},
                    "trace": {"timings_ms": {"provider_execute": 35.0}},
                },
            },
        },
    )

    summary = payload["observability"]["trace_intelligence_summary"]
    assert summary["failure_taxonomy"]["top_reason_codes"][0] == "provider_timeout"
    assert summary["bottleneck_summary"]["slowest_nodes"][0] == "n2"
    assert "analyzed 2 node event(s)" in payload["observability"]["trace_summary"]



def test_step227_proposal_flow_surfaces_designer_constraint_findings():
    flow = DesignerProposalFlow(
        normalizer=FixedIntentNormalizer(),
        patch_builder=ForbiddenPatchBuilder(),
    )

    bundle = flow.propose(
        "Add a legacy pipeline node",
        working_save_ref="ws-1",
    )

    assert bundle.precheck.overall_status == "blocked"
    assert any(f.issue_code == "FORBIDDEN_NODE_KIND" for f in bundle.precheck.blocking_findings)
    assert any(f.issue_code == "DESIGNER_CONSTRAINT_UNSAFE" for f in bundle.precheck.blocking_findings)
