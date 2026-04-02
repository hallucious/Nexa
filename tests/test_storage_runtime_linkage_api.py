from __future__ import annotations

import pytest

from src.engine.execution_artifact_hashing import ExecutionHashReport
from src.engine.execution_snapshot import ExecutionSnapshotBuilder
from src.engine.execution_timeline import ExecutionTimeline, NodeExecutionSpan
from src.storage.lifecycle_api import (
    create_commit_snapshot_from_working_save,
    create_execution_record_and_update_working_save,
    create_execution_record_from_commit_snapshot,
    create_serialized_commit_snapshot_from_working_save,
    create_serialized_execution_record_from_commit_snapshot,
    create_serialized_execution_transition,
    create_serialized_savefile_execution_payload,
    create_serialized_circuit_execution_payload,
    create_serialized_audit_export_payload,
    create_serialized_audit_bundle_contents,
    create_serialized_audit_replay_components,
)
from src.storage.models.commit_snapshot_model import CommitApprovalModel, CommitLineageModel, CommitSnapshotMeta, CommitSnapshotModel, CommitValidationModel
from src.storage.models.shared_sections import CircuitModel, ResourcesModel, StateModel
from src.storage.models.working_save_model import RuntimeModel, UIModel, WorkingSaveMeta, WorkingSaveModel


def make_working_save(*, working_save_id: str = 'ws-1') -> WorkingSaveModel:
    return WorkingSaveModel(
        meta=WorkingSaveMeta(
            format_version='1.0.0',
            storage_role='working_save',
            name='Draft',
            working_save_id=working_save_id,
        ),
        circuit=CircuitModel(
            nodes=[{'id': 'n1'}],
            edges=[],
            entry='n1',
            outputs=[{'name': 'out', 'source': 'n1'}],
        ),
        resources=ResourcesModel(prompts={}, providers={}, plugins={}),
        state=StateModel(input={'question': 'What is AI?'}, working={}, memory={}),
        runtime=RuntimeModel(status='validated', validation_summary={'blocking_count': 0}),
        ui=UIModel(layout={}, metadata={}),
    )


def make_snapshot(*, status: str = 'success'):
    timeline = ExecutionTimeline(
        execution_id='exec-1',
        start_ms=1000,
        end_ms=2000,
        duration_ms=1000,
        node_spans=[NodeExecutionSpan('n1', 1000, 2000, 1000, status)],
    )
    return ExecutionSnapshotBuilder().build(
        execution_id='exec-1',
        timeline=timeline,
        outputs={'out': {'value': 'done'}},
        hash_report=ExecutionHashReport(execution_id='exec-1', node_hashes=[]),
    )


def make_unapproved_commit_snapshot() -> CommitSnapshotModel:
    return CommitSnapshotModel(
        meta=CommitSnapshotMeta(
            format_version='1.0.0',
            storage_role='commit_snapshot',
            name='Draft',
            commit_id='cs-1',
            source_working_save_id='ws-1',
        ),
        circuit=CircuitModel(nodes=[{'id': 'n1'}], edges=[], entry='n1', outputs=[{'name': 'out', 'source': 'n1'}]),
        resources=ResourcesModel(prompts={}, providers={}, plugins={}),
        state=StateModel(input={}, working={}, memory={}),
        validation=CommitValidationModel(validation_result='passed', summary={}),
        approval=CommitApprovalModel(approval_completed=False, approval_status='pending', summary={}),
        lineage=CommitLineageModel(source_working_save_id='ws-1', metadata={}),
    )


def test_create_execution_record_from_commit_snapshot_uses_snapshot_identity():
    working = make_working_save()
    commit_snapshot = create_commit_snapshot_from_working_save(working, commit_id='cs-1')
    record = create_execution_record_from_commit_snapshot(make_snapshot(), commit_snapshot)
    assert record.source.commit_id == 'cs-1'
    assert record.source.working_save_id == 'ws-1'
    assert record.meta.title == 'Draft'


def test_create_execution_record_from_commit_snapshot_rejects_unapproved_snapshot():
    with pytest.raises(ValueError):
        create_execution_record_from_commit_snapshot(make_snapshot(), make_unapproved_commit_snapshot())


def test_create_execution_record_from_commit_snapshot_rejects_failed_validation_snapshot():
    working = make_working_save()
    commit_snapshot = create_commit_snapshot_from_working_save(working, commit_id='cs-1', validation_result='failed')
    with pytest.raises(ValueError):
        create_execution_record_from_commit_snapshot(make_snapshot(), commit_snapshot)


def test_create_execution_record_and_update_working_save_links_record_and_summary():
    working = make_working_save()
    commit_snapshot = create_commit_snapshot_from_working_save(working, commit_id='cs-1')
    record, updated = create_execution_record_and_update_working_save(make_snapshot(), commit_snapshot, working)
    assert record.source.commit_id == 'cs-1'
    assert updated.runtime.last_run['commit_id'] == 'cs-1'
    assert updated.runtime.last_run['run_id'] == record.meta.run_id
    assert updated.runtime.status == 'executed'


def test_create_execution_record_and_update_working_save_rejects_mismatched_working_save():
    working = make_working_save(working_save_id='ws-1')
    other_working = make_working_save(working_save_id='ws-2')
    commit_snapshot = create_commit_snapshot_from_working_save(working, commit_id='cs-1')
    with pytest.raises(ValueError):
        create_execution_record_and_update_working_save(make_snapshot(), commit_snapshot, other_working)


def test_create_execution_record_and_update_working_save_propagates_output_summary_fields():
    working = make_working_save()
    commit_snapshot = create_commit_snapshot_from_working_save(working, commit_id='cs-1')
    record, updated = create_execution_record_and_update_working_save(make_snapshot(), commit_snapshot, working)
    assert updated.runtime.last_run['output_count'] == 1
    assert updated.runtime.last_run['output_refs'] == ['out']
    assert updated.runtime.last_run['semantic_status'] == 'normal'
    assert record.outputs.final_outputs[0].value_payload == {'value': 'done'}


def test_create_execution_record_and_update_working_save_propagates_trace_and_artifact_linkage_summary():
    working = make_working_save()
    commit_snapshot = create_commit_snapshot_from_working_save(working, commit_id='cs-1')
    record, updated = create_execution_record_and_update_working_save(
        make_snapshot(),
        commit_snapshot,
        working,
        trace_ref='trace://exec-1',
        event_stream_ref='events://exec-1',
    )
    assert updated.runtime.last_run['trace_ref'] == 'trace://exec-1'
    assert updated.runtime.last_run['event_stream_ref'] == 'events://exec-1'
    assert updated.runtime.last_run['primary_trace_ref'] == 'events://exec-1'
    assert updated.runtime.last_run['artifact_ids'] == ['artifact::output::out']
    assert updated.runtime.last_run['replay_ready'] is True
    assert updated.runtime.last_run['audit_ready'] is True
    assert record.node_results.results[0].artifact_refs == []


def test_create_serialized_commit_snapshot_from_working_save_exposes_commit_boundary_payload():
    working = make_working_save()
    payload = create_serialized_commit_snapshot_from_working_save(working, commit_id='cs-1')
    assert payload['meta']['storage_role'] == 'commit_snapshot'
    assert payload['meta']['commit_id'] == 'cs-1'
    assert payload['meta']['source_working_save_id'] == 'ws-1'


def test_create_serialized_execution_record_from_commit_snapshot_exposes_native_record_payload():
    working = make_working_save()
    commit_snapshot = create_commit_snapshot_from_working_save(working, commit_id='cs-1')
    payload = create_serialized_execution_record_from_commit_snapshot(
        make_snapshot(),
        commit_snapshot,
        trace_ref='trace://exec-1',
        event_stream_ref='events://exec-1',
    )
    assert payload['source']['commit_id'] == 'cs-1'
    assert payload['timeline']['trace_ref'] == 'trace://exec-1'
    assert payload['timeline']['event_stream_ref'] == 'events://exec-1'


def test_create_serialized_execution_transition_returns_execution_record_updated_working_save_and_contract():
    working = make_working_save()
    commit_snapshot = create_commit_snapshot_from_working_save(working, commit_id='cs-1')
    transition = create_serialized_execution_transition(
        make_snapshot(),
        commit_snapshot,
        working,
        trace_ref='trace://exec-1',
        event_stream_ref='events://exec-1',
    )
    assert transition['execution_record']['source']['commit_id'] == 'cs-1'
    assert transition['updated_working_save']['runtime']['status'] == 'executed'
    assert transition['execution_record_reference_contract']['primary_trace_ref'] == 'events://exec-1'
    assert transition['last_run_summary']['replay_ready'] is True


from src.contracts.savefile_executor_aligned import NodeExecutionResult, SavefileExecutionTrace
from tests.savefile_test_helpers import make_demo_savefile


def test_create_serialized_savefile_execution_payload_uses_lifecycle_api_shape():
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

    payload = create_serialized_savefile_execution_payload(savefile, trace, started_at=1.0, ended_at=2.0)

    assert payload['execution_record']['meta']['run_id'] == 'savefile-run-1'
    assert payload['execution_record_reference_contract']['run_id'] == 'savefile-run-1'
    assert payload['replay_payload']['execution_id'] == 'savefile-run-1'


def test_create_serialized_circuit_execution_payload_uses_lifecycle_api_shape():
    circuit = {
        'id': 'demo-circuit',
        'nodes': [{'id': 'node_a'}, {'id': 'node_b'}],
    }
    final_state = {'node_a': {'value': 'hello'}, 'node_b': {'value': 'world'}}

    payload = create_serialized_circuit_execution_payload(
        circuit,
        final_state,
        initial_state={'message': 'Hello Nexa'},
        execution_configs={'node_a': {'provider': 'echo'}},
        started_at=1.0,
        ended_at=2.0,
        trace={'events': []},
        artifacts=[],
    )

    assert payload['execution_record']['meta']['run_id'] == 'demo-circuit'
    assert payload['execution_record_reference_contract']['run_id'] == 'demo-circuit'
    assert payload['replay_payload']['execution_id'] == 'demo-circuit'



def test_create_serialized_audit_export_payload_centralizes_audit_components():
    payload = {
        'result': {'state': {'node_a': {'value': 'hello'}}},
        'summary': {'duration_ms': 1},
        'trace': {'events': []},
        'artifacts': [{'name': 'greeting', 'value': 'hello'}],
        'replay_payload': {
            'execution_id': 'audit-demo',
            'node_order': ['node_a'],
            'circuit': {'id': 'audit-demo', 'nodes': [{'id': 'node_a'}]},
            'execution_configs': {},
            'input_state': {'message': 'hello'},
            'expected_outputs': {'node_a': {'value': 'hello'}},
        },
    }

    audit_payload = create_serialized_audit_export_payload(payload)

    assert audit_payload['metadata']['format'] == 'nexa.audit_pack'
    assert audit_payload['replay_payload']['execution_id'] == 'audit-demo'
    assert audit_payload['execution_record']['meta']['run_id'] == 'audit-demo'
    assert audit_payload['execution_record_reference_contract']['run_id'] == 'audit-demo'
    assert audit_payload['execution_trace_payload']['state']['node_a']['value'] == 'hello'


def test_create_serialized_audit_bundle_contents_exposes_file_oriented_components():
    payload = {
        'result': {'state': {'node_a': {'value': 'hello'}}},
        'summary': {'duration_ms': 1},
        'trace': {'events': []},
        'artifacts': [{'name': 'greeting', 'value': 'hello'}],
        'replay_payload': {
            'execution_id': 'audit-demo',
            'node_order': ['node_a'],
            'circuit': {'id': 'audit-demo', 'nodes': [{'id': 'node_a'}]},
            'execution_configs': {},
            'input_state': {'message': 'hello'},
            'expected_outputs': {'node_a': {'value': 'hello'}},
        },
    }

    contents = create_serialized_audit_bundle_contents(payload)

    assert contents['metadata.json']['format'] == 'nexa.audit_pack'
    assert contents['replay_payload.json']['execution_id'] == 'audit-demo'
    assert contents['execution_record.json']['meta']['run_id'] == 'audit-demo'
    assert contents['execution_record_reference_contract.json']['run_id'] == 'audit-demo'


def test_create_serialized_audit_replay_components_normalizes_replay_inputs():
    payload = {
        'replay_payload': {
            'execution_id': 'audit-demo',
            'node_order': ['node_a'],
            'circuit': {'id': 'audit-demo', 'nodes': [{'id': 'node_a'}]},
            'execution_configs': {},
            'input_state': {'message': 'hello'},
            'expected_outputs': {'node_a': {'value': 'hello'}},
        },
        'execution_record': {
            'meta': {'run_id': 'audit-demo', 'status': 'completed'},
            'source': {'commit_id': 'commit::unknown'},
            'timeline': {'trace_ref': 'trace://audit-demo', 'event_stream_ref': 'events://audit-demo'},
            'outputs': {'final_outputs': []},
            'artifacts': {'artifacts': []},
            'node_results': {'results': []},
            'diagnostics': {'warnings': [], 'errors': []},
            'observability': {'trace_summary': '', 'provider_usage_summary': {}, 'plugin_usage_summary': {}, 'refs': []},
        },
    }

    components = create_serialized_audit_replay_components(payload)

    assert components['replay_payload']['execution_id'] == 'audit-demo'
    assert components['execution_record']['meta']['run_id'] == 'audit-demo'
    assert components['execution_record_reference_contract']['run_id'] == 'audit-demo'
    assert components['primary_trace_ref'] == 'events://audit-demo'
