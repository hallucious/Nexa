from __future__ import annotations

from typing import Any, Callable, Optional

from src.platform.plugin import Plugin, PluginResult as ContractPluginResult, safe_execute_plugin
from src.platform.plugin_auto_loader import load_plugin_entry
from src.platform.plugin_result import PluginResult, normalize_plugin_result


class _CallablePluginAdapter(Plugin):
    def __init__(self, *, plugin_name: str, plugin_callable: Callable[..., Any]) -> None:
        self.name = plugin_name
        self._plugin_callable = plugin_callable
        self.last_raw_result: Any = None

    def execute(self, **kwargs: Any) -> ContractPluginResult:
        call_kwargs = dict(kwargs)
        call_kwargs.pop("stage", None)
        raw_result = self._plugin_callable(**call_kwargs)
        self.last_raw_result = raw_result
        if isinstance(raw_result, ContractPluginResult):
            return raw_result
        compat = normalize_plugin_result(raw_result)
        return ContractPluginResult(
            success=compat.success,
            output=compat.output,
            error=compat.error,
            latency_ms=compat.latency_ms,
            reason_code=compat.reason_code,
            stage=kwargs.get("stage"),
            resource_usage=compat.resource_usage,
        )


def execute_plugin_callable(
    *,
    plugin_name: str,
    plugin_callable: Callable[..., Any],
    stage: str = "CORE",
    timeout_ms: Optional[int] = None,
    **kwargs: Any,
) -> PluginResult:
    """Execute a callable plugin through the canonical safe execution path."""
    adapter = _CallablePluginAdapter(
        plugin_name=plugin_name,
        plugin_callable=plugin_callable,
    )
    contract_result = safe_execute_plugin(
        plugin=adapter,
        timeout_ms=timeout_ms,
        stage=stage,
        **kwargs,
    )

    runtime_result = normalize_plugin_result(adapter.last_raw_result)
    runtime_result.success = contract_result.success
    runtime_result.error = contract_result.error
    runtime_result.latency_ms = contract_result.latency_ms
    runtime_result.reason_code = contract_result.reason_code
    runtime_result.stage = contract_result.stage
    runtime_result.resource_usage = contract_result.resource_usage

    if contract_result.output is not None and runtime_result.output is None:
        runtime_result.output = contract_result.output

    return runtime_result


def execute_plugin_entry(
    *,
    plugin_name: str,
    entry: str,
    stage: str = "CORE",
    timeout_ms: Optional[int] = None,
    **kwargs: Any,
) -> PluginResult:
    """Resolve an entry path and execute it through the canonical plugin executor."""
    plugin_callable = load_plugin_entry(entry)
    return execute_plugin_callable(
        plugin_name=plugin_name,
        plugin_callable=plugin_callable,
        stage=stage,
        timeout_ms=timeout_ms,
        **kwargs,
    )
