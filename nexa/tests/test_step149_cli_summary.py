from src.cli.nexa_cli import build_parser, build_execution_summary


def test_step149_cli_parser_accepts_summary_option():
    parser = build_parser()

    args = parser.parse_args(
        [
            "run",
            "test.nex",
            "--summary",
        ]
    )

    assert args.command == "run"
    assert args.circuit == "test.nex"
    assert args.summary is True


def test_step149_build_execution_summary_counts_state_changes():
    initial_state = {
        "question": "What is Nexa?",
        "lang": "ko",
    }

    final_state = {
        "question": "What is Nexa?",
        "lang": "ko",
        "answer": "Nexa is a workflow engine.",
        "summary": "workflow engine",
    }

    summary = build_execution_summary(
        initial_state=initial_state,
        final_state=final_state,
        started_at=10.0,
        ended_at=10.25,
    )

    assert summary["initial_state_keys"] == 2
    assert summary["final_state_keys"] == 4
    assert summary["node_outputs"] == 2
    assert summary["produced_keys"] == ["answer", "summary"]
    assert summary["execution_time_ms"] == 250.0