import json

from src.cli.nexa_cli import build_parser, main
from src.contracts.savefile_factory import make_minimal_savefile
from src.contracts.savefile_loader import load_savefile_from_path
from src.contracts.savefile_serializer import save_savefile_file


def _write_valid_savefile(path):
    savefile = make_minimal_savefile(
        name="demo_edit",
        version="1.0.0",
        entry="node1",
        node_type="plugin",
        resource_ref={"plugin": "plugin.main"},
        plugins={"plugin.main": {"entry": "plugins.example.run"}},
        ui_metadata={"created_by": "test"},
    )
    save_savefile_file(savefile, str(path))



def test_cli_parser_accepts_savefile_set_name():
    parser = build_parser()

    args = parser.parse_args(["savefile", "set-name", "demo.nex", "--name", "renamed"])

    assert args.command == "savefile"
    assert args.savefile_command == "set-name"
    assert args.input == "demo.nex"
    assert args.name == "renamed"



def test_cli_parser_accepts_savefile_set_entry():
    parser = build_parser()

    args = parser.parse_args(["savefile", "set-entry", "demo.nex", "--entry", "node2"])

    assert args.command == "savefile"
    assert args.savefile_command == "set-entry"
    assert args.input == "demo.nex"
    assert args.entry == "node2"


def test_cli_parser_accepts_savefile_set_description():
    parser = build_parser()

    args = parser.parse_args(["savefile", "set-description", "demo.nex", "--description", "updated description"])

    assert args.command == "savefile"
    assert args.savefile_command == "set-description"
    assert args.input == "demo.nex"
    assert args.description == "updated description"



def test_savefile_set_name_command_updates_file_in_place(tmp_path, monkeypatch, capsys):
    in_path = tmp_path / "demo.nex"
    _write_valid_savefile(in_path)

    monkeypatch.setattr(
        "sys.argv",
        ["nexa", "savefile", "set-name", str(in_path), "--name", "renamed_demo"],
    )

    exit_code = main()

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "ok"
    assert payload["input"] == str(in_path)
    assert payload["name"] == "renamed_demo"

    savefile = load_savefile_from_path(str(in_path))
    assert savefile.meta.name == "renamed_demo"
    assert savefile.circuit.entry == "node1"



def test_savefile_set_name_command_rejects_invalid_empty_name_without_overwriting(tmp_path, monkeypatch, capsys):
    in_path = tmp_path / "demo.nex"
    _write_valid_savefile(in_path)
    before = in_path.read_text(encoding="utf-8")

    monkeypatch.setattr(
        "sys.argv",
        ["nexa", "savefile", "set-name", str(in_path), "--name", ""],
    )

    exit_code = main()

    assert exit_code == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "error"
    assert payload["error_type"] == "SavefileValidationError"
    assert in_path.read_text(encoding="utf-8") == before



def test_savefile_set_entry_command_updates_file_in_place(tmp_path, monkeypatch, capsys):
    in_path = tmp_path / "demo.nex"
    savefile = make_minimal_savefile(
        name="demo_edit",
        version="1.0.0",
        entry="node1",
        node_type="plugin",
        resource_ref={"plugin": "plugin.main"},
        plugins={"plugin.main": {"entry": "plugins.example.run"}},
        ui_metadata={"created_by": "test"},
    )
    savefile.circuit.nodes.append(
        type(savefile.circuit.nodes[0])(
            id="node2",
            type="plugin",
            resource_ref={"plugin": "plugin.main"},
            inputs={},
            outputs={},
        )
    )
    save_savefile_file(savefile, str(in_path))

    monkeypatch.setattr(
        "sys.argv",
        ["nexa", "savefile", "set-entry", str(in_path), "--entry", "node2"],
    )

    exit_code = main()

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "ok"
    assert payload["entry"] == "node2"

    reloaded = load_savefile_from_path(str(in_path))
    assert reloaded.circuit.entry == "node2"
    assert reloaded.meta.name == "demo_edit"



def test_savefile_set_entry_command_rejects_unknown_entry_without_overwriting(tmp_path, monkeypatch, capsys):
    in_path = tmp_path / "demo.nex"
    _write_valid_savefile(in_path)
    before = in_path.read_text(encoding="utf-8")

    monkeypatch.setattr(
        "sys.argv",
        ["nexa", "savefile", "set-entry", str(in_path), "--entry", "missing_node"],
    )

    exit_code = main()

    assert exit_code == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "error"
    assert payload["error_type"] == "SavefileValidationError"
    assert "Entry node 'missing_node' not found in nodes" in payload["message"]
    assert in_path.read_text(encoding="utf-8") == before

def test_savefile_set_description_command_updates_file_in_place(tmp_path, monkeypatch, capsys):
    in_path = tmp_path / "demo.nex"
    _write_valid_savefile(in_path)

    monkeypatch.setattr(
        "sys.argv",
        ["nexa", "savefile", "set-description", str(in_path), "--description", "updated description"],
    )

    exit_code = main()

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "ok"
    assert payload["description"] == "updated description"

    reloaded = load_savefile_from_path(str(in_path))
    assert reloaded.meta.description == "updated description"
    assert reloaded.meta.name == "demo_edit"
    assert reloaded.circuit.entry == "node1"



def test_savefile_set_description_command_rejects_non_nex_input(tmp_path, monkeypatch, capsys):
    in_path = tmp_path / "demo.json"
    in_path.write_text("{}", encoding="utf-8")
    before = in_path.read_text(encoding="utf-8")

    monkeypatch.setattr(
        "sys.argv",
        ["nexa", "savefile", "set-description", str(in_path), "--description", "updated description"],
    )

    exit_code = main()

    assert exit_code == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "error"
    assert payload["error_type"] == "ValueError"
    assert "savefile input must use .nex extension" in payload["message"]
    assert in_path.read_text(encoding="utf-8") == before

