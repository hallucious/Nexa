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
