from __future__ import annotations

from dataclasses import asdict, dataclass, field, is_dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import json
import time

from src.platform.prompt_loader import PromptLoaderError
from src.platform.prompt_registry import PromptRegistry
from src.platform.prompt_spec import PromptSpecError
from src.platform.plugin_result import PluginResult, normalize_plugin_result
from src.contracts.provider_contract import ProviderRequest, ProviderResult
from src.engine.compiled_resource_graph import (
    CompiledResourceGraph,
    compile_execution_config_to_graph,
)
from src.engine.execution_event import ExecutionEvent
from src.engine.execution_event_emitter import ExecutionEventEmitter
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


@dataclass
class RuntimeMetrics:
    plugin_calls: int = 0
    provider_calls: int = 0
    executed_nodes: int = 0
    wave_count: int = 0

    def to_dict(self) -> Dict[str, int]:
        return {
            "plugin_calls": self.plugin_calls,
            "provider_calls": self.provider_calls,
            "executed_nodes": self.executed_nodes,
            "wave_count": self.wave_count,
        }


class NodeExecutionRuntime:
    """
    Step135+ runtime coordinator.

    Runtime responsibilities:
    1. normalize input into execution config
    2. compile execution config into compiled resource graph
    3. execute graph through GraphScheduler
    4. resolve deterministic final output

    Note: pre/post trace markers are preserved for existing observability contracts.
    """

    def __init__(
        self,
        provider_executor,
        observability_file: str = "OBSERVABILITY.jsonl",
        plugin_registry: Optional[Dict[str, Any]] = None,
        event_emitter: Optional[ExecutionEventEmitter] = None,
        prompt_registry: Optional[Any] = None,
    ):
        self.provider_executor = provider_executor
        self.observability_file = Path(observability_file)
        self.plugin_registry = plugin_registry or {}
        self.prompt_registry = prompt_registry or PromptRegistry()
        self.metrics = RuntimeMetrics()
        self.event_emitter = event_emitter or ExecutionEventEmitter()
        self.execution_id: str = "runtime-default"

    # ------------------------------------------------------------------
    # Step152 runtime metrics helpers
    # ------------------------------------------------------------------

    def reset_metrics(self) -> None:
        self.metrics = RuntimeMetrics()

    def record_wave(self) -> None:
        self.metrics.wave_count += 1

    def set_execution_id(self, execution_id: str) -> None:
        self.execution_id = execution_id

    def execute_plugin(self, plugin_id: str, **kwargs):
        if plugin_id not in self.plugin_registry:
            raise ValueError(f"Unknown plugin: {plugin_id}")

        self.metrics.plugin_calls += 1
        plugin_callable = self.plugin_registry[plugin_id]
        return plugin_callable(**kwargs)

    def execute_provider(self, provider_id: str, **kwargs):
        self.metrics.provider_calls += 1
        return self.provider_executor.execute(provider_id, **kwargs)

    def execute_node(self, node_id: str, func, **kwargs):
        self.metrics.executed_nodes += 1
        return func(**kwargs)

    def get_metrics(self) -> Dict[str, int]:
        return self.metrics.to_dict()

    def get_execution_events(self) -> List[ExecutionEvent]:
        return self.event_emitter.get_events()

    # ------------------------------------------------------------------
    # Step158 event helpers
    # ------------------------------------------------------------------

    def _emit_event(
        self,
        event_type: str,
        payload: Optional[Dict[str, Any]] = None,
        *,
        node_id: Optional[str] = None,
    ) -> None:
        self.event_emitter.emit(
            ExecutionEvent.now(
                event_type,
                payload or {},
                execution_id=self.execution_id,
                node_id=node_id,
            )
        )

    def _emit_artifact_preview_events(self, node_id: str, artifacts: List[Artifact]) -> None:
        for artifact in artifacts:
            if artifact.type != "preview":
                continue

            self._emit_event(
                "artifact_preview",
                {
                    "artifact_name": artifact.name,
                    "artifact_type": artifact.type,
                    "data": artifact.data,
                    "metadata": artifact.metadata,
                },
                node_id=node_id,
            )

    def _emit_progress_event_from_plugin_result(
        self,
        node_id: str,
        plugin_id: str,
        plugin_result: PluginResult,
    ) -> None:
        if not isinstance(plugin_result.trace, dict):
            return

        progress = plugin_result.trace.get("progress")
        if not isinstance(progress, dict):
            return

        payload = {"plugin_id": plugin_id}
        payload.update(progress)

        self._emit_event("progress", payload, node_id=node_id)

    # ------------------------------------------------------------------
    # Execution internals
    # ------------------------------------------------------------------

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



    def _provider_call(self, provider_ref: str, prompt: str, context: Dict[str, Any]) -> Dict[str, Any]:
        self.metrics.provider_calls += 1

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

    def _resolve_prompt_spec(self, prompt_ref: str, prompt_version: Optional[str] = None):
        if prompt_version:
            return self.prompt_registry.get(prompt_ref, prompt_version)
        return self.prompt_registry.get(prompt_ref)

    def _render_prompt(
        self,
        prompt_ref: str,
        context: Dict[str, Any],
        *,
        prompt_version: Optional[str] = None,
        prompt_inputs: Optional[Dict[str, Any]] = None,
    ) -> str:
        try:
            spec = self._resolve_prompt_spec(prompt_ref, prompt_version)
        except (FileNotFoundError, RuntimeError) as exc:
            # Backward compatibility for legacy prompt_ref-only execution configs.
            # Modern prompt binding should fail hard when an explicit version is requested.
            if prompt_version is not None:
                raise ValueError(
                    f"prompt resolution failed for '{prompt_ref}:{prompt_version}': {exc}"
                ) from exc
            return f"{prompt_ref}:{context}"
        except PromptLoaderError as exc:
            raise ValueError(f"prompt resolution failed for '{prompt_ref}': {exc}") from exc

        render_inputs = prompt_inputs if prompt_inputs is not None else context
        try:
            return spec.render(render_inputs)
        except PromptSpecError as exc:
            raise ValueError(f"prompt render failed for '{prompt_ref}': {exc}") from exc

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

    def _coerce_node_to_execution_plan(self, normalized_node: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """Normalize any execution config dict into a canonical execution plan."""
        plan = dict(normalized_node)
        runtime_config = dict(plan.get("runtime_config") or {})
        runtime_config.pop("emit_primary_artifact", None)
        runtime_config.setdefault("write_observability", True)
        plan["runtime_config"] = runtime_config
        return plan, {}

    def _flatten_node_output_aliases(self, flat: Dict[str, Any], node_id: str, output: Any) -> None:
        dotted_prefixes = [f"node.{node_id}.output", f"{node_id}.output"]
        for prefix in dotted_prefixes:
            flat[prefix] = output

        def _walk(prefix: str, value: Any) -> None:
            if isinstance(value, dict):
                for key, item in value.items():
                    if not isinstance(key, str) or not key:
                        continue
                    child_prefix = f"{prefix}.{key}"
                    flat[child_prefix] = item
                    _walk(child_prefix, item)

        for prefix in dotted_prefixes:
            _walk(prefix, output)

    def _build_flat_context(self, state: Dict[str, Any]) -> Dict[str, Any]:
        flat: Dict[str, Any] = {}
        node_outputs = state.get("__node_outputs__")

        for key, value in state.items():
            if key == "__node_outputs__":
                continue
            flat[key] = value
            flat[f"input.{key}"] = value

        if isinstance(node_outputs, dict):
            for node_id, node_output in node_outputs.items():
                if not isinstance(node_id, str) or not node_id:
                    continue
                self._flatten_node_output_aliases(flat, node_id, node_output)

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
        has_resource = (
            "prompt" in normalized
            or "provider" in normalized
            or bool(normalized.get("plugins"))
        )
        if not has_resource:
            return None
        return compile_execution_config_to_graph(normalized)

    def _resolve_graph_plugin_inputs(self, plugin_config: Dict[str, Any], flat_context: Dict[str, Any]) -> Dict[str, Any]:
        inputs = plugin_config.get("inputs") or {}
        if not inputs:
            return {}
        return {name: flat_context.get(context_key) for name, context_key in inputs.items()}

    def _resolve_prompt_inputs(
        self,
        prompt_config: Dict[str, Any],
        flat_context: Dict[str, Any],
        compat_context: Dict[str, Any],
    ) -> Dict[str, Any]:
        input_mapping = prompt_config.get("inputs") or {}
        if input_mapping:
            return {
                name: flat_context.get(context_key)
                for name, context_key in input_mapping.items()
            }
        return compat_context

    def _validate_external_graph_inputs(self, graph: CompiledResourceGraph, flat_context: Dict[str, Any]) -> None:
        missing: List[str] = []
        for resource in graph.resources.values():
            for read_key in sorted(resource.reads):
                if read_key in flat_context:
                    continue
                if read_key.startswith(("input.", "system.")):
                    continue
                if read_key.startswith("node.") or ".output" in read_key:
                    missing.append(f"{resource.id} reads {read_key}")
        if missing:
            raise ValueError("missing cross-node input reference: " + "; ".join(missing))

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
            prompt_version = (
                prompt_cfg.get("prompt_version")
                or prompt_cfg.get("version")
                or config.get("prompt_version")
            )
            compat_context = self._build_compat_context(flat_context)
            prompt_inputs = self._resolve_prompt_inputs(prompt_cfg, flat_context, compat_context)

            def render_stage():
                trace.events.append("prompt_render")
                rendered = self._render_prompt(
                    str(prompt_ref or ""),
                    compat_context,
                    prompt_version=str(prompt_version) if prompt_version is not None else None,
                    prompt_inputs=prompt_inputs,
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
            bound_inputs = self._resolve_graph_plugin_inputs(plugin_cfg, flat_context)
            trace.plugin_trace["post"].append(plugin_id)

            def plugin_stage():
                trace.events.append(f"plugin_execute:{plugin_id}")
                self.metrics.plugin_calls += 1
                result = self.execute_plugin(plugin_id, **bound_inputs)
                return normalize_plugin_result(result)

            plugin_result = self._measure(f"plugin_execute:{plugin_id}", plugin_stage, trace)
            for write_key, value in self._extract_plugin_output_mapping(plugin_result, sorted(resource.writes)).items():
                flat_context[write_key] = value
            for artifact in plugin_result.artifacts:
                if isinstance(artifact, Artifact):
                    artifacts.append(artifact)

            self._emit_progress_event_from_plugin_result(
                node_id=config.get("node_id") or config.get("config_id") or "execution_config",
                plugin_id=plugin_id,
                plugin_result=plugin_result,
            )

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

        self._validate_external_graph_inputs(graph, flat_context)

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
            self.record_wave()
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
            config.get("node_id")
            or config.get("config_id")
            or "execution_config"
        )
        trace = NodeTrace()
        artifacts: List[Artifact] = []
        flat_context = self._build_flat_context(state)

        node_started_at = time.time()
        self._emit_event("node_started", {}, node_id=node_id)

        graph = self._compile_execution_plan(config)
        provider_output = self._execute_compiled_graph(config, graph, flat_context, trace, artifacts) if graph is not None else None


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

        self._emit_artifact_preview_events(node_id, artifacts)

        duration_ms = round((time.time() - node_started_at) * 1000.0, 3)
        self._emit_event(
            "node_completed",
            {
                "duration_ms": duration_ms,
                "artifact_count": len(artifacts),
                "metrics": self.get_metrics(),
            },
            node_id=node_id,
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
