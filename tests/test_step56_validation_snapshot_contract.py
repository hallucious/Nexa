from __future__ import annotations

"""Step56: Validation Rule Snapshot Contract

Invariants:
- trace.meta.validation.snapshot exists when validation executed
- snapshot.applied_rules is canonical (sorted, unique)
- snapshot does not affect structural_fingerprint (fingerprint depends only on EngineStructure)
- trace JSON serialization is stable with snapshot present
"""

from src.engine.engine import Engine
from src.engine.validation.validator import APPLIED_RULE_IDS
from src.engine.fingerprint import compute_fingerprint


def test_step56_validation_snapshot_presence_and_canonical_rules():
    eng = Engine(entry_node_id="n1", node_ids=["n1"])
    trace = eng.execute(revision_id="r1")

    assert isinstance(trace.meta, dict)
    vmeta = trace.meta.get("validation")
    assert isinstance(vmeta, dict)

    snap = vmeta.get("snapshot")
    assert isinstance(snap, dict)

    assert snap.get("snapshot_version") == "1"
    applied = snap.get("applied_rules")
    assert isinstance(applied, list)
    assert applied == sorted(applied)
    assert len(applied) == len(set(applied))

    # should include exactly the executed rules set
    assert applied == sorted(set(APPLIED_RULE_IDS))


def test_step56_validation_snapshot_not_in_structural_fingerprint():
    eng = Engine(entry_node_id="n1", node_ids=["n1"])
    trace = eng.execute(revision_id="r1")

    # recompute fingerprint from structure only
    expected = compute_fingerprint(eng.to_structure()).value
    assert trace.structural_fingerprint == expected

    # even if snapshot is tampered, fingerprint remains the same (by design contract)
    trace.meta["validation"]["snapshot"]["applied_rules"].append("ZZZ-999")
    assert trace.structural_fingerprint == expected


def test_step56_trace_json_stable_with_snapshot():
    eng = Engine(entry_node_id="n1", node_ids=["n1"])
    trace = eng.execute(revision_id="r1")
    js = trace.to_json(stable=True)
    # canonical field name must be present
    assert '"snapshot"' in js
    assert '"applied_rules"' in js
