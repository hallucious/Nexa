from pathlib import Path
from src.contracts.nex_plugin_resolver import resolve_plugins


def test_plugin_resolution(tmp_path):
    plugins_dir = tmp_path / "plugins"
    plugins_dir.mkdir()

    (plugins_dir / "text.cleaner").mkdir()

    plugin_refs = [
        {"plugin_id": "text.cleaner", "required": True},
        {"plugin_id": "image.caption", "required": False},
    ]

    result = resolve_plugins(plugin_refs, plugins_dir)

    assert "text.cleaner" in result.found
    assert "image.caption" in result.missing_optional
    assert not result.missing_required
