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


def test_engine_cli_run_public_working_save_materializes_source_artifact_identity(tmp_path, monkeypatch):
    circuit_path = tmp_path / "public_identity_run.nex"
    out_path = tmp_path / "result.json"
    save_nex_artifact_file(_working_save(), circuit_path)

    monkeypatch.setattr("sys.argv", ["nexa", "run", str(circuit_path), "--out", str(out_path)])

    exit_code = main()

    assert exit_code == 0
    payload = json.loads(out_path.read_text(encoding="utf-8"))
    assert payload["source_artifact"]["storage_role"] == "working_save"
    assert payload["source_artifact"]["canonical_ref"] == "public-demo-draft"
    assert payload["source_artifact"]["working_save_id"] == "public-demo-draft"
    assert payload["execution_record"]["source"]["working_save_id"] == "public-demo-draft"
    assert payload["execution_record"]["source"]["commit_id"].startswith("uncommitted::")
    assert payload["replay_payload"]["source_artifact"]["working_save_id"] == "public-demo-draft"


def test_engine_cli_run_public_commit_snapshot_materializes_source_artifact_identity(tmp_path, monkeypatch):
    circuit_path = tmp_path / "public_commit_identity_run.nex"
    out_path = tmp_path / "result.json"
    snapshot = create_commit_snapshot_from_working_save(_working_save(), commit_id="commit-001")
    save_nex_artifact_file(snapshot, circuit_path)

    monkeypatch.setattr("sys.argv", ["nexa", "run", str(circuit_path), "--out", str(out_path)])

    exit_code = main()

    assert exit_code == 0
    payload = json.loads(out_path.read_text(encoding="utf-8"))
    assert payload["source_artifact"]["storage_role"] == "commit_snapshot"
    assert payload["source_artifact"]["canonical_ref"] == "commit-001"
    assert payload["source_artifact"]["commit_id"] == "commit-001"
    assert payload["source_artifact"]["working_save_id"] == "public-demo-draft"
    assert payload["execution_record"]["source"]["commit_id"] == "commit-001"
    assert payload["execution_record"]["source"]["working_save_id"] == "public-demo-draft"
    assert payload["replay_payload"]["source_artifact"]["commit_id"] == "commit-001"



def test_savefile_commit_converts_public_working_save_to_public_commit_snapshot(tmp_path, monkeypatch, capsys):
    in_path = tmp_path / "public_working_save.nex"
    out_path = tmp_path / "public_commit_snapshot.nex"
    save_nex_artifact_file(_working_save(), in_path)

    monkeypatch.setattr(
        "sys.argv",
        [
            "nexa",
            "savefile",
            "commit",
            str(in_path),
            str(out_path),
            "--commit-id",
            "commit-002",
        ],
    )

    exit_code = main()

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "ok"
    assert payload["storage_role"] == "commit_snapshot"
    assert payload["canonical_ref"] == "commit-002"
    assert payload["source_working_save_id"] == "public-demo-draft"
    raw = json.loads(out_path.read_text(encoding="utf-8"))
    assert raw["meta"]["storage_role"] == "commit_snapshot"
    assert raw["meta"]["commit_id"] == "commit-002"
    assert raw["meta"]["source_working_save_id"] == "public-demo-draft"



def test_savefile_commit_converts_legacy_savefile_to_public_commit_snapshot(tmp_path, monkeypatch, capsys):
    from src.contracts.savefile_factory import make_minimal_savefile
    from src.contracts.savefile_serializer import save_savefile_file

    in_path = tmp_path / "legacy_input.nex"
    out_path = tmp_path / "legacy_commit_snapshot.nex"
    legacy = make_minimal_savefile(
        name="legacy_demo",
        version="1.0.0",
        entry="node1",
        node_type="plugin",
        resource_ref={"plugin": "plugin.main"},
        outputs={"result": "output.value"},
        circuit_outputs=[{"name": "result", "node_id": "node1", "path": "output.value"}],
        plugins={"plugin.main": {"entry": "plugins.example.run", "config": {}}},
    )
    save_savefile_file(legacy, str(in_path))

    monkeypatch.setattr(
        "sys.argv",
        [
            "nexa",
            "savefile",
            "commit",
            str(in_path),
            str(out_path),
            "--commit-id",
            "commit-legacy-001",
        ],
    )

    exit_code = main()

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "ok"
    assert payload["input_mode"] == "legacy"
    raw = json.loads(out_path.read_text(encoding="utf-8"))
    assert raw["meta"]["storage_role"] == "commit_snapshot"
    assert raw["meta"]["commit_id"] == "commit-legacy-001"
    assert raw["meta"]["source_working_save_id"]



def test_savefile_commit_rejects_public_commit_snapshot_input(tmp_path, monkeypatch, capsys):
    in_path = tmp_path / "already_committed.nex"
    out_path = tmp_path / "ignored_output.nex"
    snapshot = create_commit_snapshot_from_working_save(_working_save(), commit_id="commit-003")
    save_nex_artifact_file(snapshot, in_path)

    monkeypatch.setattr(
        "sys.argv",
        [
            "nexa",
            "savefile",
            "commit",
            str(in_path),
            str(out_path),
            "--commit-id",
            "commit-004",
        ],
    )

    exit_code = main()

    assert exit_code == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "error"
    assert payload["subcommand"] == "commit"
    assert "working_save artifacts" in payload["message"]



def test_savefile_checkout_converts_public_commit_snapshot_to_public_working_save(tmp_path, monkeypatch, capsys):
    in_path = tmp_path / "public_commit_snapshot.nex"
    out_path = tmp_path / "checked_out_working_save.nex"
    snapshot = create_commit_snapshot_from_working_save(_working_save(), commit_id="commit-010")
    save_nex_artifact_file(snapshot, in_path)

    monkeypatch.setattr(
        "sys.argv",
        [
            "nexa",
            "savefile",
            "checkout",
            str(in_path),
            str(out_path),
            "--working-save-id",
            "restored-ws-010",
        ],
    )

    exit_code = main()

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "ok"
    assert payload["input_mode"] == "public_commit_snapshot"
    assert payload["storage_role"] == "working_save"
    assert payload["working_save_id"] == "restored-ws-010"
    assert payload["source_commit_id"] == "commit-010"
    raw = json.loads(out_path.read_text(encoding="utf-8"))
    assert raw["meta"]["storage_role"] == "working_save"
    assert raw["meta"]["working_save_id"] == "restored-ws-010"
    assert raw["runtime"]["status"] == "draft"



def test_savefile_checkout_rejects_public_working_save_input(tmp_path, monkeypatch, capsys):
    in_path = tmp_path / "public_working_save.nex"
    out_path = tmp_path / "ignored_checkout.nex"
    save_nex_artifact_file(_working_save(), in_path)

    monkeypatch.setattr(
        "sys.argv",
        [
            "nexa",
            "savefile",
            "checkout",
            str(in_path),
            str(out_path),
        ],
    )

    exit_code = main()

    assert exit_code == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "error"
    assert payload["subcommand"] == "checkout"
    assert "commit_snapshot artifacts" in payload["message"]



def test_savefile_upgrade_converts_legacy_savefile_to_public_working_save(tmp_path, monkeypatch, capsys):
    from src.contracts.savefile_factory import make_minimal_savefile
    from src.contracts.savefile_serializer import save_savefile_file

    in_path = tmp_path / "legacy_input.nex"
    out_path = tmp_path / "upgraded_working_save.nex"
    legacy = make_minimal_savefile(
        name="legacy_upgrade_demo",
        version="1.0.0",
        entry="node1",
        node_type="plugin",
        resource_ref={"plugin": "plugin.main"},
        outputs={"result": "output.value"},
        circuit_outputs=[{"name": "result", "node_id": "node1", "path": "output.value"}],
        plugins={"plugin.main": {"entry": "plugins.example.run", "config": {}}},
    )
    save_savefile_file(legacy, str(in_path))

    monkeypatch.setattr(
        "sys.argv",
        [
            "nexa",
            "savefile",
            "upgrade",
            str(in_path),
            str(out_path),
            "--working-save-id",
            "legacy-upgrade-ws",
        ],
    )

    exit_code = main()

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "ok"
    assert payload["input_mode"] == "legacy"
    assert payload["storage_role"] == "working_save"
    assert payload["working_save_id"] == "legacy-upgrade-ws"
    raw = json.loads(out_path.read_text(encoding="utf-8"))
    assert raw["meta"]["storage_role"] == "working_save"
    assert raw["meta"]["working_save_id"] == "legacy-upgrade-ws"



def test_savefile_upgrade_rejects_public_artifact_input(tmp_path, monkeypatch, capsys):
    in_path = tmp_path / "public_input.nex"
    out_path = tmp_path / "ignored_upgrade.nex"
    save_nex_artifact_file(_working_save(), in_path)

    monkeypatch.setattr(
        "sys.argv",
        [
            "nexa",
            "savefile",
            "upgrade",
            str(in_path),
            str(out_path),
        ],
    )

    exit_code = main()

    assert exit_code == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "error"
    assert payload["subcommand"] == "upgrade"
    assert "legacy savefiles" in payload["message"]


def test_savefile_share_export_writes_public_link_share_payload(tmp_path, monkeypatch, capsys):
    artifact_path = tmp_path / "public_share_source.nex"
    share_path = tmp_path / "public_share.json"
    save_nex_artifact_file(_working_save(name="share_source"), artifact_path)

    monkeypatch.setattr(
        "sys.argv",
        ["nexa", "savefile", "share", "export", str(artifact_path), str(share_path), "--title", "Shared Demo", "--expires-at", "2026-04-20T00:00:00+00:00", "--issued-by-user-ref", "user-owner"],
    )

    exit_code = main()

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "ok"
    assert payload["share_id"].startswith("share_")
    assert payload["storage_role"] == "working_save"
    raw = json.loads(share_path.read_text(encoding="utf-8"))
    assert raw["share"]["transport"] == "link"
    assert raw["share"]["title"] == "Shared Demo"
    assert payload["operation_capabilities"] == ["inspect_metadata", "download_artifact", "import_copy", "run_artifact"]
    assert payload["stored_lifecycle_state"] == "active"
    assert payload["lifecycle_state"] == "active"
    assert payload["expires_at"] == "2026-04-20T00:00:00+00:00"
    assert payload["issued_by_user_ref"] == "user-owner"
    assert raw["share"]["lifecycle"]["state"] == "active"
    assert raw["artifact"]["meta"]["storage_role"] == "working_save"


def test_savefile_info_reports_public_link_share_summary(tmp_path, monkeypatch, capsys):
    artifact_path = tmp_path / "public_share_source.nex"
    share_path = tmp_path / "public_share.json"
    save_nex_artifact_file(_working_save(name="share_source"), artifact_path)

    monkeypatch.setattr("sys.argv", ["nexa", "savefile", "share", "export", str(artifact_path), str(share_path)])
    assert main() == 0
    capsys.readouterr()

    monkeypatch.setattr("sys.argv", ["nexa", "savefile", "info", str(share_path)])
    exit_code = main()

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["input_mode"] == "public_link_share"
    assert payload["share_id"].startswith("share_")
    assert payload["storage_role"] == "working_save"
    assert payload["viewer_capabilities"] == ["inspect_metadata", "download_artifact", "import_copy"]
    assert payload["operation_capabilities"] == ["inspect_metadata", "download_artifact", "import_copy", "run_artifact"]
    assert payload["stored_lifecycle_state"] == "active"
    assert payload["lifecycle_state"] == "active"


def test_savefile_share_import_materializes_public_artifact(tmp_path, monkeypatch, capsys):
    artifact_path = tmp_path / "public_commit_source.nex"
    share_path = tmp_path / "public_share.json"
    imported_path = tmp_path / "imported_snapshot.nex"
    snapshot = create_commit_snapshot_from_working_save(_working_save(name="share_source"), commit_id="commit-share-import")
    save_nex_artifact_file(snapshot, artifact_path)

    monkeypatch.setattr("sys.argv", ["nexa", "savefile", "share", "export", str(artifact_path), str(share_path)])
    assert main() == 0
    capsys.readouterr()

    monkeypatch.setattr("sys.argv", ["nexa", "savefile", "share", "import", str(share_path), str(imported_path)])
    exit_code = main()

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["input_mode"] == "public_share"
    assert payload["storage_role"] == "commit_snapshot"
    raw = json.loads(imported_path.read_text(encoding="utf-8"))
    assert raw["meta"]["storage_role"] == "commit_snapshot"
    assert raw["meta"]["commit_id"] == "commit-share-import"


def test_engine_cli_run_public_link_share_emits_share_identity(tmp_path, monkeypatch):
    artifact_path = tmp_path / "public_run_source.nex"
    share_path = tmp_path / "public_share.json"
    out_path = tmp_path / "result.json"
    save_nex_artifact_file(_working_save(name="share_source"), artifact_path)

    monkeypatch.setattr("sys.argv", ["nexa", "savefile", "share", "export", str(artifact_path), str(share_path)])
    assert main() == 0

    monkeypatch.setattr("sys.argv", ["nexa", "run", str(share_path), "--out", str(out_path)])
    exit_code = main()

    assert exit_code == 0
    payload = json.loads(out_path.read_text(encoding="utf-8"))
    assert payload["storage_role"] == "working_save"
    assert payload["source_share_id"].startswith("share_")
    assert payload["source_artifact"]["share_id"] == payload["source_share_id"]
    assert payload["replay_payload"]["source_artifact"]["share_id"] == payload["source_share_id"]


def test_savefile_checkout_accepts_public_link_share_commit_snapshot(tmp_path, monkeypatch, capsys):
    artifact_path = tmp_path / "public_checkout_source.nex"
    share_path = tmp_path / "public_checkout_share.json"
    checkout_path = tmp_path / "checked_out.nex"
    snapshot = create_commit_snapshot_from_working_save(_working_save(name="checkout_share"), commit_id="commit-share-checkout")
    save_nex_artifact_file(snapshot, artifact_path)

    monkeypatch.setattr("sys.argv", ["nexa", "savefile", "share", "export", str(artifact_path), str(share_path)])
    assert main() == 0
    capsys.readouterr()

    monkeypatch.setattr("sys.argv", ["nexa", "savefile", "checkout", str(share_path), str(checkout_path)])
    exit_code = main()

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["input_mode"] == "public_share"
    assert payload["storage_role"] == "working_save"
    raw = json.loads(checkout_path.read_text(encoding="utf-8"))
    assert raw["meta"]["storage_role"] == "working_save"
