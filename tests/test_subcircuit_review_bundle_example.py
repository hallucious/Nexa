from src.contracts.savefile_loader import load_savefile
from src.savefiles.validator import validate_savefile
from src.savefiles.executor import SavefileExecutor
from src.contracts.provider_contract import ProviderResult
from src.platform.provider_registry import ProviderRegistry


class _EchoProvider:
    def __init__(self, name: str):
        self.name = name

    def execute(self, request):
        prompt = request.prompt
        if self.name == "openai:gpt":
            if "initial judgment draft" in prompt:
                output = {"result": "Initial draft for: Which market entry strategy is safer?"}
            else:
                output = {
                    "result": "Reviewed result based on critique and evidence",
                    "confidence": 0.81,
                    "reasoning_summary": "Critique and evidence were synthesized",
                }
        elif self.name == "anthropic:claude":
            output = {
                "issues_found": ["Regulatory risk underweighted"],
                "reasoning_summary": "Draft has a weak assumption",
            }
        elif self.name == "perplexity:search":
            output = {
                "evidence_summary": "Evidence suggests APAC compliance burden is meaningful",
                "confidence": 0.72,
            }
        else:
            output = {"result": prompt}
        return ProviderResult(
            output=output,
            raw_text=None,
            structured=None,
            artifacts=[],
            trace={"provider": self.name},
            error=None,
        )


def _review_bundle_payload():
    return {
        "meta": {"name": "review_bundle_demo", "version": "2.0.0"},
        "circuit": {
            "entry": "draft_generator",
            "nodes": [
                {
                    "id": "draft_generator",
                    "kind": "provider",
                    "label": "Draft Generator",
                    "execution": {
                        "provider": {
                            "provider_id": "openai:gpt",
                            "model": "gpt-main",
                            "prompt_ref": "draft_prompt",
                            "inputs": {"question": "input.question"},
                        }
                    },
                    "outputs": {"result": "state.working.draft"},
                },
                {
                    "id": "review_bundle_stage",
                    "kind": "subcircuit",
                    "label": "Review Bundle Stage",
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
                            "kind": "provider",
                            "execution": {
                                "provider": {
                                    "provider_id": "anthropic:claude",
                                    "model": "claude-review",
                                    "prompt_ref": "critic_prompt",
                                    "inputs": {
                                        "question": "input.question",
                                        "draft": "input.draft",
                                    },
                                }
                            },
                            "outputs": {"issues_found": "state.working.issues_found", "reasoning_summary": "state.working.critique_summary"},
                        },
                        {
                            "id": "evidence_check",
                            "kind": "provider",
                            "execution": {
                                "provider": {
                                    "provider_id": "perplexity:search",
                                    "model": "perplexity-main",
                                    "prompt_ref": "search_prompt",
                                    "inputs": {
                                        "question": "input.question",
                                        "draft": "input.draft",
                                    },
                                }
                            },
                            "outputs": {"evidence_summary": "state.working.evidence_summary", "confidence": "state.working.evidence_confidence"},
                        },
                        {
                            "id": "review_synthesizer",
                            "kind": "provider",
                            "execution": {
                                "provider": {
                                    "provider_id": "openai:gpt",
                                    "model": "gpt-synth",
                                    "prompt_ref": "synth_prompt",
                                    "inputs": {
                                        "issues": "node.draft_critic.output.issues_found",
                                        "evidence": "node.evidence_check.output.evidence_summary",
                                    },
                                }
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
            "prompts": {
                "draft_prompt": {"template": "Create an initial judgment draft for the user's question. {{question}}"},
                "critic_prompt": {"template": "Critique the draft."},
                "search_prompt": {"template": "Check external evidence relevant to the question and draft."},
                "synth_prompt": {"template": "Synthesize critique and evidence into a revised conclusion."},
            },
            "providers": {
                "openai:gpt": {"type": "gpt"},
                "anthropic:claude": {"type": "claude"},
                "perplexity:search": {"type": "perplexity"},
            },
            "plugins": {},
        },
        "state": {"input": {"question": "Which market entry strategy is safer?"}, "working": {}, "memory": {}},
        "ui": {"layout": {}, "metadata": {}},
    }


def test_review_bundle_official_example_validates_and_executes():
    payload = _review_bundle_payload()
    savefile = load_savefile(payload)
    validate_savefile(savefile)

    registry = ProviderRegistry()
    registry.register("openai:gpt", _EchoProvider("openai:gpt"))
    registry.register("anthropic:claude", _EchoProvider("anthropic:claude"))
    registry.register("perplexity:search", _EchoProvider("perplexity:search"))

    trace = SavefileExecutor(registry).execute(savefile, run_id="review-bundle")

    assert trace.status == "success"
    assert trace.node_results["draft_generator"].status == "success"
    assert trace.node_results["review_bundle_stage"].status == "success"
    assert trace.node_results["review_bundle_stage"].output == {
        "result": "Reviewed result based on critique and evidence",
        "confidence": 0.81,
        "reasoning_summary": "Critique and evidence were synthesized",
    }
    assert trace.final_state["working"]["reviewed"] == "Reviewed result based on critique and evidence"


def test_review_bundle_official_example_supports_provider_kind_loader_canonicalization():
    savefile = load_savefile(_review_bundle_payload())
    first = savefile.circuit.nodes[0]
    assert first.node_kind == "ai"
    assert first.resource_ref["provider"] == "openai:gpt"
    assert first.resource_ref["prompt"] == "draft_prompt"
    child = savefile.circuit.subcircuits["review_bundle"]["nodes"][0]
    assert child["kind"] == "provider"
