from __future__ import annotations

import copy
import json
from typing import Any, Dict

from src.contracts.savefile_format import Savefile


ROOT_SECTIONS = ("meta", "circuit", "resources", "state", "ui")


class SavefileSerializationError(ValueError):
    """Raised when a Savefile cannot be serialized to the canonical contract."""


def _deepcopy_dict(value: Dict[str, Any] | None) -> Dict[str, Any]:
    if value is None:
        return {}
    return copy.deepcopy(value)


def serialize_savefile(savefile: Savefile) -> Dict[str, Any]:
    """Convert Savefile into canonical JSON-serializable dict.

    The emitted payload always contains the explicit canonical root sections:
    ``meta``, ``circuit``, ``resources``, ``state``, and ``ui``.
    """
    if savefile.ui is None:
        raise SavefileSerializationError("savefile.ui must exist")

    return {
        "meta": {
            "name": savefile.meta.name,
            "version": savefile.meta.version,
            "description": savefile.meta.description,
        },
        "circuit": {
            "entry": savefile.circuit.entry,
            "nodes": [
                {
                    **({"id": node.id}),
                    **({"type": node.type} if node.type is not None else {}),
                    **({"kind": node.kind} if node.kind is not None else {}),
                    **({"label": node.label} if node.label is not None else {}),
                    "resource_ref": _deepcopy_dict(node.resource_ref),
                    "inputs": _deepcopy_dict(node.inputs),
                    "outputs": _deepcopy_dict(node.outputs),
                    **({"execution": copy.deepcopy(node.execution)} if node.execution else {}),
                }
                for node in savefile.circuit.nodes
            ],
            "edges": [
                {
                    "from": edge.from_node,
                    "to": edge.to_node,
                }
                for edge in savefile.circuit.edges
            ],
            "outputs": copy.deepcopy(savefile.circuit.outputs),
            "subcircuits": copy.deepcopy(savefile.circuit.subcircuits),
        },
        "resources": {
            "prompts": {
                key: {"template": value.template}
                for key, value in savefile.resources.prompts.items()
            },
            "providers": {
                key: {
                    "type": value.type,
                    "model": value.model,
                    "config": _deepcopy_dict(value.config),
                }
                for key, value in savefile.resources.providers.items()
            },
            "plugins": {
                key: {"entry": value.entry}
                for key, value in savefile.resources.plugins.items()
            },
        },
        "state": {
            "input": _deepcopy_dict(savefile.state.input),
            "working": _deepcopy_dict(savefile.state.working),
            "memory": _deepcopy_dict(savefile.state.memory),
        },
        "ui": {
            "layout": _deepcopy_dict(savefile.ui.layout),
            "metadata": _deepcopy_dict(savefile.ui.metadata),
        },
    }


def save_savefile_file(savefile: Savefile, file_path: str) -> None:
    """Save Savefile to .nex file using the canonical root contract."""
    data = serialize_savefile(savefile)

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")
