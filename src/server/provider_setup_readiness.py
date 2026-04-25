from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Mapping, Optional, Sequence

from src.storage.models.commit_snapshot_model import CommitSnapshotModel
from src.storage.models.loaded_nex_artifact import LoadedNexArtifact
from src.storage.models.working_save_model import WorkingSaveModel

_MANAGED_PROVIDER_ALIASES = {
    "openai": "openai",
    "gpt": "openai",
    "anthropic": "anthropic",
    "claude": "anthropic",
    "gemini": "gemini",
    "google": "gemini",
    "perplexity": "perplexity",
    "pplx": "perplexity",
    "codex": "codex",
}

_GOOD_PROBE_STATUSES = {"reachable", "warning"}


@dataclass(frozen=True)
class ProviderSetupBlockingFinding:
    provider_key: str
    reason_code: str
    message: str
    display_name: Optional[str] = None
    probe_status: Optional[str] = None

    def to_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "severity": "blocked",
            "reason_code": self.reason_code,
            "message": self.message,
            "provider_key": self.provider_key,
        }
        if self.display_name:
            payload["display_name"] = self.display_name
        if self.probe_status:
            payload["probe_status"] = self.probe_status
        return payload


@dataclass(frozen=True)
class ProviderSetupReadiness:
    required_provider_keys: tuple[str, ...] = ()
    ready_provider_keys: tuple[str, ...] = ()
    blocking_findings: tuple[ProviderSetupBlockingFinding, ...] = ()

    @property
    def requires_provider_setup(self) -> bool:
        return bool(self.blocking_findings)

    @property
    def primary_finding(self) -> ProviderSetupBlockingFinding | None:
        return self.blocking_findings[0] if self.blocking_findings else None


def infer_managed_provider_key(value: Any) -> str | None:
    normalized = str(value or "").strip().lower()
    if not normalized:
        return None
    if normalized in _MANAGED_PROVIDER_ALIASES:
        return _MANAGED_PROVIDER_ALIASES[normalized]
    tokens = tuple(token for token in re.split(r"[^a-z0-9]+", normalized) if token)
    if not tokens:
        return None
    for priority_tokens, provider_key in (
        (("codex",), "codex"),
        (("gemini", "google"), "gemini"),
        (("anthropic", "claude"), "anthropic"),
        (("perplexity", "pplx"), "perplexity"),
        (("openai", "gpt"), "openai"),
    ):
        if any(token in priority_tokens for token in tokens):
            return provider_key
    return None


def _row_timestamp(row: Mapping[str, Any] | None, *field_names: str) -> str:
    if row is None:
        return ""
    for field_name in field_names:
        value = str(row.get(field_name) or "").strip()
        if value:
            return value
    return ""


def _latest_row(rows: Sequence[Mapping[str, Any]], *field_names: str) -> Mapping[str, Any] | None:
    latest: Mapping[str, Any] | None = None
    latest_key = ""
    for row in rows:
        key = _row_timestamp(row, *field_names)
        if latest is None or key >= latest_key:
            latest = row
            latest_key = key
    return latest


def _as_mapping(value: Any) -> Mapping[str, Any] | None:
    return value if isinstance(value, Mapping) else None


def _resource_provider_key_map(resources_providers: Mapping[str, Any]) -> dict[str, str]:
    resolved: dict[str, str] = {}
    candidate_field_names = (
        "provider_key",
        "managed_provider_key",
        "provider_family",
        "provider_id",
        "provider_ref",
        "provider",
        "family",
        "backend",
        "type",
        "engine",
        "vendor",
        "display_name",
        "name",
    )
    nested_field_names = ("provider", "config", "metadata", "runtime")
    for raw_ref, raw_payload in resources_providers.items():
        ref = str(raw_ref or "").strip()
        if not ref:
            continue
        candidates: list[Any] = [ref]
        payload = _as_mapping(raw_payload)
        if payload is not None:
            for field_name in candidate_field_names:
                candidates.append(payload.get(field_name))
            for nested_name in nested_field_names:
                nested = _as_mapping(payload.get(nested_name))
                if nested is None:
                    continue
                for field_name in candidate_field_names:
                    candidates.append(nested.get(field_name))
        provider_key = next((candidate for candidate in (infer_managed_provider_key(item) for item in candidates) if candidate is not None), None)
        if provider_key is not None:
            resolved[ref] = provider_key
    return resolved


def _artifact_components(source_payload: Any) -> tuple[Sequence[Mapping[str, Any]], Mapping[str, Any], Mapping[str, Any]]:
    if isinstance(source_payload, LoadedNexArtifact):
        source_payload = source_payload.parsed_model if source_payload.parsed_model is not None else source_payload.raw
    if isinstance(source_payload, WorkingSaveModel | CommitSnapshotModel):
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


def _required_provider_keys_from_nodes(
    nodes: Sequence[Mapping[str, Any]],
    *,
    provider_key_map: Mapping[str, str],
    subcircuits: Mapping[str, Any],
    seen_child_refs: set[str],
) -> set[str]:
    required: set[str] = set()
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
        provider_key = provider_key_map.get(str(provider_ref or "").strip()) or infer_managed_provider_key(provider_ref)
        if provider_key is not None:
            required.add(provider_key)

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
        required.update(
            _required_provider_keys_from_nodes(
                child_nodes,
                provider_key_map=provider_key_map,
                subcircuits=nested_subcircuits,
                seen_child_refs=seen_child_refs,
            )
        )
    return required


def extract_required_provider_keys(source_payload: Any) -> tuple[str, ...]:
    nodes, resources_providers, subcircuits = _artifact_components(source_payload)
    provider_key_map = _resource_provider_key_map(resources_providers)
    required = _required_provider_keys_from_nodes(
        nodes,
        provider_key_map=provider_key_map,
        subcircuits=subcircuits,
        seen_child_refs=set(),
    )
    return tuple(sorted(required))


def evaluate_required_provider_setup(
    *,
    workspace_id: str,
    source_payload: Any,
    provider_binding_rows: Sequence[Mapping[str, Any]] = (),
    managed_secret_rows: Sequence[Mapping[str, Any]] = (),
    provider_probe_rows: Sequence[Mapping[str, Any]] = (),
) -> ProviderSetupReadiness:
    required_provider_keys = extract_required_provider_keys(source_payload)
    if not required_provider_keys:
        return ProviderSetupReadiness(required_provider_keys=())

    ready_provider_keys: list[str] = []
    blocking_findings: list[ProviderSetupBlockingFinding] = []

    for provider_key in required_provider_keys:
        binding_candidates = [
            row
            for row in provider_binding_rows
            if str(row.get("workspace_id") or "").strip() == workspace_id
            and str(row.get("provider_key") or "").strip().lower() == provider_key
        ]
        binding_row = _latest_row(binding_candidates, "updated_at", "created_at")
        display_name = str((binding_row or {}).get("display_name") or provider_key).strip() or provider_key
        if binding_row is None:
            blocking_findings.append(
                ProviderSetupBlockingFinding(
                    provider_key=provider_key,
                    display_name=display_name,
                    reason_code="launch.provider_binding_missing",
                    message=f"The required AI model ({display_name}) is not connected for this workspace yet.",
                )
            )
            continue

        if not bool(binding_row.get("enabled", True)):
            blocking_findings.append(
                ProviderSetupBlockingFinding(
                    provider_key=provider_key,
                    display_name=display_name,
                    reason_code="launch.provider_binding_disabled",
                    message=f"The required AI model ({display_name}) is currently disabled for this workspace.",
                )
            )
            continue

        credential_source = str(binding_row.get("credential_source") or "managed").strip().lower() or "managed"
        if credential_source != "managed":
            blocking_findings.append(
                ProviderSetupBlockingFinding(
                    provider_key=provider_key,
                    display_name=display_name,
                    reason_code="launch.provider_credential_source_unsupported",
                    message=f"The required AI model ({display_name}) uses an unsupported credential path for product launch.",
                )
            )
            continue

        secret_ref = str(binding_row.get("secret_ref") or "").strip()
        if not secret_ref:
            blocking_findings.append(
                ProviderSetupBlockingFinding(
                    provider_key=provider_key,
                    display_name=display_name,
                    reason_code="launch.provider_secret_missing",
                    message=f"The required AI model ({display_name}) is missing its managed secret reference.",
                )
            )
            continue

        secret_candidates = [
            row
            for row in managed_secret_rows
            if str(row.get("workspace_id") or "").strip() == workspace_id
            and (
                str(row.get("secret_ref") or "").strip() == secret_ref
                or str(row.get("provider_key") or "").strip().lower() == provider_key
            )
        ]
        secret_row = _latest_row(secret_candidates, "last_rotated_at", "updated_at", "created_at")
        if secret_row is None:
            blocking_findings.append(
                ProviderSetupBlockingFinding(
                    provider_key=provider_key,
                    display_name=display_name,
                    reason_code="launch.provider_secret_unresolved",
                    message=f"The required AI model ({display_name}) could not resolve its managed secret.",
                )
            )
            continue

        probe_candidates = [
            row
            for row in provider_probe_rows
            if str(row.get("workspace_id") or "").strip() == workspace_id
            and str(row.get("provider_key") or "").strip().lower() == provider_key
        ]
        latest_probe = _latest_row(probe_candidates, "occurred_at", "updated_at", "created_at")
        if latest_probe is not None:
            probe_timestamp = _row_timestamp(latest_probe, "occurred_at", "updated_at", "created_at")
            binding_timestamp = _row_timestamp(binding_row, "updated_at", "created_at")
            secret_timestamp = _row_timestamp(secret_row, "last_rotated_at", "updated_at", "created_at")
            probe_is_stale = bool(
                probe_timestamp
                and (
                    (binding_timestamp and probe_timestamp < binding_timestamp)
                    or (secret_timestamp and probe_timestamp < secret_timestamp)
                )
            )
            probe_status = str(latest_probe.get("probe_status") or "").strip().lower()
            if not probe_is_stale and probe_status and probe_status not in _GOOD_PROBE_STATUSES:
                blocking_findings.append(
                    ProviderSetupBlockingFinding(
                        provider_key=provider_key,
                        display_name=display_name,
                        reason_code="launch.provider_probe_failed",
                        message=f"The required AI model ({display_name}) failed the latest connectivity check.",
                        probe_status=probe_status,
                    )
                )
                continue

        ready_provider_keys.append(provider_key)

    return ProviderSetupReadiness(
        required_provider_keys=required_provider_keys,
        ready_provider_keys=tuple(sorted(ready_provider_keys)),
        blocking_findings=tuple(blocking_findings),
    )
