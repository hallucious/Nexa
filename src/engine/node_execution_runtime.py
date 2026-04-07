from __future__ import annotations

import asyncio
from dataclasses import asdict, dataclass, field, is_dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import json
import time

from src.platform.prompt_loader import PromptLoaderError
from src.platform.prompt_registry import PromptRegistry
from src.platform.prompt_spec import PromptSpecError
from src.platform.plugin_result import PluginResult, normalize_plugin_result
from src.contracts.provider_contract import ProviderRequest
from src.providers.provider_contract import ProviderResult
from src.contracts.budget_routing_contract import RiskLevel, RoutingContext
from src.contracts.confidence_contract import BasisType, ConfidenceBasis, build_assessment
from src.contracts.safety_gate_contract import PermissionSet
from src.engine.budget_router import decide_route, log_route
from src.engine.confidence_aggregator import propagate_confidence
from src.engine.safety_gate import evaluate_gate
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
from src.engine.validation.output_verifier import run_output_verifier
from src.contracts.artifact_contract import infer_artifact_type, make_typed_artifact


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
    verifier_trace: List[Dict[str, Any]] = field(default_factory=list)
    typed_artifact_refs: List[str] = field(default_factory=list)
    precision: Dict[str, Any] = field(
        default_factory=lambda: {
            "routing": [],
            "safety_gates": [],
            "confidence_assessments": [],
            "node_confidence": None,
        }
    )


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


@dataclass
class ReviewRequiredPause(Exception):
    node_id: str
    payload: Dict[str, Any]

    def __str__(self) -> str:
        reason = self.payload.get("reason") or "review_required"
        return f"execution paused for review: {reason}"


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

        request = kwargs.pop("request", None)
        if request is None:
            prompt = kwargs.pop("prompt", "")
            context = kwargs.pop("context", {})
            options = kwargs.pop("options", {})
            metadata = kwargs.pop("metadata", {})
            if kwargs:
                options = {**dict(options or {}), **kwargs}
            request = ProviderRequest(
                provider_id=provider_id,
                prompt=str(prompt),
                context=dict(context or {}),
                options=dict(options or {}),
                metadata=dict(metadata or {}),
            )
        elif not isinstance(request, ProviderRequest):
            raise TypeError("request must be ProviderRequest")

        return self.provider_executor.execute(request)

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

    def _build_artifact_preview_payload(self, artifact: Artifact) -> Dict[str, Any]:
        preview_data = artifact.data
        preview_kind = "unknown"
        preview_summary = None

        if isinstance(preview_data, dict):
            preview_kind = "mapping"
            preview_summary = f"mapping[{len(preview_data)}]"
        elif isinstance(preview_data, (list, tuple)):
            preview_kind = "sequence"
            preview_summary = f"sequence[{len(preview_data)}]"
        elif isinstance(preview_data, str):
            preview_kind = "text"
            preview_summary = preview_data[:120]
        elif preview_data is None:
            preview_kind = "empty"
            preview_summary = None
        else:
            preview_kind = type(preview_data).__name__
            preview_summary = str(preview_data)[:120]

        return {
            "artifact_name": artifact.name,
            "artifact_type": artifact.type,
            "data": preview_data,
            "metadata": artifact.metadata,
            "is_final_artifact": False,
            "preview_kind": preview_kind,
            "preview_summary": preview_summary,
        }

    def _emit_artifact_preview_events(self, node_id: str, artifacts: List[Artifact]) -> None:
        for artifact in artifacts:
            if artifact.type != "preview":
                continue

            self._emit_event(
                "artifact_preview",
                self._build_artifact_preview_payload(artifact),
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

    def _extract_review_required_payload(
        self,
        *,
        plugin_id: str,
        plugin_result: PluginResult,
    ) -> Optional[Dict[str, Any]]:
        if not isinstance(plugin_result.trace, dict):
            return None

        review_required = plugin_result.trace.get("review_required")
        if review_required is None:
            return None

        payload: Dict[str, Any] = {"plugin_id": plugin_id}

        if isinstance(review_required, dict):
            payload.update(review_required)
        elif isinstance(review_required, str):
            payload["reason"] = review_required
        elif isinstance(review_required, bool):
            if not review_required:
                return None
        else:
            payload["reason"] = str(review_required)

        payload.setdefault("reason", "plugin_requested_review")
        payload.setdefault("is_blocking", False)
        payload.setdefault("resume", {
            "can_resume": True,
            "resume_strategy": "restart_from_node",
            "requires_revalidation": ["structural_validation", "determinism_pre_validation"],
        })
        return payload

    def _emit_review_required_event_from_plugin_result(
        self,
        node_id: str,
        plugin_id: str,
        plugin_result: PluginResult,
    ) -> Optional[Dict[str, Any]]:
        payload = self._extract_review_required_payload(
            plugin_id=plugin_id,
            plugin_result=plugin_result,
        )
        if payload is None:
            return None

        self._emit_event("review_required", payload, node_id=node_id)
        return payload

    def _review_gate_enabled(self, runtime_config: Dict[str, Any]) -> bool:
        if runtime_config.get("pause_on_review_required") is True:
            return True
        review_gate = runtime_config.get("review_gate")
        if isinstance(review_gate, dict):
            return review_gate.get("pause_on_review_required") is True
        return False

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
            "verifier_trace": trace.verifier_trace,
            "typed_artifact_refs": trace.typed_artifact_refs,
        }
        with self.observability_file.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")



    @staticmethod
    def _clamp01(value: Any, *, default: float = 0.0) -> float:
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            return default
        return max(0.0, min(1.0, numeric))

    def _derive_difficulty_estimate(
        self,
        *,
        prompt: str,
        runtime_routing: Dict[str, Any],
        provider_cfg: Dict[str, Any],
    ) -> float:
        explicit = runtime_routing.get("difficulty_estimate")
        if explicit is None:
            explicit = provider_cfg.get("difficulty_estimate")
        if explicit is not None:
            return self._clamp01(explicit, default=0.5)
        prompt_length_score = min(len(prompt or "") / 1200.0, 1.0)
        structure_bonus = 0.1 if isinstance(provider_cfg.get("inputs"), dict) and len(provider_cfg.get("inputs") or {}) > 1 else 0.0
        return self._clamp01(0.25 + prompt_length_score + structure_bonus, default=0.5)

    def _merge_runtime_provider_settings(
        self,
        runtime_config: Dict[str, Any],
        provider_cfg: Dict[str, Any],
        key: str,
    ) -> Dict[str, Any]:
        merged: Dict[str, Any] = {}
        runtime_value = runtime_config.get(key)
        provider_value = provider_cfg.get(key)
        if isinstance(runtime_value, dict):
            merged.update(runtime_value)
        if isinstance(provider_value, dict):
            merged.update(provider_value)
        return merged

    def _build_permission_set(
        self,
        *,
        runtime_config: Dict[str, Any],
        provider_cfg: Dict[str, Any],
    ) -> PermissionSet:
        safety_cfg = self._merge_runtime_provider_settings(runtime_config, provider_cfg, "safety_gate")
        return PermissionSet(
            allowed_providers=list(safety_cfg.get("allowed_providers") or []),
            allowed_plugins=list(safety_cfg.get("allowed_plugins") or []),
            allowed_actions=list(safety_cfg.get("allowed_actions") or []),
            denied_providers=list(safety_cfg.get("denied_providers") or []),
            denied_plugins=list(safety_cfg.get("denied_plugins") or []),
            denied_actions=list(safety_cfg.get("denied_actions") or []),
            requires_human_approval=bool(safety_cfg.get("requires_human_approval", False)),
        )

    def _build_routing_context(
        self,
        *,
        node_id: str,
        provider_ref: str,
        prompt: str,
        context: Dict[str, Any],
        runtime_config: Dict[str, Any],
        provider_cfg: Dict[str, Any],
    ) -> RoutingContext:
        runtime_routing = self._merge_runtime_provider_settings(runtime_config, provider_cfg, "budget_routing")
        allowed_providers = list(
            runtime_routing.get("allowed_providers")
            or provider_cfg.get("provider_candidates")
            or [provider_ref]
        )
        if provider_ref not in allowed_providers:
            allowed_providers.append(provider_ref)
        allowed_models = list(runtime_routing.get("allowed_models") or provider_cfg.get("allowed_models") or [])
        configured_model = provider_cfg.get("model")
        if isinstance(configured_model, str) and configured_model and configured_model not in allowed_models:
            allowed_models.insert(0, configured_model)
        task_type = str(runtime_routing.get("task_type") or provider_cfg.get("task_type") or "general_generation")
        difficulty_estimate = self._derive_difficulty_estimate(
            prompt=prompt,
            runtime_routing=runtime_routing,
            provider_cfg=provider_cfg,
        )
        risk_level = str(
            runtime_routing.get("risk_level")
            or self._merge_runtime_provider_settings(runtime_config, provider_cfg, "safety_gate").get("data_sensitivity")
            or RiskLevel.LOW
        )
        if risk_level not in RiskLevel._ALL:
            risk_level = RiskLevel.LOW
        prior_failures = context.get("prior_failures") if isinstance(context.get("prior_failures"), list) else []
        retry_count = context.get("retry_count", runtime_routing.get("retry_count", 0))
        try:
            retry_count = int(retry_count)
        except (TypeError, ValueError):
            retry_count = 0
        return RoutingContext(
            node_id=node_id,
            task_type=task_type,
            current_budget=float(runtime_routing.get("current_budget", 100.0) or 0.0),
            difficulty_estimate=difficulty_estimate,
            risk_level=risk_level,
            allowed_providers=allowed_providers,
            latency_target=runtime_routing.get("latency_target"),
            quality_target=runtime_routing.get("quality_target"),
            retry_count=retry_count,
            prior_failures=[str(item) for item in prior_failures],
            safety_requirements=[str(item) for item in runtime_routing.get("safety_requirements") or []],
            allowed_models=[str(item) for item in allowed_models],
            allowed_plugins=[str(item) for item in runtime_routing.get("allowed_plugins") or []],
        )

    def _build_provider_confidence_assessment(
        self,
        *,
        node_id: str,
        selected_provider_id: str,
        output: Any,
        structured: Optional[Dict[str, Any]],
        route_decision: Dict[str, Any],
        gate_result: Dict[str, Any],
    ) -> Dict[str, Any]:
        tier = route_decision.get("selected_route_tier")
        base_by_tier = {
            "cheap": 0.45,
            "balanced": 0.6,
            "high_quality": 0.78,
            "high_safety": 0.72,
        }
        confidence_score = base_by_tier.get(str(tier), 0.55)
        if gate_result.get("status") in {"allow_with_review", "restrict"}:
            confidence_score -= 0.08
        if output is not None:
            confidence_score += 0.05
        confidence_score = self._clamp01(confidence_score, default=0.55)

        evidence_density = 0.45
        if output is not None:
            evidence_density += 0.15
        if isinstance(structured, dict) and structured:
            evidence_density += 0.15
        evidence_density = self._clamp01(evidence_density, default=0.5)

        basis: List[ConfidenceBasis] = []
        route_id = route_decision.get("route_id")
        if isinstance(route_id, str) and route_id:
            basis.append(
                ConfidenceBasis(
                    basis_type=BasisType.HEURISTIC,
                    source_ref=route_id,
                    contribution_weight=0.5,
                    note=f"route_tier={tier}",
                )
            )
        gate_id = gate_result.get("gate_id")
        if isinstance(gate_id, str) and gate_id:
            basis.append(
                ConfidenceBasis(
                    basis_type=BasisType.HEURISTIC,
                    source_ref=gate_id,
                    contribution_weight=0.5,
                    note=f"gate_status={gate_result.get('status')}",
                )
            )

        assessment = build_assessment(
            target_ref=f"node.{node_id}.provider.{selected_provider_id}",
            confidence_score=round(confidence_score, 4),
            evidence_density_score=round(evidence_density, 4),
            confidence_basis=basis,
            explanation=f"provider precision baseline derived from route_tier={tier} and gate_status={gate_result.get('status')}",
        )
        return assessment.to_dict()

    def _append_node_confidence_artifact(
        self,
        *,
        node_id: str,
        trace: NodeTrace,
        artifacts: List[Artifact],
        emit_artifact: bool = False,
    ) -> None:
        confidence_entries = trace.precision.get("confidence_assessments") if isinstance(trace.precision, dict) else None
        assessments: List[Any] = []
        if isinstance(confidence_entries, list):
            for item in confidence_entries:
                if isinstance(item, dict):
                    try:
                        from src.contracts.confidence_contract import ConfidenceAssessment
                        assessments.append(ConfidenceAssessment.from_dict(item))
                    except Exception:
                        continue
        if not assessments:
            return

        local_evidence_density = 0.6
        verifier_boost = 0.0
        if trace.verifier_trace:
            composite = trace.verifier_trace[-1] if isinstance(trace.verifier_trace[-1], dict) else {}
            local_evidence_density = self._clamp01(composite.get("aggregate_confidence", 0.65), default=0.65)
            status = composite.get("aggregate_status")
            if status == "pass":
                verifier_boost = 0.2
            elif status == "warning":
                verifier_boost = 0.1
        node_assessment = propagate_confidence(
            upstream_assessments=assessments,
            local_evidence_density=local_evidence_density,
            verifier_boost=verifier_boost,
            target_ref=f"node.{node_id}.output",
            explanation=f"node confidence propagated from {len(assessments)} provider assessment(s)",
        )
        trace.precision["node_confidence"] = node_assessment.to_dict()
        if emit_artifact:
            artifacts.append(
                Artifact(
                    type="confidence_assessment",
                    name="node_confidence",
                    data=node_assessment.to_dict(),
                    metadata={
                        "precision_kind": "confidence",
                        "target_ref": f"node.{node_id}.output",
                    },
                    producer_node=node_id,
                    timestamp_ms=time.time() * 1000.0,
                )
            )
        self._emit_event(
            "confidence_assessment_completed",
            {
                "target_ref": f"node.{node_id}.output",
                "confidence_score": node_assessment.confidence_score,
                "threshold_band": node_assessment.threshold_decision.threshold_band,
                "recommended_action": node_assessment.threshold_decision.recommended_action,
            },
            node_id=node_id,
        )

    def _provider_call(
        self,
        provider_ref: str,
        prompt: str,
        context: Dict[str, Any],
        *,
        node_id: str,
        runtime_config: Optional[Dict[str, Any]] = None,
        provider_cfg: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        self.metrics.provider_calls += 1
        runtime_config = dict(runtime_config or {})
        provider_cfg = dict(provider_cfg or {})
        routing_context = self._build_routing_context(
            node_id=node_id,
            provider_ref=provider_ref,
            prompt=prompt,
            context=context,
            runtime_config=runtime_config,
            provider_cfg=provider_cfg,
        )
        route_decision = decide_route(routing_context)
        route_log = log_route(route_decision, routing_context)

        permission_set = self._build_permission_set(runtime_config=runtime_config, provider_cfg=provider_cfg)
        safety_cfg = self._merge_runtime_provider_settings(runtime_config, provider_cfg, "safety_gate")
        gate_result = evaluate_gate(
            target_ref=f"node.{node_id}.provider",
            requested_actions=["provider_execute"],
            permission_set=permission_set,
            requested_providers=[route_decision.selected_provider_id],
            requested_plugins=list(route_decision.selected_plugins),
            data_sensitivity=str(safety_cfg.get("data_sensitivity") or routing_context.risk_level),
            policy_overrides=dict(safety_cfg.get("policy_overrides") or {}),
        )
        provider_blocked = bool(permission_set.denied_providers) and route_decision.selected_provider_id in set(permission_set.denied_providers)
        provider_not_allowed = bool(permission_set.allowed_providers) and route_decision.selected_provider_id not in set(permission_set.allowed_providers)
        if gate_result.is_blocked or provider_blocked or provider_not_allowed:
            reason_codes = list(gate_result.reason_codes or [])
            if provider_blocked:
                reason_codes.append(f"PROVIDER_DENIED:{route_decision.selected_provider_id}")
            if provider_not_allowed:
                reason_codes.append(f"PROVIDER_NOT_IN_ALLOWLIST:{route_decision.selected_provider_id}")
            raise RuntimeError(
                "provider execution blocked by safety gate: " + ", ".join(reason_codes or ["safety_gate_blocked"])
            )

        request_options: Dict[str, Any] = {}
        if isinstance(route_decision.selected_model_id, str) and route_decision.selected_model_id:
            request_options["model"] = route_decision.selected_model_id

        request = ProviderRequest(
            provider_id=route_decision.selected_provider_id,
            prompt=prompt,
            context=context,
            options=request_options,
            metadata={
                "node_id": node_id,
                "route_decision": route_decision.to_dict(),
                "route_log": route_log.to_dict(),
                "safety_gate": gate_result.to_dict(),
            },
        )
        result = self.provider_executor.execute(request)
        if not isinstance(result, ProviderResult):
            raise TypeError("ProviderExecutor must return ProviderResult")
        if not result.success:
            raise RuntimeError(result.error or result.reason_code or "provider_error")

        raw = dict(result.raw) if isinstance(result.raw, dict) else {}
        output = raw.get("output")
        if output is None:
            output = result.text
        structured = raw.get("structured") if isinstance(raw.get("structured"), dict) else None

        confidence_assessment = self._build_provider_confidence_assessment(
            node_id=node_id,
            selected_provider_id=route_decision.selected_provider_id,
            output=output,
            structured=structured,
            route_decision=route_decision.to_dict(),
            gate_result=gate_result.to_dict(),
        )

        trace_payload = dict(raw.get("trace", {})) if isinstance(raw.get("trace"), dict) else {}
        trace_payload.setdefault("provider", route_decision.selected_provider_id)
        trace_payload.update(
            {
                "route_decision": route_decision.to_dict(),
                "route_log": route_log.to_dict(),
                "safety_gate": gate_result.to_dict(),
                "confidence_assessment": confidence_assessment,
            }
        )

        payload: Dict[str, Any] = {
            "output": output,
            "trace": trace_payload,
            "artifacts": list(raw.get("artifacts", [])),
            "text": result.text,
            "success": result.success,
            "metrics": {
                "latency_ms": int(result.metrics.latency_ms),
                "tokens_used": result.metrics.tokens_used,
            },
            "selected_provider_id": route_decision.selected_provider_id,
            "route_decision": route_decision.to_dict(),
            "route_log": route_log.to_dict(),
            "safety_gate": gate_result.to_dict(),
            "confidence_assessment": confidence_assessment,
        }
        if result.reason_code is not None:
            payload["reason_code"] = result.reason_code
        if result.error is not None:
            payload["error"] = result.error

        if output is None and isinstance(structured, dict):
            payload.update(structured)
        elif isinstance(structured, dict):
            payload["structured"] = structured
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
            # Bounded legacy compatibility path.
            # When prompt_version is explicit, always fail hard — there is no silent fallback.
            # When prompt_version is absent and the registry cannot resolve the prompt,
            # fall back to a deterministic placeholder string "{prompt_ref}:{context}".
            # This path exists only for execution configs that do not yet have a registry-backed
            # prompt spec (e.g. integration tests that use symbolic prompt_ref values).
            # New code MUST use a PromptRegistry-backed prompt spec.
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
                return self._provider_call(
                    provider_id,
                    prompt,
                    compat_context,
                    node_id=str(config.get("node_id") or config.get("config_id") or "execution_config"),
                    runtime_config=dict(config.get("runtime_config") or {}),
                    provider_cfg=provider_cfg,
                )

            provider_result = self._measure("provider_execute", provider_stage, trace) or {}
            if isinstance(provider_result, dict):
                trace.provider_trace = provider_result.get("trace")
                route_log = provider_result.get("route_log")
                if isinstance(route_log, dict):
                    trace.precision.setdefault("routing", []).append(route_log)
                safety_gate = provider_result.get("safety_gate")
                if isinstance(safety_gate, dict):
                    trace.precision.setdefault("safety_gates", []).append(safety_gate)
                confidence_assessment = provider_result.get("confidence_assessment")
                if isinstance(confidence_assessment, dict):
                    trace.precision.setdefault("confidence_assessments", []).append(confidence_assessment)
                state_holder["last_provider_output"] = provider_result.get("output")
                flat_context[f"provider.{provider_id}.output"] = provider_result.get("output")
                selected_provider_id = provider_result.get("selected_provider_id")
                if isinstance(selected_provider_id, str) and selected_provider_id and selected_provider_id != provider_id:
                    flat_context[f"provider.{selected_provider_id}.output"] = provider_result.get("output")
                for key, value in provider_result.items():
                    if key in {"output", "trace", "artifacts"}:
                        continue
                    flat_context[f"provider.{provider_id}.{key}"] = value
                    flat_context[key] = value
                    if isinstance(selected_provider_id, str) and selected_provider_id and selected_provider_id != provider_id:
                        flat_context[f"provider.{selected_provider_id}.{key}"] = value
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
                result = self.execute_plugin(plugin_id, **bound_inputs)
                return normalize_plugin_result(result)

            plugin_result = self._measure(f"plugin_execute:{plugin_id}", plugin_stage, trace)
            for write_key, value in self._extract_plugin_output_mapping(plugin_result, sorted(resource.writes)).items():
                flat_context[write_key] = value
            for artifact in plugin_result.artifacts:
                if isinstance(artifact, Artifact):
                    artifacts.append(artifact)

            runtime_node_id = config.get("node_id") or config.get("config_id") or "execution_config"
            self._emit_progress_event_from_plugin_result(
                node_id=runtime_node_id,
                plugin_id=plugin_id,
                plugin_result=plugin_result,
            )
            review_required_payload = self._emit_review_required_event_from_plugin_result(
                node_id=runtime_node_id,
                plugin_id=plugin_id,
                plugin_result=plugin_result,
            )
            if review_required_payload is not None and self._review_gate_enabled(dict(config.get("runtime_config") or {})):
                resume_payload = dict(review_required_payload.get("resume") or {})
                resume_payload.setdefault("can_resume", True)
                resume_payload.setdefault("resume_strategy", "restart_from_node")
                resume_payload.setdefault("requires_revalidation", ["structural_validation", "determinism_pre_validation"])
                resume_payload.setdefault("resume_from_node_id", runtime_node_id)
                review_required_payload["resume"] = resume_payload
                raise ReviewRequiredPause(node_id=runtime_node_id, payload=review_required_payload)

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

    def _append_typed_artifact(
        self,
        *,
        artifacts: List[Artifact],
        trace: NodeTrace,
        artifact_type: str,
        producer_ref: str,
        payload: Any,
        validation_status: str,
        artifact_name: str,
        metadata: Optional[Dict[str, Any]] = None,
        trace_refs: Optional[List[str]] = None,
    ) -> str:
        envelope = make_typed_artifact(
            artifact_type=artifact_type,
            producer_ref=producer_ref,
            payload=payload,
            validation_status=validation_status,
            metadata=dict(metadata or {}),
            trace_refs=list(trace_refs or []),
        )
        trace.typed_artifact_refs.append(envelope.artifact_id)
        artifacts.append(
            Artifact(
                type=artifact_type,
                name=artifact_name,
                data=envelope.to_dict(),
                metadata={
                    "typed_artifact": True,
                    "artifact_type": envelope.artifact_type,
                    "artifact_schema_version": envelope.artifact_schema_version,
                    **dict(metadata or {}),
                },
                producer_node=producer_ref.replace("node.", "", 1),
                timestamp_ms=time.time() * 1000.0,
            )
        )
        return envelope.artifact_id

    def _run_output_verifier_if_configured(
        self,
        *,
        config: Dict[str, Any],
        node_id: str,
        final_output: Any,
        trace: NodeTrace,
        artifacts: List[Artifact],
    ) -> None:
        verifier_config = config.get("verifier")
        if verifier_config is None:
            return
        if not isinstance(verifier_config, dict):
            raise ValueError("verifier must be object")

        target_ref = f"node.{node_id}.output"
        composite = run_output_verifier(final_output, verifier_config, target_ref=target_ref)
        trace.verifier_trace.append(composite.to_dict())
        trace.events.append(f"verifier:{composite.aggregate_status}")

        verifier_id = str(verifier_config.get("verifier_id") or "output_verifier")
        verifier_trace_ref = f"trace://{self.execution_id}/{node_id}/verifier"
        verifier_artifact_id = self._append_typed_artifact(
            artifacts=artifacts,
            trace=trace,
            artifact_type="validation_report",
            producer_ref=f"node.{node_id}",
            payload=composite.to_dict(),
            validation_status="valid" if composite.aggregate_status == "pass" else "partial",
            artifact_name=verifier_id,
            metadata={
                "report_kind": "verifier",
                "target_ref": target_ref,
                "aggregate_status": composite.aggregate_status,
            },
            trace_refs=[verifier_trace_ref],
        )

        emitted_artifact_refs = [verifier_artifact_id]
        emitted_trace_refs = [verifier_trace_ref]

        if bool(verifier_config.get("emit_output_artifact", False)):
            declared_output_type = verifier_config.get("expected_artifact_type")
            if not isinstance(declared_output_type, str) or not declared_output_type:
                declared_output_type = infer_artifact_type(final_output)
            output_trace_ref = f"trace://{self.execution_id}/{node_id}/output"
            typed_output_artifact_id = self._append_typed_artifact(
                artifacts=artifacts,
                trace=trace,
                artifact_type=declared_output_type,
                producer_ref=f"node.{node_id}",
                payload=final_output,
                validation_status="valid" if composite.aggregate_status == "pass" else "partial",
                artifact_name="final_typed_output",
                metadata={
                    "report_kind": "typed_output",
                    "target_ref": target_ref,
                },
                trace_refs=[output_trace_ref],
            )
            emitted_artifact_refs.append(typed_output_artifact_id)
            emitted_trace_refs.append(output_trace_ref)

        self._emit_event(
            "verification_completed",
            {
                "verifier_id": verifier_id,
                "target_ref": target_ref,
                "status": composite.aggregate_status,
                "score": composite.aggregate_score,
                "confidence": composite.aggregate_confidence,
                "blocking_reason_codes": composite.blocking_reason_codes,
                "recommended_next_step": composite.recommended_next_step,
                "artifact_refs": emitted_artifact_refs,
                "trace_refs": emitted_trace_refs,
            },
            node_id=node_id,
        )

        if bool(verifier_config.get("blocking", False)) and composite.aggregate_status == "fail":
            raise ValueError(
                "output verification failed: " + ", ".join(composite.blocking_reason_codes or ["verification_failed"])
            )

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

        try:
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

            self._run_output_verifier_if_configured(
                config=config,
                node_id=node_id,
                final_output=final_output,
                trace=trace,
                artifacts=artifacts,
            )
            self._append_node_confidence_artifact(
                node_id=node_id,
                trace=trace,
                artifacts=artifacts,
                emit_artifact=bool(runtime_config.get("emit_confidence_artifact", False)),
            )

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
                    "status": "success",
                    "duration_ms": duration_ms,
                    "artifact_count": len(artifacts),
                    "metrics": self.get_metrics(),
                },
                node_id=node_id,
            )

            return result
        except ReviewRequiredPause as exc:
            duration_ms = round((time.time() - node_started_at) * 1000.0, 3)
            self._emit_event(
                "node_completed",
                {
                    "status": "partial",
                    "duration_ms": duration_ms,
                    "artifact_count": len(artifacts),
                    "metrics": self.get_metrics(),
                    "review_required": exc.payload,
                    "resume": dict(exc.payload.get("resume") or {}),
                    "error": str(exc),
                    "error_type": type(exc).__name__,
                },
                node_id=node_id,
            )
            raise
        except Exception as exc:
            duration_ms = round((time.time() - node_started_at) * 1000.0, 3)
            self._emit_event(
                "node_completed",
                {
                    "status": "failed",
                    "duration_ms": duration_ms,
                    "artifact_count": len(artifacts),
                    "metrics": self.get_metrics(),
                    "error": str(exc),
                    "error_type": type(exc).__name__,
                },
                node_id=node_id,
            )
            raise
        finally:
            if runtime_config.get("write_observability", True):
                self._write_observability(node_id, trace)

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

    # ------------------------------------------------------------------
    # Async execution path
    # ------------------------------------------------------------------

    async def _execute_resource_from_graph_async(
        self,
        resource_id: str,
        config: Dict[str, Any],
        graph,
        flat_context: Dict[str, Any],
        trace,
        artifacts: List,
        prompt_configs: Dict[str, Any],
        provider_configs: Dict[str, Any],
        plugin_configs: Dict[str, Any],
        state_holder: Dict[str, Any],
    ) -> Any:
        """Async wrapper: executes a single graph resource.

        The underlying resource execution (provider HTTP call, plugin call,
        prompt rendering) is I/O bound.  We offload it to a thread via
        asyncio.to_thread so the event loop is never blocked and
        other wave-sibling coroutines can make progress concurrently.
        """
        return await asyncio.to_thread(
            self._execute_resource_from_graph,
            resource_id,
            config,
            graph,
            flat_context,
            trace,
            artifacts,
            prompt_configs,
            provider_configs,
            plugin_configs,
            state_holder,
        )

    async def _execute_compiled_graph_async(
        self,
        config: Dict[str, Any],
        graph,
        flat_context: Dict[str, Any],
        trace,
        artifacts: List,
    ) -> Any:
        """Async version of _execute_compiled_graph.

        Uses GraphScheduler.execute_async() with asyncio.gather() so
        same-wave resources execute concurrently.
        """
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

        async def resource_executor_async(resource_id: str) -> Any:
            return await self._execute_resource_from_graph_async(
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

        execution_result = await scheduler.execute_async(resource_executor_async)
        for wave in execution_result.waves:
            self.record_wave()
            trace.events.append(f"wave:{wave.index}:{','.join(wave.resource_ids)}")
        return state_holder["last_provider_output"]

    async def _execute_execution_config_async(
        self,
        config: Dict[str, Any],
        state: Dict[str, Any],
        *,
        plan_extras: Optional[Dict[str, Any]] = None,
    ) -> NodeResult:
        """Async version of _execute_execution_config.

        Uses _execute_compiled_graph_async for true async wave execution.
        All other phases (validation, output resolution, events) are
        lightweight CPU work and run directly in the event loop thread.
        """
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

        try:
            graph = self._compile_execution_plan(config)
            if graph is not None:
                provider_output = await self._execute_compiled_graph_async(
                    config, graph, flat_context, trace, artifacts
                )
            else:
                provider_output = None

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

            self._run_output_verifier_if_configured(
                config=config,
                node_id=node_id,
                final_output=final_output,
                trace=trace,
                artifacts=artifacts,
            )
            self._append_node_confidence_artifact(
                node_id=node_id,
                trace=trace,
                artifacts=artifacts,
                emit_artifact=bool(runtime_config.get("emit_confidence_artifact", False)),
            )

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
                    "status": "success",
                    "duration_ms": duration_ms,
                    "artifact_count": len(artifacts),
                    "metrics": self.get_metrics(),
                },
                node_id=node_id,
            )
            return result

        except ReviewRequiredPause as exc:
            duration_ms = round((time.time() - node_started_at) * 1000.0, 3)
            self._emit_event(
                "node_completed",
                {
                    "status": "partial",
                    "duration_ms": duration_ms,
                    "artifact_count": len(artifacts),
                    "metrics": self.get_metrics(),
                    "review_required": exc.payload,
                    "resume": dict(exc.payload.get("resume") or {}),
                    "error": str(exc),
                    "error_type": type(exc).__name__,
                },
                node_id=node_id,
            )
            raise
        except Exception as exc:
            duration_ms = round((time.time() - node_started_at) * 1000.0, 3)
            self._emit_event(
                "node_completed",
                {
                    "status": "failed",
                    "duration_ms": duration_ms,
                    "artifact_count": len(artifacts),
                    "metrics": self.get_metrics(),
                    "error": str(exc),
                    "error_type": type(exc).__name__,
                },
                node_id=node_id,
            )
            raise
        finally:
            if runtime_config.get("write_observability", True):
                self._write_observability(node_id, trace)

    async def execute_async(self, node: Dict[str, Any], state: Dict[str, Any]) -> NodeResult:
        """True async entry point for node execution.

        Same contract as execute() but uses asyncio.gather() for
        same-wave resource concurrency inside _execute_compiled_graph_async.
        """
        normalized_node = self._normalize_node_payload(node)
        execution_plan, plan_extras = self._coerce_node_to_execution_plan(normalized_node)
        return await self._execute_execution_config_async(
            execution_plan, state, plan_extras=plan_extras
        )
