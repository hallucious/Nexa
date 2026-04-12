from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from typing import Any, Callable

from src.server.fastapi_binding_models import FastApiRouteDependencies


@dataclass
class InMemoryManagedSecretMetadataStore:
    _rows_by_secret_ref: dict[str, dict[str, Any]] = field(default_factory=dict)

    @staticmethod
    def _infer_secret_authority(secret_ref: str, metadata: Mapping[str, Any]) -> str | None:
        explicit = str(metadata.get("secret_authority") or "").strip()
        if explicit:
            return explicit
        normalized = str(secret_ref or "").strip()
        if normalized.startswith("aws-secretsmanager://"):
            return "aws_secrets_manager"
        if normalized.startswith("secret://"):
            return "managed"
        return None

    def write_receipt(self, receipt: Mapping[str, Any]) -> dict[str, Any]:
        secret_ref = str(receipt.get("secret_ref") or "").strip()
        secret_version_ref = str(receipt.get("secret_version_ref") or "").strip() or None
        last_rotated_at = str(receipt.get("last_rotated_at") or "").strip() or None
        if not secret_ref:
            raise ValueError("managed_secret_metadata_store.receipt_invalid")
        normalized = {
            "secret_ref": secret_ref,
            "secret_version_ref": secret_version_ref,
            "last_rotated_at": last_rotated_at,
            "secret_authority": self._infer_secret_authority(secret_ref, receipt),
        }
        self._rows_by_secret_ref[secret_ref] = normalized
        return dict(normalized)

    def read(self, secret_ref: str) -> dict[str, Any] | None:
        normalized_secret_ref = str(secret_ref or "").strip()
        row = self._rows_by_secret_ref.get(normalized_secret_ref)
        return dict(row) if row is not None else None


ManagedSecretWriter = Callable[[str, str, str, Mapping[str, Any]], Mapping[str, Any]]
ManagedSecretMetadataReader = Callable[[str], Mapping[str, Any] | None]


def bind_managed_secret_metadata_store(
    *,
    dependencies: FastApiRouteDependencies,
    store: InMemoryManagedSecretMetadataStore,
) -> FastApiRouteDependencies:
    base_writer = dependencies.managed_secret_writer
    base_reader = dependencies.managed_secret_metadata_reader

    def _writer(workspace_id: str, provider_key: str, secret_value: str, metadata: Mapping[str, Any]) -> Mapping[str, Any]:
        receipt = base_writer(workspace_id, provider_key, secret_value, metadata)
        store.write_receipt(receipt)
        return receipt

    def _reader(secret_ref: str) -> Mapping[str, Any] | None:
        local_row = store.read(secret_ref)
        if local_row is not None:
            return local_row
        if base_reader is not None:
            return base_reader(secret_ref)
        return None

    return replace(
        dependencies,
        managed_secret_writer=_writer,
        managed_secret_metadata_reader=_reader,
    )
