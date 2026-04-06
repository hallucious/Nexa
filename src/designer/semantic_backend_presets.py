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


_PRESET_SPECS: tuple[SemanticBackendPresetSpec, ...] = (
    SemanticBackendPresetSpec(
        preset="gpt",
        aliases=("openai", "gpt"),
        env_var_names=("OPENAI_API_KEY",),
        provider_name="designer.semantic.gpt",
    ),
    SemanticBackendPresetSpec(
        preset="claude",
        aliases=("anthropic", "claude"),
        env_var_names=("ANTHROPIC_API_KEY",),
        provider_name="designer.semantic.claude",
    ),
    SemanticBackendPresetSpec(
        preset="gemini",
        aliases=("google", "gemini"),
        env_var_names=("GEMINI_API_KEY", "GOOGLE_API_KEY"),
        provider_name="designer.semantic.gemini",
    ),
    SemanticBackendPresetSpec(
        preset="perplexity",
        aliases=("perplexity", "pplx"),
        env_var_names=("PERPLEXITY_API_KEY",),
        provider_name="designer.semantic.perplexity",
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
    env = env or os.environ
    available: list[str] = []
    for spec in _PRESET_SPECS:
        if any((env.get(name) or "").strip() for name in spec.env_var_names):
            available.append(spec.preset)
    return tuple(available)


def build_semantic_backend_from_preset(
    preset: str,
    *,
    providers: Mapping[str, Any] | None = None,
    provider_factories: Mapping[str, Callable[[], Any]] | None = None,
    temperature: float = 0.0,
    max_output_tokens: int = 1200,
    instructions: str | None = None,
    prompt_builder: Callable[[str, str, Mapping[str, Any]], str] | None = None,
) -> GenerateTextSemanticBackend:
    canonical = normalize_semantic_backend_preset(preset)
    spec = _PRESET_TO_SPEC[canonical]
    provider = _resolve_provider(canonical, providers=providers, provider_factories=provider_factories)
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
) -> Any:
    normalized_providers = _normalize_provider_mapping(providers or {})
    if canonical_preset in normalized_providers:
        return normalized_providers[canonical_preset]
    normalized_factories = _normalize_factory_mapping(provider_factories or {})
    factory = normalized_factories.get(canonical_preset)
    if factory is not None:
        return factory()
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
