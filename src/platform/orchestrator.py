from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from src.models.decision_models import Decision, GateResult
from src.pipeline.contracts import standard_spec
from src.pipeline.runner import GateContext

from .prompt_spec import PromptSpec
from .worker import TextWorker, WorkerResult
from .plugin import Plugin


@dataclass(frozen=True)
class GateBlueprint:
    """Blueprint for building a gate callable without modifying PipelineRunner (v0.1).

    v0.1 supports:
    - fallback_executor: reuse existing gate function (no behavior change)
    - prompt_spec + worker: render prompt and call worker to decide PASS/STOP

    plugins/policy are reserved for Step 4+ (extension points).
    """

    gate_prefix: str  # e.g. "G1"
    prompt_spec: Optional[PromptSpec] = None
    worker: Optional[TextWorker] = None
    plugins: list[Plugin] = field(default_factory=list)
    policy: Optional[str] = None
    fallback_executor: Optional[Callable[[GateContext], GateResult]] = None


class GateOrchestrator:
    """Builds executable gate callables from GateBlueprints."""

    def build(self, bp: GateBlueprint) -> Callable[[GateContext], GateResult]:
        def _exec(ctx: GateContext) -> GateResult:
            # 0) Fallback path: preserve legacy behavior
            if bp.fallback_executor is not None:
                return bp.fallback_executor(ctx)

            if bp.prompt_spec is None or bp.worker is None:
                # Developer misconfiguration; STOP safely with standardized artifacts.
                return self._stop_with_artifacts(ctx, bp.gate_prefix, reason="MISSING_COMPONENTS")

            # 1) Render prompt from context
            # v0.1 convention: inputs for prompt rendering come from ctx.context
            try:
                rendered = bp.prompt_spec.render(ctx.context)
            except Exception as e:
                return self._stop_with_artifacts(
                    ctx,
                    bp.gate_prefix,
                    reason=f"PROMPT_RENDER_ERROR: {type(e).__name__}: {e}",
                )

            # 2) Worker call
            wr: WorkerResult = bp.worker.generate_text(prompt=rendered)

            # 3) Decide (v0.1)
            decision = Decision.PASS if wr.success else Decision.STOP

            # 4) Write standard artifacts
            outputs = self._write_standard_artifacts(
                run_dir=Path(ctx.run_dir),
                gate_prefix=bp.gate_prefix,
                decision=decision.value,
                worker_result=wr,
            )

            meta: Dict[str, Any] = {
                "gate": bp.gate_prefix,
                "worker_name": wr.worker_name,
                "worker_success": wr.success,
                "worker_latency_ms": wr.latency_ms,
            }
            if wr.error:
                meta["worker_error"] = wr.error

            return GateResult(decision=decision, message=bp.gate_prefix, outputs=outputs, meta=meta)

        return _exec

    def _write_standard_artifacts(
        self,
        *,
        run_dir: Path,
        gate_prefix: str,
        decision: str,
        worker_result: Optional[WorkerResult] = None,
    ) -> Dict[str, str]:
        spec = standard_spec(gate_prefix)

        (run_dir / f"{gate_prefix}_DECISION.md").write_text(
            f"# {gate_prefix} DECISION\n\n{decision}\n",
            encoding="utf-8",
        )

        out_payload: Dict[str, Any] = {"gate": gate_prefix, "decision": decision}
        if worker_result is not None:
            out_payload["worker"] = {
                "name": worker_result.worker_name,
                "success": worker_result.success,
                "text": worker_result.text,
                "raw": worker_result.raw,
                "error": worker_result.error,
                "latency_ms": worker_result.latency_ms,
            }

        (run_dir / f"{gate_prefix}_OUTPUT.json").write_text(
            json.dumps(out_payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        meta_payload: Dict[str, Any] = {"gate": gate_prefix, "decision": decision}
        if worker_result is not None:
            meta_payload.update(
                {
                    "worker_name": worker_result.worker_name,
                    "worker_success": worker_result.success,
                    "provider_latency_ms": worker_result.latency_ms,
                }
            )

        (run_dir / f"{gate_prefix}_META.json").write_text(
            json.dumps(meta_payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        outputs = {
            f"{gate_prefix}_DECISION.md": f"{gate_prefix}_DECISION.md",
            f"{gate_prefix}_OUTPUT.json": f"{gate_prefix}_OUTPUT.json",
            f"{gate_prefix}_META.json": f"{gate_prefix}_META.json",
        }
        spec.validate(outputs)
        return outputs

    def _stop_with_artifacts(self, ctx: GateContext, gate_prefix: str, reason: str) -> GateResult:
        outputs = self._write_standard_artifacts(
            run_dir=Path(ctx.run_dir),
            gate_prefix=gate_prefix,
            decision=Decision.STOP.value,
            worker_result=None,
        )
        return GateResult(
            decision=Decision.STOP,
            message=gate_prefix,
            outputs=outputs,
            meta={"stop_detail": reason},
        )
