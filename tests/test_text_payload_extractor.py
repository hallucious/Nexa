from src.engine.text_extractor import extract_char_representation, extract_word_representation


def test_extract_word_representation_builds_word_units():
    result = extract_word_representation("I eat ramen")

    assert [unit.unit_kind for unit in result.units] == ["word", "word", "word"]
    assert [unit.payload for unit in result.units] == ["I", "eat", "ramen"]
    assert [unit.canonical_label for unit in result.units] == ["I", "eat", "ramen"]


def test_extract_char_representation_builds_char_units():
    result = extract_char_representation("ab")

    assert [unit.unit_kind for unit in result.units] == ["char", "char"]
    assert [unit.payload for unit in result.units] == ["a", "b"]
