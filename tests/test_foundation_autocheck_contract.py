from __future__ import annotations

from pathlib import Path
import re

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
DOCS_DIR = REPO_ROOT / "docs"
FOUNDATION_MAP = DOCS_DIR / "FOUNDATION_MAP.md"
BLUEPRINT = DOCS_DIR / "BLUEPRINT.md"


def _parse_foundation_table_rows(md: str) -> list[tuple[str, str, str]]:
    """Return list of (doc_name, path, status) from markdown pipe tables."""
    rows: list[tuple[str, str, str]] = []
    for line in md.splitlines():
        s = line.strip()
        if not s.startswith("|"):
            continue
        # skip header separators
        if re.match(r"^\|\s*-+\s*\|", s):
            continue
        parts = [p.strip() for p in s.strip("|").split("|")]
        if len(parts) < 3:
            continue
        doc_name, path, status = parts[0], parts[1], parts[2]
        if doc_name.lower() == "문서" or path.lower() == "경로":
            continue
        rows.append((doc_name, path, status))
    return rows


def test_foundation_map_exists():
    assert FOUNDATION_MAP.exists(), "docs/FOUNDATION_MAP.md must exist"


def test_blueprint_references_foundation_map():
    assert BLUEPRINT.exists(), "docs/BLUEPRINT.md must exist"
    bp = BLUEPRINT.read_text(encoding="utf-8")
    assert "docs/FOUNDATION_MAP.md" in bp, "BLUEPRINT must reference docs/FOUNDATION_MAP.md"


def test_active_docs_in_foundation_map_exist_on_disk():
    md = FOUNDATION_MAP.read_text(encoding="utf-8")
    rows = _parse_foundation_table_rows(md)

    missing: list[str] = []
    for doc_name, rel_path, status in rows:
        if status != "Active":
            continue
        p = REPO_ROOT / rel_path
        if not p.exists():
            missing.append(f"{doc_name} -> {rel_path}")

    assert not missing, "Active foundation docs must exist:\n" + "\n".join(missing)
