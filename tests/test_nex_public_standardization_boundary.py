from __future__ import annotations

import pytest

from src.storage.lifecycle_api import create_commit_snapshot_from_working_save
from src.storage.models.shared_sections import CircuitModel, ResourcesModel, StateModel
from src.storage.models.working_save_model import RuntimeModel, UIModel, WorkingSaveMeta, WorkingSaveModel
from src.storage.nex_api import (
    checkout_public_nex_working_copy,
    describe_public_nex_artifact,
    export_public_nex_artifact,
    get_public_nex_format_boundary,
    import_public_nex_artifact,
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


def test_export_public_nex_artifact_rejects_unsupported_storage_role_on_dict_input() -> None:
    payload = export_public_nex_artifact(_working_save())
    payload["meta"]["storage_role"] = "not_a_real_role"

    with pytest.raises(ValueError, match="explicit meta.storage_role"):
        export_public_nex_artifact(payload)


def test_export_public_nex_artifact_error_surfaces_blocking_finding_detail() -> None:
    # Declaring commit_snapshot role but leaving runtime/ui in place is a
    # non-canonical surface; the coerce step must surface the underlying
    # blocking finding message (e.g. forbidden section) so external
    # standardization consumers can identify the cause programmatically.
    payload = export_public_nex_artifact(_working_save())
    payload["meta"]["storage_role"] = "commit_snapshot"

    with pytest.raises(ValueError) as exc:
        export_public_nex_artifact(payload)

    message = str(exc.value)
    assert "not loadable for export" in message
    # The blocking detail should be appended after the canonical prefix.
    assert ":" in message


def test_validate_working_save_does_not_silently_overwrite_conflicting_role() -> None:
    # Previously, validate_working_save dict-path silently coerced any
    # storage_role into working_save. That hid role confusion. The public
    # standardization boundary now requires role conflicts on a dict input
    # to surface as a WORKING_SAVE_ROLE_MISMATCH finding, symmetric with
    # validate_commit_snapshot.
    from src.storage.nex_api import validate_working_save

    payload = {
        "meta": {
            "format_version": "1.0.0",
            "storage_role": "commit_snapshot",
            "working_save_id": "ws-1",
            "name": "role_conflict",
        },
        "circuit": {"entry": "node1", "nodes": [], "edges": [], "outputs": []},
        "resources": {"prompts": {}, "providers": {}, "plugins": {}},
        "state": {"input": {}, "working": {}, "memory": {}},
        "runtime": {"status": "draft", "validation_summary": {}, "last_run": {}, "errors": []},
        "ui": {"layout": {}, "metadata": {}},
    }

    report = validate_working_save(payload)

    codes = {f.code for f in report.findings}
    assert "WORKING_SAVE_ROLE_MISMATCH" in codes
    assert report.result == "failed"


def test_validate_working_save_defaults_missing_role_to_working_save() -> None:
    # Role absent on dict input must continue to default to working_save
    # (legacy-compat parity). Only an explicit conflicting role now fails.
    from src.storage.nex_api import validate_working_save

    payload = {
        "meta": {
            "format_version": "1.0.0",
            "working_save_id": "ws-1",
            "name": "missing_role",
        },
        "circuit": {"entry": "node1", "nodes": [{"id": "node1", "type": "plugin"}], "edges": [], "outputs": [{"name": "r", "source": "state.working.r"}]},
        "resources": {"prompts": {}, "providers": {}, "plugins": {}},
        "state": {"input": {}, "working": {}, "memory": {}},
        "runtime": {"status": "draft", "validation_summary": {}, "last_run": {}, "errors": []},
        "ui": {"layout": {}, "metadata": {}},
    }

    report = validate_working_save(payload)

    codes = {f.code for f in report.findings}
    assert "WORKING_SAVE_ROLE_MISMATCH" not in codes


def test_public_nex_boundary_declares_canonical_import_and_checkout_entrypoints() -> None:
    operations = {entry.operation: entry for entry in get_public_nex_format_boundary().artifact_operation_boundaries}

    assert operations["import_copy"].canonical_api == "import_public_nex_artifact"
    assert operations["checkout_working_copy"].canonical_api == "checkout_public_nex_working_copy"


def test_import_public_nex_artifact_returns_role_preserving_canonical_copy() -> None:
    payload = export_public_nex_artifact(_working_save())
    payload["internal_note"] = {"debug": True}

    imported = import_public_nex_artifact(payload)

    assert isinstance(imported, WorkingSaveModel)
    assert imported.meta.storage_role == "working_save"
    assert imported.meta.working_save_id == "ws-public-1"
    assert not hasattr(imported, "internal_note")


def test_checkout_public_nex_working_copy_converts_public_commit_snapshot_to_working_save() -> None:
    snapshot = create_commit_snapshot_from_working_save(_working_save(), commit_id="commit-public-checkout")
    payload = export_public_nex_artifact(snapshot)

    working_copy = checkout_public_nex_working_copy(payload, working_save_id="ws-checkout-1")

    assert isinstance(working_copy, WorkingSaveModel)
    assert working_copy.meta.storage_role == "working_save"
    assert working_copy.meta.working_save_id == "ws-checkout-1"
    assert working_copy.meta.name == "public_demo"
    assert working_copy.runtime.status == "draft"


def test_checkout_public_nex_working_copy_rejects_working_save_source() -> None:
    with pytest.raises(ValueError, match="commit_snapshot source artifact"):
        checkout_public_nex_working_copy(_working_save())
