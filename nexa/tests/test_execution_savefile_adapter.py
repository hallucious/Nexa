from __future__ import annotations

from src.cli.savefile_runtime import _load_execution_context
from src.contracts.nex_contract import WORKING_SAVE_ROLE
from src.savefiles.executor import execute_ai_node
from src.contracts.savefile_format import NodeSpec
from src.platform.provider_registry import ProviderRegistry
from src.providers.provider_adapter_contract import make_failure
from src.storage.execution_savefile_adapter import (
    ExecutionSavefileAdapter,
    execution_savefile_from_commit_snapshot_model,
)
from src.storage.lifecycle_api import create_commit_snapshot_from_working_save
from src.storage.models.shared_sections import CircuitModel, ResourcesModel, StateModel
from src.storage.models.working_save_model import RuntimeModel, UIModel, WorkingSaveMeta, WorkingSaveModel
from src.storage.serialization import save_nex_artifact_file



def _working_save() -> WorkingSaveModel:
    return WorkingSaveModel(
        meta=WorkingSaveMeta(
            format_version="1.0.0",
            storage_role=WORKING_SAVE_ROLE,
            working_save_id="ws-adapter-1",
            name="Example Workflow",
        ),
        circuit=CircuitModel(
            nodes=[
                {
                    "id": "step1",
                    "kind": "ai",
                    "resource_ref": {"prompt": "main", "provider": "p1"},
                    "inputs": {"question": "input.question"},
                    "outputs": {"text": "state.working.answer"},
                }
            ],
            edges=[],
            entry="step1",
            outputs=[{"name": "answer", "node_id": "step1", "path": "text"}],
        ),
        resources=ResourcesModel(
            prompts={"main": {"template": "Answer: {{question}}"}},
            providers={"p1": {"type": "test", "model": "test-model", "config": {}}},
            plugins={},
        ),
        state=StateModel(input={"question": "What is Nexa?"}, working={}, memory={}),
        runtime=RuntimeModel(status="draft", validation_summary={}, last_run={}, errors=[]),
        ui=UIModel(layout={}, metadata={}),
    )


class _BridgeStyleFailingProvider:
    def execute(self, request):
        return make_failure(
            error="backend unavailable",
            raw={},
            reason_code="AI.provider_error",
            latency_ms=5,
        )



def test_load_execution_context_uses_execution_adapter_for_public_nex(tmp_path):
    artifact_path = tmp_path / "adapter_working_save.nex"
    save_nex_artifact_file(_working_save(), artifact_path)

    context = _load_execution_context(str(artifact_path))

    assert isinstance(context.savefile, ExecutionSavefileAdapter)
    assert context.savefile.meta.name == "Example Workflow"
    assert context.savefile.circuit.nodes[0].id == "step1"



def test_execution_adapter_for_commit_snapshot_preserves_commit_metadata_in_ui():
    snapshot = create_commit_snapshot_from_working_save(_working_save(), commit_id="commit-adapter-1")

    adapter = execution_savefile_from_commit_snapshot_model(snapshot)

    assert adapter.ui.metadata["storage_role"] == "commit_snapshot"
    assert adapter.ui.metadata["commit_id"] == "commit-adapter-1"
    assert adapter.circuit.entry == "step1"



def test_execute_ai_node_handles_string_provider_error_from_bridge_contract():
    savefile = execution_savefile_from_commit_snapshot_model(
        create_commit_snapshot_from_working_save(_working_save(), commit_id="commit-adapter-err")
    )
    node = NodeSpec(
        id="step1",
        kind="ai",
        resource_ref={"prompt": "main", "provider": "p1"},
        inputs={"question": "input.question"},
        outputs={"text": "state.working.answer"},
    )
    provider_registry = ProviderRegistry()
    provider_registry.register("p1", _BridgeStyleFailingProvider())

    result = execute_ai_node(
        node=node,
        savefile=savefile,
        state={"input": {"question": "What is Nexa?"}, "working": {}, "memory": {}},
        node_outputs={},
        provider_registry=provider_registry,
    )

    assert result.status == "failure"
    assert result.error == "Provider error: backend unavailable"
