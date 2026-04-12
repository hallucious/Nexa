from __future__ import annotations

import pytest

from src.server.fastapi_binding_models import FastApiRouteDependencies
from src.server.managed_secret_metadata_store import (
    InMemoryManagedSecretMetadataStore,
    bind_managed_secret_metadata_store,
)


def test_managed_secret_metadata_store_normalizes_and_reads_receipts() -> None:
    store = InMemoryManagedSecretMetadataStore()
    receipt = store.write_receipt({
        "secret_ref": "secret://ws-001/openai",
        "secret_version_ref": "v3",
        "last_rotated_at": "2026-04-11T12:05:00+00:00",
    })

    assert receipt["secret_authority"] == "managed"
    selected = store.read("secret://ws-001/openai")
    assert selected is not None
    assert selected["secret_version_ref"] == "v3"


def test_managed_secret_metadata_store_rejects_invalid_receipts() -> None:
    store = InMemoryManagedSecretMetadataStore()
    with pytest.raises(ValueError):
        store.write_receipt({"secret_version_ref": "v1"})


def test_bind_managed_secret_metadata_store_wires_writer_and_reader_dependencies() -> None:
    deps = bind_managed_secret_metadata_store(
        dependencies=FastApiRouteDependencies(
            managed_secret_writer=lambda workspace_id, provider_key, secret_value, metadata: {
                "secret_ref": f"secret://{workspace_id}/{provider_key}",
                "secret_version_ref": "v7",
                "last_rotated_at": str(metadata.get("now_iso") or "2026-04-11T12:00:00+00:00"),
            },
        ),
        store=InMemoryManagedSecretMetadataStore(),
    )

    receipt = deps.managed_secret_writer("ws-001", "openai", "secret-value", {"now_iso": "2026-04-11T12:09:00+00:00"})
    assert receipt["secret_version_ref"] == "v7"

    metadata = deps.managed_secret_metadata_reader("secret://ws-001/openai")
    assert metadata is not None
    assert metadata["secret_version_ref"] == "v7"
    assert metadata["last_rotated_at"] == "2026-04-11T12:09:00+00:00"



def test_managed_secret_metadata_store_lists_rows_in_reverse_chronological_order() -> None:
    store = InMemoryManagedSecretMetadataStore()
    store.write_receipt({
        'secret_ref': 'secret://workspace-alpha/openai',
        'secret_version_ref': 'v1',
        'last_rotated_at': '2026-04-12T10:00:00+00:00',
        'workspace_id': 'workspace-alpha',
        'provider_key': 'openai',
    })
    store.write_receipt({
        'secret_ref': 'secret://workspace-alpha/anthropic',
        'secret_version_ref': 'v2',
        'last_rotated_at': '2026-04-12T11:00:00+00:00',
        'workspace_id': 'workspace-alpha',
        'provider_key': 'anthropic',
    })

    rows = store.list_all_rows()

    assert [row['provider_key'] for row in rows] == ['anthropic', 'openai']
    assert rows[0]['workspace_id'] == 'workspace-alpha'
