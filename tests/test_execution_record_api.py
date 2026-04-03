from __future__ import annotations

import json

from src.engine.execution_artifact_hashing import ExecutionHashReport, NodeOutputHash
from src.engine.execution_snapshot import ExecutionSnapshotBuilder
from src.engine.execution_timeline import ExecutionTimeline, NodeExecutionSpan
from src.storage.execution_record_api import (
    build_execution_record_reference_contract,
    create_execution_record_from_snapshot,
    summarize_execution_record_for_working_save,
    synthesize_execution_record_reference_contract_from_payload,
    materialize_execution_record_from_payload,
    build_execution_record_reference_contract_from_serialized_record,
    create_serialized_execution_record_from_savefile_trace,
    create_serialized_execution_record_from_circuit_run,
)
from src.storage.serialization import save_execution_record_file, serialize_execution_record



from src.contracts.savefile_executor_aligned import NodeExecutionResult, SavefileExecutionTrace
from tests.savefile_test_helpers import make_demo_savefile


def test_create_serialized_execution_record_from_savefile_trace_preserves_native_trace_details():
    savefile = make_demo_savefile(name='demo-savefile')
    trace = SavefileExecutionTrace(
        run_id='savefile-run-1',
        savefile_name='demo-savefile',
        status='success',
        node_results={
            'node1': NodeExecutionResult(
                node_id='node1',
                status='success',
                output={'answer': 'hello'},
                artifacts=[{'type': 'report', 'summary': 'artifact-summary'}],
                trace={'provider': 'echo'},
            )
        },
        final_state={'input': {'text': 'hello'}, 'working': {'answer': 'hello'}, 'memory': {}},
        all_artifacts=[{'type': 'report', 'summary': 'artifact-summary'}],
    )

    payload = create_serialized_execution_record_from_savefile_trace(savefile, trace, started_at=1.0, ended_at=2.0)

    assert payload['meta']['run_id'] == 'savefile-run-1'
    assert payload['timeline']['trace_ref'] == 'trace://savefile-run-1'
    assert payload['source']['trigger_reason'] == 'savefile_trace_materialization'
    assert payload['outputs']['final_outputs'][0]['output_ref'] == 'node1'
    assert payload['artifacts']['artifact_count'] >= 2
    assert payload['node_results']['results'][0]['trace_ref'] == 'trace://savefile-run-1#node:node1'

def make_snapshot():
    timeline = ExecutionTimeline(
        execution_id='exec-1',
        start_ms=1000,
        end_ms=2500,
        duration_ms=1500,
        node_spans=[
            NodeExecutionSpan('node_a', 1100, 1500, 400, 'success'),
            NodeExecutionSpan('node_b', 1600, 2400, 800, 'failed', error='provider timeout'),
        ],
    )
    hash_report = ExecutionHashReport(
        execution_id='exec-1',
        node_hashes=[NodeOutputHash(node_id='node_a', algorithm='sha256', hash_value='abc')],
    )
    return ExecutionSnapshotBuilder().build(
        execution_id='exec-1',
        timeline=timeline,
        outputs={'final_answer': {'text': 'hello'}},
        hash_report=hash_report,
    )


def test_create_execution_record_from_snapshot_builds_expected_sections(tmp_path):
    record = create_execution_record_from_snapshot(
        make_snapshot(),
        commit_id='commit-1',
        trigger_type='manual_run',
        input_summary={'question': 'What is AI?'},
        trace_ref='trace://exec-1',
    )
    assert record.meta.run_id == 'exec-1'
    assert record.source.commit_id == 'commit-1'
    assert record.timeline.trace_ref == 'trace://exec-1'
    assert len(record.node_results.results) == 2
    assert record.outputs.final_outputs[0].output_ref == 'final_answer'

    path = save_execution_record_file(record, tmp_path / 'run_001.json')
    payload = json.loads(path.read_text(encoding='utf-8'))
    assert payload['source']['commit_id'] == 'commit-1'
    assert payload['meta']['status'] == 'completed'


def test_summarize_execution_record_for_working_save_returns_small_summary():
    record = create_execution_record_from_snapshot(make_snapshot(), commit_id='commit-1')
    summary = summarize_execution_record_for_working_save(record)
    assert summary['run_id'] == 'exec-1'
    assert summary['commit_id'] == 'commit-1'
    assert 'trace_ref' in summary


def test_serialize_execution_record_returns_mapping():
    payload = serialize_execution_record(create_execution_record_from_snapshot(make_snapshot(), commit_id='commit-1'))
    assert payload['meta']['run_id'] == 'exec-1'
    assert payload['source']['commit_id'] == 'commit-1'


def test_create_execution_record_from_snapshot_materializes_output_payloads_and_node_previews():
    record = create_execution_record_from_snapshot(
        make_snapshot(),
        commit_id='commit-1',
        final_outputs={'final_answer': {'text': 'hello'}, 'score': 0.9},
    )
    assert record.outputs.final_outputs[0].value_payload == {'text': 'hello'}
    assert record.outputs.final_outputs[0].value_type == 'dict'
    assert record.outputs.final_outputs[1].value_payload == 0.9


def test_create_execution_record_from_snapshot_normalizes_non_json_safe_outputs():
    record = create_execution_record_from_snapshot(
        make_snapshot(),
        commit_id='commit-1',
        final_outputs={'final_answer': {'items': {'a', 'b'}}},
    )
    payload = record.outputs.final_outputs[0].value_payload
    assert payload['items'] == ['a', 'b'] or payload['items'] == ['b', 'a']


def test_summarize_execution_record_for_working_save_includes_output_refs_and_semantic_status():
    record = create_execution_record_from_snapshot(make_snapshot(), commit_id='commit-1')
    summary = summarize_execution_record_for_working_save(record)
    assert summary['output_count'] == 1
    assert summary['output_refs'] == ['final_answer']
    assert summary['semantic_status'] == 'normal'


def test_create_execution_record_from_snapshot_auto_links_hash_artifacts_and_observability_refs():
    record = create_execution_record_from_snapshot(
        make_snapshot(),
        commit_id='commit-1',
        trace_ref='trace://exec-1',
        event_stream_ref='events://exec-1',
    )
    assert record.artifacts.artifact_count == 2
    artifact = record.artifacts.artifact_refs[0]
    assert artifact.artifact_id == 'artifact::node_a'
    assert artifact.ref == 'hash://sha256/abc'
    assert record.artifacts.artifact_refs[1].artifact_id == 'artifact::output::final_answer'
    assert record.node_results.results[0].artifact_refs == ['artifact::node_a']
    assert record.node_results.results[0].trace_ref == 'events://exec-1#node:node_a'
    assert 'trace://exec-1' in (record.observability.observability_refs or [])
    assert 'events://exec-1' in (record.observability.observability_refs or [])
    assert 'hash://sha256/abc' in (record.observability.observability_refs or [])


def test_create_execution_record_from_snapshot_builds_output_value_refs_from_trace_ref():
    record = create_execution_record_from_snapshot(
        make_snapshot(),
        commit_id='commit-1',
        trace_ref='trace://exec-1',
    )
    assert record.outputs.final_outputs[0].value_ref == 'trace://exec-1#output:final_answer'


def test_build_execution_record_reference_contract_prefers_event_stream_and_indexes_refs():
    record = create_execution_record_from_snapshot(
        make_snapshot(),
        commit_id='commit-1',
        trace_ref='trace://exec-1',
        event_stream_ref='events://exec-1',
    )
    contract = build_execution_record_reference_contract(record)
    assert contract['primary_trace_ref'] == 'events://exec-1'
    assert contract['node_trace_refs']['node_a'] == 'events://exec-1#node:node_a'
    assert contract['output_value_refs']['final_answer'] == 'trace://exec-1#output:final_answer'
    assert contract['artifact_refs']['artifact::output::final_answer'] == 'trace://exec-1#output:final_answer'
    assert contract['unresolved_output_refs'] == []
    assert contract['is_replay_ready'] is True
    assert contract['is_audit_ready'] is True


def test_build_execution_record_reference_contract_reports_unresolved_refs():
    record = create_execution_record_from_snapshot(
        make_snapshot(),
        commit_id='commit-1',
        trace_ref=None,
    )
    contract = build_execution_record_reference_contract(record)
    assert contract['primary_trace_ref'] is None
    assert contract['unresolved_output_refs'] == ['final_answer']
    assert contract['unresolved_artifact_refs'] == []
    assert contract['is_replay_ready'] is False
    assert contract['is_audit_ready'] is False



def test_synthesize_execution_record_reference_contract_from_payload_creates_contract_when_missing():
    payload = {
        "trace": {"events": ["started", "completed"]},
        "artifacts": [{"name": "a"}],
        "replay_payload": {
            "execution_id": "run-123",
            "node_order": ["node_a"],
            "expected_outputs": {"node_a": {"value": "ok"}},
        },
    }

    contract = synthesize_execution_record_reference_contract_from_payload(payload)

    assert contract["run_id"] == "run-123"
    assert contract["primary_trace_ref"] == "events://run-123"
    assert contract["node_trace_refs"]["node_a"] == "events://run-123#node:node_a"
    assert contract["output_value_refs"]["node_a"] == "trace://run-123#output:node_a"
    assert contract["is_replay_ready"] is True
    assert payload["execution_record_reference_contract"] == contract


def test_synthesize_execution_record_reference_contract_from_payload_prefers_materialized_over_stale_contract():
    # Stale on-disk contract claims is_replay_ready=True with a trace ref.
    # Payload has only replay_payload.expected_outputs — no structural detail (trace/node_order/input_state).
    # After the fix, unconditional materialization runs before the stale fallback and produces a fresh
    # identity-bearing record from expected_outputs. The fresh contract wins; stale primary_trace_ref is discarded.
    payload = {
        "execution_record_reference_contract": {
            "primary_trace_ref": "events://existing",
            "is_replay_ready": True,
            "is_audit_ready": True,
        },
        "replay_payload": {
            "execution_id": "run-123",
            "expected_outputs": {"node_a": {"value": "ok"}},
        },
    }

    contract = synthesize_execution_record_reference_contract_from_payload(payload)

    # Fresh contract built from materialized record — no trace in payload so primary_trace_ref is None.
    assert contract["run_id"] == "run-123"
    assert contract["primary_trace_ref"] is None
    assert contract["is_replay_ready"] is False


def test_synthesize_execution_record_reference_contract_from_payload_falls_back_to_stale_only_when_materialization_fails():
    # Stale contract is returned only when materialization cannot produce an identity-bearing record.
    # Here replay_payload is absent, so materialize_execution_record_from_payload returns nothing useful.
    payload = {
        "execution_record_reference_contract": {
            "run_id": "stale-run",
            "primary_trace_ref": "events://stale",
            "is_replay_ready": True,
            "is_audit_ready": True,
        },
    }

    contract = synthesize_execution_record_reference_contract_from_payload(payload)

    assert contract["run_id"] == "stale-run"
    assert contract["primary_trace_ref"] == "events://stale"




def test_materialize_execution_record_from_payload_rebuilds_thin_native_record_when_richer_payload_exists():
    payload = {
        "execution_record": {
            "meta": {"run_id": "run-123", "status": "completed"},
            "source": {"commit_id": "commit-thin"},
        },
        "trace": {"events": ["started", "completed"]},
        "replay_payload": {
            "execution_id": "run-123",
            "node_order": ["node_a"],
            "input_state": {"message": "hi"},
            "expected_outputs": {"node_a": {"value": "ok"}},
        },
        "result": {
            "status": "success",
            "state": {"node_a": {"value": "ok"}},
            "node_results": {
                "node_a": {"status": "success", "output": {"value": "ok"}},
            },
        },
    }

    record = materialize_execution_record_from_payload(payload)

    assert record["meta"]["run_id"] == "run-123"
    assert record["source"]["commit_id"] == "commit-thin"
    assert record["timeline"]["event_stream_ref"] == "events://run-123"
    assert record["outputs"]["final_outputs"][0]["output_ref"] == "node_a"


def test_materialize_execution_record_from_payload_creates_native_record_and_contract_inputs():
    payload = {
        "trace": {"events": ["started", "completed"]},
        "artifacts": [{"name": "a"}],
        "replay_payload": {
            "execution_id": "run-123",
            "node_order": ["node_a"],
            "input_state": {"message": "hi"},
            "expected_outputs": {"node_a": {"value": "ok"}},
        },
        "result": {
            "status": "success",
            "state": {"node_a": {"value": "ok"}},
            "node_results": {
                "node_a": {"status": "success", "output": {"value": "ok"}},
            },
        },
    }

    record = materialize_execution_record_from_payload(payload)

    assert record["meta"]["run_id"] == "run-123"
    assert record["timeline"]["trace_ref"] == "trace://run-123"
    assert record["timeline"]["event_stream_ref"] == "events://run-123"
    assert payload["execution_record"] == record


def test_build_execution_record_reference_contract_from_serialized_record_indexes_native_record():
    payload = {
        "trace": {"events": ["started", "completed"]},
        "replay_payload": {
            "execution_id": "run-123",
            "node_order": ["node_a"],
            "expected_outputs": {"node_a": {"value": "ok"}},
        },
        "result": {
            "status": "success",
            "state": {"node_a": {"value": "ok"}},
            "node_results": {
                "node_a": {"status": "success", "output": {"value": "ok"}},
            },
        },
    }
    record = materialize_execution_record_from_payload(payload)
    contract = build_execution_record_reference_contract_from_serialized_record(record)

    assert contract["run_id"] == "run-123"
    assert contract["primary_trace_ref"] == "events://run-123"
    assert contract["is_replay_ready"] is True


def test_create_serialized_execution_record_from_circuit_run_builds_native_record_directly():
    circuit = {
        "id": "hello-circuit",
        "nodes": [
            {"id": "hello_node"},
            {"id": "judge_node"},
        ],
    }
    final_state = {
        "hello_node": {"value": "hello"},
        "judge_node": {"value": "approved"},
    }

    payload = create_serialized_execution_record_from_circuit_run(
        circuit,
        final_state,
        started_at=1.0,
        ended_at=2.0,
        execution_id='hello-exec',
        input_state={"message": "hi"},
        trace={"events": ["started", "completed"]},
        artifacts=[{"type": "report", "summary": "artifact-summary"}],
    )

    assert payload['meta']['run_id'] == 'hello-exec'
    assert payload['source']['trigger_reason'] == 'circuit_run_materialization'
    assert payload['timeline']['trace_ref'] == 'trace://hello-exec'
    assert payload['timeline']['event_stream_ref'] == 'events://hello-exec'
    assert payload['outputs']['final_outputs'][0]['output_ref'] == 'hello_node'
    assert payload['outputs']['final_outputs'][1]['output_ref'] == 'judge_node'
    assert payload['artifacts']['artifact_count'] >= 3


def test_synthesize_execution_record_reference_contract_prefers_native_execution_record_over_replay_reconstruction():
    native_record = create_serialized_execution_record_from_circuit_run(
        {
            "id": "native-circuit",
            "nodes": [{"id": "native_node"}],
        },
        {"native_node": {"value": "ok"}},
        execution_id='native-exec',
        trace={"events": ["started", "completed"]},
    )
    payload = {
        "execution_record": native_record,
        "replay_payload": {
            "execution_id": "different-exec",
            "node_order": ["other_node"],
            "expected_outputs": {"other_node": {"value": "wrong"}},
        },
    }

    contract = synthesize_execution_record_reference_contract_from_payload(payload)

    assert contract['run_id'] == 'native-exec'
    assert contract['primary_trace_ref'] == 'events://native-exec'
    assert 'native_node' in contract['node_trace_refs']
    assert 'other_node' not in contract['node_trace_refs']




def test_synthesize_execution_record_reference_contract_prefers_materialized_truth_over_stale_existing_contract():
    payload = {
        "execution_record": {
            "meta": {"run_id": "run-123", "status": "completed"},
            "source": {"commit_id": "commit-thin"},
        },
        "execution_record_reference_contract": {
            "run_id": "stale-exec",
            "primary_trace_ref": "events://stale-exec",
            "node_trace_refs": {"other_node": "events://stale-exec#node:other_node"},
            "is_replay_ready": True,
            "is_audit_ready": True,
        },
        "trace": {"events": ["started", "completed"]},
        "replay_payload": {
            "execution_id": "run-123",
            "node_order": ["node_a"],
            "expected_outputs": {"node_a": {"value": "ok"}},
        },
        "result": {
            "status": "success",
            "state": {"node_a": {"value": "ok"}},
            "node_results": {
                "node_a": {"status": "success", "output": {"value": "ok"}},
            },
        },
    }

    contract = synthesize_execution_record_reference_contract_from_payload(payload)

    assert contract["run_id"] == "run-123"
    assert contract["primary_trace_ref"] == "events://run-123"
    assert "node_a" in contract["node_trace_refs"]
    assert "other_node" not in contract["node_trace_refs"]
    assert payload["execution_record_reference_contract"] == contract


def test_synthesize_execution_record_reference_contract_recomputes_stale_existing_contract_from_native_record():
    native_record = create_serialized_execution_record_from_circuit_run(
        {
            "id": "native-circuit",
            "nodes": [{"id": "native_node"}],
        },
        {"native_node": {"value": "ok"}},
        execution_id='native-exec',
        trace={"events": ["started", "completed"]},
    )
    payload = {
        "execution_record": native_record,
        "execution_record_reference_contract": {
            "run_id": "stale-exec",
            "primary_trace_ref": "events://stale-exec",
            "node_trace_refs": {"other_node": "events://stale-exec#node:other_node"},
            "is_replay_ready": True,
            "is_audit_ready": True,
        },
        "replay_payload": {
            "execution_id": "different-exec",
            "node_order": ["other_node"],
            "expected_outputs": {"other_node": {"value": "wrong"}},
        },
    }

    contract = synthesize_execution_record_reference_contract_from_payload(payload)

    assert contract['run_id'] == 'native-exec'
    assert contract['primary_trace_ref'] == 'events://native-exec'
    assert 'native_node' in contract['node_trace_refs']
    assert 'other_node' not in contract['node_trace_refs']
    assert payload['execution_record_reference_contract'] == contract


def test_materialize_execution_record_from_payload_rebuilds_top_level_thin_record_when_richer_payload_exists():
    payload = {
        "meta": {"run_id": "run-123", "status": "completed"},
        "source": {"commit_id": "commit-thin"},
        "trace": {"events": ["started", "completed"]},
        "replay_payload": {
            "execution_id": "run-123",
            "node_order": ["node_a"],
            "input_state": {"message": "hi"},
            "expected_outputs": {"node_a": {"value": "ok"}},
        },
        "result": {
            "status": "success",
            "state": {"node_a": {"value": "ok"}},
            "node_results": {
                "node_a": {"status": "success", "output": {"value": "ok"}},
            },
        },
    }

    record = materialize_execution_record_from_payload(payload)

    assert record["meta"]["run_id"] == "run-123"
    assert record["source"]["commit_id"] == "commit-thin"
    assert record["timeline"]["event_stream_ref"] == "events://run-123"


def test_synthesize_execution_record_reference_contract_prefers_materialized_truth_over_top_level_thin_record():
    payload = {
        "meta": {"run_id": "run-123", "status": "completed"},
        "source": {"commit_id": "commit-thin"},
        "execution_record_reference_contract": {
            "run_id": "stale-exec",
            "primary_trace_ref": "events://stale-exec",
            "node_trace_refs": {"other_node": "events://stale-exec#node:other_node"},
            "is_replay_ready": True,
            "is_audit_ready": True,
        },
        "trace": {"events": ["started", "completed"]},
        "replay_payload": {
            "execution_id": "run-123",
            "node_order": ["node_a"],
            "expected_outputs": {"node_a": {"value": "ok"}},
        },
        "result": {
            "status": "success",
            "state": {"node_a": {"value": "ok"}},
            "node_results": {
                "node_a": {"status": "success", "output": {"value": "ok"}},
            },
        },
    }

    contract = synthesize_execution_record_reference_contract_from_payload(payload)

    assert contract["run_id"] == "run-123"
    assert contract["commit_id"] == "commit-thin"
    assert contract["primary_trace_ref"] == "events://run-123"
    assert "node_a" in contract["node_trace_refs"]
    assert "other_node" not in contract["node_trace_refs"]
    assert payload["execution_record_reference_contract"] == contract


# ──────────────────────────────────────────────────────────────────────────────
# Regression tests for truth-ordering fixes (F1 + F2)
# ──────────────────────────────────────────────────────────────────────────────

def test_f1_synthesize_and_create_artifact_components_agree_on_primary_trace_ref_for_expected_outputs_only_payload():
    """F1 regression: synthesize_* and create_serialized_execution_artifact_components must agree
    on primary_trace_ref when the payload has only replay_payload.expected_outputs (no trace, no
    node_order, no node_results, no input_state) and a stale execution_record_reference_contract.

    Before the fix, synthesize_* returned the stale contract's primary_trace_ref ('events://stale')
    while create_serialized_execution_artifact_components returned None.
    After the fix, both return None (fresh contract from materialized record, no trace in payload).
    """
    from src.storage.lifecycle_api import create_serialized_execution_artifact_components

    payload = {
        "execution_record_reference_contract": {
            "run_id": "run-123",
            "primary_trace_ref": "events://stale",
            "is_replay_ready": True,
            "is_audit_ready": True,
        },
        "replay_payload": {
            "execution_id": "run-123",
            "expected_outputs": {"node_a": {"value": "ok"}},
        },
    }

    # synthesize_* path
    import copy
    payload_for_synth = copy.deepcopy(payload)
    synth_contract = synthesize_execution_record_reference_contract_from_payload(payload_for_synth)

    # create_serialized_execution_artifact_components path
    payload_for_components = copy.deepcopy(payload)
    components = create_serialized_execution_artifact_components(payload_for_components)
    components_contract = components.get("execution_record_reference_contract", {})

    assert synth_contract.get("primary_trace_ref") == components_contract.get("primary_trace_ref"), (
        f"synthesize_* returned {synth_contract.get('primary_trace_ref')!r} but "
        f"create_serialized_execution_artifact_components returned {components_contract.get('primary_trace_ref')!r}"
    )
    # Both should have discarded the stale "events://stale" in favour of the fresh (None) value.
    assert synth_contract.get("primary_trace_ref") is None
    assert components_contract.get("primary_trace_ref") is None


def test_f2_materialize_prefers_result_node_results_over_stale_expected_outputs_for_final_outputs():
    """F2 regression: materialize_execution_record_from_payload must prefer snapshot.node_outputs
    (built from result.node_results, which has actual execution truth) over the stale
    replay_payload.expected_outputs when they differ.

    Before the fix, expected_outputs won unconditionally when non-empty, so a stale
    replay_payload.expected_outputs would shadow the richer result.node_results output.
    """
    payload = {
        "replay_payload": {
            "execution_id": "run-stale-test",
            "node_order": ["node_a"],
            "input_state": {"message": "hi"},
            "expected_outputs": {"node_a": "STALE_VALUE"},   # stale from a prior run
        },
        "result": {
            "status": "success",
            "state": {"node_a": "FRESH_VALUE"},
            "node_results": {
                "node_a": {"status": "success", "output": "FRESH_VALUE"},
            },
        },
        "trace": {"events": ["started", "completed"]},
    }

    record = materialize_execution_record_from_payload(payload)

    final_outputs = record.get("outputs", {}).get("final_outputs", [])
    assert final_outputs, "Expected at least one final_output entry"

    node_a_output = next(
        (item for item in final_outputs if item.get("output_ref") == "node_a"),
        None,
    )
    assert node_a_output is not None, "node_a not found in final_outputs"

    # value_payload comes from snapshot.node_outputs, which resolved result.node_results first.
    assert node_a_output.get("value_payload") == "FRESH_VALUE", (
        f"Expected 'FRESH_VALUE' from result.node_results but got {node_a_output.get('value_payload')!r}. "
        "Stale replay_payload.expected_outputs appears to have outranked richer result truth."
    )


def test_create_execution_record_from_snapshot_supports_paused_status_and_semantic_summary():
    record = create_execution_record_from_snapshot(
        make_snapshot(),
        commit_id='commit-1',
        status='paused',
        termination_reason='quality_review_required',
    )
    assert record.meta.status == 'paused'
    assert record.outputs.semantic_status == 'paused'
    assert record.diagnostics.termination_reason == 'quality_review_required'


def test_create_serialized_execution_record_from_circuit_run_infers_paused_status_from_trace_event():
    circuit = {
        'id': 'paused-circuit',
        'nodes': [{'id': 'n1'}],
    }
    payload = create_serialized_execution_record_from_circuit_run(
        circuit,
        {'n1': {'value': 'draft'}},
        execution_id='paused-exec',
        trace={
            'events': [
                {'type': 'execution_started'},
                {'type': 'execution_paused', 'payload': {'reason': 'quality_review_required'}},
            ]
        },
    )
    assert payload['meta']['status'] == 'paused'
    assert payload['outputs']['semantic_status'] == 'paused'
    assert payload['diagnostics']['termination_reason'] == 'quality_review_required'


def test_materialize_execution_record_from_payload_preserves_paused_status_from_trace():
    payload = {
        'trace': {
            'events': [
                {'type': 'execution_started'},
                {'type': 'execution_paused', 'payload': {'reason': 'human_review_required'}},
            ]
        },
        'replay_payload': {
            'execution_id': 'run-paused',
            'node_order': ['node_a'],
            'input_state': {'message': 'hi'},
            'expected_outputs': {'node_a': {'value': 'draft'}},
        },
        'result': {
            'status': 'success',
            'state': {'node_a': {'value': 'draft'}},
            'node_results': {
                'node_a': {'status': 'partial', 'output': {'value': 'draft'}},
            },
        },
    }

    record = materialize_execution_record_from_payload(payload)

    assert record['meta']['status'] == 'paused'
    assert record['outputs']['semantic_status'] == 'paused'
    assert record['diagnostics']['termination_reason'] == 'human_review_required'
