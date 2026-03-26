from pathlib import Path
import json
from src.engine.cli_legacy_nex_runtime import resolve_plugins


def test_plugin_resolution_with_metadata(tmp_path):
    plugins_dir = tmp_path / "plugins"
    plugins_dir.mkdir()

    p = plugins_dir / "text.cleaner"
    p.mkdir()

    meta = {
        "plugin_id": "text.cleaner",
        "version": "1.0.0",
        "entrypoint": "main.py",
        "type": "node"
    }

    (p / "plugin.json").write_text(json.dumps(meta), encoding="utf-8")

    refs = [
        {"plugin_id": "text.cleaner", "version": "1.0.0", "required": True},
        {"plugin_id": "text.cleaner", "version": "2.0.0", "required": True},
    ]

    result = resolve_plugins(refs, plugins_dir)

    assert "text.cleaner" in result.found
    assert len(result.version_mismatch) == 1
