from __future__ import annotations

from src.contracts.artifact_contract import make_typed_artifact
from src.contracts.verifier_reason_codes import REQUIREMENT_TEXT_TOO_SHORT
from src.engine.validation.output_verifier import run_output_verifier
from src.storage.execution_record_api import create_serialized_execution_record_from_circuit_run


def test_step204_execution_record_materialization_preserves_typed_artifact_metadata() -> None:
    composite = run_output_verifier(
        "tiny",
        {
            "verifier_id": "answer_quality",
            "modes": [
                {
                    "verifier_type": "requirement",
                    "allow_empty": False,
                    "min_text_length": 10,
                }
            ],
        },
        target_ref="node.draft.output",
    )
    envelope = make_typed_artifact(
        artifact_type="validation_report",
        producer_ref="node.draft",
        payload=composite.to_dict(),
        validation_status="partial",
        metadata={"aggregate_status": composite.aggregate_status, "report_kind": "verifier"},
        trace_refs=["trace://run-typed/draft/verifier"],
    )
    raw_artifact = {
        "type": "validation_report",
        "name": "answer_quality",
        "data": envelope.to_dict(),
        "metadata": {"typed_artifact": True},
        "producer_node": "draft",
    }

    payload = create_serialized_execution_record_from_circuit_run(
        {"id": "demo", "nodes": [{"id": "draft"}]},
        {"draft": "tiny"},
        execution_id="run-typed",
        artifacts=[raw_artifact],
    )

    typed = next(item for item in payload["artifacts"]["artifact_refs"] if item["artifact_type"] == "validation_report")
    assert typed["artifact_schema_version"] == "1.0.0"
    assert typed["producer_ref"] == "node.draft"
    assert typed["validation_status"] == "partial"
    assert typed["payload_preview"]["aggregate_status"] == "warning"
    assert typed["trace_refs"] == ["trace://run-typed/draft/verifier"]

    node_card = payload["node_results"]["results"][0]
    assert typed["artifact_id"] in node_card["typed_artifact_refs"]
    assert node_card["verifier_status"] == "warning"
    assert REQUIREMENT_TEXT_TOO_SHORT in node_card["verifier_reason_codes"]

    verifier_summary = payload["observability"]["verifier_summary"]
    assert verifier_summary["verifier_report_count"] == 1
    assert verifier_summary["status_counts"]["warning"] == 1
    assert REQUIREMENT_TEXT_TOO_SHORT in verifier_summary["blocking_reason_codes"]
