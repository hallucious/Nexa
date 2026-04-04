from __future__ import annotations

from pathlib import Path
import sys

from src.contracts.savefile_loader import load_savefile
from src.contracts.savefile_executor_aligned import SavefileExecutor
from src.platform.provider_registry import ProviderRegistry


def _review_bundle_payload(entry_path: str) -> dict:
    return {
        "meta": {"name": "review-bundle", "version": "2.0.0"},
        "circuit": {
            "entry": "draft_generator",
            "nodes": [
                {
                    "id": "draft_generator",
                    "kind": "provider",
                    "execution": {
                        "provider": {
                            "provider_id": "provider.gpt",
                            "prompt_ref": "prompt.draft",
                            "inputs": {"question": "input.question"},
                        }
                    },
                },
                {
                    "id": "review_bundle_stage",
                    "kind": "subcircuit",
                    "execution": {
                        "subcircuit": {
                            "child_circuit_ref": "internal:review_bundle",
                            "input_mapping": {
                                "question": "input.question",
                                "draft": "node.draft_generator.output.result",
                            },
                            "output_binding": {
                                "result": "child.output.result",
                                "confidence": "child.output.confidence",
                                "reasoning_summary": "child.output.reasoning_summary",
                            },
                            "runtime_policy": {
                                "trace_mode": "full",
                                "fail_fast": True,
                            },
                        }
                    },
                    "outputs": {"result": "state.working.reviewed"},
                },
            ],
            "edges": [{"from": "draft_generator", "to": "review_bundle_stage"}],
            "outputs": [{"name": "final_result", "source": "state.working.reviewed"}],
            "subcircuits": {
                "review_bundle": {
                    "entry": "draft_critic",
                    "nodes": [
                        {
                            "id": "draft_critic",
                            "type": "plugin",
                            "resource_ref": {"plugin": "plugin.review"},
                            "inputs": {"text": "input.draft"},
                            "outputs": {"result": "state.working.critique"},
                        },
                        {
                            "id": "evidence_check",
                            "type": "plugin",
                            "resource_ref": {"plugin": "plugin.review"},
                            "inputs": {"text": "input.question"},
                            "outputs": {"result": "state.working.evidence"},
                        },
                        {
                            "id": "review_synthesizer",
                            "type": "plugin",
                            "resource_ref": {"plugin": "plugin.synth"},
                            "inputs": {
                                "draft": "input.draft",
                                "critique": "node.draft_critic.output.result",
                                "evidence": "node.evidence_check.output.result",
                            },
                            "outputs": {
                                "result": "state.working.result",
                                "confidence": "state.working.confidence",
                                "reasoning_summary": "state.working.reasoning_summary",
                            },
                        },
                    ],
                    "edges": [
                        {"from": "draft_critic", "to": "review_synthesizer"},
                        {"from": "evidence_check", "to": "review_synthesizer"},
                    ],
                    "outputs": [
                        {"name": "result", "source": "state.working.result"},
                        {"name": "confidence", "source": "state.working.confidence"},
                        {"name": "reasoning_summary", "source": "state.working.reasoning_summary"},
                    ],
                }
            },
        },
        "resources": {
            "prompts": {"prompt.draft": {"template": "Draft: {{question}}"}},
            "providers": {"provider.gpt": {"type": "mock", "config": {}}},
            "plugins": {
                "plugin.review": {"entry": entry_path},
                "plugin.synth": {"entry": entry_path},
            },
        },
        "state": {"input": {"question": "Which is safer?"}, "working": {}, "memory": {}},
        "ui": {"layout": {}, "metadata": {}},
    }


class _Provider:
    def execute(self, request):
        from src.contracts.provider_contract import ProviderResult
        q = request.prompt.replace("Draft: ", "")
        return ProviderResult(
            raw_text=f"draft:{q}",
            structured={"result": f"draft:{q}"},
            output={"result": f"draft:{q}"},
            artifacts=[],
            trace={},
            error=None,
        )


def test_subcircuit_batch2_review_bundle_observability_and_artifact_linkage(tmp_path: Path) -> None:
    mod = tmp_path / "review_plugins.py"
    mod.write_text(
        """def run(**kwargs):
    if 'critique' in kwargs or 'evidence' in kwargs:
        return {'output': {'result': f"reviewed:{kwargs['draft']}", 'confidence': 0.8, 'reasoning_summary': 'ok'}, 'artifacts': [{'kind': 'summary', 'value': 'artifact'}], 'trace': {'stage': 'synth'}, 'error': None}
    text = kwargs.get('text', '')
    return {'output': {'result': f"seen:{text}"}, 'artifacts': [{'kind': 'note', 'value': text}], 'trace': {'stage': 'review'}, 'error': None}
""",
        encoding="utf-8",
    )
    sys.path.insert(0, str(tmp_path))
    try:
        payload = _review_bundle_payload("review_plugins.run")
        savefile = load_savefile(payload)
        registry = ProviderRegistry()
        registry.register("provider.gpt", _Provider())
        trace = SavefileExecutor(registry).execute(savefile, run_id="batch2-review")
    finally:
        sys.path.remove(str(tmp_path))

    assert trace.status == "success"
    result = trace.node_results["review_bundle_stage"]
    assert result.status == "success"
    assert result.output["result"].startswith("reviewed:draft:")
    assert result.trace["child_run_id"] == "subcircuit:review_bundle_stage:review_bundle"
    assert result.trace["child_trace_ref"] == "subcircuit:review_bundle_stage:review_bundle"
    assert result.trace["child_status"] == "success"
    assert result.trace["child_artifact_count"] >= 1
    assert result.trace["child_warning_count"] == 0
    assert result.trace["child_error_count"] == 0
    assert result.trace["child_output_provenance"]["result"] == "state.working.result"
    assert result.trace["child_node_statuses"]["review_synthesizer"] == "success"
    assert result.trace["child_duration_ms"] >= 0
    assert result.trace["child_artifact_refs"][0].startswith("artifact:")
    assert "child_trace" in result.trace
    assert result.artifacts
