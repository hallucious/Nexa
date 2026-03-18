
from __future__ import annotations

from typing import Any, Dict

from src.platform.execution_config_registry import (
    ExecutionConfigRefError,
    resolve_execution_config,
)


def validate_execution_config_ref(ref: str) -> None:
    """Validate exact hash-only NodeSpec reference.

    NodeSpec must use:
        ec_<hash>

    Version suffixes are intentionally forbidden at the NodeSpec layer.
    """
    if not isinstance(ref, str) or not ref:
        raise ExecutionConfigRefError("execution_config_ref must be non-empty string")

    if not ref.startswith("ec_"):
        raise ExecutionConfigRefError(
            "execution_config_ref must use exact hash artifact id (ec_<hash>)"
        )

    if len(ref) <= 3:
        raise ExecutionConfigRefError(
            "execution_config_ref missing hash portion after 'ec_'"
        )

    if ":" in ref:
        raise ExecutionConfigRefError(
            "execution_config_ref must not contain version suffix"
        )


class NodeSpecResolver:
    """Resolve NodeSpec execution_config_ref using ExecutionConfigRegistry."""

    def __init__(self, registry):
        self.registry = registry

    def resolve(self, node_spec: Dict[str, Any]):
        if "execution_config_ref" in node_spec:
            ref = node_spec["execution_config_ref"]
        elif "execution_config" in node_spec:
            ref = node_spec["execution_config"]
        else:
            raise ValueError("NodeSpec missing execution_config reference")

        validate_execution_config_ref(ref)

        return resolve_execution_config(ref, registry=self.registry)
