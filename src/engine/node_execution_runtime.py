
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import time
import json
from pathlib import Path

from src.platform.plugin_result import normalize_plugin_result


@dataclass
class Artifact:
    type: str
    name: str
    data: Any
    metadata: Dict[str, Any] = field(default_factory=dict)
    producer_node: Optional[str] = None
    timestamp_ms: Optional[float] = None


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
    artifacts: List[Artifact] = field(default_factory=list)
    trace: NodeTrace = field(default_factory=NodeTrace)


class NodeExecutionRuntime:
    """Node execution runtime with artifact schema + append-only artifact lifecycle + plugin artifacts (Step111)."""

    def __init__(
        self,
        provider_execution,
        pre_plugins=None,
        post_plugins=None,
        observability_file: str = "OBSERVABILITY.jsonl",
    ):
        self.provider_execution = provider_execution
        self.pre_plugins = pre_plugins or []
        self.post_plugins = post_plugins or []
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

    def _run_plugins(self, plugins, node_id, state, stage, trace, artifacts):
        """Run plugins and append their emitted artifacts (append-only).

        Backward-compat: when no plugins are configured, record explicit noop markers
        so earlier contracts (Step106) remain valid.
        """
        if not plugins:
            if stage == "pre":
                trace.plugin_trace["pre"].append("noop_pre_plugin")
            elif stage == "post":
                trace.plugin_trace["post"].append("noop_post_plugin")
            return

        for plugin in plugins:
            trace.plugin_trace[stage].append(plugin.__class__.__name__)
            result = normalize_plugin_result(plugin.run(node_id=node_id, state=state))

            for a in result.artifacts:
                if isinstance(a, Artifact):
                    artifacts.append(a)

    def execute(self, node: Dict[str, Any], state: Dict[str, Any]) -> NodeResult:
        node_id = node.get("id", "unknown")
        trace = NodeTrace()
        collected_artifacts: List[Artifact] = []

        # PRE PLUGINS
        def pre_stage():
            trace.events.append("pre_plugins")
            self._run_plugins(self.pre_plugins, node_id, state, "pre", trace, collected_artifacts)

        self._measure("pre_plugins", pre_stage, trace)

        # PROMPT RENDER
        def render_stage():
            trace.events.append("prompt_render")
            prompt_template = node.get("prompt", "")
            return prompt_template.format(**state) if prompt_template else ""

        rendered_prompt = self._measure("prompt_render", render_stage, trace)

        # PROVIDER EXECUTION
        def provider_stage():
            trace.events.append("provider_execute")
            return self.provider_execution.execute(rendered_prompt)

        provider_result = self._measure("provider_execute", provider_stage, trace)
        trace.provider_trace = provider_result.get("trace")

        output = provider_result.get("output")

        primary_artifact = Artifact(
            type="provider_output",
            name="primary_output",
            data=output,
            producer_node=node_id,
            timestamp_ms=time.time() * 1000.0,
        )
        collected_artifacts.append(primary_artifact)

        # provider artifacts
        extra_artifacts = provider_result.get("artifacts", [])
        for a in extra_artifacts:
            if isinstance(a, Artifact):
                collected_artifacts.append(a)

        # POST PLUGINS
        def post_stage():
            trace.events.append("post_plugins")
            self._run_plugins(self.post_plugins, node_id, state, "post", trace, collected_artifacts)

        self._measure("post_plugins", post_stage, trace)

        result = NodeResult(
            node_id=node_id,
            output=output,
            artifacts=collected_artifacts,
            trace=trace,
        )

        self._write_observability(node_id, trace)
        return result
