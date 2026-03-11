from __future__ import annotations

from dataclasses import asdict, dataclass, field, is_dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import json
import time

from src.platform.plugin_result import PluginResult, normalize_plugin_result
from src.contracts.provider_contract import ProviderRequest, ProviderResult
from src.engine.compiled_resource_graph import (
    CompiledResourceGraph,
    compile_execution_config_to_graph,
)
from src.engine.final_output_resolver import (
    FinalOutputResolverError,
    resolve_final_output,
)
from src.engine.graph_scheduler import GraphScheduler


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
    Step135+ runtime coordinator.

    Runtime responsibilities:
    1. normalize input into execution config
    2. compile execution config into compiled resource graph
    3. execute graph through GraphScheduler
    4. resolve deterministic final output

    Compatibility note:
    - legacy pre/post plugin execution path is removed
    - but pre/post trace markers are preserved for existing observability contracts
    """

    def __init__(
        self,
        provider_executor,
        pre_plugins=None,
        post_plugins=None,
        observability_file: str = "OBSERVABILITY.jsonl",
        plugin_registry: Optional[Dict[str, Any]] = None,
    ):
        self.provider_executor = provider_executor
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

    def _record_pre_stage_trace(self, trace: NodeTrace):
        trace.events.append("pre_plugins")
        trace.plugin_trace["pre"].append("noop_pre_plugin")

    def _record_post_stage_trace(self, trace: NodeTrace, config: Dict[str, Any]):
        trace.events.append("post_plugins")
        if not config.get("plugins"):
            trace.plugin_trace["post"].append("noop_post_plugin")

    def _provider_call(self, provider_ref: str, prompt: str, context: Dict[str, Any]) -> Dict[str, Any]:
        request = ProviderRequest(
            provider_id=provider_ref,
            prompt=prompt,
            context=context,
            options={},
            metadata={},
        )
        result = self.provider_executor.execute(request)
        if not isinstance(result, ProviderResult):
            raise TypeError("ProviderExecutor must return ProviderResult")
        if result.error is not None:
            raise RuntimeError(result.error.message)

        payload: Dict[str, Any] = {
            "output": result.output,
            "trace": result.trace,
            "artifacts": list(result.artifacts),
        }
        if result.output is None and isinstance(result.structured, dict):
            payload.update(result.structured)
        elif isinstance(result.structured, dict):
            payload["structured"] = result.structured
        return payload

    def _render_prompt(self, prompt_ref: str, context: Dict[str, Any], *, render_mode: str = "step123") -> str:
        if render_mode == "legacy_format":
            return prompt_ref.format(**context) if prompt_ref else ""
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
            or "prompt" in node
            or "provider" in node
            or "plugins" in node
            or "validation_rules" in node
            or "output_mapping" in node
        ) and "id" not in node

    def _coerce_node_to_execution_plan(self, normalized_node: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        if self._looks_like_execution_config(normalized_node):
            plan = dict(normalized_node)
            runtime_config = dict(plan.get("runtime_config") or {})
            runtime_config.pop("legacy_plugin_mode", None)
            runtime_config.pop("emit_primary_artifact", None)
            runtime_config.setdefault("write_observability", True)
            plan["runtime_config"] = runtime_config
            return plan, {}

        node_id = normalized_node.get("id", "unknown")
        plan = {
            "config_id": f"legacy.{node_id}",
            "node_id": node_id,
            "prompt_ref": normalized_node.get("prompt", ""),
            "provider_ref": "__legacy_provider__",
            "validation_rules": [],
            "output_mapping": {},
            "runtime_config": {
                "prompt_render_mode": "legacy_format",
                "return_raw_output": True,
                "write_observability": True,
                "legacy_node_id": node_id,
            },
        }
        return plan, {}

    def _build_flat_context(self, state: Dict[str, Any]) -> Dict[str, Any]:
        flat: Dict[str, Any] = dict(state)
        for key, value in state.items():
            flat[f"input.{key}"] = value
        return flat

    def _build_compat_context(self, flat_context: Dict[str, Any]) -> Dict[str, Any]:
        compat: Dict[str, Any] = {key: value for key, value in flat_context.items() if "." not in key}
        nested: Dict[str, Any] = {
            "input": {},
            "prompt": {},
            "provider": {},
            "plugin": {},
            "plugins": {},
            "output": {},
            "system": {},
        }
        for key, value in flat_context.items():
            parts = key.split(".")
            if len(parts) < 2:
                continue
            domain = parts[0]
            normalized_domain = "plugins" if domain == "plugin" else domain
            if normalized_domain not in nested:
                continue
            current: Dict[str, Any] = nested[normalized_domain]
            for part in parts[1:-1]:
                current = current.setdefault(part, {})
            current[parts[-1]] = value
            compat[key] = value
        compat.update(nested)
        return compat

    def _normalize_config_for_compilation(self, config: Dict[str, Any]) -> Dict[str, Any]:
        compiled: Dict[str, Any] = {}

        prompt_config = config.get("prompt")
        if isinstance(prompt_config, dict):
            compiled["prompt"] = dict(prompt_config)
        elif config.get("prompt_ref") is not None:
            compiled["prompt"] = {
                "prompt_id": str(config.get("prompt_ref") or "prompt"),
                "inputs": dict((config.get("prompt_inputs") or {})),
            }

        provider_config = config.get("provider")
        if isinstance(provider_config, dict):
            compiled["provider"] = dict(provider_config)
        elif config.get("provider_ref") is not None:
            provider_inputs = dict(config.get("provider_inputs") or {})
            compiled["provider"] = {
                "provider_id": str(config.get("provider_ref") or "provider"),
            }
            if provider_inputs:
                compiled["provider"]["inputs"] = provider_inputs

        plugin_configs = config.get("plugins")
        if isinstance(plugin_configs, list):
            compiled["plugins"] = [dict(item) for item in plugin_configs]
        else:
            compiled["plugins"] = []

        return compiled

    def _compile_execution_plan(self, config: Dict[str, Any]) -> Optional[CompiledResourceGraph]:
        normalized = self._normalize_config_for_compilation(config)
        if not normalized:
            return None
        return compile_execution_config_to_graph(normalized)

    def _resolve_graph_plugin_inputs(self, plugin_config: Dict[str, Any], flat_context: Dict[str, Any]) -> Dict[str, Any]:
        inputs = plugin_config.get("inputs") or {}
        if not inputs:
            return {}
        return {name: flat_context.get(context_key) for name, context_key in inputs.items()}

    def _extract_plugin_output_mapping(self, plugin_result: PluginResult, write_keys: List[str]) -> Dict[str, Any]:
        if len(write_keys) == 1 and write_keys[0].endswith(".result"):
            output = plugin_result.output
            if isinstance(output, dict) and set(output.keys()) == {"result"}:
                output = output["result"]
            return {write_keys[0]: output}

        output = plugin_result.output
        if isinstance(output, dict):
            mapped: Dict[str, Any] = {}
            for write_key in write_keys:
                field_name = write_key.split(".")[-1]
                mapped[write_key] = output.get(field_name)
            return mapped

        if len(write_keys) == 1:
            return {write_keys[0]: output}

        raise ValueError("plugin output must be dict when multiple output fields are declared")

    def _resolve_provider_prompt(
        self,
        provider_config: Dict[str, Any],
        config: Dict[str, Any],
        flat_context: Dict[str, Any],
    ) -> str:
        input_mapping = provider_config.get("inputs") or {}
        if input_mapping:
            resolved_inputs = {
                name: flat_context.get(context_key)
                for name, context_key in input_mapping.items()
            }
            if len(resolved_inputs) == 1:
                only_value = next(iter(resolved_inputs.values()))
                return "" if only_value is None else str(only_value)
            return json.dumps(resolved_inputs, ensure_ascii=False, sort_keys=True)

        prompt_config = config.get("prompt")
        if isinstance(prompt_config, dict):
            prompt_id = prompt_config.get("prompt_id")
            if isinstance(prompt_id, str):
                return str(flat_context.get(f"prompt.{prompt_id}.rendered", ""))

        prompt_ref = config.get("prompt_ref")
        if prompt_ref is not None:
            return str(flat_context.get(f"prompt.{prompt_ref}.rendered", ""))

        return ""

    def _execute_resource_from_graph(
        self,
        resource_id: str,
        config: Dict[str, Any],
        graph: CompiledResourceGraph,
        flat_context: Dict[str, Any],
        trace: NodeTrace,
        artifacts: List[Artifact],
        prompt_configs: Dict[str, Dict[str, Any]],
        provider_configs: Dict[str, Dict[str, Any]],
        plugin_configs: Dict[str, Dict[str, Any]],
        state_holder: Dict[str, Any],
    ) -> Any:
        resource = graph.resources[resource_id]

        if resource.type == "prompt":
            prompt_cfg = prompt_configs[resource_id]
            prompt_ref = config.get("prompt_ref")
            if prompt_ref is None:
                prompt_ref = prompt_cfg.get("prompt_id", "")
            compat_context = self._build_compat_context(flat_context)

            def render_stage():
                trace.events.append("prompt_render")
                rendered = self._render_prompt(
                    str(prompt_ref or ""),
                    compat_context,
                    render_mode=config.get("runtime_config", {}).get("prompt_render_mode", "step123"),
                )
                write_key = next(iter(resource.writes))
                flat_context[write_key] = rendered
                return rendered

            return self._measure("prompt_render", render_stage, trace)

        if resource.type == "provider":
            provider_cfg = provider_configs[resource_id]
            provider_id = provider_cfg["provider_id"]

            def provider_stage():
                trace.events.append("provider_execute")
                compat_context = self._build_compat_context(flat_context)
                prompt = self._resolve_provider_prompt(provider_cfg, config, flat_context)
                return self._provider_call(provider_id, prompt, compat_context)

            provider_result = self._measure("provider_execute", provider_stage, trace) or {}
            if isinstance(provider_result, dict):
                trace.provider_trace = provider_result.get("trace")
                state_holder["last_provider_output"] = provider_result.get("output")
                flat_context[f"provider.{provider_id}.output"] = provider_result.get("output")
                for key, value in provider_result.items():
                    if key in {"output", "trace", "artifacts"}:
                        continue
                    flat_context[f"provider.{provider_id}.{key}"] = value
                    flat_context[key] = value
            else:
                state_holder["last_provider_output"] = provider_result
                flat_context[f"provider.{provider_id}.output"] = provider_result

            artifacts.append(
                Artifact(
                    type="provider_output",
                    name="primary_output",
                    data=state_holder["last_provider_output"],
                    producer_node=config.get("node_id") or config.get("config_id"),
                    timestamp_ms=time.time() * 1000.0,
                )
            )
            if isinstance(provider_result, dict):
                for artifact in provider_result.get("artifacts", []):
                    if isinstance(artifact, Artifact):
                        artifacts.append(artifact)
            return provider_result

        if resource.type == "plugin":
            plugin_cfg = plugin_configs[resource_id]
            plugin_id = plugin_cfg["plugin_id"]
            plugin_callable = self._resolve_plugin_callable(plugin_id)
            bound_inputs = self._resolve_graph_plugin_inputs(plugin_cfg, flat_context)
            trace.plugin_trace["post"].append(plugin_id)

            def plugin_stage():
                trace.events.append(f"plugin_execute:{plugin_id}")
                result = plugin_callable(**bound_inputs)
                return normalize_plugin_result(result)

            plugin_result = self._measure(f"plugin_execute:{plugin_id}", plugin_stage, trace)
            for write_key, value in self._extract_plugin_output_mapping(plugin_result, sorted(resource.writes)).items():
                flat_context[write_key] = value
            for artifact in plugin_result.artifacts:
                if isinstance(artifact, Artifact):
                    artifacts.append(artifact)
            return plugin_result

        raise ValueError(f"Unsupported resource type: {resource.type}")

    def _execute_compiled_graph(
        self,
        config: Dict[str, Any],
        graph: CompiledResourceGraph,
        flat_context: Dict[str, Any],
        trace: NodeTrace,
        artifacts: List[Artifact],
    ) -> Any:
        compiled_config = self._normalize_config_for_compilation(config)
        prompt_configs = {
            f"prompt.{item['prompt_id']}": item
            for item in [compiled_config.get("prompt")]
            if isinstance(item, dict) and isinstance(item.get("prompt_id"), str)
        }
        provider_configs = {
            f"provider.{item['provider_id']}": item
            for item in [compiled_config.get("provider")]
            if isinstance(item, dict) and isinstance(item.get("provider_id"), str)
        }
        plugin_configs = {}
        for plugin_cfg in compiled_config.get("plugins", []):
            plugin_id = plugin_cfg.get("plugin_id")
            instance_id = plugin_cfg.get("id") or plugin_id
            if isinstance(instance_id, str):
                plugin_configs[f"plugin.{instance_id}"] = plugin_cfg

        scheduler = GraphScheduler(graph)
        state_holder = {"last_provider_output": None}

        def resource_executor(resource_id: str):
            return self._execute_resource_from_graph(
                resource_id=resource_id,
                config=config,
                graph=graph,
                flat_context=flat_context,
                trace=trace,
                artifacts=artifacts,
                prompt_configs=prompt_configs,
                provider_configs=provider_configs,
                plugin_configs=plugin_configs,
                state_holder=state_holder,
            )

        execution_result = scheduler.execute(resource_executor)
        for wave in execution_result.waves:
            trace.events.append(f"wave:{wave.index}:{','.join(wave.resource_ids)}")
        return state_holder["last_provider_output"]

    def _resolve_final_output(
        self,
        config: Dict[str, Any],
        graph: Optional[CompiledResourceGraph],
        flat_context: Dict[str, Any],
        trace: NodeTrace,
        provider_output: Any,
    ) -> Any:
        mapping = config.get("output_mapping", {})
        runtime_config = dict(config.get("runtime_config") or {})

        if mapping:
            final_output: Any = {out_key: flat_context.get(ctx_key) for out_key, ctx_key in mapping.items()}
            flat_context.update({f"output.{k}": v for k, v in final_output.items()})
            trace.events.append("final_output:explicit_mapping")
            return final_output

        if runtime_config.get("return_raw_output"):
            flat_context["output.value"] = provider_output
            flat_context["output.source"] = "__raw_provider_output__"
            flat_context["output.candidates"] = []
            trace.events.append("final_output:raw_provider_output")
            return provider_output

        if graph is None:
            trace.events.append("final_output:empty")
            return {}

        resolved = resolve_final_output(graph, flat_context)
        flat_context["output.value"] = resolved.value
        flat_context["output.source"] = resolved.source_key
        flat_context["output.candidates"] = resolved.candidates
        trace.events.append(f"final_output:{resolved.source_key}")
        return resolved.value

    def _execute_execution_config(
        self,
        config: Dict[str, Any],
        state: Dict[str, Any],
        *,
        plan_extras: Optional[Dict[str, Any]] = None,
    ) -> NodeResult:
        runtime_config = dict(config.get("runtime_config") or {})
        node_id = (
            runtime_config.get("legacy_node_id")
            or config.get("node_id")
            or config.get("config_id")
            or "execution_config"
        )
        trace = NodeTrace()
        artifacts: List[Artifact] = []
        flat_context = self._build_flat_context(state)

        # Preserve observability contract without executing legacy pre-stage logic.
        self._measure("pre_plugins", lambda: self._record_pre_stage_trace(trace), trace)

        graph = self._compile_execution_plan(config)
        provider_output = self._execute_compiled_graph(config, graph, flat_context, trace, artifacts) if graph is not None else None

        # Preserve observability contract without executing legacy post-stage logic.
        self._measure("post_plugins", lambda: self._record_post_stage_trace(trace, config), trace)

        def validation_stage():
            trace.events.append("validation")
            compat_context = self._build_compat_context(flat_context)
            for rule in config.get("validation_rules", []):
                self._run_validation(rule, compat_context)

        self._measure("validation", validation_stage, trace)

        try:
            final_output = self._resolve_final_output(
                config=config,
                graph=graph,
                flat_context=flat_context,
                trace=trace,
                provider_output=provider_output,
            )
        except FinalOutputResolverError as exc:
            raise ValueError(f"final output resolution failed: {exc}") from exc

        result = NodeResult(
            node_id=node_id,
            output=final_output,
            artifacts=artifacts,
            trace=trace,
        )

        if runtime_config.get("write_observability", True):
            self._write_observability(node_id, trace)
        return result

    def execute(self, node: Dict[str, Any], state: Dict[str, Any]) -> NodeResult:
        normalized_node = self._normalize_node_payload(node)
        execution_plan, plan_extras = self._coerce_node_to_execution_plan(normalized_node)
        return self._execute_execution_config(execution_plan, state, plan_extras=plan_extras)

    def execute_by_config_id(self, registry, config_id: str, state: Dict[str, Any]) -> NodeResult:
        """
        Execute a registered execution config by config_id.

        The registry must provide:
            get(config_id) -> dict
        """
        config = registry.get(config_id)
        if not isinstance(config, dict):
            raise TypeError("execution config registry must return dict config")
        return self.execute(config, state)