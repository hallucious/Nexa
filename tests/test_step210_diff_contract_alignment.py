from pathlib import Path

from src.engine.diff_formatter import render_diff_ops
from src.engine.diff_types import DiffResult, UnitDiff
from src.engine.representation_model import ComparableUnit
from src.engine.text_extractor import extract_word_representation
from src.engine.unit_alignment import align_unit_sequences
from src.engine.unit_comparator import compare_aligned_unit_sequences


def test_word_extractor_returns_comparable_units_only():
    rep = extract_word_representation("I eat ramen")
    assert [u.unit_kind for u in rep.units] == ["word", "word", "word"]
    assert all(isinstance(u, ComparableUnit) for u in rep.units)


def test_comparator_returns_diff_result_not_diff_ops():
    a = extract_word_representation("I eat ramen")
    b = extract_word_representation("I eat sushi")
    alignment = align_unit_sequences(a.units, b.units)
    diff_result = compare_aligned_unit_sequences(alignment)
    assert isinstance(diff_result, DiffResult)
    assert all(isinstance(d, UnitDiff) for d in diff_result.unit_diffs)


def test_formatter_is_only_layer_that_emits_diffops():
    diff_result = DiffResult(
        unit_diffs=[
            UnitDiff(unit_kind="word", label="i", status="unchanged", delta="I"),
            UnitDiff(unit_kind="word", label="ramen", status="removed", delta="ramen"),
            UnitDiff(unit_kind="word", label="sushi", status="added", delta="sushi"),
        ],
        summary={},
        metrics={},
    )
    ops = render_diff_ops(diff_result)
    assert [(op.op_type, op.text) for op in ops] == [
        ("equal", "I"),
        ("delete", "ramen"),
        ("insert", "sushi"),
    ]


def test_unit_comparator_does_not_import_diffop():
    source = Path("src/engine/unit_comparator.py").read_text(encoding="utf-8")
    assert "DiffOp" not in source
