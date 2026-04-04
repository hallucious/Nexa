from __future__ import annotations

from src.contracts.savefile_factory import create_savefile, make_minimal_savefile
from src.contracts.savefile_loader import load_savefile
from src.contracts.savefile_serializer import serialize_savefile
from src.contracts.savefile_validator import validate_savefile


def test_create_savefile_materializes_explicit_empty_sections():
    savefile = create_savefile(
        name="demo",
        version="2.0.0",
        entry="n1",
        nodes=[
            {
                "id": "n1",
                "type": "plugin",
                "resource_ref": {"plugin": "plugin.clean"},
                "inputs": {"text": "state.input.text"},
                "outputs": {"text": "state.working.cleaned"},
            }
        ],
        plugins={"plugin.clean": {"entry": "pkg.clean"}},
    )

    payload = serialize_savefile(savefile)

    assert payload["resources"] == {
        "prompts": {},
        "providers": {},
        "plugins": {"plugin.clean": {"entry": "pkg.clean"}},
    }
    assert payload["state"] == {"input": {}, "working": {}, "memory": {}}
    assert payload["ui"] == {"layout": {}, "metadata": {}}

    warnings = validate_savefile(savefile)
    assert warnings == []


def test_make_minimal_savefile_roundtrips_through_loader_and_validator():
    savefile = make_minimal_savefile(
        name="demo",
        version="2.0.0",
        entry="node1",
        node_type="ai",
        resource_ref={"prompt": "prompt.main", "provider": "provider.main"},
        inputs={"text": "state.input.text"},
        outputs={"answer": "state.working.answer"},
        prompts={"prompt.main": {"template": "Answer {{text}}"}},
        providers={"provider.main": {"type": "openai", "model": "gpt-5"}},
        state_input={"text": "hello"},
        ui_metadata={"source": "factory"},
    )

    payload = serialize_savefile(savefile)
    loaded = load_savefile(payload)
    warnings = validate_savefile(loaded)

    assert warnings == []
    assert loaded.meta.name == "demo"
    assert loaded.ui.metadata == {"source": "factory"}
    assert loaded.circuit.nodes[0].id == "node1"


def test_create_savefile_deepcopies_mutable_input_dicts():
    node = {
        "id": "n1",
        "type": "plugin",
        "resource_ref": {"plugin": "plugin.clean"},
        "inputs": {"text": "state.input.text"},
        "outputs": {"text": "state.working.cleaned"},
    }
    ui_layout = {"n1": {"x": 10, "y": 20}}
    state_input = {"text": "hello"}

    savefile = create_savefile(
        name="demo",
        version="2.0.0",
        entry="n1",
        nodes=[node],
        plugins={"plugin.clean": {"entry": "pkg.clean"}},
        state_input=state_input,
        ui_layout=ui_layout,
    )

    node["resource_ref"]["plugin"] = "plugin.changed"
    node["inputs"]["text"] = "state.input.changed"
    ui_layout["n1"]["x"] = 999
    state_input["text"] = "mutated"

    assert savefile.circuit.nodes[0].resource_ref == {"plugin": "plugin.clean"}
    assert savefile.circuit.nodes[0].inputs == {"text": "state.input.text"}
    assert savefile.ui.layout == {"n1": {"x": 10, "y": 20}}
    assert savefile.state.input == {"text": "hello"}


def test_create_savefile_preserves_subcircuits_and_outputs():
    savefile = create_savefile(
        name="demo",
        version="2.0.0",
        entry="review_bundle_stage",
        nodes=[
            {
                "id": "review_bundle_stage",
                "kind": "subcircuit",
                "label": "Review Bundle Stage",
                "execution": {
                    "subcircuit": {
                        "child_circuit_ref": "internal:review_bundle",
                        "input_mapping": {"question": "input.question"},
                        "output_binding": {"result": "child.output.result"},
                    }
                },
            }
        ],
        outputs=[{"name": "final_result", "source": "node.review_bundle_stage.output.result"}],
        subcircuits={
            "review_bundle": {
                "nodes": [
                    {
                        "id": "critic",
                        "kind": "provider",
                        "execution": {
                            "provider": {"provider_id": "provider.review", "prompt_ref": "prompt.review"}
                        },
                    }
                ],
                "edges": [],
                "outputs": [{"name": "result", "source": "node.critic.output.result"}],
            }
        },
        prompts={"prompt.review": {"template": "Review {{question}}"}},
        providers={"provider.review": {"type": "openai", "model": "gpt-5"}},
        state_input={"question": "What is safer?"},
    )

    payload = serialize_savefile(savefile)
    loaded = load_savefile(payload)

    assert payload["circuit"]["outputs"] == [{"name": "final_result", "source": "node.review_bundle_stage.output.result"}]
    assert "review_bundle" in payload["circuit"]["subcircuits"]
    assert loaded.circuit.outputs == [{"name": "final_result", "source": "node.review_bundle_stage.output.result"}]
    assert "review_bundle" in loaded.circuit.subcircuits
