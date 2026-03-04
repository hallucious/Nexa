from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import time
import json
from pathlib import Path


@dataclass
class NodeTrace:
    events: List[str] = field(default_factory=list)
    timings_ms: Dict[str, float] = field(default_factory=dict)
    provider_trace: Optional[Any] = None
    plugin_trace: Dict[str, List[str]] = field(default_factory=lambda: {"pre": [], "post": []})


@dataclass
class NodeResult:
    node_id: str
    output: Any
    artifacts: List[Any] = field(default_factory=list)
    trace: NodeTrace = field(default_factory=NodeTrace)


class NodeExecutionRuntime:
    """Node execution runtime with observability logging (Step107)."""

    def __init__(self, provider_execution, observability_file: str = "OBSERVABILITY.jsonl"):
        self.provider_execution = provider_execution
        self.observability_file = Path(observability_file)

    def _measure(self, name: str, fn, trace: NodeTrace):
        start = time.time()
        result = fn()
        end = time.time()
        trace.timings_ms[name] = (end - start) * 1000.0
        return result

    def _write_observability(self, node_id: str, trace: NodeTrace):
        record = {
            "node_id": node_id,
            "events": trace.events,
            "timings_ms": trace.timings_ms,
            "provider": trace.provider_trace.get("provider") if isinstance(trace.provider_trace, dict) else None,
        }
        with self.observability_file.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")

    def execute(self, node: Dict[str, Any], state: Dict[str, Any]) -> NodeResult:
        node_id = node.get("id", "unknown")
        trace = NodeTrace()

        def pre_stage():
            trace.events.append("pre_plugins")
            trace.plugin_trace["pre"].append("noop_pre_plugin")

        self._measure("pre_plugins", pre_stage, trace)

        def render_stage():
            trace.events.append("prompt_render")
            prompt_template = node.get("prompt", "")
            return prompt_template.format(**state) if prompt_template else ""

        rendered_prompt = self._measure("prompt_render", render_stage, trace)

        def provider_stage():
            trace.events.append("provider_execute")
            return self.provider_execution.execute(rendered_prompt)

        provider_result = self._measure("provider_execute", provider_stage, trace)
        trace.provider_trace = provider_result.get("trace")

        output = provider_result.get("output")

        def post_stage():
            trace.events.append("post_plugins")
            trace.plugin_trace["post"].append("noop_post_plugin")

        self._measure("post_plugins", post_stage, trace)

        result = NodeResult(
            node_id=node_id,
            output=output,
            artifacts=[],
            trace=trace,
        )

        self._write_observability(node_id, trace)
        return result