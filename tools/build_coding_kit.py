
"""
build_coding_kit.py

Purpose
-------
Automatically generate the three files required for Claude coding tasks:

1. Nexa.zip
2. Nexa_AI_CONTEXT.md
3. task_prompt.txt

Output directory:
build/
"""

from pathlib import Path
import zipfile
import shutil

ROOT = Path(__file__).resolve().parents[1]

# Directories included in Nexa.zip
SRC_DIRS = [
    "src",
    "tests",
    "docs",
    "examples",
    "scripts"
]

# Individual files included
FILES = [
    "requirements.txt"
]

CODING_KIT_DIR = ROOT / "tools" / "coding_kit"
BUILD_DIR = ROOT / "build"


def build_zip():
    zip_path = BUILD_DIR / "Nexa.zip"

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:

        for d in SRC_DIRS:
            path = ROOT / d
            if not path.exists():
                continue

            for file in path.rglob("*"):
                if file.is_file():
                    z.write(file, file.relative_to(ROOT))

        for f in FILES:
            file = ROOT / f
            if file.exists():
                z.write(file, file.relative_to(ROOT))


def build_context():
    output = BUILD_DIR / "Nexa_AI_CONTEXT.md"

    parts = []

    for file in sorted(CODING_KIT_DIR.glob("*")):

        if file.name == "task_prompt_template.txt":
            continue

        text = file.read_text(encoding="utf-8")

        header = f"\n\n# FILE: {file.name}\n\n"
        parts.append(header + text)

    output.write_text("\n".join(parts), encoding="utf-8")


def build_prompt():
    template = CODING_KIT_DIR / "task_prompt_template.txt"
    output = BUILD_DIR / "task_prompt.txt"

    if template.exists():
        shutil.copy(template, output)
    else:
        output.write_text(
            "Follow Nexa architecture rules and implement the requested task.",
            encoding="utf-8"
        )


def main():
    BUILD_DIR.mkdir(exist_ok=True)

    build_zip()
    build_context()
    build_prompt()

    print("Nexa Coding Kit build complete.")
    print("Output directory:", BUILD_DIR)


if __name__ == "__main__":
    main()
