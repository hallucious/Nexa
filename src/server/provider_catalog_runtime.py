from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Literal

ProviderPlanKey = Literal["free", "pro", "team"]
ProviderModelTier = Literal["economy", "standard"]
ProviderCatalogSource = Literal["canonical_catalog", "external", "cache", "workspace"]

_ALLOWED_PLAN_KEYS = {"free", "pro", "team"}
_ALLOWED_TIERS = {"economy", "standard"}

_PROVIDER_ALIASES: dict[str, str] = {
    "anthropic": "anthropic",
    "claude": "anthropic",
    "openai": "openai",
    "gpt": "openai",
}

_MODEL_ALIASES: dict[str, str] = {
    "haiku": "claude-haiku-3",
    "claude-haiku": "claude-haiku-3",
    "claude-haiku-3": "claude-haiku-3",
    "sonnet": "claude-sonnet-4",
    "claude-sonnet": "claude-sonnet-4",
    "claude-sonnet-4": "claude-sonnet-4",
    "gpt-4o": "gpt-4o",
    "openai-gpt-4o": "gpt-4o",
}


@dataclass(frozen=True)
class ProviderModelCatalogEntry:
    provider_key: str
    provider_family: str
    model_ref: str
    model_display_name: str
    tier: ProviderModelTier
    plan_availability: tuple[ProviderPlanKey, ...]
    default_for_plans: tuple[ProviderPlanKey, ...] = ()
    cost_ratio: float = 1.0
    pricing_unit: str = "relative_unit"
    managed_supported: bool = True
    recommended_scope: str = "workspace"
    local_env_var_hint: str | None = None
    default_secret_name_template: str | None = None
    lifecycle_state: str = "active"
    role: str | None = None
    updated_at: str | None = None

    def __post_init__(self) -> None:
        provider_key = normalize_provider_key(self.provider_key)
        model_ref = normalize_model_ref(self.model_ref)
        tier = str(self.tier or "").strip().lower()
        if tier not in _ALLOWED_TIERS:
            raise ValueError(f"Unsupported provider model tier: {self.tier!r}")
        plan_availability = tuple(normalize_plan_key(item) for item in self.plan_availability)
        default_for_plans = tuple(normalize_plan_key(item) for item in self.default_for_plans)
        if not plan_availability:
            raise ValueError("ProviderModelCatalogEntry.plan_availability must be non-empty")
        if self.cost_ratio <= 0:
            raise ValueError("ProviderModelCatalogEntry.cost_ratio must be positive")
        object.__setattr__(self, "provider_key", provider_key)
        object.__setattr__(self, "model_ref", model_ref)
        object.__setattr__(self, "tier", tier)
        object.__setattr__(self, "plan_availability", tuple(dict.fromkeys(plan_availability)))
        object.__setattr__(self, "default_for_plans", tuple(dict.fromkeys(default_for_plans)))

    @property
    def provider_model_key(self) -> str:
        return f"{self.provider_key}:{self.model_ref}"

    def to_row(self) -> dict[str, Any]:
        return {
            "provider_model_key": self.provider_model_key,
            "provider_key": self.provider_key,
            "provider_family": self.provider_family,
            "model_ref": self.model_ref,
            "model_display_name": self.model_display_name,
            "tier": self.tier,
            "plan_availability": self.plan_availability,
            "default_for_plans": self.default_for_plans,
            "cost_ratio": self.cost_ratio,
            "pricing_unit": self.pricing_unit,
            "managed_supported": self.managed_supported,
            "recommended_scope": self.recommended_scope,
            "local_env_var_hint": self.local_env_var_hint,
            "default_secret_name_template": self.default_secret_name_template,
            "lifecycle_state": self.lifecycle_state,
            "role": self.role,
            "updated_at": self.updated_at,
        }


@dataclass(frozen=True)
class ProviderModelAccessDecision:
    allowed: bool
    provider_key: str
    model_ref: str | None
    plan_key: ProviderPlanKey
    reason_code: str
    message: str
    selected_model_ref: str | None = None
    tier: str | None = None
    cost_ratio: float | None = None

    def to_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "allowed": self.allowed,
            "provider_key": self.provider_key,
            "plan_key": self.plan_key,
            "reason_code": self.reason_code,
            "message": self.message,
        }
        if self.model_ref:
            payload["model_ref"] = self.model_ref
        if self.selected_model_ref:
            payload["selected_model_ref"] = self.selected_model_ref
        if self.tier:
            payload["tier"] = self.tier
        if self.cost_ratio is not None:
            payload["cost_ratio"] = self.cost_ratio
        return payload


def normalize_plan_key(value: Any) -> ProviderPlanKey:
    normalized = str(value or "free").strip().lower()
    if normalized in {"starter", "basic"}:
        normalized = "free"
    if normalized not in _ALLOWED_PLAN_KEYS:
        raise ValueError(f"Unsupported provider plan key: {value!r}")
    return normalized  # type: ignore[return-value]


def normalize_provider_key(value: Any) -> str:
    normalized = str(value or "").strip().lower()
    if not normalized:
        raise ValueError("provider_key must be non-empty")
    if ":" in normalized:
        normalized = normalized.split(":", 1)[0].strip()
    return _PROVIDER_ALIASES.get(normalized, normalized)


def normalize_model_ref(value: Any) -> str:
    normalized = str(value or "").strip().lower()
    if not normalized:
        raise ValueError("model_ref must be non-empty")
    return _MODEL_ALIASES.get(normalized, normalized)


def _normalize_sequence(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        stripped = value.strip()
        return (stripped,) if stripped else ()
    return tuple(str(item).strip() for item in value if str(item).strip())


def _entry_from_row(row: Mapping[str, Any]) -> ProviderModelCatalogEntry:
    return ProviderModelCatalogEntry(
        provider_key=str(row.get("provider_key") or "").strip(),
        provider_family=str(row.get("provider_family") or row.get("provider_key") or "").strip(),
        model_ref=str(row.get("model_ref") or "").strip(),
        model_display_name=str(row.get("model_display_name") or row.get("model_ref") or "").strip(),
        tier=str(row.get("tier") or "economy").strip().lower(),  # type: ignore[arg-type]
        plan_availability=tuple(normalize_plan_key(item) for item in _normalize_sequence(row.get("plan_availability"))),
        default_for_plans=tuple(normalize_plan_key(item) for item in _normalize_sequence(row.get("default_for_plans"))),
        cost_ratio=float(row.get("cost_ratio") or 1.0),
        pricing_unit=str(row.get("pricing_unit") or "relative_unit").strip() or "relative_unit",
        managed_supported=bool(row.get("managed_supported", True)),
        recommended_scope=str(row.get("recommended_scope") or "workspace").strip() or "workspace",
        local_env_var_hint=str(row.get("local_env_var_hint") or "").strip() or None,
        default_secret_name_template=str(row.get("default_secret_name_template") or "").strip() or None,
        lifecycle_state=str(row.get("lifecycle_state") or "active").strip() or "active",
        role=str(row.get("role") or "").strip() or None,
        updated_at=str(row.get("updated_at") or "").strip() or None,
    )


_CANONICAL_PROVIDER_MODEL_ENTRIES: tuple[ProviderModelCatalogEntry, ...] = (
    ProviderModelCatalogEntry(
        provider_key="anthropic",
        provider_family="anthropic",
        model_ref="claude-haiku-3",
        model_display_name="Claude Haiku 3",
        tier="economy",
        plan_availability=("free", "pro", "team"),
        default_for_plans=("free", "pro", "team"),
        cost_ratio=1.0,
        local_env_var_hint="ANTHROPIC_API_KEY",
        default_secret_name_template="nexa/{workspace_id}/providers/anthropic",
        role="default low-cost baseline",
    ),
    ProviderModelCatalogEntry(
        provider_key="anthropic",
        provider_family="anthropic",
        model_ref="claude-sonnet-4",
        model_display_name="Claude Sonnet 4",
        tier="standard",
        plan_availability=("pro", "team"),
        cost_ratio=4.0,
        local_env_var_hint="ANTHROPIC_API_KEY",
        default_secret_name_template="nexa/{workspace_id}/providers/anthropic",
        role="higher quality standard path",
    ),
    ProviderModelCatalogEntry(
        provider_key="openai",
        provider_family="openai",
        model_ref="gpt-4o",
        model_display_name="GPT-4o",
        tier="standard",
        plan_availability=("pro", "team"),
        default_for_plans=("pro", "team"),
        cost_ratio=3.0,
        local_env_var_hint="OPENAI_API_KEY",
        default_secret_name_template="nexa/{workspace_id}/providers/openai",
        role="alternative standard path",
    ),
)


def default_provider_model_catalog_entries() -> tuple[ProviderModelCatalogEntry, ...]:
    return tuple(_CANONICAL_PROVIDER_MODEL_ENTRIES)


def default_provider_model_catalog_rows() -> tuple[dict[str, Any], ...]:
    return tuple(entry.to_row() for entry in default_provider_model_catalog_entries())


def _entries(rows: Sequence[Mapping[str, Any]] | None = None) -> tuple[ProviderModelCatalogEntry, ...]:
    if rows is None:
        return default_provider_model_catalog_entries()
    return tuple(_entry_from_row(row) for row in rows)


def provider_catalog_rows_from_model_catalog(rows: Sequence[Mapping[str, Any]] | None = None) -> tuple[dict[str, Any], ...]:
    grouped: dict[str, list[ProviderModelCatalogEntry]] = {}
    for entry in _entries(rows):
        if entry.lifecycle_state == "archived":
            continue
        grouped.setdefault(entry.provider_key, []).append(entry)

    provider_rows: list[dict[str, Any]] = []
    display_names = {
        "anthropic": "Anthropic Claude",
        "openai": "OpenAI GPT",
    }
    for provider_key, entries in sorted(grouped.items()):
        first = entries[0]
        default_entry = next((entry for entry in entries if "free" in entry.default_for_plans), None)
        if default_entry is None:
            default_entry = next((entry for entry in entries if entry.default_for_plans), entries[0])
        provider_rows.append(
            {
                "provider_key": provider_key,
                "provider_family": first.provider_family,
                "display_name": display_names.get(provider_key, first.provider_family),
                "managed_supported": any(entry.managed_supported for entry in entries),
                "recommended_scope": first.recommended_scope,
                "local_env_var_hint": first.local_env_var_hint,
                "default_secret_name_template": first.default_secret_name_template,
                "default_model_ref": default_entry.model_ref,
                "allowed_model_refs": tuple(entry.model_ref for entry in entries),
                "lifecycle_state": first.lifecycle_state,
                "updated_at": first.updated_at,
            }
        )
    return tuple(provider_rows)


def provider_cost_catalog_rows_from_model_catalog(rows: Sequence[Mapping[str, Any]] | None = None) -> tuple[dict[str, Any], ...]:
    return tuple(
        {
            "provider_model_key": entry.provider_model_key,
            "provider_key": entry.provider_key,
            "provider_family": entry.provider_family,
            "model_ref": entry.model_ref,
            "model_display_name": entry.model_display_name,
            "tier": entry.tier,
            "plan_availability": entry.plan_availability,
            "default_for_plans": entry.default_for_plans,
            "cost_ratio": entry.cost_ratio,
            "pricing_unit": entry.pricing_unit,
            "lifecycle_state": entry.lifecycle_state,
            "updated_at": entry.updated_at,
        }
        for entry in _entries(rows)
        if entry.lifecycle_state != "archived"
    )


def _catalog_by_provider_and_model(
    rows: Sequence[Mapping[str, Any]] | None = None,
) -> dict[tuple[str, str], ProviderModelCatalogEntry]:
    resolved: dict[tuple[str, str], ProviderModelCatalogEntry] = {}
    for entry in _entries(rows):
        if entry.lifecycle_state == "archived":
            continue
        resolved[(entry.provider_key, entry.model_ref)] = entry
    return resolved


def resolve_default_model_for_provider(
    provider_key: str,
    *,
    plan_key: str = "free",
    catalog_rows: Sequence[Mapping[str, Any]] | None = None,
) -> ProviderModelCatalogEntry | None:
    normalized_provider = normalize_provider_key(provider_key)
    normalized_plan = normalize_plan_key(plan_key)
    candidates = [
        entry
        for entry in _entries(catalog_rows)
        if entry.provider_key == normalized_provider
        and entry.lifecycle_state != "archived"
        and normalized_plan in entry.plan_availability
    ]
    if not candidates:
        return None
    explicit_default = next((entry for entry in candidates if normalized_plan in entry.default_for_plans), None)
    if explicit_default is not None:
        return explicit_default
    # If the plan has access but no explicit provider-local default, pick the
    # cheapest available model to keep preflight behavior conservative.
    return sorted(candidates, key=lambda item: (item.cost_ratio, item.model_ref))[0]


def resolve_provider_model_access(
    *,
    provider_key: str,
    model_ref: str | None = None,
    plan_key: str = "free",
    catalog_rows: Sequence[Mapping[str, Any]] | None = None,
) -> ProviderModelAccessDecision:
    try:
        normalized_provider = normalize_provider_key(provider_key)
        normalized_plan = normalize_plan_key(plan_key)
    except ValueError as exc:
        return ProviderModelAccessDecision(
            allowed=False,
            provider_key=str(provider_key or "").strip().lower(),
            model_ref=str(model_ref or "").strip().lower() or None,
            plan_key="free",
            reason_code="provider_model_access.invalid_input",
            message=str(exc),
        )

    selected_entry: ProviderModelCatalogEntry | None
    selected_model_ref: str | None
    if model_ref is None or not str(model_ref).strip():
        selected_entry = resolve_default_model_for_provider(
            normalized_provider,
            plan_key=normalized_plan,
            catalog_rows=catalog_rows,
        )
        selected_model_ref = selected_entry.model_ref if selected_entry is not None else None
    else:
        try:
            selected_model_ref = normalize_model_ref(model_ref)
        except ValueError as exc:
            return ProviderModelAccessDecision(
                allowed=False,
                provider_key=normalized_provider,
                model_ref=str(model_ref or "").strip().lower() or None,
                selected_model_ref=None,
                plan_key=normalized_plan,
                reason_code="provider_model_access.invalid_model_ref",
                message=str(exc),
            )
        selected_entry = _catalog_by_provider_and_model(catalog_rows).get((normalized_provider, selected_model_ref))

    if selected_entry is None:
        return ProviderModelAccessDecision(
            allowed=False,
            provider_key=normalized_provider,
            model_ref=str(model_ref or "").strip().lower() or None,
            selected_model_ref=selected_model_ref,
            plan_key=normalized_plan,
            reason_code="provider_model_access.model_not_in_catalog",
            message="Requested provider/model is not part of the canonical provider catalog.",
        )

    if normalized_plan not in selected_entry.plan_availability:
        return ProviderModelAccessDecision(
            allowed=False,
            provider_key=normalized_provider,
            model_ref=str(model_ref or "").strip().lower() or None,
            selected_model_ref=selected_entry.model_ref,
            plan_key=normalized_plan,
            reason_code="provider_model_access.plan_not_allowed",
            message="The current plan cannot use the requested AI model.",
            tier=selected_entry.tier,
            cost_ratio=selected_entry.cost_ratio,
        )

    return ProviderModelAccessDecision(
        allowed=True,
        provider_key=normalized_provider,
        model_ref=str(model_ref or "").strip().lower() or None,
        selected_model_ref=selected_entry.model_ref,
        plan_key=normalized_plan,
        reason_code="provider_model_access.allowed",
        message="Provider/model access is allowed by the canonical catalog.",
        tier=selected_entry.tier,
        cost_ratio=selected_entry.cost_ratio,
    )


def resolve_provider_model_cost(
    *,
    provider_key: str,
    model_ref: str | None = None,
    catalog_rows: Sequence[Mapping[str, Any]] | None = None,
) -> ProviderModelCatalogEntry | None:
    normalized_provider = normalize_provider_key(provider_key)
    if model_ref is None or not str(model_ref).strip():
        return resolve_default_model_for_provider(normalized_provider, plan_key="free", catalog_rows=catalog_rows) or resolve_default_model_for_provider(normalized_provider, plan_key="pro", catalog_rows=catalog_rows)
    normalized_model_ref = normalize_model_ref(model_ref)
    return _catalog_by_provider_and_model(catalog_rows).get((normalized_provider, normalized_model_ref))



@dataclass(frozen=True)
class ProviderModelRequirement:
    provider_key: str
    model_ref: str | None = None
    source_ref: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "provider_key", normalize_provider_key(self.provider_key))
        if self.model_ref is not None and str(self.model_ref).strip():
            object.__setattr__(self, "model_ref", normalize_model_ref(self.model_ref))
        else:
            object.__setattr__(self, "model_ref", None)


def _as_mapping(value: Any) -> Mapping[str, Any] | None:
    return value if isinstance(value, Mapping) else None


def _source_components(source_payload: Any) -> tuple[Sequence[Mapping[str, Any]], Mapping[str, Any], Mapping[str, Any]]:
    # Local imports keep the catalog runtime independent of storage imports for
    # basic provider catalog use.
    try:
        from src.storage.models.commit_snapshot_model import CommitSnapshotModel
        from src.storage.models.loaded_nex_artifact import LoadedNexArtifact
        from src.storage.models.working_save_model import WorkingSaveModel
    except Exception:  # pragma: no cover - storage modules are normally present.
        CommitSnapshotModel = WorkingSaveModel = LoadedNexArtifact = ()  # type: ignore[assignment]

    if "LoadedNexArtifact" in locals() and isinstance(source_payload, LoadedNexArtifact):  # type: ignore[arg-type]
        source_payload = source_payload.parsed_model if source_payload.parsed_model is not None else source_payload.raw
    if "WorkingSaveModel" in locals() and isinstance(source_payload, WorkingSaveModel | CommitSnapshotModel):  # type: ignore[arg-type]
        return (
            tuple(node for node in source_payload.circuit.nodes if isinstance(node, Mapping)),
            source_payload.resources.providers,
            source_payload.circuit.subcircuits,
        )

    payload = _as_mapping(source_payload) or {}
    circuit = _as_mapping(payload.get("circuit")) or {}
    resources = _as_mapping(payload.get("resources")) or {}
    subcircuits = _as_mapping(payload.get("subcircuits")) or _as_mapping(circuit.get("subcircuits")) or {}
    nodes = tuple(node for node in (circuit.get("nodes") or ()) if isinstance(node, Mapping))
    providers = _as_mapping(resources.get("providers")) or {}
    return nodes, providers, subcircuits


def _provider_resource_map(resources_providers: Mapping[str, Any]) -> dict[str, tuple[str, str | None]]:
    resolved: dict[str, tuple[str, str | None]] = {}
    for raw_ref, raw_payload in resources_providers.items():
        ref = str(raw_ref or "").strip()
        if not ref:
            continue
        payload = _as_mapping(raw_payload) or {}
        candidates = (
            payload.get("provider_key"),
            payload.get("managed_provider_key"),
            payload.get("provider_family"),
            payload.get("provider_id"),
            payload.get("provider_ref"),
            payload.get("provider"),
            payload.get("family"),
            payload.get("backend"),
            payload.get("type"),
            payload.get("vendor"),
            payload.get("display_name"),
            ref,
        )
        provider_key = None
        for candidate in candidates:
            try:
                provider_key = normalize_provider_key(candidate)
                if provider_key in {"anthropic", "openai"}:
                    break
            except ValueError:
                continue
        if provider_key is None:
            continue
        model_candidate = (
            payload.get("model_ref")
            or payload.get("model")
            or payload.get("model_id")
            or payload.get("default_model_ref")
        )
        model_ref = None
        if str(model_candidate or "").strip():
            try:
                model_ref = normalize_model_ref(model_candidate)
            except ValueError:
                model_ref = str(model_candidate).strip().lower() or None
        resolved[ref] = (provider_key, model_ref)
    return resolved


def _requirements_from_nodes(
    nodes: Sequence[Mapping[str, Any]],
    *,
    provider_resource_map: Mapping[str, tuple[str, str | None]],
    subcircuits: Mapping[str, Any],
    seen_child_refs: set[str],
) -> list[ProviderModelRequirement]:
    requirements: list[ProviderModelRequirement] = []
    for node in nodes:
        resource_ref = _as_mapping(node.get("resource_ref")) or {}
        execution = _as_mapping(node.get("execution")) or {}
        provider_exec = _as_mapping(execution.get("provider")) or {}

        provider_ref = (
            resource_ref.get("provider")
            or node.get("provider_ref")
            or provider_exec.get("provider_id")
            or provider_exec.get("provider_ref")
        )
        model_ref = (
            provider_exec.get("model_ref")
            or provider_exec.get("model")
            or provider_exec.get("model_id")
            or node.get("model_ref")
            or node.get("model")
        )

        provider_key = None
        resource_model_ref = None
        provider_ref_text = str(provider_ref or "").strip()
        if provider_ref_text in provider_resource_map:
            provider_key, resource_model_ref = provider_resource_map[provider_ref_text]
        if provider_key is None:
            try:
                provider_key = normalize_provider_key(provider_ref)
            except ValueError:
                provider_key = None

        if provider_key is not None:
            effective_model_ref = str(model_ref or resource_model_ref or "").strip() or None
            requirements.append(
                ProviderModelRequirement(
                    provider_key=provider_key,
                    model_ref=effective_model_ref,
                    source_ref=str(node.get("node_id") or provider_ref_text or "").strip() or None,
                )
            )

        node_kind = str(node.get("kind") or node.get("type") or "").strip().lower()
        if node_kind != "subcircuit":
            continue
        subcircuit_exec = _as_mapping(execution.get("subcircuit")) or {}
        child_ref = str(subcircuit_exec.get("child_circuit_ref") or "").strip()
        if not child_ref or not child_ref.startswith("internal:") or child_ref in seen_child_refs:
            continue
        child_name = child_ref.split(":", 1)[1]
        child_payload = _as_mapping(subcircuits.get(child_name)) or _as_mapping(subcircuits.get(child_ref))
        if child_payload is None:
            continue
        seen_child_refs.add(child_ref)
        child_nodes = tuple(item for item in (child_payload.get("nodes") or ()) if isinstance(item, Mapping))
        nested_subcircuits = _as_mapping(child_payload.get("subcircuits")) or subcircuits
        requirements.extend(
            _requirements_from_nodes(
                child_nodes,
                provider_resource_map=provider_resource_map,
                subcircuits=nested_subcircuits,
                seen_child_refs=seen_child_refs,
            )
        )
    return requirements


def extract_provider_model_requirements(source_payload: Any) -> tuple[ProviderModelRequirement, ...]:
    nodes, resources_providers, subcircuits = _source_components(source_payload)
    provider_map = _provider_resource_map(resources_providers)
    requirements = _requirements_from_nodes(
        nodes,
        provider_resource_map=provider_map,
        subcircuits=subcircuits,
        seen_child_refs=set(),
    )
    # Deduplicate while preserving deterministic order.
    seen: set[tuple[str, str | None, str | None]] = set()
    unique: list[ProviderModelRequirement] = []
    for requirement in requirements:
        key = (requirement.provider_key, requirement.model_ref, requirement.source_ref)
        if key in seen:
            continue
        seen.add(key)
        unique.append(requirement)
    return tuple(unique)


def evaluate_provider_model_access_for_artifact(
    *,
    source_payload: Any,
    plan_key: str = "free",
    catalog_rows: Sequence[Mapping[str, Any]] | None = None,
) -> tuple[ProviderModelAccessDecision, ...]:
    decisions: list[ProviderModelAccessDecision] = []
    for requirement in extract_provider_model_requirements(source_payload):
        decisions.append(
            resolve_provider_model_access(
                provider_key=requirement.provider_key,
                model_ref=requirement.model_ref,
                plan_key=plan_key,
                catalog_rows=catalog_rows,
            )
        )
    return tuple(decisions)

__all__ = [
    "ProviderModelAccessDecision",
    "ProviderModelCatalogEntry",
    "ProviderModelRequirement",
    "default_provider_model_catalog_entries",
    "default_provider_model_catalog_rows",
    "normalize_model_ref",
    "normalize_plan_key",
    "normalize_provider_key",
    "provider_catalog_rows_from_model_catalog",
    "provider_cost_catalog_rows_from_model_catalog",
    "resolve_default_model_for_provider",
    "resolve_provider_model_access",
    "resolve_provider_model_cost",
    "extract_provider_model_requirements",
    "evaluate_provider_model_access_for_artifact",
]
