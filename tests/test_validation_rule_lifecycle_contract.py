from pathlib import Path
import re


def test_validation_rule_lifecycle_version_sync():
    repo = Path(__file__).resolve().parents[1]
    doc = (repo / "docs" / "specs" / "policies" / "validation_rule_lifecycle.md").read_text(encoding="utf-8")
    code = (repo / "src" / "contracts" / "runtime_contract_versions.py").read_text(encoding="utf-8")

    m = re.search(r"Version:\s*([0-9]+\.[0-9]+\.[0-9]+)", doc)
    assert m, "Lifecycle spec version missing"
    doc_version = m.group(1)

    m2 = re.search(r'VALIDATION_RULE_LIFECYCLE_VERSION\s*=\s*"([^"]+)"', code)
    assert m2, "Lifecycle version constant missing"
    code_version = m2.group(1)

    assert doc_version == code_version, "Lifecycle spec version mismatch"
