from src.contracts.artifact_contract import (
    ArtifactContractError,
    make_typed_artifact,
    registered_artifact_types,
)


def test_step200_typed_artifact_contract_builds_validation_report_envelope():
    artifact = make_typed_artifact(
        artifact_type="validation_report",
        producer_ref="node.answer",
        payload={"status": "pass"},
        validation_status="valid",
        trace_refs=["trace://run/node.answer/verifier"],
    )

    assert artifact.artifact_type == "validation_report"
    assert artifact.artifact_schema_version == "1.0.0"
    assert artifact.producer_ref == "node.answer"
    assert artifact.validation_status == "valid"
    assert artifact.trace_refs == ["trace://run/node.answer/verifier"]
    assert artifact.payload == {"status": "pass"}
    assert artifact.artifact_id.startswith("artifact::validation_report::")


def test_step200_typed_artifact_contract_rejects_unregistered_type():
    try:
        make_typed_artifact(
            artifact_type="unknown_type",
            producer_ref="node.answer",
            payload={"status": "pass"},
        )
    except ArtifactContractError as exc:
        assert "unregistered artifact_type" in str(exc)
    else:
        raise AssertionError("expected ArtifactContractError for unregistered artifact type")


def test_step200_typed_artifact_contract_registry_contains_precision_core_types():
    types = set(registered_artifact_types())
    assert {"text", "json_object", "validation_report", "score_vector"}.issubset(types)
