from __future__ import annotations

from src.storage.models.shared_sections import CircuitModel, ResourcesModel, StateModel
from src.storage.models.working_save_model import RuntimeModel, UIModel, WorkingSaveMeta, WorkingSaveModel
from src.storage.models.commit_snapshot_model import CommitApprovalModel, CommitLineageModel, CommitSnapshotMeta, CommitSnapshotModel, CommitValidationModel
from src.ui.template_gallery import read_template_gallery_view_model


def _empty_working_save() -> WorkingSaveModel:
    return WorkingSaveModel(
        meta=WorkingSaveMeta(format_version="1.0.0", storage_role="working_save", working_save_id="ws-empty", name="Empty"),
        circuit=CircuitModel(nodes=[], edges=[], entry=None, outputs=[]),
        resources=ResourcesModel(prompts={}, providers={}, plugins={}),
        state=StateModel(input={}, working={}, memory={}),
        runtime=RuntimeModel(status="draft", validation_summary={}, last_run={}, errors=[]),
        ui=UIModel(layout={}, metadata={}),
    )


def test_template_gallery_lists_representative_starter_workflows_for_empty_working_save() -> None:
    vm = read_template_gallery_view_model(_empty_working_save())

    assert vm.visible is True
    assert vm.gallery_status == "ready"
    assert len(vm.templates) == 10
    assert {item.template_id for item in vm.templates} == {
        "text_summarizer",
        "review_classifier",
        "document_analyzer",
        "email_drafter",
        "code_reviewer",
        "news_briefer",
        "qa_responder",
        "data_extractor",
        "translation_helper",
        "content_rewriter",
    }


def test_template_gallery_hides_for_non_empty_or_non_working_save_contexts() -> None:
    non_empty = WorkingSaveModel(
        meta=WorkingSaveMeta(format_version="1.0.0", storage_role="working_save", working_save_id="ws-full", name="Full"),
        circuit=CircuitModel(nodes=[{"id": "n1"}], edges=[], entry="n1", outputs=[]),
        resources=ResourcesModel(prompts={}, providers={}, plugins={}),
        state=StateModel(input={}, working={}, memory={}),
        runtime=RuntimeModel(status="draft", validation_summary={}, last_run={}, errors=[]),
        ui=UIModel(layout={}, metadata={}),
    )
    commit = CommitSnapshotModel(
        meta=CommitSnapshotMeta(format_version="1.0.0", storage_role="commit_snapshot", commit_id="c1", source_working_save_id="ws-full", name="Commit"),
        circuit=CircuitModel(nodes=[], edges=[], entry=None, outputs=[]),
        resources=ResourcesModel(prompts={}, providers={}, plugins={}),
        state=StateModel(input={}, working={}, memory={}),
        validation=CommitValidationModel(validation_result="pass", summary={}),
        approval=CommitApprovalModel(approval_completed=True, approval_status="approved", summary={}),
        lineage=CommitLineageModel(source_working_save_id="ws-full"),
    )

    assert read_template_gallery_view_model(non_empty).visible is False
    assert read_template_gallery_view_model(commit).visible is False
