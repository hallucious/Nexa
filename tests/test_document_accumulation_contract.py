from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
BLUEPRINT = REPO_ROOT / "docs" / "BLUEPRINT.md"
README = REPO_ROOT / "docs" / "README.md"
DEVELOPMENT = REPO_ROOT / "docs" / "DEVELOPMENT.md"


def _extract_doc_paths(text: str) -> list[Path]:
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
def test_blueprint_principles_are_explicit():
    assert BLUEPRINT.exists(), "docs/BLUEPRINT.md must exist"
    t = BLUEPRINT.read_text(encoding="utf-8")

    assert "Execution Engine-based architecture" in t, "BLUEPRINT must explicitly state the execution-engine architecture"
    assert "docs/specs/_active_specs.yaml" in t, "BLUEPRINT must explicitly declare the active spec source of truth"


@pytest.mark.contract
def test_core_docs_reference_existing_docs():
    texts = [
        BLUEPRINT.read_text(encoding="utf-8"),
        README.read_text(encoding="utf-8"),
        DEVELOPMENT.read_text(encoding="utf-8"),
    ]
    paths = []
    for t in texts:
        paths.extend(_extract_doc_paths(t))

    assert paths, "Core docs must reference at least one docs/*.md file"

    missing: list[str] = []
    for p in paths:
        rel = p.relative_to(REPO_ROOT)
        if not p.exists():
            missing.append(str(rel))

    assert not missing, "Missing referenced docs:\n" + "\n".join(sorted(set(missing)))


@pytest.mark.contract
def test_core_docs_include_specs_entries():
    texts = [
        BLUEPRINT.read_text(encoding="utf-8"),
        README.read_text(encoding="utf-8"),
        DEVELOPMENT.read_text(encoding="utf-8"),
    ]
    paths = []
    for t in texts:
        paths.extend(_extract_doc_paths(t))

    specs_root = (REPO_ROOT / "docs" / "specs").resolve()
    spec_docs = [p for p in paths if specs_root in p.parents and p.name.endswith(".md")]

    assert spec_docs, "Core docs must include at least one docs/specs/*.md entry"
