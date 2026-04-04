from src.contracts.savefile_loader import load_savefile


def _payload():
    return {
        "meta": {"name": "demo", "version": "2.0.0"},
        "circuit": {
            "entry": "n1",
            "nodes": [
                {
                    "id": "n1",
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
            "edges": [],
            "outputs": [],
            "subcircuits": {
                "review_bundle": {
                    "entry": "c1",
                    "nodes": [
                        {
                            "id": "c1",
                            "type": "plugin",
                            "resource_ref": {"plugin": "plugin.echo"},
                            "inputs": {"text": "input.question"},
                            "outputs": {"result": "state.working.result"},
                        }
                    ],
                    "edges": [],
                    "outputs": [{"name": "result", "source": "state.working.result"}],
                }
            },
        },
        "resources": {"prompts": {}, "providers": {}, "plugins": {"plugin.echo": {"entry": "pkg.echo"}}},
        "state": {"input": {"question": "hi"}, "working": {}, "memory": {}},
        "ui": {"layout": {}, "metadata": {}},
    }


def test_load_savefile_reads_subcircuit_node_and_registry():
    savefile = load_savefile(_payload())
    node = savefile.circuit.nodes[0]
    assert node.node_kind == "subcircuit"
    assert node.execution["subcircuit"]["child_circuit_ref"] == "internal:review_bundle"
    assert "review_bundle" in savefile.circuit.subcircuits
