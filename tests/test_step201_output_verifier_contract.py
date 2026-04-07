from src.engine.validation.output_verifier import run_output_verifier


def test_step201_output_verifier_aggregates_structural_requirement_and_logical_modes():
    config = {
        "verifier_id": "answer_quality",
        "modes": [
            {
                "verifier_type": "structural",
                "expected_artifact_type": "json_object",
                "required_keys": ["answer", "reason"],
            },
            {
                "verifier_type": "requirement",
                "allow_empty": False,
                "required_text_fragments": ["answer"],
            },
            {
                "verifier_type": "logical",
                "forbidden_substrings": ["contradiction"],
            },
        ],
    }

    result = run_output_verifier({"answer": "ok", "reason": "clear answer"}, config, target_ref="node.n1.output")

    assert result.aggregate_status == "pass"
    assert result.recommended_next_step == "continue"
    assert len(result.constituent_results) == 3
    assert all(item.status == "pass" for item in result.constituent_results)


def test_step201_output_verifier_detects_structural_and_requirement_failures():
    config = {
        "verifier_id": "answer_quality",
        "modes": [
            {
                "verifier_type": "structural",
                "expected_artifact_type": "json_object",
                "required_keys": ["answer"],
            },
            {
                "verifier_type": "requirement",
                "allow_empty": False,
                "min_text_length": 20,
            },
        ],
    }

    result = run_output_verifier("tiny", config, target_ref="node.n1.output")

    assert result.aggregate_status == "fail"
    assert "STRUCTURE_OUTPUT_TYPE_MISMATCH" in result.blocking_reason_codes
    assert result.recommended_next_step == "retry"
