import zipfile

from src.contracts.nex_bundle_loader import load_nex_bundle
from src.contracts.nex_loader import deserialize_nex
from src.contracts.nex_serializer import save_nex_file


def test_bundle_loader(tmp_path):
    bundle = tmp_path / "test.nexb"

    temp = tmp_path / "build"
    temp.mkdir()

    (temp / "plugins").mkdir()
    save_nex_file(
        deserialize_nex(
            {
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
        ),
        str(temp / "circuit.nex"),
    )

    with zipfile.ZipFile(bundle, 'w') as zf:
        for p in temp.rglob("*"):
            zf.write(p, p.relative_to(temp))

    b = load_nex_bundle(str(bundle))

    assert b.circuit_path.exists()
    assert b.plugins_dir.exists()

    b.cleanup()
