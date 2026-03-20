from src.engine.representation_model import ComparableUnit
from src.engine.unit_alignment import align_unit_sequences


def make_unit(unit_id: str, label: str, payload: str) -> ComparableUnit:
    return ComparableUnit(
        unit_id=unit_id,
        unit_kind="word",
        canonical_label=label,
        payload=payload,
        metadata={"position": int(unit_id)},
    )


def test_align_unit_sequences_equal_delete_insert():
    units_a = [
        make_unit("0", "i", "I"),
        make_unit("1", "eat", "eat"),
        make_unit("2", "ramen", "ramen"),
    ]
    units_b = [
        make_unit("0", "i", "I"),
        make_unit("1", "eat", "eat"),
        make_unit("2", "sushi", "sushi"),
    ]

    result = align_unit_sequences(units_a, units_b)

    assert [block.op_type for block in result.blocks] == ["equal", "replace"]
    assert [u.payload for u in result.blocks[0].units_a] == ["I", "eat"]
    assert [u.payload for u in result.blocks[1].units_a] == ["ramen"]
    assert [u.payload for u in result.blocks[1].units_b] == ["sushi"]
