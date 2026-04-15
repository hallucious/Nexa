from __future__ import annotations

import pytest

from src.storage.lifecycle_api import create_commit_snapshot_from_working_save
from src.storage.models.shared_sections import CircuitModel, ResourcesModel, StateModel
from src.storage.models.working_save_model import RuntimeModel, UIModel, WorkingSaveMeta, WorkingSaveModel
from src.storage.nex_api import (
    describe_public_nex_artifact,
    export_public_nex_artifact,
    get_public_nex_format_boundary,
)


def _working_save() -> WorkingSaveModel:
    return WorkingSaveModel(
        meta=WorkingSaveMeta(
            format_version="1.0.0",
            storage_role="working_save",
            working_save_id="ws-public-1",
            name="public_demo",
        ),
        circuit=CircuitModel(
            entry="node1",
            nodes=[
                {
                    "id": "node1",
                    "type": "plugin",
                    "resource_ref": {"plugin": "plugin.main"},
                    "inputs": {"text": "state.input.text"},
                    "outputs": {"result": "output.value"},
                }
            ],
            edges=[],
            outputs=[{"name": "result", "node_id": "node1", "path": "output.value"}],
        ),
        resources=ResourcesModel(
            prompts={},
            providers={},
            plugins={"plugin.main": {"entry": "plugins.example.run", "config": {}}},
        ),
        state=StateModel(input={"text": "hello"}, working={}, memory={}),
        runtime=RuntimeModel(status="draft", validation_summary={}, last_run={}, errors=[]),
        ui=UIModel(layout={}, metadata={}),
    )


def test_get_public_nex_format_boundary_declares_role_specific_surface() -> None:
    boundary = get_public_nex_format_boundary()

    assert boundary.format_family == ".nex"
    assert boundary.shared_backbone_sections == ("meta", "circuit", "resources", "state")
    assert boundary.supported_roles == ("working_save", "commit_snapshot")
    assert boundary.legacy_default_role == "working_save"

    working = boundary.role_boundary("working_save")
    assert working.required_sections == ("meta", "circuit", "resources", "state", "runtime", "ui")
    assert working.optional_sections == ("designer",)
    assert working.forbidden_sections == ()
    assert working.identity_field == "working_save_id"

    commit = boundary.role_boundary("commit_snapshot")
    assert commit.required_sections == ("meta", "circuit", "resources", "state", "validation", "approval", "lineage")
    assert commit.optional_sections == ()
    assert commit.forbidden_sections == ("runtime", "ui", "designer")
    assert commit.identity_field == "commit_id"


def test_export_public_nex_artifact_canonicalizes_working_save_dict_surface() -> None:
    payload = export_public_nex_artifact(_working_save())
    payload["designer"] = {"pending": True}
    payload["internal_note"] = {"debug": True}

    exported = export_public_nex_artifact(payload)

    assert tuple(exported.keys()) == ("meta", "circuit", "resources", "state", "runtime", "ui", "designer")
    assert exported["meta"]["storage_role"] == "working_save"
    assert "internal_note" not in exported


def test_export_public_nex_artifact_requires_explicit_storage_role() -> None:
    payload = export_public_nex_artifact(_working_save())
    payload["meta"].pop("storage_role")

    with pytest.raises(ValueError, match="explicit meta.storage_role"):
        export_public_nex_artifact(payload)


def test_export_public_nex_artifact_rejects_non_canonical_commit_snapshot_surface() -> None:
    snapshot = create_commit_snapshot_from_working_save(_working_save(), commit_id="commit-public-1")
    payload = export_public_nex_artifact(snapshot)
    payload["ui"] = {"layout": {}, "metadata": {}}

    with pytest.raises(ValueError, match="not loadable for export"):
        export_public_nex_artifact(payload)


def test_describe_public_nex_artifact_returns_role_aware_identity() -> None:
    snapshot = create_commit_snapshot_from_working_save(_working_save(), commit_id="commit-public-1")

    descriptor = describe_public_nex_artifact(snapshot)

    assert descriptor.storage_role == "commit_snapshot"
    assert descriptor.canonical_ref == "commit-public-1"
    assert descriptor.identity_field == "commit_id"
    assert descriptor.required_sections == ("meta", "circuit", "resources", "state", "validation", "approval", "lineage")
    assert descriptor.forbidden_sections == ("runtime", "ui", "designer")
    assert descriptor.export_ready is True
    assert descriptor.source_working_save_id == "ws-public-1"
