from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Callable, Mapping

from src.designer.semantic_backend import GenerateTextSemanticBackend
from src.providers.env_diagnostics import (
    ProviderKeyResolution,
    ProviderAccessPathType,
    resolve_provider_key,
)


@dataclass(frozen=True)
class SemanticBackendPresetSpec:
    preset: str
    aliases: tuple[str, ...]
    env_var_names: tuple[str, ...]
    provider_name: str
    display_name: str


_PRESET_SPECS: tuple[SemanticBackendPresetSpec, ...] = (
    SemanticBackendPresetSpec(
        preset="gpt",
        aliases=("openai", "gpt"),
        env_var_names=("OPENAI_API_KEY",),
        provider_name="designer.semantic.gpt",
        display_name="OpenAI",
    ),
    SemanticBackendPresetSpec(
        preset="claude",
        aliases=("anthropic", "claude"),
        env_var_names=("ANTHROPIC_API_KEY",),
        provider_name="designer.semantic.claude",
        display_name="Claude",
    ),
    SemanticBackendPresetSpec(
        preset="gemini",
        aliases=("google", "gemini"),
        env_var_names=("GEMINI_API_KEY", "GOOGLE_API_KEY"),
        provider_name="designer.semantic.gemini",
        display_name="Gemini",
    ),
    SemanticBackendPresetSpec(
        preset="perplexity",
        aliases=("perplexity", "pplx"),
        env_var_names=("PERPLEXITY_API_KEY",),
        provider_name="designer.semantic.perplexity",
        display_name="Perplexity",
    ),
)

_ALIAS_TO_PRESET = {
    alias.lower(): spec.preset
    for spec in _PRESET_SPECS
    for alias in spec.aliases
}
_PRESET_TO_SPEC = {spec.preset: spec for spec in _PRESET_SPECS}


def supported_semantic_backend_presets() -> tuple[str, ...]:
    return tuple(spec.preset for spec in _PRESET_SPECS)


def normalize_semantic_backend_preset(value: str) -> str:
    normalized = (value or "").strip().lower()
    if not normalized:
        raise ValueError("semantic backend preset must be non-empty")
    canonical = _ALIAS_TO_PRESET.get(normalized)
    if canonical is None:
        supported = ", ".join(supported_semantic_backend_presets())
        raise ValueError(f"unknown semantic backend preset: {value!r}. Supported presets: {supported}")
    return canonical


def semantic_backend_preset_specs() -> Mapping[str, SemanticBackendPresetSpec]:
    return dict(_PRESET_TO_SPEC)


def available_semantic_backend_presets(*, env: Mapping[str, str] | None = None) -> tuple[str, ...]:
    env = os.environ if env is None else env
    available: list[str] = []
    for spec in _PRESET_SPECS:
        if any((env.get(name) or "").strip() for name in spec.env_var_names):
            available.append(spec.preset)
    return tuple(available)


def available_semantic_backend_presets_with_session(
    *,
    session_keys: Mapping[str, str] | None = None,
    env: Mapping[str, str] | None = None,
) -> tuple[str, ...]:
    """Return presets available via any path: session-injected key OR env var.

    This is the beginner-safe version of available_semantic_backend_presets().
    A preset is considered available if the user has supplied a key through the
    UI (session_keys) even when no env var is set.

    Args:
        session_keys: Mapping of preset → raw API key entered in the UI.
                      Keys are not stored persistently; they live only for the
                      current session.
        env:          Optional env override (defaults to os.environ).
    """
    session_keys = session_keys or {}
    env = os.environ if env is None else env
    available: list[str] = []
    for spec in _PRESET_SPECS:
        # Session-injected key takes priority
        if (session_keys.get(spec.preset) or "").strip():
            available.append(spec.preset)
            continue
        # Env var fallback
        if any((env.get(name) or "").strip() for name in spec.env_var_names):
            available.append(spec.preset)
    return tuple(available)


def resolve_semantic_backend_key(
    preset: str,
    *,
    session_key: str | None = None,
    env: Mapping[str, str] | None = None,
) -> ProviderKeyResolution:
    """Resolve an API key for a preset through the layered access path.

    Wraps env_diagnostics.resolve_provider_key() with preset-specific metadata.
    Callers receive a ProviderKeyResolution that describes both the resolved key
    and which path was used (session, env var, or .env file).
    """
    canonical = normalize_semantic_backend_preset(preset)
    spec = _PRESET_TO_SPEC[canonical]
    return resolve_provider_key(
        canonical,
        spec.env_var_names,
        session_key=session_key,
        env=env,
    )


def missing_semantic_backend_preset_env_vars(
    preset: str,
    *,
    env: Mapping[str, str] | None = None,
) -> tuple[str, ...]:
    canonical = normalize_semantic_backend_preset(preset)
    env = os.environ if env is None else env
    spec = _PRESET_TO_SPEC[canonical]
    if any((env.get(name) or "").strip() for name in spec.env_var_names):
        return ()
    return tuple(spec.env_var_names)


def semantic_backend_preset_is_available(
    preset: str,
    *,
    env: Mapping[str, str] | None = None,
) -> bool:
    return not missing_semantic_backend_preset_env_vars(preset, env=env)


def first_available_semantic_backend_preset(
    *,
    env: Mapping[str, str] | None = None,
) -> str | None:
    available = available_semantic_backend_presets(env=env)
    if not available:
        return None
    return available[0]


def build_semantic_backend_from_preset(
    preset: str,
    *,
    providers: Mapping[str, Any] | None = None,
    provider_factories: Mapping[str, Callable[[], Any]] | None = None,
    use_env_provider: bool = False,
    temperature: float = 0.0,
    max_output_tokens: int = 1200,
    instructions: str | None = None,
    prompt_builder: Callable[[str, str, Mapping[str, Any]], str] | None = None,
) -> GenerateTextSemanticBackend:
    canonical = normalize_semantic_backend_preset(preset)
    spec = _PRESET_TO_SPEC[canonical]
    provider = _resolve_provider(
        canonical,
        providers=providers,
        provider_factories=provider_factories,
        use_env_provider=use_env_provider,
    )
    return GenerateTextSemanticBackend(
        provider=provider,
        provider_name=spec.provider_name,
        temperature=temperature,
        max_output_tokens=max_output_tokens,
        instructions=instructions,
        prompt_builder=prompt_builder,
    )


def _resolve_provider(
    canonical_preset: str,
    *,
    providers: Mapping[str, Any] | None,
    provider_factories: Mapping[str, Callable[[], Any]] | None,
    use_env_provider: bool,
) -> Any:
    normalized_providers = _normalize_provider_mapping(providers or {})
    if canonical_preset in normalized_providers:
        return normalized_providers[canonical_preset]
    normalized_factories = _normalize_factory_mapping(provider_factories or {})
    factory = normalized_factories.get(canonical_preset)
    if factory is not None:
        return factory()
    if use_env_provider:
        return build_live_semantic_provider_from_preset(canonical_preset)
    raise ValueError(
        "No provider configured for semantic backend preset "
        f"{canonical_preset!r}. Supply semantic_backend_preset_providers or semantic_backend_preset_factories."
    )


def _normalize_provider_mapping(mapping: Mapping[str, Any]) -> dict[str, Any]:
    normalized: dict[str, Any] = {}
    for key, value in mapping.items():
        normalized[normalize_semantic_backend_preset(key)] = value
    return normalized


def _normalize_factory_mapping(mapping: Mapping[str, Callable[[], Any]]) -> dict[str, Callable[[], Any]]:
    normalized: dict[str, Callable[[], Any]] = {}
    for key, value in mapping.items():
        normalized[normalize_semantic_backend_preset(key)] = value
    return normalized


def build_live_semantic_provider_from_preset(preset: str) -> Any:
    """Build a real provider instance from environment-configured credentials.

    Network calls are still deferred until ``generate_text(...)`` is invoked.
    This keeps semantic backend wiring live-provider-ready without requiring
    callers to manually assemble provider objects.
    """

    canonical = normalize_semantic_backend_preset(preset)
    factory = _default_provider_factory_for_preset(canonical)
    return factory()


def semantic_backend_preset_factory_from_env(preset: str) -> Callable[[], Any]:
    canonical = normalize_semantic_backend_preset(preset)
    return _default_provider_factory_for_preset(canonical)


def build_semantic_backend_from_key(
    preset: str,
    api_key: str,
    *,
    temperature: float = 0.0,
    max_output_tokens: int = 1200,
    instructions: str | None = None,
    prompt_builder: Callable[[str, str, Mapping[str, Any]], str] | None = None,
) -> GenerateTextSemanticBackend:
    """Build a semantic backend from a directly-supplied API key.

    This is the beginner-safe entry point.  No env var lookup is performed;
    the caller supplies the key that the user entered in the UI.

    Typical flow:
      1. User selects a provider in the ProviderInlineKeyEntryView UI.
      2. User pastes their API key.
      3. UI calls resolve_semantic_backend_key(preset, session_key=pasted_key).
      4. If resolved, UI calls build_semantic_backend_from_key(preset, api_key).

    Args:
        preset:    Canonical preset name ("gpt", "claude", "gemini", "perplexity").
        api_key:   Raw API key entered by the user.
    """
    if not api_key or not api_key.strip():
        raise ValueError("api_key must be non-empty when building from inline key")
    canonical = normalize_semantic_backend_preset(preset)
    spec = _PRESET_TO_SPEC[canonical]
    provider = _build_provider_from_inline_key(canonical, api_key.strip())
    return GenerateTextSemanticBackend(
        provider=provider,
        provider_name=spec.provider_name,
        temperature=temperature,
        max_output_tokens=max_output_tokens,
        instructions=instructions,
        prompt_builder=prompt_builder,
    )


def build_semantic_backend_with_session(
    preset: str,
    *,
    session_key: str | None = None,
    env: Mapping[str, str] | None = None,
    temperature: float = 0.0,
    max_output_tokens: int = 1200,
    instructions: str | None = None,
    prompt_builder: Callable[[str, str, Mapping[str, Any]], str] | None = None,
) -> GenerateTextSemanticBackend:
    """Build a semantic backend through the full layered resolution path.

    Tries session_key first (beginner / UI path), then env var, then .env file.
    Raises ValueError if no key is available on any path.
    """
    resolution = resolve_semantic_backend_key(preset, session_key=session_key, env=env)
    if not resolution.access_path.resolved or not resolution.api_key:
        raise ValueError(
            f"No API key available for preset {preset!r}. "
            "Enter your key in the provider setup UI or set the corresponding environment variable."
        )
    if resolution.access_path.path_type == ProviderAccessPathType.SESSION_INJECTED:
        return build_semantic_backend_from_key(
            preset,
            resolution.api_key,
            temperature=temperature,
            max_output_tokens=max_output_tokens,
            instructions=instructions,
            prompt_builder=prompt_builder,
        )
    # env var or .env file — use existing env-based factory
    return build_semantic_backend_from_preset(
        preset,
        use_env_provider=True,
        temperature=temperature,
        max_output_tokens=max_output_tokens,
        instructions=instructions,
        prompt_builder=prompt_builder,
    )


def _build_provider_from_inline_key(canonical_preset: str, api_key: str) -> Any:
    """Build a provider instance using a directly-supplied API key."""
    if canonical_preset == "gpt":
        from src.providers.gpt_provider import GPTProvider
        return GPTProvider.from_api_key(api_key)
    if canonical_preset == "claude":
        from src.providers.claude_provider import ClaudeProvider
        return ClaudeProvider.from_api_key(api_key)
    if canonical_preset == "gemini":
        from src.providers.gemini_provider import GeminiProvider
        return GeminiProvider.from_api_key(api_key)
    if canonical_preset == "perplexity":
        from src.providers.perplexity_provider import PerplexityProvider
        return PerplexityProvider.from_api_key(api_key)
    supported = ", ".join(supported_semantic_backend_presets())
    raise ValueError(f"unknown semantic backend preset: {canonical_preset!r}. Supported presets: {supported}")


def _default_provider_factory_for_preset(canonical_preset: str) -> Callable[[], Any]:
    if canonical_preset == "gpt":
        from src.providers.gpt_provider import GPTProvider

        return GPTProvider.from_env
    if canonical_preset == "claude":
        from src.providers.claude_provider import ClaudeProvider

        return ClaudeProvider.from_env
    if canonical_preset == "gemini":
        from src.providers.gemini_provider import GeminiProvider

        return GeminiProvider.from_env
    if canonical_preset == "perplexity":
        from src.providers.perplexity_provider import PerplexityProvider

        return PerplexityProvider.from_env
    supported = ", ".join(supported_semantic_backend_presets())
    raise ValueError(f"unknown semantic backend preset: {canonical_preset!r}. Supported presets: {supported}")
