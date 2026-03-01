from __future__ import annotations

from pathlib import Path
import re

from src.contracts.spec_versions import (
    ENGINE_EXECUTION_MODEL_VERSION,
    ENGINE_TRACE_MODEL_VERSION,
    VALIDATION_ENGINE_CONTRACT_VERSION,
    VALIDATION_RULE_CATALOG_VERSION,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


def _extract_version_from_doc(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    m = re.search(r"^Version:\s*(.+)$", text, re.MULTILINE)
    if not m:
        raise AssertionError(f"No Version field found in {path}")
    return m.group(1).strip()


def _assert_version_sync(doc_rel_path: str, expected: str):
    doc_path = REPO_ROOT / doc_rel_path
    assert doc_path.exists(), f"{doc_rel_path} missing"
    doc_version = _extract_version_from_doc(doc_path)
    assert doc_version == expected, (
        f"{doc_rel_path} version mismatch: "
        f"doc={doc_version} code={expected}"
    )


def test_execution_model_version_sync():
    _assert_version_sync(
        "docs/specs/execution_model.md",
        ENGINE_EXECUTION_MODEL_VERSION,
    )


def test_trace_model_version_sync():
    _assert_version_sync(
        "docs/specs/trace_model.md",
        ENGINE_TRACE_MODEL_VERSION,
    )


def test_validation_engine_contract_version_sync():
    _assert_version_sync(
        "docs/specs/validation_engine_contract.md",
        VALIDATION_ENGINE_CONTRACT_VERSION,
    )


def test_validation_rule_catalog_version_sync():
    _assert_version_sync(
        "docs/specs/validation_rule_catalog.md",
        VALIDATION_RULE_CATALOG_VERSION,
    )
