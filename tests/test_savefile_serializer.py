from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.contracts.savefile_format import Savefile, SavefileMeta
from src.contracts.savefile_loader import load_savefile, load_savefile_from_path
from src.contracts.savefile_serializer import (
    ROOT_SECTIONS,
    SavefileSerializationError,
    save_savefile_file,
    serialize_savefile,
)
from src.contracts.savefile_validator import validate_savefile


BASE_DIR = Path(__file__).resolve().parents[1]
DEMO_DIR = BASE_DIR / "examples" / "real_ai_bug_autopsy_multinode"


def _minimal_savefile_dict():
    return {
        "meta": {
            "name": "demo",
            "version": "2.0.0",
            "description": "minimal savefile",
        },
        "circuit": {
            "entry": "node1",
            "nodes": [
                {
                    "id": "node1",
                    "type": "ai",
                    "resource_ref": {
                        "prompt": "prompt.main",
                        "provider": "provider.main",
                    },
                    "inputs": {"text": "state.input.text"},
                    "outputs": {"answer": "state.working.answer"},
                }
            ],
            "edges": [],
        },
        "resources": {
            "prompts": {
                "prompt.main": {"template": "Answer {{text}}"},
            },
            "providers": {
                "provider.main": {
                    "type": "openai",
                    "model": "gpt-5",
                    "config": {},
                }
            },
            "plugins": {},
        },
        "state": {
            "input": {"text": "hello"},
            "working": {},
            "memory": {},
        },
        "ui": {
            "layout": {},
            "metadata": {},
        },
    }


def test_serialize_savefile_emits_explicit_ui_root_section():
    savefile = load_savefile(_minimal_savefile_dict())

    payload = serialize_savefile(savefile)

    assert tuple(payload.keys()) == ROOT_SECTIONS
    assert payload["ui"] == {"layout": {}, "metadata": {}}


def test_save_savefile_file_roundtrips_with_explicit_ui(tmp_path):
    savefile = load_savefile(_minimal_savefile_dict())
    path = tmp_path / "roundtrip.nex"

    save_savefile_file(savefile, str(path))

    raw = json.loads(path.read_text(encoding="utf-8"))
    assert tuple(raw.keys()) == ROOT_SECTIONS
    assert "ui" in raw
    assert raw["ui"] == {"layout": {}, "metadata": {}}

    loaded = load_savefile_from_path(str(path))
    warnings = validate_savefile(loaded)

    assert warnings == []
    assert loaded.ui.layout == {}
    assert loaded.ui.metadata == {}


def test_serialize_savefile_rejects_missing_ui_object():
    savefile = Savefile(
        meta=SavefileMeta(name="demo", version="2.0.0"),
        circuit=load_savefile(_minimal_savefile_dict()).circuit,
        resources=load_savefile(_minimal_savefile_dict()).resources,
        state=load_savefile(_minimal_savefile_dict()).state,
        ui=None,
    )

    with pytest.raises(SavefileSerializationError, match="savefile.ui must exist"):
        serialize_savefile(savefile)


@pytest.mark.parametrize(
    "path",
    [
        DEMO_DIR / "investment_demo_A.nex",
        DEMO_DIR / "investment_demo_B.nex",
    ],
)
def test_official_savefile_examples_include_explicit_ui_section(path):
    raw = json.loads(path.read_text(encoding="utf-8"))

    assert "ui" in raw
    assert isinstance(raw["ui"], dict)

    savefile = load_savefile(raw)
    warnings = validate_savefile(savefile)
    assert warnings == []
