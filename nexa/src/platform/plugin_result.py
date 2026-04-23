from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class PluginResult:
    """Runtime-facing plugin result surface.

    This intentionally carries both:
    - lightweight graph-runtime payload fields (output / artifacts / trace)
    - safe execution metadata (success / error / latency / reason_code / stage)
    """

    output: Optional[Any] = None
    artifacts: List[Any] = field(default_factory=list)
    trace: Optional[Dict[str, Any]] = None
    success: bool = True
    error: Optional[str] = None
    latency_ms: int = 0
    reason_code: Optional[str] = None
    stage: Optional[str] = None
    resource_usage: Optional[Dict[str, Any]] = None

    @property
    def data(self) -> Optional[Any]:
        return self.output

    @property
    def metrics(self) -> Dict[str, Any]:
        return {
            "latency_ms": int(self.latency_ms),
            "resource_usage": self.resource_usage,
        }


class PluginContext:
    """Context passed to plugins during execution."""

    def __init__(self, node_id: str, state: Dict[str, Any]):
        self.node_id = node_id
        self.state = state


def normalize_plugin_result(result: Any) -> PluginResult:
    """Ensure plugin outputs conform to the runtime PluginResult surface."""

    if result is None:
        return PluginResult()

    if isinstance(result, PluginResult):
        return result

    try:
        from src.platform.plugin import PluginResult as ContractPluginResult
    except Exception:  # pragma: no cover
        ContractPluginResult = None  # type: ignore[assignment]

    if ContractPluginResult is not None and isinstance(result, ContractPluginResult):
        return PluginResult(
            output=result.output,
            success=result.success,
            error=result.error,
            latency_ms=result.latency_ms,
            reason_code=result.reason_code,
            stage=result.stage,
            resource_usage=result.resource_usage,
        )

    if isinstance(result, dict):
        structured_keys = {
            "output",
            "artifacts",
            "trace",
            "success",
            "error",
            "latency_ms",
            "reason_code",
            "stage",
            "resource_usage",
        }
        if structured_keys.intersection(result.keys()):
            return PluginResult(
                output=result.get("output"),
                artifacts=list(result.get("artifacts", [])),
                trace=result.get("trace"),
                success=bool(result.get("success", True)),
                error=result.get("error"),
                latency_ms=int(result.get("latency_ms", 0) or 0),
                reason_code=result.get("reason_code"),
                stage=result.get("stage"),
                resource_usage=result.get("resource_usage"),
            )
        return PluginResult(output=result)

    return PluginResult(output=result)
