from __future__ import annotations

from pathlib import Path
import re

from src.contracts.spec_versions import SPEC_VERSIONS

REPO_ROOT = Path(__file__).resolve().parents[1]
ACTIVE_SPECS_YAML = REPO_ROOT / "docs/specs/_active_specs.yaml"


def _extract_version_from_doc(path: Path) -> str:
    text = path.read_text(encoding="utf-8")

    # Authoritative: first top-level 'Version: X.Y.Z' line (no leading dash).
    m = re.search(r"^Version:\s*([0-9]+\.[0-9]+\.[0-9]+)\s*$", text, flags=re.MULTILINE)
    if m:
        return m.group(1).strip()

    # Fallback: '- Version: X.Y.Z' (older spec header formats).
    m2 = re.search(r"^-\s*Version:\s*([0-9]+\.[0-9]+\.[0-9]+)\s*$", text, flags=re.MULTILINE)
    if m2:
        return m2.group(1).strip()

    raise AssertionError(f"Missing Version: X.Y.Z in {path.as_posix()}")


def _extract_active_spec_doc_paths_from_yaml(yaml_text: str) -> list[str]:
    """Source of truth: docs/specs/_active_specs.yaml"""
    m = re.search(
        r"^active_specs\s*:\s*$([\s\S]*?)(?=^\S|\Z)",
        yaml_text,
        flags=re.MULTILINE,
    )
    if not m:
        raise AssertionError("Missing 'active_specs:' block in docs/specs/_active_specs.yaml")

    block = m.group(1)
    paths: list[str] = []
    for line in block.splitlines():
        line = line.strip()
        if line.startswith("- "):
            paths.append(line[2:].strip())

    if not paths:
        raise AssertionError("No active spec doc paths found in docs/specs/_active_specs.yaml")
    return paths


def test_spec_version_sync_contract():
    yaml_path = ACTIVE_SPECS_YAML
    assert yaml_path.exists(), "docs/specs/_active_specs.yaml missing"
    yaml_text = yaml_path.read_text(encoding="utf-8")

    active_docs = _extract_active_spec_doc_paths_from_yaml(yaml_text)

    # Contract: every Active spec MUST be present in SPEC_VERSIONS and must match doc Version line.
    for rel in active_docs:
        doc_path = REPO_ROOT / rel
        assert doc_path.exists(), f"Active spec doc missing: {rel}"

        spec_version = _extract_version_from_doc(doc_path)

        assert rel in SPEC_VERSIONS, f"SPEC_VERSIONS missing key for active spec: {rel}"
        assert (
            SPEC_VERSIONS[rel] == spec_version
        ), f"Spec version mismatch for {rel}: SPEC_VERSIONS={SPEC_VERSIONS[rel]} doc={spec_version}"
