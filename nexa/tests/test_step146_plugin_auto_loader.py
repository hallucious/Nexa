from src.platform.plugin_auto_loader import load_plugin_registry
from src.cli.nexa_cli import build_parser


def test_step146_plugin_auto_loader_loads_plugins_from_directory(tmp_path):
    plugin_file = tmp_path / "sample_plugin.py"
    plugin_file.write_text(
        """
def echo(text):
    return {"result": text}

PLUGINS = {
    "echo": echo,
}
""",
        encoding="utf-8",
    )

    registry = load_plugin_registry(str(tmp_path))

    assert "echo" in registry
    assert callable(registry["echo"])
    assert registry["echo"]("nexa") == {"result": "nexa"}


def test_step146_cli_parser_accepts_plugins_directory():
    parser = build_parser()

    args = parser.parse_args(
        ["run", "test.nex", "--configs", "configs", "--plugins", "plugins"]
    )

    assert args.command == "run"
    assert args.circuit == "test.nex"
    assert args.configs == "configs"
    assert args.plugins == "plugins"