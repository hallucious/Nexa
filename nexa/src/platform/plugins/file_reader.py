from __future__ import annotations

from pathlib import Path
from typing import Any


def read_file_as_text(file_path: str, *, encoding: str | None = "utf-8") -> str:
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"file not found: {file_path}")
    if not path.is_file():
        raise ValueError(f"path is not a file: {file_path}")

    encodings = [encoding] if encoding else []
    encodings.extend([e for e in ("utf-8-sig", "utf-8", "cp949", "latin-1") if e not in encodings])
    last_error: Exception | None = None
    for candidate in encodings:
        try:
            return path.read_text(encoding=candidate)
        except UnicodeDecodeError as exc:
            last_error = exc
            continue
    if last_error is not None:
        raise last_error
    return path.read_text()


def read_file_plugin(*, file_path: str, filename: str | None = None, encoding: str | None = "utf-8", **_: Any) -> dict[str, Any]:
    path = Path(file_path)
    text = read_file_as_text(file_path, encoding=encoding)
    return {
        "text": text,
        "source_type": "file",
        "filename": filename or path.name,
        "file_path": str(path),
    }


PLUGINS = {
    "nexa.file_reader": {
        "callable": read_file_plugin,
        "version": "1.0.0",
        "description": "Read a local text file into Nexa input context.",
    }
}
