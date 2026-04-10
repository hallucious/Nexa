from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Callable, Mapping

from src.designer.semantic_backend import GenerateTextSemanticBackend


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
