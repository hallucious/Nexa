
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

# Step110: Plugin Artifact Emission Contract


@dataclass
class PluginResult:
    """Standard return contract for plugins."""

    output: Optional[Any] = None
    artifacts: List[Any] = field(default_factory=list)
    trace: Optional[Dict[str, Any]] = None


class PluginContext:
    """Context passed to plugins during execution."""

    def __init__(self, node_id: str, state: Dict[str, Any]):
        self.node_id = node_id
        self.state = state


def normalize_plugin_result(result: Any) -> PluginResult:
    """Ensure plugin outputs conform to PluginResult."""

    if result is None:
        return PluginResult()

    if isinstance(result, PluginResult):
        return result

    # allow dict-based result
    if isinstance(result, dict):
        return PluginResult(
            output=result.get("output"),
            artifacts=result.get("artifacts", []),
            trace=result.get("trace"),
        )

    # fallback: treat raw value as output
    return PluginResult(output=result)
