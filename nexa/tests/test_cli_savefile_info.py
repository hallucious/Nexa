import json

from src.cli.nexa_cli import build_parser, main
from src.contracts.savefile_factory import make_minimal_savefile
from src.contracts.savefile_serializer import save_savefile_file


def _write_valid_savefile(path):
    savefile = make_minimal_savefile(
        name="demo_info",
        version="1.2.3",
        description="demo file",
        entry="node1",
        node_type="plugin",
        resource_ref={"plugin": "plugin.main"},
        plugins={"plugin.main": {"entry": "plugins.example.run"}},
        state_input={"x": 1},
        ui_layout={"node1": {"x": 10, "y": 20}},
        ui_metadata={"created_by": "test"},
    )
    save_savefile_file(savefile, str(path))


def _write_invalid_but_loadable_savefile(path):
    savefile = make_minimal_savefile(
        name="demo_info_invalid",
        version="1.0.0",
        entry="node1",
        node_type="plugin",
        resource_ref={"plugin": "plugin.main"},
        plugins={"plugin.main": {"entry": "plugins.example.run"}},
        inputs={"x": "ui.metadata.secret"},
        ui_metadata={"secret": "value"},
    )
    save_savefile_file(savefile, str(path))


def test_cli_parser_accepts_savefile_info():
    parser = build_parser()

    args = parser.parse_args(["savefile", "info", "demo.nex"])

    assert args.command == "savefile"
    assert args.savefile_command == "info"
    assert args.input == "demo.nex"


def test_savefile_info_command_reports_summary_for_valid_savefile(tmp_path, monkeypatch, capsys):
    in_path = tmp_path / "demo.nex"
    _write_valid_savefile(in_path)

    monkeypatch.setattr("sys.argv", ["nexa", "savefile", "info", str(in_path)])

    exit_code = main()

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "ok"
    assert payload["input"] == str(in_path)
    assert payload["name"] == "demo_info"
    assert payload["version"] == "1.2.3"
    assert payload["description"] == "demo file"
    assert payload["entry"] == "node1"
    assert payload["node_count"] == 1
    assert payload["edge_count"] == 0
    assert payload["plugin_count"] == 1
    assert payload["prompt_count"] == 0
    assert payload["provider_count"] == 0
    assert payload["state_input_key_count"] == 1
    assert payload["state_working_key_count"] == 0
    assert payload["state_memory_key_count"] == 0
    assert payload["ui_layout_key_count"] == 1
    assert payload["ui_metadata_key_count"] == 1


def test_savefile_info_command_allows_read_only_summary_for_invalid_but_loadable_savefile(tmp_path, monkeypatch, capsys):
    in_path = tmp_path / "invalid_but_loadable.nex"
    _write_invalid_but_loadable_savefile(in_path)

    monkeypatch.setattr("sys.argv", ["nexa", "savefile", "info", str(in_path)])

    exit_code = main()

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "ok"
    assert payload["name"] == "demo_info_invalid"
    assert payload["ui_metadata_key_count"] == 1


def test_savefile_info_command_reports_error_for_non_nex_input(monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["nexa", "savefile", "info", "bad.json"])

    exit_code = main()

    assert exit_code == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "error"
    assert payload["error_type"] == "ValueError"
    assert "must use .nex extension" in payload["message"]
    assert payload["subcommand"] == "info"


def test_savefile_info_command_reports_error_for_missing_file(monkeypatch, capsys):
    missing_path = "missing_demo.nex"

    monkeypatch.setattr("sys.argv", ["nexa", "savefile", "info", missing_path])

    exit_code = main()

    assert exit_code == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "error"
    assert payload["error_type"] == "FileNotFoundError"
    assert payload["input"] == missing_path
    assert payload["subcommand"] == "info"
