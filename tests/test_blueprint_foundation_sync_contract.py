from __future__ import annotations

from pathlib import Path
import re

REPO_ROOT = Path(__file__).resolve().parents[1]
ACTIVE_SPECS_YAML = REPO_ROOT / "docs/specs/_active_specs.yaml"


def _extract_active_from_yaml(text: str) -> set[str]:
    """
    Parse docs/specs/_active_specs.yaml.

    Expected minimal shape:

    active_specs:
      - docs/specs/foo.md
      - docs/specs/bar.md
    """
    m = re.search(r"^active_specs\s*:\s*$([\s\S]*?)(?=^\S|\Z)", text, flags=re.MULTILINE)
    if not m:
        raise AssertionError("Missing 'active_specs:' block in docs/specs/_active_specs.yaml")

    block = m.group(1)
    paths = set()
    for line in block.splitlines():
        line = line.strip()
        if line.startswith("- "):
            paths.add(line[2:].strip())
    if not paths:
        raise AssertionError("No active specs found in docs/specs/_active_specs.yaml")
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
        r"^\s*[-*]\s+(docs/specs/[^\s]+\.md)\s*\((?:Status:)?\s*Active\)\s*$",
        text,
        flags=re.MULTILINE,
    )
    for p in bullet_matches:
        paths.add(p.strip())

    return paths


def test_active_specs_yaml_and_foundation_map_are_identical():
    yaml_path = ACTIVE_SPECS_YAML
    foundation_path = REPO_ROOT / "docs/FOUNDATION_MAP.md"

    assert yaml_path.exists(), "docs/specs/_active_specs.yaml missing"
    assert foundation_path.exists(), "docs/FOUNDATION_MAP.md missing"

    yaml_text = yaml_path.read_text(encoding="utf-8")
    foundation_text = foundation_path.read_text(encoding="utf-8")

    yaml_active = _extract_active_from_yaml(yaml_text)
    fm_active = _extract_active_from_foundation(foundation_text)

    only_in_yaml = sorted(yaml_active - fm_active)
    only_in_foundation = sorted(fm_active - yaml_active)

    assert not only_in_yaml, (
        "Active specs present in _active_specs.yaml but not marked Active in FOUNDATION_MAP: "
        f"{only_in_yaml}"
    )
    assert not only_in_foundation, (
        "Specs marked Active in FOUNDATION_MAP but missing from _active_specs.yaml: "
        f"{only_in_foundation}"
    )
