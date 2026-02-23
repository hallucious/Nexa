from __future__ import annotations

from pathlib import Path

from src.platform.plugin import FileWritePlugin, PluginResult


def test_file_write_plugin_writes_content(tmp_path: Path):
    plugin = FileWritePlugin()
    target = tmp_path / "out" / "hello.txt"

    result = plugin.execute(path=target, content="hi", encoding="utf-8", mkdirs=True, overwrite=True)

    assert isinstance(result, PluginResult)
    assert result.success is True
    assert result.error is None
    assert result.output is not None
    assert result.output["path"].endswith("hello.txt")
    assert target.read_text(encoding="utf-8") == "hi"


def test_file_write_plugin_respects_overwrite_false(tmp_path: Path):
    plugin = FileWritePlugin()
    target = tmp_path / "a.txt"
    target.write_text("old", encoding="utf-8")

    result = plugin.execute(path=target, content="new", overwrite=False)

    assert result.success is False
    assert result.error is not None
