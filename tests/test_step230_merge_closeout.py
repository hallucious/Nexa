from __future__ import annotations

from src.circuit.circuit_runner import CircuitRunner
from src.circuit.fingerprint import compute_circuit_fingerprint, compute_execution_surface_fingerprint
from src.engine.human_decision_registry import HumanDecisionRegistry
from src.engine.node_execution_runtime import ReviewRequiredPause
from src.storage.execution_record_api import create_serialized_execution_record_from_circuit_run


class _Registry:
    def __init__(self, configs=None):
        self._configs = configs or {}

    def get(self, config_id):
        return self._configs.get(config_id)

    def register(self, config):
        self._configs[config["config_id"]] = config


class _OneShotPausingRuntime:
    def __init__(self, pause_config_id: str, outputs=None):
        self._pause_config_id = pause_config_id
        self._outputs = outputs or {}
        self._paused_once = False
        self.events = []

    def execute_by_config_id(self, registry, config_id, state):
        class R:
            def __init__(self, output):
                self.output = output

        if config_id == self._pause_config_id and not self._paused_once:
            self._paused_once = True
            raise ReviewRequiredPause(
                node_id="n_pause",
                payload={"reason": "human_review_required", "review_type": "quality"},
            )
        return R(self._outputs.get(config_id, f"out:{config_id}"))

    def _emit_event(self, event_type, payload, *, node_id=None):
        self.events.append((event_type, payload, node_id))

    def set_execution_id(self, eid):
        self._execution_id = eid


def _make_registry(*config_ids: str) -> _Registry:
    registry = _Registry()
    for config_id in config_ids:
        registry.register({"config_id": config_id})
    return registry


def test_step230_review_gate_resume_declares_merge_result_from_human_choice():
    runtime = _OneShotPausingRuntime("cfg.pause")
    registry = _make_registry("cfg.a", "cfg.pause")
    human_registry = HumanDecisionRegistry()
    runner = CircuitRunner(runtime, registry, human_decision_registry=human_registry)

    circuit = {
        "id": "review-circuit",
        "nodes": [
            {"id": "n_a", "execution_config_ref": "cfg.a", "depends_on": []},
            {"id": "n_pause", "execution_config_ref": "cfg.pause", "depends_on": ["n_a"]},
        ],
    }

    paused = runner.execute(circuit, {"input": "x"})
    persisted = paused.paused_run_state.to_dict()
    persisted["source_commit_id"] = "commit-1"
    persisted["structure_fingerprint"] = compute_circuit_fingerprint(circuit)
    persisted["execution_surface_fingerprint"] = compute_execution_surface_fingerprint(circuit)

    resume_payload = paused.paused_run_state.to_resume_request_payload()
    resume_payload["source_commit_id"] = "commit-1"
    resume_payload["structure_fingerprint"] = compute_circuit_fingerprint(circuit)
    resume_payload["execution_surface_fingerprint"] = compute_execution_surface_fingerprint(circuit)
    resume_payload["human_decision"] = {
        "decision_type": "choose_merge",
        "actor_ref": "user:alice",
        "selected_option_ref": "b-2",
        "candidate_branch_ids": ["b-1", "b-2"],
        "rationale_text": "pick higher-quality candidate",
    }
    resumed_state = dict(paused)
    resumed_state["__paused_run_state__"] = persisted
    resumed_state["__resume__"] = resume_payload

    resumed = runner.execute(circuit, resumed_state)
    assert resumed["n_pause"] == "out:cfg.pause"

    decision_record = human_registry.all_records()[0]
    assert decision_record.decision_type == "choose_merge"
    assert decision_record.downstream_action == "merge"
    assert decision_record.selected_option_ref == "b-2"

    merge_events = [event for event in runtime.events if event[0] == "merge_result_declared"]
    assert len(merge_events) == 1
    _, payload, node_id = merge_events[0]
    assert node_id == "n_pause"
    assert payload["merge_result"]["selected_branch_id"] == "b-2"
    assert payload["merge_result"]["discarded_branch_ids"] == ["b-1"]
    assert payload["merge_result"]["merge_policy"]["strategy"] == "human_choice"


def test_step230_execution_record_projects_merge_summary():
    payload = create_serialized_execution_record_from_circuit_run(
        {"id": "merge-circuit", "nodes": [{"id": "n1"}]},
        {"n1": {"value": "done"}},
        execution_id="merge-exec",
        trace={
            "events": [
                {
                    "type": "merge_result_declared",
                    "payload": {
                        "merge_result": {
                            "merge_id": "m-1",
                            "selected_branch_id": "b-2",
                            "discarded_branch_ids": ["b-1"],
                            "merge_policy": {
                                "policy_id": "review_gate_human_merge",
                                "strategy": "human_choice",
                                "conflict_action": "escalate",
                                "require_human_on_tie": False,
                            },
                            "conflict_detected": False,
                            "requires_human_decision": False,
                            "merged_artifact_refs": [],
                            "explanation": "review_gate_human_merge selected=b-2; discarded=1; source=n1",
                        },
                        "target_ref": "node.n1.review_gate",
                        "decision_type": "choose_merge",
                        "selected_option_ref": "b-2",
                        "candidate_branch_ids": ["b-1", "b-2"],
                        "previous_execution_id": "exec-prev",
                    },
                }
            ],
            "node_results": {
                "n1": {"status": "success", "trace": {"timings_ms": {"provider_execute": 10.0}}}
            },
        },
    )

    summary = payload["observability"]["merge_summary"]
    assert summary["merge_count"] == 1
    assert summary["merge_ids"] == ["m-1"]
    assert summary["selected_branch_ids"] == ["b-2"]
    assert summary["discarded_branch_ids"] == ["b-1"]
    assert summary["policies"] == ["human_choice"]
    assert summary["target_refs"] == ["node.n1.review_gate"]
    assert summary["decision_types"] == ["choose_merge"]
