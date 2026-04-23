import json

import pytest

from src.cli.nexa_cli import _is_savefile_contract
from src.contracts.savefile_format import (
    CircuitSpec,
    NodeSpec,
    PluginResource,
    ResourcesSpec,
    Savefile,
    SavefileMeta,
    StateSpec,
    UISpec,
)
from tests.savefile_test_helpers import make_demo_savefile_payload
from src.contracts.savefile_loader import load_savefile
from src.savefiles.validator import SavefileValidationError, validate_savefile


def _minimal_savefile_dict():
    payload = make_demo_savefile_payload()
    payload["circuit"]["entry"] = "n1"
    payload["circuit"]["nodes"][0].update(
        {
            "id": "n1",
            "type": "plugin",
            "resource_ref": {"plugin": "plugin.clean"},
            "inputs": {"text": "state.input.text"},
            "outputs": {"text": "state.working.cleaned"},
        }
    )
    payload["resources"] = {
        "prompts": {},
        "providers": {},
        "plugins": {"plugin.clean": {"entry": "pkg.clean"}},
    }
    payload["state"]["input"] = {"text": "hello"}
    payload["state"]["working"] = {}
    payload["state"]["memory"] = {}
    return payload



def test_load_savefile_requires_ui_section():
    payload = _minimal_savefile_dict()
    payload.pop("ui")

    with pytest.raises(KeyError) as excinfo:
        load_savefile(payload)

    assert "Missing required savefile section(s): ui" in str(excinfo.value)


def test_is_savefile_contract_returns_false_when_ui_missing(tmp_path):
    path = tmp_path / "missing_ui.nex"
    payload = _minimal_savefile_dict()
    payload.pop("ui")
    path.write_text(json.dumps(payload), encoding="utf-8")

    assert _is_savefile_contract(str(path)) is False


def test_validate_savefile_rejects_missing_ui_object():
    savefile = Savefile(
        meta=SavefileMeta(name="demo", version="2.0.0"),
        circuit=CircuitSpec(
            entry="n1",
            nodes=[
                NodeSpec(
                    id="n1",
                    type="plugin",
                    resource_ref={"plugin": "plugin.clean"},
                    inputs={"text": "state.input.text"},
                    outputs={},
                )
            ],
            edges=[],
        ),
        resources=ResourcesSpec(plugins={"plugin.clean": PluginResource(entry="pkg.clean")}),
        state=StateSpec(),
        ui=None,
    )

    with pytest.raises(SavefileValidationError, match="ui section must exist"):
        validate_savefile(savefile)


def test_validate_savefile_rejects_ui_path_even_when_ui_present():
    savefile = load_savefile(_minimal_savefile_dict())
    savefile.circuit.nodes[0].inputs["text"] = "ui.layout.node1"

    with pytest.raises(SavefileValidationError, match="references UI section"):
        validate_savefile(savefile)


def test_load_savefile_accepts_explicit_ui_section():
    savefile = load_savefile(_minimal_savefile_dict())

    assert isinstance(savefile.ui, UISpec)
    assert savefile.ui.layout == {}
    assert savefile.ui.metadata == {}
