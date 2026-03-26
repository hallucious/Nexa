import zipfile
from pathlib import Path
import tempfile
import shutil


class NexBundle:
    def __init__(self, temp_dir: Path):
        self.temp_dir = temp_dir
        self.circuit_path = temp_dir / "circuit.nex"
        self.plugins_dir = temp_dir / "plugins"

    def cleanup(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)


def load_nex_bundle(bundle_path: str, *, require_plugins: bool = True) -> NexBundle:
    bundle_file = Path(bundle_path)

    if not bundle_file.exists():
        raise RuntimeError(f"Bundle not found: {bundle_path}")

    temp_dir = Path(tempfile.mkdtemp(prefix="nexa_bundle_"))

    with zipfile.ZipFile(bundle_file, 'r') as zf:
        zf.extractall(temp_dir)

    circuit = temp_dir / "circuit.nex"
    plugins = temp_dir / "plugins"

    if not circuit.exists():
        raise RuntimeError("circuit.nex missing in bundle")

    if require_plugins and not plugins.exists():
        raise RuntimeError("plugins/ missing in bundle")

    return NexBundle(temp_dir)
