import re
from pathlib import Path
import yaml

SPEC_DIR = Path("docs/specs")

version_pattern = re.compile(r"Version:\s*([0-9]+\.[0-9]+\.[0-9]+)")
status_pattern = re.compile(r"Status:\s*Active")

active_specs = {}
active_list = []

for path in SPEC_DIR.rglob("*.md"):
    text = path.read_text(encoding="utf-8")

    version_match = version_pattern.search(text)
    status_match = status_pattern.search(text)

    if version_match and status_match:
        version = version_match.group(1)
        key = str(path).replace("\\", "/")

        active_specs[key] = version
        active_list.append(key)

# _active_specs.yaml
yaml_path = SPEC_DIR / "_active_specs.yaml"
yaml_path.write_text(
    yaml.dump({"active_specs": sorted(active_list)}),
    encoding="utf-8",
)

# spec_version_registry.py
spec_file = Path("src/contracts/spec_version_registry.py")

lines = ["SPEC_VERSIONS = {\n"]

for k, v in sorted(active_specs.items()):
    lines.append(f'    "{k}": "{v}",\n')

lines.append("}\n")

spec_file.write_text("".join(lines), encoding="utf-8")