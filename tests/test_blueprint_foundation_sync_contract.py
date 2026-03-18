from __future__ import annotations

from pathlib import Path
import re

REPO_ROOT = Path(__file__).resolve().parents[1]
ACTIVE_SPECS_YAML = REPO_ROOT / "docs/specs/_active_specs.yaml"
BLUEPRINT = REPO_ROOT / "docs/BLUEPRINT.md"


def _extract_active_from_yaml(text: str) -> set[str]:
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


def test_active_specs_yaml_exists_and_has_entries():
    assert ACTIVE_SPECS_YAML.exists(), "docs/specs/_active_specs.yaml missing"
    yaml_text = ACTIVE_SPECS_YAML.read_text(encoding="utf-8")
    active = _extract_active_from_yaml(yaml_text)
    assert active, "_active_specs.yaml must contain at least one active spec"


def test_blueprint_references_authoritative_active_specs_yaml():
    assert BLUEPRINT.exists(), "docs/BLUEPRINT.md must exist"
    bp = BLUEPRINT.read_text(encoding="utf-8")
    assert "docs/specs/_active_specs.yaml" in bp, "BLUEPRINT must reference docs/specs/_active_specs.yaml as source of truth"


def test_blueprint_references_constitution_and_execution_rules():
    assert BLUEPRINT.exists(), "docs/BLUEPRINT.md must exist"
    bp = BLUEPRINT.read_text(encoding="utf-8")
    assert "docs/ARCHITECTURE_CONSTITUTION.md" in bp, "BLUEPRINT must reference docs/ARCHITECTURE_CONSTITUTION.md"
    assert "docs/architecture/EXECUTION_RULES.md" in bp, "BLUEPRINT must reference docs/architecture/EXECUTION_RULES.md"
