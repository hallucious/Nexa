from pathlib import Path
import re


def test_execution_environment_version_sync():
    repo = Path(__file__).resolve().parents[1]
    doc = (repo / "docs" / "specs" / "contracts" / "execution_environment_contract.md").read_text(encoding="utf-8")
    code = (repo / "src" / "contracts" / "runtime_contract_versions.py").read_text(encoding="utf-8")

    m = re.search(r"Version:\s*([0-9]+\.[0-9]+\.[0-9]+)", doc)
    assert m, "EEC spec version missing"
    doc_version = m.group(1)

    m2 = re.search(r'EXECUTION_ENVIRONMENT_CONTRACT_VERSION\s*=\s*"([^"]+)"', code)
    assert m2, "EEC version constant missing"
    code_version = m2.group(1)

    assert doc_version == code_version, "EEC spec version mismatch"
