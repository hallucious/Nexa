from __future__ import annotations

"""Step52: Validation Rule Catalog Formalization Contract

Invariant:
- docs/specs/policies/validation_rule_catalog.md (Implemented Rules table) is authoritative.
- ValidationEngine must emit violations whose (rule_id, rule_name, severity, location_type)
  exactly match the catalog rows for implemented rules.
"""

from pathlib import Path
import re
from typing import Dict, Tuple

from src.engine.engine import Engine
from src.engine.validation.validator import ValidationEngine
from src.engine.model import Channel


def _repo_root() -> Path:
    # tests/ -> repo root
    return Path(__file__).resolve().parents[1]


def _load_catalog_table() -> Dict[str, Tuple[str, str, str]]:
    doc = (_repo_root() / "docs" / "specs" / "policies" / "validation_rule_catalog.md").read_text(encoding="utf-8")
    # Find Implemented Rules table block
    # We parse lines between the header and the next blank line after table
    lines = doc.splitlines()

    start = None
    for i, line in enumerate(lines):
        if line.strip() == "### Implemented Rules (Authoritative)":
            start = i
            break
    assert start is not None, "Missing Implemented Rules section"

    # table starts after next line that begins with '| rule_id'
    j = None
    for i in range(start, len(lines)):
        if lines[i].lstrip().startswith("| rule_id |"):
            j = i
            break
    assert j is not None, "Missing Implemented Rules table header"

    # rows start after separator line (|---|...)
    k = j + 2
    table_rows = []
    for i in range(k, len(lines)):
        ln = lines[i].strip()
        if not ln.startswith("|"):
            break
        table_rows.append(ln)

    out: Dict[str, Tuple[str, str, str]] = {}
    pat = re.compile(r"^\|\s*([A-Z]{2,5}-\d{3})\s*\|\s*([^|]+?)\s*\|\s*(error|warning)\s*\|\s*(engine|node|channel|flow)\s*\|")
    for row in table_rows:
        m = pat.match(row)
        assert m, f"Unparseable table row: {row}"
        rid, rname, sev, ltype = m.group(1), m.group(2), m.group(3), m.group(4)
        out[rid] = (rname, sev, ltype)
    assert out, "Implemented Rules table parsed empty"
    return out


def test_catalog_table_is_authoritative_and_matches_emitted_violations():
    table = _load_catalog_table()

    ve = ValidationEngine()

    # ENG-001: Missing Entry
    eng = Engine(entry_node_id="", node_ids=["n1"])
    res = ve.validate(eng, revision_id="r1")
    v = res.violations[0]
    assert v.rule_id in table
    rname, sev, ltype = table[v.rule_id]
    assert v.rule_name == rname
    assert v.severity.value == sev
    assert v.location_type == ltype

    # NODE-001: Duplicate node_id
    eng2 = Engine(entry_node_id="n1", node_ids=["n1", "n1"])
    res2 = ve.validate(eng2, revision_id="r2")
    found = {vv.rule_id: vv for vv in res2.violations}
    assert "NODE-001" in found
    v2 = found["NODE-001"]
    rname, sev, ltype = table[v2.rule_id]
    assert v2.rule_name == rname
    assert v2.severity.value == sev
    assert v2.location_type == ltype

    # ENG-003: Cycle
    eng3 = Engine(
        entry_node_id="a",
        node_ids=["a", "b"],
        channels=[
            Channel(channel_id="c1", src_node_id="a", dst_node_id="b"),
            Channel(channel_id="c2", src_node_id="b", dst_node_id="a"),
        ],
    )
    res3 = ve.validate(eng3, revision_id="r3")
    found3 = {vv.rule_id: vv for vv in res3.violations}
    assert "ENG-003" in found3
    v3 = found3["ENG-003"]
    rname, sev, ltype = table[v3.rule_id]
    assert v3.rule_name == rname
    assert v3.severity.value == sev
    assert v3.location_type == ltype
