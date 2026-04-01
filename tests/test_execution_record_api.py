from __future__ import annotations

import json

from src.engine.execution_artifact_hashing import ExecutionHashReport, NodeOutputHash
from src.engine.execution_snapshot import ExecutionSnapshotBuilder
from src.engine.execution_timeline import ExecutionTimeline, NodeExecutionSpan
from src.storage.execution_record_api import (
    create_execution_record_from_snapshot,
    summarize_execution_record_for_working_save,
)
from src.storage.serialization import save_execution_record_file, serialize_execution_record


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
