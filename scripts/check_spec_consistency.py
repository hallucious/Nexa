import importlib.util
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

DOCS_SPECS = ROOT / "docs" / "specs"

ACTIVE_SPECS_PRIMARY = DOCS_SPECS / "_active_specs.yaml"
ACTIVE_SPECS_FALLBACK = DOCS_SPECS / "indexes" / "_active_specs.yaml"

SPEC_VERSIONS_FILE = ROOT / "src" / "contracts" / "spec_versions.py"
FOUNDATION_MAP = ROOT / "docs" / "FOUNDATION_MAP.md"


def resolve_active_specs_file():
    if ACTIVE_SPECS_PRIMARY.exists():
        return ACTIVE_SPECS_PRIMARY

    if ACTIVE_SPECS_FALLBACK.exists():
        return ACTIVE_SPECS_FALLBACK

    raise FileNotFoundError(
        f"Active specs file not found. Checked: {ACTIVE_SPECS_PRIMARY} and {ACTIVE_SPECS_FALLBACK}"
    )


def load_active_specs(active_specs_file: Path):
    specs = []

    for line in active_specs_file.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("- "):
            specs.append(stripped[2:].strip())

    return specs


def load_spec_versions():
    if not SPEC_VERSIONS_FILE.exists():
        raise FileNotFoundError(f"spec_versions.py not found: {SPEC_VERSIONS_FILE}")

    spec = importlib.util.spec_from_file_location(
        "nexa_spec_versions_module",
        SPEC_VERSIONS_FILE,
    )
    module = importlib.util.module_from_spec(spec)

    if spec.loader is None:
        raise RuntimeError("Failed to load spec_versions.py")

    spec.loader.exec_module(module)

    if not hasattr(module, "SPEC_VERSIONS"):
        raise RuntimeError("SPEC_VERSIONS not found in spec_versions.py")

    spec_versions = getattr(module, "SPEC_VERSIONS")

    if not isinstance(spec_versions, dict):
        raise RuntimeError("SPEC_VERSIONS is not a dict")

    return spec_versions


def extract_header_value(path: Path, field_name: str):
    text = path.read_text(encoding="utf-8")
    prefix = f"{field_name}:"

    for line in text.splitlines()[:20]:
        if line.startswith(prefix):
            return line.split(":", 1)[1].strip()

    return None


def has_required_header_fields(path: Path):
    text = path.read_text(encoding="utf-8")
    head = "\n".join(text.splitlines()[:20])

    required = [
        "Spec ID:",
        "Version:",
        "Status:",
        "Category:",
        "Depends On:",
    ]

    return [field for field in required if field not in head]


def check_headers(spec_paths):
    problems = []

    for spec in spec_paths:
        path = ROOT / spec

        if not path.exists():
            problems.append((spec, "file not found"))
            continue

        missing_fields = has_required_header_fields(path)

        if missing_fields:
            problems.append((spec, f"missing header fields: {', '.join(missing_fields)}"))

    return problems


def check_version_sync(spec_paths, versions):
    mismatches = []

    for spec in spec_paths:
        path = ROOT / spec

        if not path.exists():
            mismatches.append((spec, "file not found", None))
            continue

        if spec not in versions:
            mismatches.append((spec, "missing in SPEC_VERSIONS", None))
            continue

        doc_version = extract_header_value(path, "Version")
        code_version = versions[spec]

        if doc_version != code_version:
            mismatches.append((spec, doc_version, code_version))

    return mismatches


def parse_foundation_map_active_specs():
    if not FOUNDATION_MAP.exists():
        raise FileNotFoundError(f"FOUNDATION_MAP.md not found: {FOUNDATION_MAP}")

    text = FOUNDATION_MAP.read_text(encoding="utf-8")
    active_specs = set()

    path_pattern = re.compile(r"(docs/specs/[^\s)]+\.md)")

    for line in text.splitlines():
        if "Active" not in line:
            continue

        for match in path_pattern.findall(line):
            active_specs.add(match.strip())

    chunks = text.split("\n\n")
    for chunk in chunks:
        if "Active" not in chunk:
            continue

        for match in path_pattern.findall(chunk):
            active_specs.add(match.strip())

    return active_specs


def check_foundation_map(spec_paths):
    foundation_active = parse_foundation_map_active_specs()
    missing = []

    for spec in spec_paths:
        if spec not in foundation_active:
            missing.append(spec)

    return missing


def main():
    print("Checking Nexa spec consistency\n")

    active_specs_file = resolve_active_specs_file()
    active_specs = load_active_specs(active_specs_file)
    versions = load_spec_versions()

    print("Active specs:", len(active_specs))
    print("Active specs file:", active_specs_file)
    print("Foundation map:", FOUNDATION_MAP)
    print("Spec versions file:", SPEC_VERSIONS_FILE)

    header_problems = check_headers(active_specs)
    version_mismatches = check_version_sync(active_specs, versions)
    foundation_mismatches = check_foundation_map(active_specs)

    if header_problems:
        print("\nHeader problems:")
        for spec, detail in header_problems:
            print(f" - {spec}: {detail}")

    if version_mismatches:
        print("\nVersion mismatches:")
        for spec, doc_version, code_version in version_mismatches:
            print(f" - {spec} | doc={doc_version} | code={code_version}")

    if foundation_mismatches:
        print("\nMissing in FOUNDATION_MAP Active set:")
        for spec in foundation_mismatches:
            print(" -", spec)

    if not header_problems and not version_mismatches and not foundation_mismatches:
        print("\nAll spec contracts are consistent.")


if __name__ == "__main__":
    main()