from __future__ import annotations

from src.circuit.circuit_runner import CircuitRunner
from src.contracts.circuit_fingerprint import compute_circuit_fingerprint, compute_execution_surface_fingerprint
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


def test_resume_human_decision_is_registered_and_emitted():
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
    assert paused.paused_run_state is not None

    persisted = paused.paused_run_state.to_dict()
    persisted["source_commit_id"] = "commit-1"
    persisted["structure_fingerprint"] = compute_circuit_fingerprint(circuit)
    persisted["execution_surface_fingerprint"] = compute_execution_surface_fingerprint(circuit)

    resume_payload = paused.paused_run_state.to_resume_request_payload()
    resume_payload["source_commit_id"] = "commit-1"
    resume_payload["structure_fingerprint"] = compute_circuit_fingerprint(circuit)
    resume_payload["execution_surface_fingerprint"] = compute_execution_surface_fingerprint(circuit)
    resume_payload["human_decision"] = {
        "decision_type": "approve",
        "actor_ref": "user:alice",
        "rationale_text": "approved after quality review",
    }
    resumed_state = dict(paused)
    resumed_state["__paused_run_state__"] = persisted
    resumed_state["__resume__"] = resume_payload

    resumed = runner.execute(circuit, resumed_state)
    assert resumed["n_pause"] == "out:cfg.pause"
    assert human_registry.count() == 1
    record = human_registry.all_records()[0]
    assert record.decision_type == "approve"
    assert record.actor_ref == "user:alice"
    assert record.downstream_action == "continue"
    assert record.target_ref == "node.n_pause.review_gate"
    assert record.trace_refs == [f"trace://{paused.paused_run_state.paused_execution_id}#node:n_pause"]

    decision_events = [event for event in runtime.events if event[0] == "human_decision_recorded"]
    assert len(decision_events) == 1
    _, payload, node_id = decision_events[0]
    assert node_id == "n_pause"
    assert payload["decision_type"] == "approve"
    assert payload["actor_ref"] == "user:alice"


def test_create_execution_record_from_circuit_run_projects_human_decision_summary():
    circuit = {
        "id": "circuit-1",
        "nodes": [
            {"id": "n_a"},
        ],
    }
    final_state = {"n_a": {"value": "done"}}
    trace = {
        "events": [
            {
                "type": "human_decision_recorded",
                "payload": {
                    "decision_id": "hd-1",
                    "target_ref": "node.n_a.review_gate",
                    "decision_type": "approve",
                    "actor_ref": "user:bob",
                    "downstream_action": "continue",
                    "timestamp": "2026-04-07T00:00:00+00:00",
                    "trace_refs": ["trace://exec-1#node:n_a"],
                },
            }
        ]
    }

    record = create_serialized_execution_record_from_circuit_run(
        circuit,
        final_state,
        execution_id="exec-1",
        trace=trace,
    )

    summary = record["observability"]["human_decision_summary"]
    assert summary["decision_count"] == 1
    assert summary["decision_types"] == ["approve"]
    assert summary["actor_refs"] == ["user:bob"]
    assert summary["downstream_actions"] == ["continue"]
    assert summary["target_refs"] == ["node.n_a.review_gate"]
