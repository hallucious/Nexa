import json
import zipfile

from src.engine.cli_legacy_nex_runtime import load_nex_bundle


def _example_legacy_nex_payload():
    return {
        "format": {"kind": "nexa.circuit", "version": "1.0.0"},
        "circuit": {
            "circuit_id": "bundle.demo",
            "name": "Bundle Demo",
            "entry_node_id": "n1",
            "description": "bundle loader test payload",
        },
        "nodes": [
            {
                "node_id": "n1",
                "kind": "execution",
                "prompt_ref": "prompt.main",
                "provider_ref": "provider.openai.gpt5",
                "plugin_refs": [],
            }
        ],
        "edges": [],
        "flow": [],
        "execution": {
            "strict_determinism": False,
            "node_failure_policies": {},
            "node_fallback_map": {},
            "node_retry_policy": {},
        },
        "resources": {
            "prompts": {"prompt.main": {"template": "Hi"}},
            "providers": {
                "provider.openai.gpt5": {
                    "provider_type": "openai",
                    "model": "gpt-5",
                    "config": {},
                }
            },
        },
        "plugins": [],
    }


def test_bundle_loader(tmp_path):
    bundle = tmp_path / "test.nexb"

    temp = tmp_path / "build"
    temp.mkdir()

    (temp / "plugins").mkdir()
    (temp / "circuit.nex").write_text(
        json.dumps(_example_legacy_nex_payload(), indent=2),
        encoding="utf-8",
    )

    with zipfile.ZipFile(bundle, "w") as zf:
        for p in temp.rglob("*"):
            zf.write(p, p.relative_to(temp))

    b = load_nex_bundle(str(bundle))

    assert b.circuit_path.exists()
    assert b.plugins_dir.exists()

    b.cleanup()



def test_bundle_loader_savefile_without_plugins_when_plugins_not_required(tmp_path):
    bundle = tmp_path / "savefile.nexb"

    temp = tmp_path / "build_savefile"
    temp.mkdir()

    (temp / "circuit.nex").write_text(
        """{
  \"meta\": {\"name\": \"bundle.savefile\", \"version\": \"1.0.0\", \"description\": \"savefile bundle\"},
  \"circuit\": {\"entry\": \"ai1\", \"nodes\": [{\"id\": \"ai1\", \"type\": \"ai\", \"resource_ref\": {\"prompt\": \"prompt.main\", \"provider\": \"provider.test\"}, \"inputs\": {\"name\": \"state.input.name\"}, \"outputs\": {}}], \"edges\": []},
  \"resources\": {\"prompts\": {\"prompt.main\": {\"template\": \"Hello {{name}}\"}}, \"providers\": {\"provider.test\": {\"type\": \"test\", \"model\": \"test-model\", \"config\": {}}}, \"plugins\": {}},
  \"state\": {\"input\": {\"name\": \"Nexa\"}, \"working\": {}, \"memory\": {}},
  \"ui\": {\"layout\": {}, \"metadata\": {}}
}""",
        encoding="utf-8",
    )

    with zipfile.ZipFile(bundle, "w") as zf:
        zf.write(temp / "circuit.nex", "circuit.nex")

    b = load_nex_bundle(str(bundle), require_plugins=False)

    assert b.circuit_path.exists()
    assert not b.plugins_dir.exists()

    b.cleanup()
