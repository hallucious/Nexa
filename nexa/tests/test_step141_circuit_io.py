from src.circuit.circuit_io import save_circuit, load_circuit


def test_circuit_save_load(tmp_path):

    circuit = {
        "nodes": [
            {"id": "A", "execution_config_ref": "qa.answer"}
        ]
    }

    file = tmp_path / "test.nex"

    save_circuit(circuit, str(file))

    loaded = load_circuit(str(file))

    assert loaded["nodes"][0]["id"] == "A"