import json

from src.cli.nexa_cli import build_parser, main


def test_cli_parser_accepts_savefile_template_list():
    parser = build_parser()

    args = parser.parse_args(["savefile", "template", "list"])

    assert args.command == "savefile"
    assert args.savefile_command == "template"
    assert args.savefile_template_command == "list"


def test_savefile_template_list_command_reports_available_templates(monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["nexa", "savefile", "template", "list"])

    exit_code = main()

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "ok"
    assert payload["template_count"] == 2

    templates = {item["name"]: item for item in payload["templates"]}
    assert set(templates) == {"plugin", "ai"}

    plugin = templates["plugin"]
    assert plugin["node_type"] == "plugin"
    assert plugin["defaults"]["plugin_id"] == "plugin.main"
    assert "--plugin-entry" in plugin["options"]

    ai = templates["ai"]
    assert ai["node_type"] == "ai"
    assert ai["defaults"]["provider_model"] == "gpt-4o-mini"
    assert "--prompt-template" in ai["options"]
