import json
from pathlib import Path

from src.cli.nexa_cli import main
from src.cli.savefile_runtime import is_savefile_contract
from src.storage.lifecycle_api import create_commit_snapshot_from_working_save
from src.storage.models.shared_sections import CircuitModel, ResourcesModel, StateModel
from src.storage.models.working_save_model import RuntimeModel, UIModel, WorkingSaveMeta, WorkingSaveModel
from src.storage.serialization import save_nex_artifact_file


def _working_save(*, name: str = "public_demo") -> WorkingSaveModel:
    return WorkingSaveModel(
        meta=WorkingSaveMeta(
            format_version="1.0.0",
            storage_role="working_save",
            working_save_id="public-demo-draft",
            name=name,
            description="public savefile",
        ),
        circuit=CircuitModel(
            entry="node1",
            nodes=[
                {
                    "id": "node1",
                    "type": "ai",
                    "resource_ref": {"prompt": "prompt.main", "provider": "provider.test"},
                    "inputs": {"name": "state.input.name"},
                    "outputs": {"result": "output.value"},
                }
            ],
            edges=[],
            outputs=[{"name": "result", "node_id": "node1", "path": "output.value"}],
        ),
        resources=ResourcesModel(
            prompts={"prompt.main": {"template": "Hello {{name}}"}},
            providers={"provider.test": {"type": "test", "model": "test-model", "config": {}}},
            plugins={},
        ),
        state=StateModel(input={"name": "Nexa"}, working={}, memory={}),
        runtime=RuntimeModel(status="draft", validation_summary={}, last_run={}, errors=[]),
        ui=UIModel(layout={}, metadata={"created_by": "test"}),
    )


def test_savefile_new_writes_public_working_save_payload(tmp_path, monkeypatch, capsys):
    out_path = tmp_path / "public_demo.nex"

    monkeypatch.setattr("sys.argv", ["nexa", "savefile", "new", str(out_path), "--name", "public_demo"])

    exit_code = main()

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "ok"
    assert payload["storage_role"] == "working_save"
    raw = json.loads(out_path.read_text(encoding="utf-8"))
    assert raw["meta"]["storage_role"] == "working_save"
    assert raw["meta"]["working_save_id"] == "public-demo-draft"
    assert raw["runtime"]["status"] == "draft"


def test_savefile_info_reports_public_commit_snapshot_summary(tmp_path, monkeypatch, capsys):
    working = _working_save()
    snapshot = create_commit_snapshot_from_working_save(working, commit_id="commit-001")
    in_path = tmp_path / "commit_snapshot.nex"
    save_nex_artifact_file(snapshot, in_path)

    monkeypatch.setattr("sys.argv", ["nexa", "savefile", "info", str(in_path)])

    exit_code = main()

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "ok"
    assert payload["storage_role"] == "commit_snapshot"
    assert payload["canonical_ref"] == "commit-001"
    assert payload["ui_layout_key_count"] == 0
    assert payload["ui_metadata_key_count"] == 0


def test_savefile_set_name_updates_public_working_save_in_place(tmp_path, monkeypatch, capsys):
    in_path = tmp_path / "public_edit.nex"
    save_nex_artifact_file(_working_save(), in_path)

    monkeypatch.setattr("sys.argv", ["nexa", "savefile", "set-name", str(in_path), "--name", "renamed_public"])

    exit_code = main()

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "ok"
    assert payload["name"] == "renamed_public"

    raw = json.loads(in_path.read_text(encoding="utf-8"))
    assert raw["meta"]["storage_role"] == "working_save"
    assert raw["meta"]["working_save_id"] == "public-demo-draft"
    assert raw["meta"]["name"] == "renamed_public"


def test_is_savefile_contract_accepts_public_commit_snapshot_payload(tmp_path):
    path = tmp_path / "commit_snapshot.nex"
    snapshot = create_commit_snapshot_from_working_save(_working_save(), commit_id="commit-001")
    save_nex_artifact_file(snapshot, path)

    assert is_savefile_contract(str(path)) is True


def test_engine_cli_run_public_working_save_emits_role_aware_summary(tmp_path, monkeypatch):
    circuit_path = tmp_path / "public_run.nex"
    out_path = tmp_path / "result.json"
    save_nex_artifact_file(_working_save(), circuit_path)

    monkeypatch.setattr("sys.argv", ["nexa", "run", str(circuit_path), "--out", str(out_path)])

    exit_code = main()

    assert exit_code == 0
    payload = json.loads(out_path.read_text(encoding="utf-8"))
    assert payload["storage_role"] == "working_save"
    assert payload["canonical_ref"] == "public-demo-draft"
    assert payload["replay_payload"]["circuit"]["id"] == "public_demo"
    assert payload["result"]["status"] == "success"


def test_engine_cli_run_public_commit_snapshot_emits_role_aware_summary(tmp_path, monkeypatch):
    circuit_path = tmp_path / "public_commit_run.nex"
    out_path = tmp_path / "result.json"
    snapshot = create_commit_snapshot_from_working_save(_working_save(), commit_id="commit-001")
    save_nex_artifact_file(snapshot, circuit_path)

    monkeypatch.setattr("sys.argv", ["nexa", "run", str(circuit_path), "--out", str(out_path)])

    exit_code = main()

    assert exit_code == 0
    payload = json.loads(out_path.read_text(encoding="utf-8"))
    assert payload["storage_role"] == "commit_snapshot"
    assert payload["canonical_ref"] == "commit-001"
    assert payload["replay_payload"]["circuit"]["id"] == "public_demo"
    assert payload["result"]["status"] == "success"
