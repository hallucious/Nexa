from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional
import json
import time

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
    """
    Node execution runtime with:
    - legacy node execution contract (Step111+)
    - Step123 slot-pipeline execution for ExecutionConfig-like dict input
    """

    def __init__(
        self,
        provider_execution,
        pre_plugins=None,
        post_plugins=None,
        observability_file: str = "OBSERVABILITY.jsonl",
        plugin_registry: Optional[Dict[str, Any]] = None,
    ):
        self.provider_execution = provider_execution
        self.pre_plugins = pre_plugins or []
        self.post_plugins = post_plugins or []
        self.observability_file = Path(observability_file)
        self.plugin_registry = plugin_registry or {}

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

    def _provider_call_legacy(self, rendered_prompt: str):
        if hasattr(self.provider_execution, "execute"):
            return self.provider_execution.execute(rendered_prompt)
        return self.provider_execution(rendered_prompt)

    def _provider_call_step123(self, prompt: Optional[str], context: Dict[str, Any]):
        if hasattr(self.provider_execution, "execute"):
            return self.provider_execution.execute(prompt)
        return self.provider_execution(prompt=prompt, context=context)

    def _render_prompt(self, prompt_ref: str, context: Dict[str, Any]) -> str:
        # deterministic minimal renderer for Step123
        return f"{prompt_ref}:{context}"

    def _run_validation(self, rule: str, context: Dict[str, Any]):
        if rule == "require_answer" and "answer" not in context:
            raise ValueError("validation failed: answer missing")

    def _resolve_plugin_callable(self, plugin_id: str):
        if plugin_id not in self.plugin_registry:
            raise ValueError(f"Unknown plugin: {plugin_id}")
        return self.plugin_registry[plugin_id]

    def _looks_like_execution_config(self, node: Dict[str, Any]) -> bool:
        return (
            "config_id" in node
            or "execution_config_ref" in node
            or "prompt_ref" in node
            or "provider_ref" in node
            or "validation_rules" in node
            or "output_mapping" in node
        ) and "id" not in node

    def _execute_execution_config(self, config: Dict[str, Any], state: Dict[str, Any]) -> NodeResult:
        node_id = config.get("node_id") or config.get("config_id") or "execution_config"
        trace = NodeTrace()
        artifacts: List[Artifact] = []
        context = dict(state)

        def pre_stage():
            trace.events.append("pre_plugins")
            for plugin_id in config.get("pre_plugins", []):
                trace.plugin_trace["pre"].append(plugin_id)
                result = self._resolve_plugin_callable(plugin_id)(context=context)
                if isinstance(result, dict):
                    context.update(result)

        self._measure("pre_plugins", pre_stage, trace)

        prompt = None

        def render_stage():
            trace.events.append("prompt_render")
            nonlocal prompt
            if config.get("prompt_ref"):
                prompt = self._render_prompt(config["prompt_ref"], context)
            return prompt or ""

        self._measure("prompt_render", render_stage, trace)

        def provider_stage():
            trace.events.append("provider_execute")
            if config.get("provider_ref") and self.provider_execution:
                return self._provider_call_step123(prompt, context)
            return {}

        provider_result = self._measure("provider_execute", provider_stage, trace) or {}
        if isinstance(provider_result, dict):
            trace.provider_trace = provider_result.get("trace")
            output = provider_result.get("output")
            # Step123 convenience: provider may return plain key/values instead of nested output
            if output is None:
                context.update(provider_result)
            else:
                context.update(provider_result)
        else:
            output = provider_result

        def post_stage():
            trace.events.append("post_plugins")
            for plugin_id in config.get("post_plugins", []):
                trace.plugin_trace["post"].append(plugin_id)
                result = self._resolve_plugin_callable(plugin_id)(context=context)
                if isinstance(result, dict):
                    context.update(result)

        self._measure("post_plugins", post_stage, trace)

        def validation_stage():
            trace.events.append("validation")
            for rule in config.get("validation_rules", []):
                self._run_validation(rule, context)

        self._measure("validation", validation_stage, trace)

        mapped_output: Dict[str, Any] = {}
        mapping = config.get("output_mapping", {})
        for out_key, ctx_key in mapping.items():
            mapped_output[out_key] = context.get(ctx_key)

        return NodeResult(
            node_id=node_id,
            output=mapped_output,
            artifacts=artifacts,
            trace=trace,
        )

    def _execute_legacy_node(self, node: Dict[str, Any], state: Dict[str, Any]) -> NodeResult:
        node_id = node.get("id", "unknown")

        pre_plugins = self.pre_plugins
        post_plugins = self.post_plugins

        if "pre_plugins" in node or "post_plugins" in node:
            try:
                from src.engine.plugin_loader import load_plugins
                pre_plugins = load_plugins(node.get("pre_plugins", []))
                post_plugins = load_plugins(node.get("post_plugins", []))
            except Exception:
                pre_plugins = self.pre_plugins
                post_plugins = self.post_plugins

        trace = NodeTrace()
        collected_artifacts: List[Artifact] = []

        def pre_stage():
            trace.events.append("pre_plugins")
            self._run_plugins(pre_plugins, node_id, state, "pre", trace, collected_artifacts)

        self._measure("pre_plugins", pre_stage, trace)

        def render_stage():
            trace.events.append("prompt_render")
            prompt_template = node.get("prompt", "")
            return prompt_template.format(**state) if prompt_template else ""

        rendered_prompt = self._measure("prompt_render", render_stage, trace)

        def provider_stage():
            trace.events.append("provider_execute")
            return self._provider_call_legacy(rendered_prompt)

        provider_result = self._measure("provider_execute", provider_stage, trace)
        trace.provider_trace = provider_result.get("trace") if isinstance(provider_result, dict) else None

        output = provider_result.get("output") if isinstance(provider_result, dict) else provider_result

        primary_artifact = Artifact(
            type="provider_output",
            name="primary_output",
            data=output,
            producer_node=node_id,
            timestamp_ms=time.time() * 1000.0,
        )
        collected_artifacts.append(primary_artifact)

        extra_artifacts = provider_result.get("artifacts", []) if isinstance(provider_result, dict) else []
        for a in extra_artifacts:
            if isinstance(a, Artifact):
                collected_artifacts.append(a)

        def post_stage():
            trace.events.append("post_plugins")
            self._run_plugins(post_plugins, node_id, state, "post", trace, collected_artifacts)

        self._measure("post_plugins", post_stage, trace)

        result = NodeResult(
            node_id=node_id,
            output=output,
            artifacts=collected_artifacts,
            trace=trace,
        )

        self._write_observability(node_id, trace)
        return result

    def execute(self, node: Dict[str, Any], state: Dict[str, Any]) -> NodeResult:
        if self._looks_like_execution_config(node):
            return self._execute_execution_config(node, state)
        return self._execute_legacy_node(node, state)
