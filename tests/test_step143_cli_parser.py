from src.cli.nexa_cli import build_parser


def test_cli_parser():

    parser = build_parser()

    args = parser.parse_args(
        ["run", "test.nex"]
    )

    assert args.command == "run"
    assert args.circuit == "test.nex"