from __future__ import annotations

from dataclasses import replace

from src.storage.lifecycle_api import create_commit_snapshot_from_working_save
from src.storage.nex_api import load_nex
from src.storage.serialization import serialize_commit_snapshot, serialize_working_save
from src.storage.models.shared_sections import CircuitModel, ResourcesModel, StateModel
from src.storage.models.working_save_model import RuntimeModel, UIModel, WorkingSaveMeta, WorkingSaveModel
from src.ui.i18n import DEFAULT_UI_LANGUAGE, ui_language_from_sources


def _working_save(*, app_language: str | None = None) -> WorkingSaveModel:
    metadata = {}
    if app_language is not None:
        metadata["app_language"] = app_language
    return WorkingSaveModel(
        meta=WorkingSaveMeta(
            format_version="1.0.0",
            storage_role="working_save",
            working_save_id="ws-001",
            name="Draft",
        ),
        circuit=CircuitModel(
            nodes=[{"id": "n1"}],
            edges=[],
            entry="n1",
            outputs=[{"name": "out", "source": "n1"}],
        ),
        resources=ResourcesModel(prompts={}, providers={}, plugins={}),
        state=StateModel(input={"question": "What is AI?"}, working={}, memory={}),
        runtime=RuntimeModel(status="validated", validation_summary={"blocking_count": 0}, last_run={}, errors=[]),
        ui=UIModel(layout={}, metadata=metadata),
    )


def test_working_save_serialization_preserves_app_language_for_ui_owned_restore() -> None:
    working_save = _working_save(app_language="ko-KR")

    payload = serialize_working_save(working_save)
    loaded = load_nex(payload)

    assert payload["ui"]["metadata"]["app_language"] == "ko-KR"
    assert loaded.storage_role == "working_save"
    assert loaded.parsed_model.ui.metadata["app_language"] == "ko-KR"
    assert ui_language_from_sources(loaded) == "ko"



def test_ui_language_from_sources_defaults_to_english_when_preference_is_missing() -> None:
    working_save = _working_save(app_language=None)

    assert ui_language_from_sources(working_save) == DEFAULT_UI_LANGUAGE



def test_ui_language_from_sources_falls_back_to_english_for_unsupported_persisted_value() -> None:
    working_save = _working_save(app_language="fr-FR")

    assert ui_language_from_sources(working_save) == "en"



def test_create_commit_snapshot_from_working_save_strips_canonical_ui_language_state() -> None:
    working_save = _working_save(app_language="ko-KR")

    snapshot = create_commit_snapshot_from_working_save(
        working_save,
        commit_id="commit-001",
        created_at="2026-04-07T00:00:00Z",
    )
    payload = serialize_commit_snapshot(snapshot)

    assert snapshot.meta.storage_role == "commit_snapshot"
    assert not hasattr(snapshot, "ui")
    assert "ui" not in payload
    assert payload["meta"]["source_working_save_id"] == "ws-001"



def test_commit_snapshot_rejects_ui_app_language_payload_even_when_it_looks_like_valid_preference_state() -> None:
    payload = {
        "meta": {
            "format_version": "1.0.0",
            "storage_role": "commit_snapshot",
            "commit_id": "commit-001",
            "source_working_save_id": "ws-001",
        },
        "circuit": {
            "nodes": [{"id": "n1"}],
            "edges": [],
            "entry": "n1",
            "outputs": [{"name": "out", "source": "n1"}],
        },
        "resources": {"prompts": {}, "providers": {}, "plugins": {}},
        "state": {"input": {}, "working": {}, "memory": {}},
        "validation": {"validation_result": "passed", "summary": {}},
        "approval": {"approval_completed": True, "approval_status": "approved", "summary": {}},
        "lineage": {"source_working_save_id": "ws-001", "metadata": {}},
        "ui": {"layout": {}, "metadata": {"app_language": "ko-KR"}},
    }

    loaded = load_nex(payload)

    assert loaded.storage_role == "commit_snapshot"
    assert loaded.load_status == "rejected"
    codes = {finding.code for finding in loaded.findings}
    assert "COMMIT_SNAPSHOT_FORBIDDEN_SECTION_PRESENT" in codes



def test_app_language_does_not_change_commit_snapshot_structural_truth() -> None:
    korean = _working_save(app_language="ko-KR")
    english = _working_save(app_language="en-US")

    korean_snapshot = create_commit_snapshot_from_working_save(
        korean,
        commit_id="commit-001",
        created_at="2026-04-07T00:00:00Z",
    )
    english_snapshot = create_commit_snapshot_from_working_save(
        english,
        commit_id="commit-001",
        created_at="2026-04-07T00:00:00Z",
    )

    assert serialize_commit_snapshot(korean_snapshot) == serialize_commit_snapshot(english_snapshot)



def test_non_language_ui_metadata_stays_on_working_save_side_only() -> None:
    working_save = replace(
        _working_save(app_language="ko-KR"),
        ui=UIModel(layout={"graph": {"zoom": 1.25}}, metadata={"app_language": "ko-KR", "theme": "dark"}),
    )

    payload = serialize_working_save(working_save)
    loaded = load_nex(payload)

    assert loaded.parsed_model.ui.layout == {"graph": {"zoom": 1.25}}
    assert loaded.parsed_model.ui.metadata == {"app_language": "ko-KR", "theme": "dark"}

    snapshot = create_commit_snapshot_from_working_save(
        loaded.parsed_model,
        commit_id="commit-001",
        created_at="2026-04-07T00:00:00Z",
    )
    snapshot_payload = serialize_commit_snapshot(snapshot)

    assert "ui" not in snapshot_payload
