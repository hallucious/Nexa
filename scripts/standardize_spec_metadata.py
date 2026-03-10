"""
standardize_spec_metadata.py
Automatically injects metadata into spec documents
"""

import re
from pathlib import Path

REPO_ROOT = Path(".").resolve()
SPECS_ROOT = REPO_ROOT / "docs" / "specs"

ACTIVE_SPECS_PATH = SPECS_ROOT / "_active_specs.yaml"
SPEC_VERSIONS_PATH = REPO_ROOT / "src" / "contracts" / "spec_versions.py"


def scan_spec_files():
    files = []
    for p in SPECS_ROOT.rglob("*.md"):
        if p.name.lower().startswith("readme"):
            continue
        files.append(p)
    return sorted(files)


def normalize_spec_id(path):
    name = path.stem.lower()
    name = name.replace("&", "and")
    name = re.sub(r"\s+", "_", name)
    name = re.sub(r"[^a-z0-9_]", "", name)
    name = re.sub(r"_+", "_", name)
    return name


def infer_category(path):
    parts = set(path.parts)

    if "architecture" in parts:
        return "architecture"
    if "contracts" in parts:
        return "contracts"
    if "policies" in parts:
        return "policies"
    if "foundation" in parts:
        return "foundation"
    if "history" in parts:
        return "history"

    return "misc"


def build_header(spec_id, category):

    lines = [
        f"Spec ID: {spec_id}",
        "Version: 1.0.0",
        "Status: Partial",
        f"Category: {category}",
        "Depends On:",
    ]

    return "\n".join(lines)


def has_metadata(text):

    head = text.splitlines()[:10]

    for line in head:
        if line.startswith("Spec ID:"):
            return True

    return False


def write_active_specs(paths):

    lines = ["active_specs:"]

    for p in paths:
        lines.append(f"  - {p}")

    ACTIVE_SPECS_PATH.write_text("\n".join(lines) + "\n")


def write_versions(mapping):

    lines = ["SPEC_VERSIONS = {"]

    for k, v in mapping.items():
        lines.append(f'    "{k}": "{v}",')

    lines.append("}")

    SPEC_VERSIONS_PATH.write_text("\n".join(lines) + "\n")


def main():

    specs = scan_spec_files()

    active_paths = []
    versions = {}

    for path in specs:

        text = path.read_text(encoding="utf-8")

        spec_id = normalize_spec_id(path)
        category = infer_category(path)

        if not has_metadata(text):

            header = build_header(spec_id, category)

            new_text = header + "\n\n" + text

            path.write_text(new_text, encoding="utf-8")

        rel = str(path.relative_to(REPO_ROOT)).replace("\\", "/")

        active_paths.append(rel)
        versions[rel] = "1.0.0"

    write_active_specs(active_paths)
    write_versions(versions)

    print("spec files:", len(specs))
    print("active specs:", len(active_paths))


if __name__ == "__main__":
    main()