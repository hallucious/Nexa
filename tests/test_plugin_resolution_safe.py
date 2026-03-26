from pathlib import Path
from src.engine.cli_legacy_nex_plugins import resolve_plugins


def test_plugin_resolution_safe(tmp_path):
    plugins_dir = tmp_path / "plugins"
    plugins_dir.mkdir()

    (plugins_dir / "ok.plugin").mkdir()

    refs = [
        {"plugin_id": "ok.plugin", "required": True},
        {"plugin_id": "missing.plugin", "required": False},
    ]

    result = resolve_plugins(refs, plugins_dir)

    assert "ok.plugin" in result.found
    assert "missing.plugin" in result.missing_optional
