import zipfile
from pathlib import Path
import json
from src.contracts.nex_bundle_loader import load_nex_bundle


def test_bundle_loader(tmp_path):
    bundle = tmp_path / "test.nexb"

    temp = tmp_path / "build"
    temp.mkdir()

    (temp / "plugins").mkdir()
    (temp / "circuit.nex").write_text(json.dumps({"test": True}))

    with zipfile.ZipFile(bundle, 'w') as zf:
        for p in temp.rglob("*"):
            zf.write(p, p.relative_to(temp))

    b = load_nex_bundle(str(bundle))

    assert b.circuit_path.exists()
    assert b.plugins_dir.exists()

    b.cleanup()
