from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

from src.automation.trigger_model import DEFAULT_TRIGGER_SOURCE, normalize_trigger_source
from src.circuit.circuit_runner import CircuitRunner
from src.contracts.status_taxonomy import ExecutionStatus, LaunchStatus, StreamingStatus
from src.contracts.execution_event_contract import ExecutionEvent
from src.engine.execution_event_emitter import ExecutionEventEmitter
from src.engine.node_execution_runtime import NodeExecutionRuntime
from src.providers.adapters.anthropic_messages_adapter import AnthropicMessagesAdapter
from src.providers.adapters.base_adapter import AdapterConfig
from src.providers.adapters.openai_compatible_adapter import OpenAICompatibleAdapter
from src.providers.provider_contract import make_success


class _DummyRegistry:
    def __init__(self):
        self._configs = {"cfg.ok": {"config_id": "cfg.ok"}}

    def get(self, config_id):
        return self._configs[config_id]


class _StreamingProviderExecutor:
    def __init__(self):
        self.requests = []

    def execute(self, request):
        self.requests.append(request)
        return make_success(
            text="hello world",
            raw={
                "output": "hello world",
                "trace": {"provider": request.provider_id},
                "stream": {
                    "engaged": True,
                    "chunk_count": 2,
                    "native_stream": False,
                    "partial_output": "hello world",
                    "chunks": [
                        {"index": 0, "text": "hello ", "is_final": False, "native_stream": False},
                        {"index": 1, "text": "world", "is_final": True, "native_stream": False},
                    ],
                },
            },
            latency_ms=12,
            tokens_used=7,
        )


class _IdentityRuntime:
    def __init__(self):
        self.event_emitter = ExecutionEventEmitter(event_file=None)
        self.execution_id = "runtime-default"
        self.trigger_source = DEFAULT_TRIGGER_SOURCE
        self.automation_id = None

    def set_execution_identity(self, *, execution_id: str, trigger_source: str, automation_id: Optional[str] = None):
        self.execution_id = execution_id
        self.trigger_source = trigger_source
        self.automation_id = automation_id

    def set_execution_id(self, execution_id):
        self.execution_id = execution_id
        self.trigger_source = DEFAULT_TRIGGER_SOURCE
        self.automation_id = None

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
        class Result:
            def __init__(self, output):
                self.output = output

        return Result(output=f"done:{config_id}")


@dataclass
class _ResponseAdapter:
    name: str = "streaming_adapter"

    def build_payload(self, req) -> Dict[str, Any]:
        return {"prompt": req.prompt}

    def send(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return {"output_text": "fallback text", "usage": {"output_tokens": 3}}

    def stream(self, payload: Dict[str, Any]):
        raw = self.send(payload)
        yield {
            "text": "fallback text",
            "raw": raw,
            "tokens_used": 3,
            "is_final": True,
            "native_stream": False,
        }

    def parse(self, raw: Dict[str, Any]) -> Tuple[str, Optional[int]]:
        return raw["output_text"], raw["usage"]["output_tokens"]

    def fingerprint_components(self) -> Dict[str, Any]:
        return {"adapter": self.name}


def test_execution_event_defaults_include_trigger_identity() -> None:
    event = ExecutionEvent.now("execution_started", execution_id="run-1")

    assert event.trigger_source == "manual"
    assert event.automation_id is None
    payload = event.to_dict()
    assert payload["trigger_source"] == "manual"
    assert payload["automation_id"] is None


def test_status_taxonomy_and_trigger_normalization_are_stable() -> None:
    assert normalize_trigger_source("AUTOMATION") == "automation"
    assert normalize_trigger_source("unknown-value") == "manual"
    assert LaunchStatus.STARTED.value == "started"
    assert ExecutionStatus.COMPLETED.value == "completed"
    assert StreamingStatus.COMPLETED.value == "completed"


def test_openai_and_anthropic_adapters_expose_safe_stream_fallback() -> None:
    openai = OpenAICompatibleAdapter(
        config=AdapterConfig(api_key="k", model="m", endpoint="https://example.invalid"),
        mode="responses",
    )
    openai.send = lambda payload: {"output_text": "hello", "usage": {"output_tokens": 4}}  # type: ignore[method-assign]
    openai_chunks = list(openai.stream({"prompt": "x"}))
    assert openai_chunks[0]["text"] == "hello"
    assert openai_chunks[0]["native_stream"] is False

    anthropic = AnthropicMessagesAdapter(
        config=AdapterConfig(api_key="k", model="m", endpoint="https://example.invalid")
    )
    anthropic.send = lambda payload: {"content": [{"text": "hi there"}], "usage": {"output_tokens": 2}}  # type: ignore[method-assign]
    anthropic_chunks = list(anthropic.stream({"prompt": "x"}))
    assert anthropic_chunks[0]["text"] == "hi there"
    assert anthropic_chunks[0]["native_stream"] is False


def test_node_runtime_emits_stream_lifecycle_when_streaming_is_requested() -> None:
    executor = _StreamingProviderExecutor()
    runtime = NodeExecutionRuntime(provider_executor=executor, plugin_registry={}, event_emitter=ExecutionEventEmitter(event_file=None))
    runtime.set_execution_identity(execution_id="run-stream", trigger_source="automation", automation_id="auto-1")

    config = {
        "config_id": "n1",
        "node_id": "n1",
        "provider": {"provider_id": "p1"},
        "runtime_config": {"return_raw_output": True, "stream": True},
    }

    result = runtime.execute(config, {})
    assert result.output == "hello world"
    assert executor.requests[0].options["stream"] is True

    events = runtime.get_execution_events()
    event_types = [event.type for event in events]
    assert event_types[:6] == [
        "node_started",
        "stream_started",
        "token_chunk",
        "token_chunk",
        "partial_output",
        "stream_completed",
    ]
    assert "final_output" in event_types
    assert event_types[-1] == "node_completed"
    assert all(event.trigger_source == "automation" for event in events)
    assert all(event.automation_id == "auto-1" for event in events)
    assert events[-2].payload["output"] == "hello world"


def test_circuit_runner_propagates_trigger_identity_into_runtime_events() -> None:
    runtime = _IdentityRuntime()
    runner = CircuitRunner(runtime, _DummyRegistry())

    circuit = {
        "id": "sample-circuit",
        "nodes": [
            {"id": "node_a", "execution_config_ref": "cfg.ok", "depends_on": []},
        ],
    }

    result = runner.execute(circuit, {}, trigger_source="automation", automation_id="auto-42")
    assert result["node_a"] == "done:cfg.ok"

    events = runtime.event_emitter.get_events()
    assert [event.type for event in events] == ["execution_started", "execution_completed"]
    assert all(event.trigger_source == "automation" for event in events)
    assert all(event.automation_id == "auto-42" for event in events)
    assert events[0].payload["trigger_source"] == "automation"
    assert events[1].payload["automation_id"] == "auto-42"
