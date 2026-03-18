from __future__ import annotations

import re
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
FOUNDATION_MAP = REPO_ROOT / "docs" / "FOUNDATION_MAP.md"


def _extract_doc_paths(text: str) -> list[Path]:
    """Extract docs/*.md paths from text (markdown links, inline code, plain paths)."""
    candidates: set[str] = set()

    for m in re.finditer(r"\((docs/[^\s)]+\.md)\)", text):
        candidates.add(m.group(1))
    for m in re.finditer(r"`(docs/[^`\s]+\.md)`", text):
        candidates.add(m.group(1))
    for m in re.finditer(r"\b(docs/[^\s]+\.md)\b", text):
        candidates.add(m.group(1))

    paths: list[Path] = []
    docs_root = (REPO_ROOT / "docs").resolve()
    for c in sorted(candidates):
        p = (REPO_ROOT / c).resolve()
        try:
            p.relative_to(docs_root)
        except Exception:
            continue
        paths.append(p)
    return paths


@pytest.mark.contract
def test_foundation_map_principles_are_explicit():
    assert FOUNDATION_MAP.exists(), "docs/FOUNDATION_MAP.md must exist"
    t = FOUNDATION_MAP.read_text(encoding="utf-8")

    # Must explicitly state: keep valid content, delete obsolete content.
    assert "유효한 내용" in t, "FOUNDATION_MAP must state that valid content is preserved"
    assert "삭제" in t, "FOUNDATION_MAP must state that obsolete content is deleted"
    assert "Deprecations" in t or "deprecation" in t.lower(), "FOUNDATION_MAP must explicitly state deprecations workflow decision (even if not required)"


@pytest.mark.contract
def test_foundation_map_references_existing_docs():
    t = FOUNDATION_MAP.read_text(encoding="utf-8")
    paths = _extract_doc_paths(t)

    assert paths, "FOUNDATION_MAP must reference at least one docs/*.md file"

    missing: list[str] = []
    for p in paths:
        rel = p.relative_to(REPO_ROOT)
        if not p.exists():
            missing.append(str(rel))

    assert not missing, "Missing referenced docs:\n" + "\n".join(missing)


@pytest.mark.contract
def test_foundation_map_includes_specs_entries():
    t = FOUNDATION_MAP.read_text(encoding="utf-8")
    paths = _extract_doc_paths(t)

    specs_root = (REPO_ROOT / "docs" / "specs").resolve()
    spec_docs = [p for p in paths if specs_root in p.parents and p.name.endswith(".md")]

    assert spec_docs, "FOUNDATION_MAP must include at least one docs/specs/*.md entry"
