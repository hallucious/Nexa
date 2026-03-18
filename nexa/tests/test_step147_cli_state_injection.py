import json

from src.cli.nexa_cli import build_parser, load_cli_state


def test_step147_cli_parser_accepts_state_and_var_options():
    parser = build_parser()

    args = parser.parse_args(
        [
            "run",
            "test.nex",
            "--configs",
            "configs",
            "--plugins",
            "plugins",
            "--state",
            "state.json",
            "--var",
            "question=What is Nexa?",
            "--var",
            "lang=ko",
        ]
    )

    assert args.command == "run"
    assert args.circuit == "test.nex"
    assert args.configs == "configs"
    assert args.plugins == "plugins"
    assert args.state == "state.json"
    assert args.var == ["question=What is Nexa?", "lang=ko"]


def test_step147_load_cli_state_supports_json_file_and_inline_vars(tmp_path):
    state_file = tmp_path / "state.json"
    state_file.write_text(
        json.dumps(
            {
                "question": "from_file",
                "mode": "qa",
            }
        ),
        encoding="utf-8",
    )

    state = load_cli_state(
        str(state_file),
        ["question=from_var", "lang=ko"],
    )

    assert state == {
        "question": "from_var",
        "mode": "qa",
        "lang": "ko",
    }


def test_step147_load_cli_state_rejects_invalid_var_format():
    try:
        load_cli_state(None, ["invalid-format"])
    except ValueError as exc:
        assert "invalid --var format" in str(exc)
    else:
        raise AssertionError("expected invalid --var format error")