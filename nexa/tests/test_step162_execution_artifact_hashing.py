from src.engine.execution_artifact_hashing import (
    ExecutionHashBuilder,
    NodeOutputHasher,
)


def test_step162_same_semantic_output_produces_same_hash():
    hasher = NodeOutputHasher()

    left = {"a": 1, "b": 2}
    right = {"b": 2, "a": 1}

    left_hash = hasher.hash_output("node_a", left)
    right_hash = hasher.hash_output("node_a", right)

    assert left_hash.algorithm == "sha256"
    assert right_hash.algorithm == "sha256"
    assert left_hash.hash_value == right_hash.hash_value


def test_step162_different_output_produces_different_hash():
    hasher = NodeOutputHasher()

    left = {"a": 1}
    right = {"a": 2}

    left_hash = hasher.hash_output("node_a", left)
    right_hash = hasher.hash_output("node_a", right)

    assert left_hash.hash_value != right_hash.hash_value


def test_step162_execution_hash_builder_builds_sorted_report():
    builder = ExecutionHashBuilder()

    report = builder.build(
        execution_id="exec-1",
        outputs={
            "node_b": {"value": 2},
            "node_a": {"value": 1},
        },
    )

    assert report.execution_id == "exec-1"
    assert len(report.node_hashes) == 2
    assert report.node_hashes[0].node_id == "node_a"
    assert report.node_hashes[1].node_id == "node_b"
    assert report.node_hashes[0].algorithm == "sha256"
    assert report.node_hashes[1].algorithm == "sha256"


def test_step162_non_json_serializable_output_raises_type_error():
    hasher = NodeOutputHasher()

    class NotSerializable:
        pass

    try:
        hasher.hash_output("node_x", NotSerializable())
        assert False, "expected TypeError"
    except TypeError as exc:
        assert "not JSON-serializable" in str(exc)