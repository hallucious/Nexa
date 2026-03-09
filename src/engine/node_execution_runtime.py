from __future__ import annotations

from dataclasses import asdict, dataclass, field, is_dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
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
    Node execution runtime with a unified execution-plan model.

    Supported inputs:
    - ExecutionConfig-like dicts / models
    - legacy prompt nodes, which are normalized into an internal execution plan
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

    def _render_prompt(self, prompt_ref: str, context: Dict[str, Any], *, render_mode: str = "step123") -> str:
        if render_mode == "legacy_format":
            return prompt_ref.format(**context) if prompt_ref else ""
        # deterministic minimal renderer for Step123
        return f"{prompt_ref}:{context}"

    def _run_validation(self, rule: str, context: Dict[str, Any]):
        if rule == "require_answer" and "answer" not in context:
            raise ValueError("validation failed: answer missing")

    def _resolve_plugin_callable(self, plugin_id: str):
        if plugin_id not in self.plugin_registry:
            raise ValueError(f"Unknown plugin: {plugin_id}")
        return self.plugin_registry[plugin_id]

    def _normalize_node_payload(self, node: Any) -> Dict[str, Any]:
        if isinstance(node, dict):
            return dict(node)

        if is_dataclass(node) and not isinstance(node, type):
            payload = asdict(node)
            if isinstance(payload, dict):
                return payload

        if hasattr(node, "__dict__"):
            payload = {
                key: value
                for key, value in vars(node).items()
                if not key.startswith("_")
            }
            if isinstance(payload, dict) and payload:
                return payload

        raise TypeError(f"node must be dict-like or dataclass-backed object, got {type(node).__name__}")

    def _looks_like_execution_config(self, node: Dict[str, Any]) -> bool:
        return (
            "config_id" in node
            or "execution_config_ref" in node
            or "prompt_ref" in node
            or "provider_ref" in node
            or "validation_rules" in node
            or "output_mapping" in node
        ) and "id" not in node

    def _coerce_node_to_execution_plan(self, normalized_node: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        if self._looks_like_execution_config(normalized_node):
            return normalized_node, {}

        node_id = normalized_node.get("id", "unknown")
        legacy_pre_plugins = self.pre_plugins
        legacy_post_plugins = self.post_plugins

        if "pre_plugins" in normalized_node or "post_plugins" in normalized_node:
            try:
                from src.engine.plugin_loader import load_plugins
                legacy_pre_plugins = load_plugins(normalized_node.get("pre_plugins", []))
                legacy_post_plugins = load_plugins(normalized_node.get("post_plugins", []))
            except Exception:
                legacy_pre_plugins = self.pre_plugins
                legacy_post_plugins = self.post_plugins

        plan = {
            "config_id": f"legacy.{node_id}",
            "node_id": node_id,
            "prompt_ref": normalized_node.get("prompt", ""),
            "provider_ref": "__legacy_provider__",
            "pre_plugins": [],
            "post_plugins": [],
            "validation_rules": [],
            "output_mapping": {},
            "runtime_config": {
                "prompt_render_mode": "legacy_format",
                "provider_call_mode": "legacy_prompt_only",
                "return_raw_output": True,
                "emit_primary_artifact": True,
                "write_observability": True,
                "legacy_node_id": node_id,
                "legacy_plugin_mode": True,
            },
        }
        extras = {
            "legacy_pre_plugins": legacy_pre_plugins,
            "legacy_post_plugins": legacy_post_plugins,
        }
        return plan, extras

    def _execute_execution_config(
        self,
        config: Dict[str, Any],
        state: Dict[str, Any],
        *,
        plan_extras: Optional[Dict[str, Any]] = None,
    ) -> NodeResult:
        runtime_config = dict(config.get("runtime_config") or {})
        plan_extras = dict(plan_extras or {})

        node_id = (
            runtime_config.get("legacy_node_id")
            or config.get("node_id")
            or config.get("config_id")
            or "execution_config"
        )
        trace = NodeTrace()
        artifacts: List[Artifact] = []
        context = dict(state)

        def pre_stage():
            trace.events.append("pre_plugins")
            if runtime_config.get("legacy_plugin_mode"):
                self._run_plugins(
                    plan_extras.get("legacy_pre_plugins", []),
                    node_id,
                    context,
                    "pre",
                    trace,
                    artifacts,
                )
                return

            plugin_ids = config.get("pre_plugins", [])
            if not plugin_ids:
                trace.plugin_trace["pre"].append("noop_pre_plugin")
                return

            for plugin_id in plugin_ids:
                trace.plugin_trace["pre"].append(plugin_id)
                result = self._resolve_plugin_callable(plugin_id)(context=context)
                if isinstance(result, dict):
                    context.update(result)

        self._measure("pre_plugins", pre_stage, trace)

        prompt = None

        def render_stage():
            trace.events.append("prompt_render")
            nonlocal prompt
            if config.get("prompt_ref") is not None:
                prompt = self._render_prompt(
                    config.get("prompt_ref", ""),
                    context,
                    render_mode=runtime_config.get("prompt_render_mode", "step123"),
                )
            return prompt or ""

        self._measure("prompt_render", render_stage, trace)

        def provider_stage():
            trace.events.append("provider_execute")
            provider_mode = runtime_config.get("provider_call_mode", "step123")
            if provider_mode == "legacy_prompt_only":
                return self._provider_call_legacy(prompt or "")
            if config.get("provider_ref") and self.provider_execution:
                return self._provider_call_step123(prompt, context)
            return {}

        provider_result = self._measure("provider_execute", provider_stage, trace) or {}
        if isinstance(provider_result, dict):
            trace.provider_trace = provider_result.get("trace")
            output = provider_result.get("output")
            context.update(provider_result)
        else:
            output = provider_result

        if runtime_config.get("emit_primary_artifact"):
            artifacts.append(
                Artifact(
                    type="provider_output",
                    name="primary_output",
                    data=output,
                    producer_node=node_id,
                    timestamp_ms=time.time() * 1000.0,
                )
            )
            extra_artifacts = provider_result.get("artifacts", []) if isinstance(provider_result, dict) else []
            for artifact in extra_artifacts:
                if isinstance(artifact, Artifact):
                    artifacts.append(artifact)

        def post_stage():
            trace.events.append("post_plugins")
            if runtime_config.get("legacy_plugin_mode"):
                self._run_plugins(
                    plan_extras.get("legacy_post_plugins", []),
                    node_id,
                    context,
                    "post",
                    trace,
                    artifacts,
                )
                return

            plugin_ids = config.get("post_plugins", [])
            if not plugin_ids:
                trace.plugin_trace["post"].append("noop_post_plugin")
                return

            for plugin_id in plugin_ids:
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

        mapping = config.get("output_mapping", {})
        if mapping:
            final_output: Any = {out_key: context.get(ctx_key) for out_key, ctx_key in mapping.items()}
        elif runtime_config.get("return_raw_output"):
            final_output = output
        else:
            final_output = {}

        result = NodeResult(
            node_id=node_id,
            output=final_output,
            artifacts=artifacts,
            trace=trace,
        )

        if runtime_config.get("write_observability"):
            self._write_observability(node_id, trace)
        return result

    def execute(self, node: Dict[str, Any], state: Dict[str, Any]) -> NodeResult:
        normalized_node = self._normalize_node_payload(node)
        execution_plan, plan_extras = self._coerce_node_to_execution_plan(normalized_node)
        return self._execute_execution_config(execution_plan, state, plan_extras=plan_extras)
