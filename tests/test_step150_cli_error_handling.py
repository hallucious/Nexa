import json
from types import SimpleNamespace

from src.cli.nexa_cli import (
    build_error_payload,
    build_parser,
    main,
)


def test_step150_cli_parser_accepts_error_out_option():
    parser = build_parser()

    args = parser.parse_args(
        [
            "run",
            "test.nex",
            "--error-out",
            "error.json",
        ]
    )

    assert args.command == "run"
    assert args.circuit == "test.nex"
    assert args.error_out == "error.json"


def test_step150_build_error_payload_contains_structured_fields():
    args = SimpleNamespace(
        command="run",
        circuit="test.nex",
        configs="configs",
        plugins="plugins",
    )

    payload = build_error_payload(ValueError("boom"), args)

    assert payload["status"] == "error"
    assert payload["error_type"] == "ValueError"
    assert payload["message"] == "boom"
    assert payload["command"] == "run"
    assert payload["circuit"] == "test.nex"
    assert payload["configs"] == "configs"
    assert payload["plugins"] == "plugins"


def test_step150_main_returns_non_zero_on_failure_and_writes_error_file(tmp_path, monkeypatch):
    error_file = tmp_path / "error.json"

    def fake_run_command(args):
        raise RuntimeError("forced failure")

    monkeypatch.setattr("src.cli.nexa_cli.run_command", fake_run_command)
    monkeypatch.setattr(
        "sys.argv",
        [
            "nexa",
            "run",
            "broken.nex",
            "--error-out",
            str(error_file),
        ],
    )

    exit_code = main()

    assert exit_code == 1

    payload = json.loads(error_file.read_text(encoding="utf-8"))
    assert payload["status"] == "error"
    assert payload["error_type"] == "RuntimeError"
    assert payload["message"] == "forced failure"
    assert payload["circuit"] == "broken.nex"