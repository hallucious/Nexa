import json

from src.cli.nexa_cli import build_parser, main
from src.contracts.savefile_factory import make_minimal_savefile
from src.contracts.savefile_serializer import save_savefile_file


def _write_valid_savefile(path):
    savefile = make_minimal_savefile(
        name="demo_validate",
        version="1.0.0",
        entry="node1",
        node_type="plugin",
        resource_ref={"plugin": "plugin.main"},
        plugins={"plugin.main": {"entry": "plugins.example.run"}},
        ui_metadata={"created_by": "test"},
    )
    save_savefile_file(savefile, str(path))


def _write_invalid_ui_reference_savefile(path):
    savefile = make_minimal_savefile(
        name="bad_validate",
        version="1.0.0",
        entry="node1",
        node_type="plugin",
        resource_ref={"plugin": "plugin.main"},
        plugins={"plugin.main": {"entry": "plugins.example.run"}},
        inputs={"x": "ui.metadata.secret"},
        ui_metadata={"secret": "value"},
    )
    save_savefile_file(savefile, str(path))


def test_cli_parser_accepts_savefile_validate():
    parser = build_parser()

    args = parser.parse_args(["savefile", "validate", "demo.nex"])

    assert args.command == "savefile"
    assert args.savefile_command == "validate"
    assert args.input == "demo.nex"


def test_savefile_validate_command_reports_ok_for_valid_savefile(tmp_path, monkeypatch, capsys):
    in_path = tmp_path / "demo.nex"
    _write_valid_savefile(in_path)

    monkeypatch.setattr("sys.argv", ["nexa", "savefile", "validate", str(in_path)])

    exit_code = main()

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "ok"
    assert payload["input"] == str(in_path)
    assert payload["name"] == "demo_validate"
    assert payload["entry"] == "node1"
    assert payload["node_count"] == 1
    assert payload["warning_count"] == 0
    assert payload["warnings"] == []


def test_savefile_validate_command_reports_error_for_invalid_savefile(tmp_path, monkeypatch, capsys):
    in_path = tmp_path / "bad.nex"
    _write_invalid_ui_reference_savefile(in_path)

    monkeypatch.setattr("sys.argv", ["nexa", "savefile", "validate", str(in_path)])

    exit_code = main()

    assert exit_code == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "error"
    assert payload["command"] == "savefile"
    assert payload["subcommand"] == "validate"
    assert payload["error_type"] == "SavefileValidationError"
    assert "UI must not affect execution" in payload["message"]
    assert payload["input"] == str(in_path)


def test_savefile_validate_command_reports_error_for_missing_file(monkeypatch, capsys):
    missing_path = "missing_demo.nex"

    monkeypatch.setattr("sys.argv", ["nexa", "savefile", "validate", missing_path])

    exit_code = main()

    assert exit_code == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "error"
    assert payload["error_type"] == "FileNotFoundError"
    assert payload["input"] == missing_path
