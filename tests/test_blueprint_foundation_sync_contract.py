from __future__ import annotations

from pathlib import Path
import re

REPO_ROOT = Path(__file__).resolve().parents[1]


def _extract_active_from_blueprint(text: str) -> set[str]:
    # Extract both main Active block and 2.1 cumulative block
    paths = set()

    # 1) Main Active Specifications block
    m = re.search(
        r"^##\s*2\.\s*Active Specifications\s*$([\s\S]*?)(?=^##\s|\Z)",
        text,
        re.MULTILINE,
    )
    if not m:
        raise AssertionError("Missing '## 2. Active Specifications' section in BLUEPRINT")

    block = m.group(1)
    main_paths = re.findall(r"docs/specs/[^\s]+\.md", block)
    for p in main_paths:
        paths.add(p.strip())

    return paths


def _extract_active_from_foundation(text: str) -> set[str]:
    paths = set()

    # Look for rows where status column is Active
    # Pattern: | something | docs/specs/... | Active |
    matches = re.findall(
        r"docs/specs/[^\s]+\.md[^\n]*?\|\s*Active\b",
        text,
    )

    for m in matches:
        p = re.search(r"docs/specs/[^\s]+\.md", m)
        if p:
            paths.add(p.group(0).strip())

    # Also capture bullet list additions marked as Active in text
    bullet_matches = re.findall(
        r"`?(docs/specs/[^\s`]+\.md)`?.*?Active",
        text,
    )

    for p in bullet_matches:
        paths.add(p.strip())

    return paths


def test_blueprint_and_foundation_active_specs_are_identical():
    blueprint_path = REPO_ROOT / "docs/BLUEPRINT.md"
    foundation_path = REPO_ROOT / "docs/FOUNDATION_MAP.md"

    assert blueprint_path.exists(), "docs/BLUEPRINT.md missing"
    assert foundation_path.exists(), "docs/FOUNDATION_MAP.md missing"

    blueprint_text = blueprint_path.read_text(encoding="utf-8")
    foundation_text = foundation_path.read_text(encoding="utf-8")

    bp_active = _extract_active_from_blueprint(blueprint_text)
    fm_active = _extract_active_from_foundation(foundation_text)

    only_in_blueprint = sorted(bp_active - fm_active)
    only_in_foundation = sorted(fm_active - bp_active)

    assert not only_in_blueprint, (
        "Active specs present in BLUEPRINT but not marked Active in FOUNDATION_MAP: "
        f"{only_in_blueprint}"
    )

    assert not only_in_foundation, (
        "Specs marked Active in FOUNDATION_MAP but missing from BLUEPRINT Active list: "
        f"{only_in_foundation}"
    )
