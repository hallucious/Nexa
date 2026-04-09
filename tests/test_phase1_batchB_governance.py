from __future__ import annotations

from typing import Any, Dict, Optional

from src.automation.output_destination import attempt_delivery
from src.circuit.circuit_runner import CircuitRunner
from src.engine.execution_event import ExecutionEvent
from src.engine.execution_event_emitter import ExecutionEventEmitter
from src.governance.quota import QuotaPolicy, QuotaScope, QuotaStateRecord, evaluate_quota
from src.safety.input_safety import evaluate_input_safety


class _DummyRegistry:
    def __init__(self):
        self._configs = {"cfg.ok": {"config_id": "cfg.ok"}, "cfg.dict": {"config_id": "cfg.dict"}}

    def get(self, config_id):
        return self._configs[config_id]


class _GovernanceRuntime:
    def __init__(self, *, output_by_config: Optional[Dict[str, Any]] = None):
        self.event_emitter = ExecutionEventEmitter(event_file=None)
        self.execution_id = "runtime-default"
        self.trigger_source = "manual"
        self.automation_id = None
        self.calls = []
        self.output_by_config = dict(output_by_config or {"cfg.ok": "done:cfg.ok"})

    def set_execution_identity(self, *, execution_id: str, trigger_source: str, automation_id: Optional[str] = None):
        self.execution_id = execution_id
        self.trigger_source = trigger_source
        self.automation_id = automation_id

    def _emit_event(self, event_type, payload, node_id=None):
        self.event_emitter.emit(
            ExecutionEvent.now(
                event_type,
                payload,
                execution_id=self.execution_id,
                node_id=node_id,
                trigger_source=self.trigger_source,
                automation_id=self.automation_id,
            )
        )

    def execute_by_config_id(self, registry, config_id, state):
        self.calls.append(config_id)

        class Result:
            def __init__(self, output):
                self.output = output

        return Result(output=self.output_by_config[config_id])


def test_input_safety_requires_confirmation_then_allows_after_explicit_confirmation() -> None:
    blocked = evaluate_input_safety(
        [{"input_ref": "user.prompt", "content": "Contact me at user@example.com"}],
        trigger_source="manual",
    )
    assert blocked["decision"]["overall_status"] == "confirmation_required"
    assert blocked["decision"]["launch_allowed"] is False

    allowed = evaluate_input_safety(
        [{"input_ref": "user.prompt", "content": "Contact me at user@example.com"}],
        trigger_source="manual",
        confirmed_by="tester",
        confirmed_at="2026-04-10T01:00:00Z",
    )
    assert allowed["decision"]["overall_status"] == "allow_with_warning"
    assert allowed["decision"]["launch_allowed"] is True
    assert allowed["records"][0]["final_status"] == "confirmed_then_allowed"


def test_circuit_runner_blocks_launch_on_input_safety_before_execution_starts() -> None:
    runtime = _GovernanceRuntime()
    runner = CircuitRunner(runtime, _DummyRegistry())
    circuit = {"id": "safe-circuit", "nodes": [{"id": "node_a", "execution_config_ref": "cfg.ok", "depends_on": []}]}
    state = {
        "__input_safety__": {
            "inputs": [{"input_ref": "user.prompt", "content": "api_key=sk-ABCDEF1234567890"}],
        }
    }

    result = runner.execute(circuit, state)

    assert result.governance.final_status == "blocked"
    assert runtime.calls == []
    event_types = [event.type for event in runtime.event_emitter.get_events()]
    assert event_types == ["input_safety_evaluated", "input_safety_blocked"]
    assert result["__governance__"]["input_safety"]["decision"]["overall_status"] == "blocked"



def test_quota_blocked_launch_stops_before_execution() -> None:
    runtime = _GovernanceRuntime()
    runner = CircuitRunner(runtime, _DummyRegistry())
    circuit = {"id": "quota-circuit", "nodes": [{"id": "node_a", "execution_config_ref": "cfg.ok", "depends_on": []}]}
    state = {
        "__quota__": {
            "scope": {"scope_type": "workspace", "scope_ref": "workspace.demo"},
            "policy": {"policy_id": "quota.demo", "max_run_count": 0, "hard_block_enabled": True},
            "state_record": {"consumed_run_count": 0},
            "estimated_usage": {"run_count": 1},
        }
    }

    result = runner.execute(circuit, state)

    assert result.governance.final_status == "blocked"
    assert runtime.calls == []
    event_types = [event.type for event in runtime.event_emitter.get_events()]
    assert event_types == ["quota_evaluated", "quota_blocked"]
    assert result["__governance__"]["quota"]["decision"]["blocking_reason_code"] == "QUOTA_RUN_COUNT_EXCEEDED"



def test_quota_evaluation_warns_near_limit() -> None:
    scope = QuotaScope(scope_type="workspace", scope_ref="workspace.demo")
    policy = QuotaPolicy(policy_id="quota.demo", scope_ref=scope.scope_ref, max_run_count=10, warning_threshold_ratio=0.8)
    state_record = QuotaStateRecord(scope_ref=scope.scope_ref, period_ref="day:default", consumed_run_count=7)

    decision = evaluate_quota(
        scope=scope,
        policy=policy,
        state_record=state_record,
        requested_action_type="run_launch",
        estimated_usage={"run_count": 1},
    )

    assert decision.overall_status == "allow_with_warning"
    assert decision.warning_summary is not None



def test_delivery_attempt_succeeds_with_explicit_output_selection() -> None:
    result = attempt_delivery(
        capability={
            "destination_type": "webhook",
            "destination_ref": "webhook.dest",
            "supports_text": True,
            "supports_structured_payload": False,
            "supports_attachments": False,
            "supports_idempotency_key": True,
            "supports_retry": True,
            "auth_mode": "managed",
        },
        plan={
            "destination_type": "webhook",
            "destination_ref": "webhook.dest",
            "selected_output_ref": "node_a",
            "payload_projection_mode": "summary",
        },
        outputs={"node_a": {"message": "hello"}},
    )
    assert result["record"]["latest_status"] == "succeeded"
    assert result["attempt"]["status"] == "succeeded"



def test_circuit_runner_records_delivery_success_after_execution() -> None:
    runtime = _GovernanceRuntime()
    runner = CircuitRunner(runtime, _DummyRegistry())
    circuit = {"id": "delivery-circuit", "nodes": [{"id": "node_a", "execution_config_ref": "cfg.ok", "depends_on": []}]}
    state = {
        "__delivery__": {
            "capability": {
                "destination_type": "email",
                "destination_ref": "email.primary",
                "supports_text": True,
                "supports_structured_payload": False,
                "supports_attachments": False,
                "supports_idempotency_key": True,
                "supports_retry": False,
                "auth_mode": "managed",
            },
            "plan": {
                "destination_type": "email",
                "destination_ref": "email.primary",
                "selected_output_ref": "node_a",
                "payload_projection_mode": "summary",
            },
        }
    }

    result = runner.execute(circuit, state)

    assert result["node_a"] == "done:cfg.ok"
    assert result["__governance__"]["delivery"]["record"]["latest_status"] == "succeeded"
    event_types = [event.type for event in runtime.event_emitter.get_events()]
    assert event_types[-1] == "delivery_succeeded"



def test_circuit_runner_blocks_delivery_when_destination_cannot_accept_structured_payload() -> None:
    runtime = _GovernanceRuntime(output_by_config={"cfg.dict": {"message": "structured"}})
    runner = CircuitRunner(runtime, _DummyRegistry())
    circuit = {"id": "delivery-blocked", "nodes": [{"id": "node_a", "execution_config_ref": "cfg.dict", "depends_on": []}]}
    state = {
        "__delivery__": {
            "capability": {
                "destination_type": "slack",
                "destination_ref": "slack.primary",
                "supports_text": True,
                "supports_structured_payload": False,
                "supports_attachments": False,
                "supports_idempotency_key": False,
                "supports_retry": False,
                "auth_mode": "managed",
            },
            "plan": {
                "destination_type": "slack",
                "destination_ref": "slack.primary",
                "selected_output_ref": "node_a",
                "payload_projection_mode": "final_output",
            },
        }
    }

    result = runner.execute(circuit, state)

    assert result["__governance__"]["delivery"]["record"]["latest_status"] == "blocked"
    assert result["__governance__"]["delivery"]["attempt"]["failure_reason_code"] == "DELIVERY_STRUCTURED_PAYLOAD_UNSUPPORTED"
    assert [event.type for event in runtime.event_emitter.get_events()][-1] == "delivery_blocked"
