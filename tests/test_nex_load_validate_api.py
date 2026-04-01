from __future__ import annotations

import json
from pathlib import Path

from src.storage.nex_api import load_nex, validate_commit_snapshot, validate_working_save
from src.contracts.nex_contract import COMMIT_SNAPSHOT_ROLE, WORKING_SAVE_ROLE
from src.storage.models.commit_snapshot_model import CommitSnapshotModel
from src.storage.models.working_save_model import WorkingSaveModel


def _working_save_payload() -> dict:
    return {
        "meta": {
            "format_version": "0.1.0",
            "storage_role": "working_save",
            "working_save_id": "ws_001",
            "name": "demo",
        },
        "circuit": {
            "entry": "node1",
            "nodes": [
                {
                    "id": "node1",
                    "type": "plugin",
                    "resource_ref": {"plugin": "plugin.clean"},
                    "inputs": {"text": "state.input.text"},
                    "outputs": {"cleaned": "state.working.cleaned"},
                }
            ],
            "edges": [],
            "outputs": [{"name": "result", "source": "state.working.cleaned"}],
        },
        "resources": {
            "prompts": {},
            "providers": {},
            "plugins": {"plugin.clean": {"entry": "pkg.clean"}},
        },
        "state": {
            "input": {"text": "hello"},
            "working": {},
            "memory": {},
        },
        "runtime": {
            "status": "draft",
            "validation_summary": {},
            "last_run": {},
            "errors": [],
        },
        "ui": {"layout": {}, "metadata": {}},
    }



def _commit_snapshot_payload() -> dict:
    payload = _working_save_payload()
    payload["meta"] = {
        "format_version": "0.1.0",
        "storage_role": "commit_snapshot",
        "commit_id": "commit_001",
        "name": "approved demo",
    }
    payload.pop("runtime")
    payload.pop("ui")
    payload["validation"] = {
        "validation_result": "passed",
        "summary": {},
    }
    payload["approval"] = {
        "approval_completed": True,
        "approval_status": "approved",
        "summary": {},
    }
    payload["lineage"] = {
        "parent_commit_id": None,
        "source_working_save_id": "ws_001",
        "metadata": {},
    }
    return payload



def test_load_nex_loads_working_save_with_typed_model(tmp_path: Path) -> None:
    path = tmp_path / "working_save.nex"
    path.write_text(json.dumps(_working_save_payload()), encoding="utf-8")

    loaded = load_nex(path)

    assert loaded.storage_role == WORKING_SAVE_ROLE
    assert loaded.load_status == "loaded"
    assert isinstance(loaded.parsed_model, WorkingSaveModel)
    assert loaded.parsed_model.meta.working_save_id == "ws_001"



def test_load_nex_defaults_missing_storage_role_to_working_save() -> None:
    payload = _working_save_payload()
    payload["meta"].pop("storage_role")

    loaded = load_nex(payload)

    assert loaded.storage_role == WORKING_SAVE_ROLE
    assert loaded.load_status == "loaded"
    assert loaded.migration_notes == [
        "Missing meta.storage_role; defaulted to working_save for legacy compatibility"
    ]



def test_load_nex_allows_working_save_with_findings() -> None:
    payload = _working_save_payload()
    payload["circuit"].pop("entry")
    payload["circuit"]["outputs"] = []

    loaded = load_nex(payload)

    assert loaded.storage_role == WORKING_SAVE_ROLE
    assert loaded.load_status == "loaded_with_findings"
    assert isinstance(loaded.parsed_model, WorkingSaveModel)
    codes = {f.code for f in loaded.findings}
    assert "WORKING_SAVE_ENTRY_MISSING" in codes
    assert "WORKING_SAVE_OUTPUTS_MISSING" in codes



def test_load_nex_rejects_commit_snapshot_with_blocking_findings() -> None:
    payload = _commit_snapshot_payload()
    payload["approval"]["approval_completed"] = False

    loaded = load_nex(payload)

    assert loaded.storage_role == COMMIT_SNAPSHOT_ROLE
    assert loaded.load_status == "rejected"
    assert loaded.parsed_model is None
    codes = {f.code for f in loaded.findings}
    assert "COMMIT_SNAPSHOT_APPROVAL_INCOMPLETE" in codes



def test_validate_working_save_is_permissive_but_diagnostic() -> None:
    payload = _working_save_payload()
    payload["circuit"]["entry"] = None

    report = validate_working_save(payload)

    assert report.role == WORKING_SAVE_ROLE
    assert report.result == "failed"
    assert report.blocking_count >= 1
    codes = {f.code for f in report.findings}
    assert "WORKING_SAVE_ENTRY_MISSING" in codes



def test_validate_commit_snapshot_is_strict() -> None:
    payload = _commit_snapshot_payload()
    payload["validation"]["validation_result"] = "failed"

    report = validate_commit_snapshot(payload)

    assert report.role == COMMIT_SNAPSHOT_ROLE
    assert report.result == "failed"
    codes = {f.code for f in report.findings}
    assert "COMMIT_SNAPSHOT_VALIDATION_RESULT_INVALID" in codes



def test_load_nex_returns_loaded_with_findings_for_commit_snapshot_warnings_only() -> None:
    payload = _commit_snapshot_payload()
    payload["meta"]["description"] = "ok"

    loaded = load_nex(payload)

    assert loaded.storage_role == COMMIT_SNAPSHOT_ROLE
    assert loaded.load_status == "loaded"
    assert isinstance(loaded.parsed_model, CommitSnapshotModel)



def test_commit_snapshot_rejects_runtime_ui_designer_sections() -> None:
    payload = _commit_snapshot_payload()
    payload["runtime"] = {}
    payload["ui"] = {}
    payload["designer"] = {"pending": True}

    loaded = load_nex(payload)

    assert loaded.load_status == "rejected"
    codes = {f.code for f in loaded.findings}
    assert "COMMIT_SNAPSHOT_FORBIDDEN_SECTION_PRESENT" in codes
