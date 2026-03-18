from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DOCS_DIR = REPO_ROOT / "docs"
BLUEPRINT = DOCS_DIR / "BLUEPRINT.md"
CONSTITUTION = DOCS_DIR / "ARCHITECTURE_CONSTITUTION.md"
EXECUTION_RULES = DOCS_DIR / "architecture" / "EXECUTION_RULES.md"


def test_core_architecture_docs_exist():
    assert BLUEPRINT.exists(), "docs/BLUEPRINT.md must exist"
    assert CONSTITUTION.exists(), "docs/ARCHITECTURE_CONSTITUTION.md must exist"
    assert EXECUTION_RULES.exists(), "docs/architecture/EXECUTION_RULES.md must exist"


def test_blueprint_references_core_architecture_docs():
    bp = BLUEPRINT.read_text(encoding="utf-8")
    assert "docs/ARCHITECTURE_CONSTITUTION.md" in bp, "BLUEPRINT must reference docs/ARCHITECTURE_CONSTITUTION.md"
    assert "docs/architecture/EXECUTION_RULES.md" in bp, "BLUEPRINT must reference docs/architecture/EXECUTION_RULES.md"


def test_blueprint_references_active_specs_yaml():
    bp = BLUEPRINT.read_text(encoding="utf-8")
    assert "docs/specs/_active_specs.yaml" in bp, "BLUEPRINT must reference docs/specs/_active_specs.yaml"
