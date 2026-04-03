from __future__ import annotations

import pytest

from src.storage.models.execution_record_model import (
    ExecutionArtifactsModel,
    ExecutionDiagnosticsModel,
    ExecutionInputModel,
    ExecutionIssue,
    ExecutionMetaModel,
    ExecutionObservabilityModel,
    ExecutionOutputModel,
    ExecutionRecordModel,
    ExecutionSourceModel,
    ExecutionTimelineModel,
    NodeResultsModel,
)


def make_record() -> ExecutionRecordModel:
    return ExecutionRecordModel(
        meta=ExecutionMetaModel(
            run_id='run-1',
            record_format_version='1.0.0',
            created_at='2026-04-01T00:00:00Z',
            started_at='2026-04-01T00:00:00Z',
            finished_at='2026-04-01T00:01:00Z',
            status='completed',
        ),
        source=ExecutionSourceModel(commit_id='commit-1', trigger_type='manual_run'),
        input=ExecutionInputModel(input_summary={'question': 'What is AI?'}),
        timeline=ExecutionTimelineModel(node_order=['n1']),
        node_results=NodeResultsModel(),
        outputs=ExecutionOutputModel(),
        artifacts=ExecutionArtifactsModel(),
        diagnostics=ExecutionDiagnosticsModel(),
        observability=ExecutionObservabilityModel(metrics={'total_duration_ms': 60000}),
    )


def test_execution_record_model_constructs_minimally():
    record = make_record()
    assert record.meta.run_id == 'run-1'
    assert record.source.commit_id == 'commit-1'


def test_execution_record_meta_rejects_unknown_status():
    with pytest.raises(ValueError):
        ExecutionMetaModel(
            run_id='run-1',
            record_format_version='1.0.0',
            created_at='2026-04-01T00:00:00Z',
            started_at='2026-04-01T00:00:00Z',
            status='unknown',
        )


def test_execution_record_source_requires_commit_id():
    with pytest.raises(ValueError):
        ExecutionSourceModel(commit_id='', trigger_type='manual_run')


def test_execution_issue_validates_category_and_severity():
    issue = ExecutionIssue(issue_code='E1', category='runtime', severity='high', message='boom')
    assert issue.category == 'runtime'
    with pytest.raises(ValueError):
        ExecutionIssue(issue_code='E1', category='bad', severity='high', message='boom')


def test_execution_record_meta_accepts_paused_status():
    meta = ExecutionMetaModel(
        run_id='run-paused',
        record_format_version='1.0.0',
        created_at='2026-04-01T00:00:00Z',
        started_at='2026-04-01T00:00:00Z',
        finished_at='2026-04-01T00:01:00Z',
        status='paused',
    )
    assert meta.status == 'paused'
