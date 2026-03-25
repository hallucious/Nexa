import json
from pathlib import Path

from src.cli.nexa_cli import build_parser, main
from src.contracts.savefile_loader import load_savefile_from_path
from src.contracts.savefile_validator import validate_savefile


def test_cli_parser_accepts_savefile_new_defaults():
    parser = build_parser()

    args = parser.parse_args(["savefile", "new", "demo.nex"])

    assert args.command == "savefile"
    assert args.savefile_command == "new"
    assert args.output == "demo.nex"
    assert args.node_type == "plugin"




def test_cli_parser_accepts_savefile_new_template_argument():
    parser = build_parser()

    args = parser.parse_args(["savefile", "new", "demo.nex", "--template", "ai"])

    assert args.command == "savefile"
    assert args.savefile_command == "new"
    assert args.output == "demo.nex"
    assert args.template == "ai"


def test_savefile_new_command_writes_valid_plugin_savefile(tmp_path, monkeypatch, capsys):
    out_path = tmp_path / "demo.nex"

    monkeypatch.setattr(
        "sys.argv",
        ["nexa", "savefile", "new", str(out_path), "--name", "demo_contract"],
    )

    exit_code = main()

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "ok"
    assert out_path.exists()

    savefile = load_savefile_from_path(str(out_path))
    warnings = validate_savefile(savefile)
    assert warnings == []
    assert savefile.meta.name == "demo_contract"
    assert savefile.circuit.nodes[0].type == "plugin"
    assert savefile.ui.metadata["created_by"] == "nexa savefile new"


def test_savefile_new_command_writes_valid_ai_savefile_from_template(tmp_path, monkeypatch):
    out_path = tmp_path / "demo_ai.nex"

    monkeypatch.setattr(
        "sys.argv",
        [
            "nexa",
            "savefile",
            "new",
            str(out_path),
            "--template",
            "ai",
            "--prompt-template",
            "Answer briefly.",
            "--provider-type",
            "openai",
            "--provider-model",
            "gpt-4o-mini",
        ],
    )

    exit_code = main()

    assert exit_code == 0
    savefile = load_savefile_from_path(str(out_path))
    warnings = validate_savefile(savefile)
    assert warnings == []
    node = savefile.circuit.nodes[0]
    assert node.type == "ai"
    assert node.resource_ref == {"prompt": "prompt.main", "provider": "provider.main"}
    assert savefile.resources.prompts["prompt.main"].template == "Answer briefly."
    assert savefile.resources.providers["provider.main"].model == "gpt-4o-mini"




def test_savefile_new_template_takes_precedence_over_node_type(tmp_path, monkeypatch):
    out_path = tmp_path / "demo_template_precedence.nex"

    monkeypatch.setattr(
        "sys.argv",
        [
            "nexa",
            "savefile",
            "new",
            str(out_path),
            "--template",
            "ai",
            "--node-type",
            "plugin",
            "--prompt-template",
            "Answer briefly.",
        ],
    )

    exit_code = main()

    assert exit_code == 0
    savefile = load_savefile_from_path(str(out_path))
    assert savefile.circuit.nodes[0].type == "ai"
    assert savefile.ui.metadata["template"] == "ai"


def test_savefile_new_command_rejects_non_nex_output(tmp_path, monkeypatch, capsys):
    out_path = tmp_path / "bad.json"

    monkeypatch.setattr("sys.argv", ["nexa", "savefile", "new", str(out_path)])

    exit_code = main()

    assert exit_code == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "error"
    assert payload["error_type"] == "ValueError"
    assert "must use .nex extension" in payload["message"]


def test_savefile_new_command_rejects_existing_output_without_force(tmp_path, monkeypatch, capsys):
    out_path = tmp_path / "existing.nex"
    out_path.write_text("{}", encoding="utf-8")

    monkeypatch.setattr("sys.argv", ["nexa", "savefile", "new", str(out_path)])

    exit_code = main()

    assert exit_code == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "error"
    assert payload["error_type"] == "FileExistsError"
