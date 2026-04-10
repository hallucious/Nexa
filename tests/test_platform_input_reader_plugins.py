from __future__ import annotations

import urllib.request
from pathlib import Path

from src.contracts.savefile_executor_aligned import execute_plugin_node
from src.contracts.savefile_format import (
    CircuitSpec,
    NodeSpec,
    PluginResource,
    ResourcesSpec,
    Savefile,
    SavefileMeta,
    StateSpec,
    UISpec,
)
from src.platform.plugin_executor import execute_plugin_entry
from src.platform.plugins.file_reader import read_file_as_text
from src.platform.plugins.url_reader import fetch_url_text


def _build_savefile(entry: str, *, state_input: dict[str, object]) -> Savefile:
    return Savefile(
        meta=SavefileMeta(name="input-reader", version="2.0.0"),
        circuit=CircuitSpec(entry="n1", nodes=[]),
        resources=ResourcesSpec(plugins={"reader": PluginResource(entry=entry)}),
        state=StateSpec(input=state_input, working={}, memory={}),
        ui=UISpec(),
    )


def test_read_file_as_text_reads_utf8_file(tmp_path: Path) -> None:
    file_path = tmp_path / "sample.txt"
    file_path.write_text("hello from file", encoding="utf-8")

    assert read_file_as_text(str(file_path)) == "hello from file"


def test_execute_plugin_entry_reads_local_file(tmp_path: Path) -> None:
    file_path = tmp_path / "draft.txt"
    file_path.write_text("draft body", encoding="utf-8")

    result = execute_plugin_entry(
        plugin_name="nexa.file_reader",
        entry="src.platform.plugins.file_reader.read_file_plugin",
        file_path=str(file_path),
    )

    assert result.success is True
    assert result.output == {
        "text": "draft body",
        "source_type": "file",
        "filename": "draft.txt",
        "file_path": str(file_path),
    }


def test_execute_plugin_node_reads_file_from_state_input(tmp_path: Path) -> None:
    file_path = tmp_path / "notes.txt"
    file_path.write_text("meeting notes", encoding="utf-8")
    savefile = _build_savefile(
        "src.platform.plugins.file_reader.read_file_plugin",
        state_input={"file_path": str(file_path)},
    )
    node = NodeSpec(
        id="n1",
        type="plugin",
        resource_ref={"plugin": "reader"},
        inputs={"file_path": "state.input.file_path"},
    )

    result = execute_plugin_node(
        node=node,
        savefile=savefile,
        state={"input": {"file_path": str(file_path)}, "working": {}, "memory": {}},
        node_outputs={},
    )

    assert result.status == "success"
    assert result.output["source_type"] == "file"
    assert result.output["text"] == "meeting notes"


class _FakeResponse:
    def __init__(self, body: bytes, *, charset: str = "utf-8") -> None:
        self._body = body
        self.headers = self
        self._charset = charset

    def read(self) -> bytes:
        return self._body

    def get_content_charset(self) -> str:
        return self._charset

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


def test_fetch_url_text_reads_http_payload(monkeypatch) -> None:
    def fake_urlopen(request: urllib.request.Request, timeout: int = 0):  # type: ignore[override]
        assert request.full_url == "https://example.com/data"
        return _FakeResponse(b"hello from url")

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)

    assert fetch_url_text("https://example.com/data") == "hello from url"


def test_execute_plugin_entry_reads_url(monkeypatch) -> None:
    def fake_urlopen(request: urllib.request.Request, timeout: int = 0):  # type: ignore[override]
        return _FakeResponse(b"remote text")

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)

    result = execute_plugin_entry(
        plugin_name="nexa.url_reader",
        entry="src.platform.plugins.url_reader.read_url_plugin",
        url="https://example.com/brief",
    )

    assert result.success is True
    assert result.output == {
        "text": "remote text",
        "source_type": "url",
        "url": "https://example.com/brief",
    }


def test_fetch_url_text_rejects_non_http_scheme() -> None:
    try:
        fetch_url_text("file:///tmp/x.txt")
    except ValueError as exc:
        assert "unsupported URL scheme" in str(exc)
    else:
        raise AssertionError("expected ValueError for unsupported scheme")
