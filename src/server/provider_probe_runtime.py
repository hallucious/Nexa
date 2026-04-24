from __future__ import annotations

from collections.abc import Callable
from typing import Optional

from src.providers.claude_provider import ClaudeProvider
from src.providers.codex_provider import CodexProvider
from src.providers.gemini_provider import GeminiProvider
from src.providers.gpt_provider import GPTProvider
from src.providers.perplexity_provider import PerplexityProvider
from src.providers.provider_adapter_contract import ProviderResult
from src.server.provider_probe_api import ProviderProbeRunner
from src.server.provider_probe_models import (
    ProductProviderProbeFindingView,
    ProviderProbeExecutionInput,
    ProviderProbeExecutionResult,
)

SecretValueReader = Callable[[str], Optional[str]]

_DEFAULT_TIMEOUT_MS = 10000
_MAX_TIMEOUT_MS = 60000
_MIN_TIMEOUT_SEC = 1


def _normalized_provider_name(provider_key: str, provider_family: str) -> str:
    key = str(provider_key or "").strip().lower()
    family = str(provider_family or "").strip().lower()
    return key or family


def _effective_model_ref(probe_input: ProviderProbeExecutionInput) -> str:
    requested = str(probe_input.requested_model_ref or "").strip()
    if requested:
        return requested
    default = str(probe_input.default_model_ref or "").strip()
    if default:
        return default
    return ""


def _normalized_timeout_sec(timeout_ms: Optional[int]) -> int:
    try:
        resolved_ms = int(timeout_ms) if timeout_ms is not None else _DEFAULT_TIMEOUT_MS
    except Exception:
        resolved_ms = _DEFAULT_TIMEOUT_MS
    resolved_ms = max(1000, min(resolved_ms, _MAX_TIMEOUT_MS))
    return max(_MIN_TIMEOUT_SEC, int((resolved_ms + 999) / 1000))


def _probe_prompt(probe_input: ProviderProbeExecutionInput) -> str:
    explicit = str(probe_input.probe_message or "").strip()
    if explicit:
        return explicit
    return "Connectivity probe for Nexa managed provider binding. Reply with exactly OK."


def _failure_connectivity_state(reason_code: Optional[str], error_text: str) -> str:
    normalized_reason = str(reason_code or "").strip()
    lowered = error_text.lower()
    if normalized_reason == "AI.timeout":
        return "timeout"
    if normalized_reason == "AI.provider_error":
        auth_markers = (
            "401",
            "403",
            "unauthorized",
            "forbidden",
            "invalid api key",
            "authentication",
            "incorrect api key",
            "access denied",
        )
        if any(marker in lowered for marker in auth_markers):
            return "auth_failed"
        transport_markers = (
            "dns",
            "ssl",
            "connection reset",
            "name or service not known",
            "timed out",
            "connection refused",
        )
        if any(marker in lowered for marker in transport_markers):
            return "transport_error"
        return "provider_error"
    return "unknown"


def _failure_finding(reason_code: str, connectivity_state: str, message: str) -> ProductProviderProbeFindingView:
    severity = "warning"
    field_name: Optional[str] = None
    if reason_code in {
        "provider_probe.secret_value_unavailable",
        "provider_probe.provider_family_unsupported",
        "provider_probe.secret_read_failed",
    }:
        severity = "blocked"
        field_name = "secret_ref"
    elif connectivity_state == "auth_failed":
        severity = "blocked"
        field_name = "secret_ref"
    elif connectivity_state in {"provider_error", "transport_error", "timeout"}:
        severity = "warning"
        field_name = "provider_key"
    return ProductProviderProbeFindingView(
        severity=severity,
        reason_code=reason_code,
        message=message,
        field_name=field_name,
    )


def _provider_from_api_key(*, provider_key: str, provider_family: str, api_key: str, model_ref: str, timeout_sec: int):
    normalized = _normalized_provider_name(provider_key, provider_family)
    if normalized in {"openai", "gpt"}:
        return GPTProvider(api_key, model=model_ref or "gpt-5.2", timeout_sec=timeout_sec)
    if normalized in {"anthropic", "claude"}:
        return ClaudeProvider(api_key, model=model_ref or ClaudeProvider.DEFAULT_MODEL, timeout_sec=timeout_sec)
    if normalized in {"google", "gemini"}:
        return GeminiProvider(api_key, model=model_ref or "gemini-2.5-pro")
    if normalized == "perplexity":
        return PerplexityProvider(api_key, model=model_ref or PerplexityProvider.DEFAULT_MODEL, timeout_sec=timeout_sec)
    if normalized == "codex":
        return CodexProvider(api_key, model=model_ref or CodexProvider.DEFAULT_MODEL, timeout_sec=timeout_sec)
    raise ValueError(f"provider_probe.provider_family_unsupported:{normalized or 'unknown'}")


def _success_result(result: ProviderResult, *, effective_model_ref: str) -> ProviderProbeExecutionResult:
    message = "Provider connectivity probe succeeded."
    if not str(result.text or "").strip():
        message = "Provider returned an empty probe response."
        return ProviderProbeExecutionResult(
            probe_status="warning",
            connectivity_state="unknown",
            message=message,
            reason_code="provider_probe.empty_response",
            effective_model_ref=effective_model_ref or None,
            round_trip_latency_ms=result.metrics.latency_ms,
            findings=(
                ProductProviderProbeFindingView(
                    severity="warning",
                    reason_code="provider_probe.empty_response",
                    message=message,
                    field_name="provider_key",
                ),
            ),
        )
    return ProviderProbeExecutionResult(
        probe_status="reachable",
        connectivity_state="ok",
        message=message,
        reason_code=None,
        effective_model_ref=effective_model_ref or None,
        round_trip_latency_ms=result.metrics.latency_ms,
    )


def _failure_result(*, reason_code: str, error_text: str, effective_model_ref: str, latency_ms: Optional[int] = None) -> ProviderProbeExecutionResult:
    connectivity_state = _failure_connectivity_state(reason_code, error_text)
    message = error_text.strip() or "Provider connectivity probe failed."
    return ProviderProbeExecutionResult(
        probe_status="failed" if connectivity_state != "unknown" else "blocked",
        connectivity_state=connectivity_state,
        message=message,
        reason_code=reason_code,
        effective_model_ref=effective_model_ref or None,
        round_trip_latency_ms=latency_ms,
        findings=(_failure_finding(reason_code, connectivity_state, message),),
    )


def run_provider_probe(
    probe_input: ProviderProbeExecutionInput,
    *,
    secret_value_reader: Optional[SecretValueReader] = None,
) -> ProviderProbeExecutionResult:
    effective_model_ref = _effective_model_ref(probe_input)
    if secret_value_reader is None:
        return ProviderProbeExecutionResult(
            probe_status="blocked",
            connectivity_state="unknown",
            message="Provider probe secret-value resolution is not configured for this server.",
            reason_code="provider_probe.secret_value_unavailable",
            effective_model_ref=effective_model_ref or None,
            findings=(
                ProductProviderProbeFindingView(
                    severity="blocked",
                    reason_code="provider_probe.secret_value_unavailable",
                    message="Provider probe secret-value resolution is not configured for this server.",
                    field_name="secret_ref",
                ),
            ),
        )
    try:
        secret_value = secret_value_reader(probe_input.secret_ref)
    except Exception as exc:  # noqa: BLE001
        return ProviderProbeExecutionResult(
            probe_status="blocked",
            connectivity_state="unknown",
            message=f"Managed secret value could not be read for provider probe: {type(exc).__name__}: {exc}",
            reason_code="provider_probe.secret_read_failed",
            effective_model_ref=effective_model_ref or None,
            findings=(
                ProductProviderProbeFindingView(
                    severity="blocked",
                    reason_code="provider_probe.secret_read_failed",
                    message="Managed secret value could not be read for provider probe.",
                    field_name="secret_ref",
                ),
            ),
        )
    if not str(secret_value or "").strip():
        return ProviderProbeExecutionResult(
            probe_status="blocked",
            connectivity_state="unknown",
            message="Managed secret value is unavailable for provider probe execution.",
            reason_code="provider_probe.secret_value_unavailable",
            effective_model_ref=effective_model_ref or None,
            findings=(
                ProductProviderProbeFindingView(
                    severity="blocked",
                    reason_code="provider_probe.secret_value_unavailable",
                    message="Managed secret value is unavailable for provider probe execution.",
                    field_name="secret_ref",
                ),
            ),
        )
    try:
        provider = _provider_from_api_key(
            provider_key=probe_input.provider_key,
            provider_family=probe_input.provider_family,
            api_key=str(secret_value).strip(),
            model_ref=effective_model_ref,
            timeout_sec=_normalized_timeout_sec(probe_input.timeout_ms),
        )
    except ValueError:
        return ProviderProbeExecutionResult(
            probe_status="blocked",
            connectivity_state="unknown",
            message="Provider family is not supported by the managed probe runner.",
            reason_code="provider_probe.provider_family_unsupported",
            effective_model_ref=effective_model_ref or None,
            findings=(
                ProductProviderProbeFindingView(
                    severity="blocked",
                    reason_code="provider_probe.provider_family_unsupported",
                    message="Provider family is not supported by the managed probe runner.",
                    field_name="provider_key",
                ),
            ),
        )

    result = provider.generate_text(
        prompt=_probe_prompt(probe_input),
        temperature=0.0,
        max_output_tokens=16,
        stream=False,
    )
    if result.success:
        return _success_result(result, effective_model_ref=effective_model_ref)
    return _failure_result(
        reason_code=str(result.reason_code or "AI.provider_error"),
        error_text=str(result.error or "Provider connectivity probe failed."),
        effective_model_ref=effective_model_ref,
        latency_ms=result.metrics.latency_ms,
    )


def build_provider_probe_runner(*, secret_value_reader: Optional[SecretValueReader] = None) -> ProviderProbeRunner:
    def _runner(probe_input: ProviderProbeExecutionInput) -> ProviderProbeExecutionResult:
        return run_provider_probe(probe_input, secret_value_reader=secret_value_reader)

    return _runner
