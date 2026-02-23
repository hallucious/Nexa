from __future__ import annotations

from src.pipeline.cli import parse_args


def test_cli_parse_args_accepts_request_text():
    args = parse_args(["run", "--run-id", "X", "--request", "Hello\nWorld\n"])
    assert args.cmd == "run"
    assert args.run_id == "X"
    assert args.request == "Hello\nWorld\n"
    assert args.request_file is None
