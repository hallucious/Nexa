from __future__ import annotations

from pathlib import Path
import re

from src.contracts.spec_versions import SPEC_VERSIONS

REPO_ROOT = Path(__file__).resolve().parents[1]


def _extract_version_from_doc(path: Path) -> str:
    text = path.read_text(encoding="utf-8")

    matches = re.findall(r"^Version:\s*(.+)$", text, re.MULTILINE)

    if not matches:
        raise AssertionError(f"No Version field found in {path}")

    if len(matches) > 1:
        raise AssertionError(
            f"Multiple Version fields found in {path}: {matches}"
        )

    return matches[0].strip()


def _extract_active_spec_doc_paths_from_blueprint(blueprint_text: str) -> list[str]:
    """
    Source of truth: docs/BLUEPRINT.md '## 2. Active Specifications' section.
    We extract bullet list items that look like 'docs/specs/<name>.md'.
    """
    m = re.search(
        r"^##\s*2\.\s*Active Specifications\s*$([\s\S]*?)(?=^##\s|\Z)",
        blueprint_text,
        re.MULTILINE,
    )
    if not m:
        raise AssertionError(
            "BLUEPRINT missing '## 2. Active Specifications' section"
        )

    block = m.group(1)

    paths = re.findall(
        r"^\s*-\s+([^\s]*docs/specs/[^\s]+\.md)\s*$",
        block,
        re.MULTILINE,
    )

    norm = []
    for p in paths:
        p = p.strip()
        p = p[2:] if p.startswith("./") else p
        norm.append(p)

    if not norm:
        raise AssertionError(
            "No active spec doc paths found in BLUEPRINT section"
        )

    return norm


def test_spec_versions_are_complete_and_synced_for_active_specs():
    blueprint_path = REPO_ROOT / "docs/BLUEPRINT.md"
    assert blueprint_path.exists(), "docs/BLUEPRINT.md missing"

    blueprint_text = blueprint_path.read_text(encoding="utf-8")
    active_docs = _extract_active_spec_doc_paths_from_blueprint(
        blueprint_text
    )

    missing_in_code = []
    mismatched = []
    missing_doc = []

    for doc_rel in active_docs:
        doc_path = REPO_ROOT / doc_rel

        if not doc_path.exists():
            missing_doc.append(doc_rel)
            continue

        if doc_rel not in SPEC_VERSIONS:
            missing_in_code.append(doc_rel)
            continue

        doc_version = _extract_version_from_doc(doc_path)
        code_version = SPEC_VERSIONS[doc_rel]

        if doc_version != code_version:
            mismatched.append((doc_rel, doc_version, code_version))

    assert not missing_doc, f"Active spec docs missing on disk: {missing_doc}"

    assert not missing_in_code, (
        "Active spec docs missing in src/contracts/spec_versions.py "
        f"SPEC_VERSIONS mapping: {missing_in_code}"
    )

    assert not mismatched, (
        "Active spec version mismatches (doc vs code): "
        f"{mismatched}"
    )
