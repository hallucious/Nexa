from __future__ import annotations

from src.storage.nex_api import load_nex
from src.storage.models.commit_snapshot_model import CommitSnapshotModel
from src.storage.models.working_save_model import WorkingSaveModel


def _minimal_working_save() -> dict:
    return {
        "meta": {
            "format_version": "0.1.0",
            "storage_role": "working_save",
            "working_save_id": "ws_123",
        },
        "circuit": {"nodes": [], "edges": [], "entry": None, "outputs": []},
        "resources": {"prompts": {}, "providers": {}, "plugins": {}},
        "state": {"input": {}, "working": {}, "memory": {}},
        "runtime": {"status": "draft", "validation_summary": {}, "last_run": {}, "errors": []},
        "ui": {"layout": {}, "metadata": {}},
    }



def _minimal_commit_snapshot() -> dict:
    return {
        "meta": {
            "format_version": "0.1.0",
            "storage_role": "commit_snapshot",
            "commit_id": "commit_123",
        },
        "circuit": {"nodes": [], "edges": [], "entry": "n1", "outputs": [{"name": "x", "source": "state.working.x"}]},
        "resources": {"prompts": {}, "providers": {}, "plugins": {}},
        "state": {"input": {}, "working": {}, "memory": {}},
        "validation": {"validation_result": "passed", "summary": {}},
        "approval": {"approval_completed": True, "approval_status": "approved", "summary": {}},
        "lineage": {"parent_commit_id": None, "metadata": {}},
    }



def test_load_nex_constructs_role_specific_model_types() -> None:
    working = load_nex(_minimal_working_save())
    commit = load_nex(_minimal_commit_snapshot())

    assert isinstance(working.parsed_model, WorkingSaveModel)
    assert isinstance(commit.parsed_model, CommitSnapshotModel)
    assert type(working.parsed_model) is not type(commit.parsed_model)



def test_working_save_model_keeps_runtime_and_ui() -> None:
    loaded = load_nex(_minimal_working_save())

    assert isinstance(loaded.parsed_model, WorkingSaveModel)
    assert loaded.parsed_model.runtime.status == "draft"
    assert loaded.parsed_model.ui.layout == {}



def test_commit_snapshot_model_keeps_approval_validation_lineage() -> None:
    loaded = load_nex(_minimal_commit_snapshot())

    assert isinstance(loaded.parsed_model, CommitSnapshotModel)
    assert loaded.parsed_model.validation.validation_result == "passed"
    assert loaded.parsed_model.approval.approval_completed is True
    assert loaded.parsed_model.lineage.parent_commit_id is None


def test_typed_models_preserve_subcircuits_when_present() -> None:
    payload = _minimal_working_save()
    payload["circuit"]["subcircuits"] = {
        "child": {"nodes": [], "edges": [], "outputs": []}
    }

    loaded = load_nex(payload)

    assert isinstance(loaded.parsed_model, WorkingSaveModel)
    assert loaded.parsed_model.circuit.subcircuits == {
        "child": {"nodes": [], "edges": [], "outputs": []}
    }
