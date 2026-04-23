from src.engine.run_comparator import RunComparator


class FakeNode:
    def __init__(self, output, artifacts=None, output_hash="", metadata=None):
        self.output = output
        self.artifacts = artifacts or {}
        self.output_hash = output_hash
        self.metadata = metadata or {}


class FakeSnapshot:
    def __init__(self, nodes):
        self.nodes = nodes


def fake_run(nodes):
    return {
        "snapshot": FakeSnapshot(nodes),
    }


def test_compare_no_change():
    run_a = fake_run(
        {
            "node1": FakeNode(
                output="hello",
                artifacts={},
                output_hash="hash1",
                metadata={},
            )
        }
    )

    run_b = fake_run(
        {
            "node1": FakeNode(
                output="hello",
                artifacts={},
                output_hash="hash1",
                metadata={},
            )
        }
    )

    result = RunComparator.compare(run_a, run_b)

    assert result["regression_report"].total_regressions == 0


def test_compare_node_added():
    run_a = fake_run(
        {
            "node1": FakeNode(
                output="hello",
                artifacts={},
                output_hash="hash1",
                metadata={},
            )
        }
    )

    run_b = fake_run(
        {
            "node1": FakeNode(
                output="hello",
                artifacts={},
                output_hash="hash1",
                metadata={},
            ),
            "node2": FakeNode(
                output="world",
                artifacts={},
                output_hash="hash2",
                metadata={},
            ),
        }
    )

    result = RunComparator.compare(run_a, run_b)

    assert result["diff_report"].added_nodes == ["node2"]


def test_diff_text_generated():
    run_a = fake_run(
        {
            "node1": FakeNode(
                output="hello",
                artifacts={},
                output_hash="hash1",
                metadata={},
            )
        }
    )

    run_b = fake_run(
        {
            "node1": FakeNode(
                output="hello",
                artifacts={},
                output_hash="hash1",
                metadata={},
            )
        }
    )

    result = RunComparator.compare(run_a, run_b)

    assert isinstance(result["diff_text"], str)


def test_regression_report_exists():
    run_a = fake_run(
        {
            "node1": FakeNode(
                output="hello",
                artifacts={},
                output_hash="hash1",
                metadata={},
            )
        }
    )

    run_b = fake_run(
        {
            "node1": FakeNode(
                output="changed",
                artifacts={},
                output_hash="hash2",
                metadata={},
            )
        }
    )

    result = RunComparator.compare(run_a, run_b)

    assert result["regression_report"] is not None