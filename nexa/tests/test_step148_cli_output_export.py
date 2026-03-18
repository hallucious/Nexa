import json

from src.cli.nexa_cli import build_parser, save_output


def test_step148_cli_parser_accepts_out_option():
    parser = build_parser()

    args = parser.parse_args(
        [
            "run",
            "test.nex",
            "--out",
            "result.json",
        ]
    )

    assert args.command == "run"
    assert args.out == "result.json"


def test_step148_save_output_writes_json_file(tmp_path):
    out_file = tmp_path / "result.json"

    result = {
        "status": "ok",
        "value": 123,
    }

    save_output(result, str(out_file))

    loaded = json.loads(out_file.read_text(encoding="utf-8"))

    assert loaded == result