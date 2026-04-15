from __future__ import annotations

import json

import pytest

from src.storage.lifecycle_api import create_commit_snapshot_from_working_save
from src.storage.models.shared_sections import CircuitModel, ResourcesModel, StateModel
from src.storage.models.working_save_model import RuntimeModel, UIModel, WorkingSaveMeta, WorkingSaveModel
from src.storage.share_api import (
    describe_public_nex_link_share,
    export_public_nex_link_share,
    get_public_nex_share_boundary,
    load_public_nex_link_share,
    save_public_nex_link_share_file,
)


def _working_save(*, name: str = "share_demo", description: str = "shareable artifact") -> WorkingSaveModel:
    return WorkingSaveModel(
        meta=WorkingSaveMeta(
            format_version="1.0.0",
            storage_role="working_save",
            working_save_id="ws-share-1",
            name=name,
            description=description,
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


def test_get_public_nex_share_boundary_declares_bounded_link_surface() -> None:
    boundary = get_public_nex_share_boundary()

    assert boundary.share_family == "nex.public-link-share"
    assert boundary.transport_modes == ("link",)
    assert boundary.access_modes == ("public_readonly",)
    assert boundary.supported_roles == ("working_save", "commit_snapshot")
    assert boundary.artifact_format_family == ".nex"
    assert boundary.viewer_capabilities == ("inspect_metadata", "download_artifact", "import_copy")


def test_export_public_nex_link_share_is_deterministic_for_same_artifact() -> None:
    share_a = export_public_nex_link_share(_working_save())
    share_b = export_public_nex_link_share(_working_save(), title="ignored title override")

    assert share_a["share"]["share_id"] == share_b["share"]["share_id"]
    assert share_a["share"]["transport"] == "link"
    assert share_a["share"]["access_mode"] == "public_readonly"
    assert share_a["share"]["storage_role"] == "working_save"
    assert share_a["artifact"]["meta"]["storage_role"] == "working_save"


def test_load_public_nex_link_share_round_trips_commit_snapshot() -> None:
    snapshot = create_commit_snapshot_from_working_save(_working_save(), commit_id="commit-share-1")
    payload = export_public_nex_link_share(snapshot, title="Published snapshot")

    loaded = load_public_nex_link_share(payload)
    descriptor = describe_public_nex_link_share(loaded)

    assert loaded["artifact"]["meta"]["storage_role"] == "commit_snapshot"
    assert descriptor.share_id == payload["share"]["share_id"]
    assert descriptor.share_path == f"/share/{descriptor.share_id}"
    assert descriptor.storage_role == "commit_snapshot"
    assert descriptor.canonical_ref == "commit-share-1"
    assert descriptor.source_working_save_id == "ws-share-1"


def test_load_public_nex_link_share_rejects_invalid_transport() -> None:
    payload = export_public_nex_link_share(_working_save())
    payload["share"]["transport"] = "file"

    with pytest.raises(ValueError, match="transport=link"):
        load_public_nex_link_share(payload)


def test_save_public_nex_link_share_file_writes_loadable_bundle(tmp_path) -> None:
    output_path = tmp_path / "public_share.json"

    written = save_public_nex_link_share_file(_working_save(), output_path)

    assert written == output_path
    raw = json.loads(output_path.read_text(encoding="utf-8"))
    loaded = load_public_nex_link_share(raw)
    assert loaded["share"]["share_id"].startswith("share_")
    assert loaded["share"]["title"] == "share_demo"
