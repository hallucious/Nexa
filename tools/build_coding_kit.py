"""
build_coding_kit.py

Purpose
-------
Generate the three files required for Claude coding tasks:

1. build/Nexa.zip
2. build/Nexa_AI_CONTEXT.md
3. build/task_prompt.txt

Design Rule
-----------
Nexa_AI_CONTEXT.md is a merged document of the static context files
inside tools/nexa_coding_kit.

IMPORTANT:
task_prompt.md is intentionally EXCLUDED from the merged context.
It is read separately from tools/task_prompt.md and copied as
build/task_prompt.txt because it represents the dynamic task
instruction for the current coding request.
"""

from __future__ import annotations

import shutil
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SRC_DIRS = [
    "src",
    "tests",
    "docs",
    "examples",
    "scripts",
]

FILES = [
    "requirements.txt",
]

CODING_KIT_DIR = ROOT / "tools" / "nexa_coding_kit"

# task_prompt.md lives directly under tools/, not inside nexa_coding_kit/
TASK_PROMPT_FILE = ROOT / "tools" / "task_prompt.md"

BUILD_DIR = ROOT / "build"

CONTEXT_FILES = [
    "architecture_constitution.md",
    "execution_invariants.md",
    "refactor_safety_scanner.md",
    "implementation_done_checklist.md",
    "output_contract.md",
    "repo_map.md",
    "runtime_flow.md",
    "module_map.md",
    "decision_log.md",
    "test_map.md",
    "file_manifest.md",
]


def build_zip() -> Path:
    zip_path = BUILD_DIR / "Nexa.zip"

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for dirname in SRC_DIRS:
            path = ROOT / dirname
            if not path.exists():
                continue

            for file in path.rglob("*"):
                if file.is_file():
                    zf.write(file, file.relative_to(ROOT))

        for filename in FILES:
            file = ROOT / filename
            if file.exists():
                zf.write(file, file.relative_to(ROOT))

    return zip_path


def build_context() -> Path:
    output = BUILD_DIR / "Nexa_AI_CONTEXT.md"

    if not CODING_KIT_DIR.exists():
        raise FileNotFoundError(f"Coding kit directory not found: {CODING_KIT_DIR}")

    parts: list[str] = [
        "# NEXA_AI_CONTEXT.md\n",
        "Merged static context for Nexa coding agents.\n",
        "Generated from tools/nexa_coding_kit/*.md (excluding task_prompt).\n",
    ]

    included = 0

    for name in CONTEXT_FILES:
        file = CODING_KIT_DIR / name
        if not file.exists():
            continue

        text = file.read_text(encoding="utf-8").strip()
        if not text:
            continue

        parts.append(f"\n\n---\n\n# FILE: {name}\n\n{text}\n")
        included += 1

    if included == 0:
        raise RuntimeError(
            f"No context files were merged. Check contents of: {CODING_KIT_DIR}"
        )

    output.write_text("".join(parts), encoding="utf-8")

    return output


def build_prompt() -> Path:
    """Copy tools/task_prompt.md → build/task_prompt.txt.

    The task prompt is always read from tools/task_prompt.md.
    This is the single authoritative location for the current task description.
    """
    output = BUILD_DIR / "task_prompt.txt"

    if TASK_PROMPT_FILE.exists():
        shutil.copy(TASK_PROMPT_FILE, output)
        return output

    # Fallback: write a placeholder so the build never fails silently
    output.write_text(
        "Follow Nexa architecture rules and implement the requested task.\n",
        encoding="utf-8",
    )

    return output


def main() -> None:
    BUILD_DIR.mkdir(exist_ok=True)

    zip_path = build_zip()
    context_path = build_context()
    prompt_path = build_prompt()

    print("Nexa Coding Kit build complete.")
    print(f"  Nexa.zip:          {zip_path}")
    print(f"  Nexa_AI_CONTEXT.md: {context_path}")
    print(f"  task_prompt.txt:   {prompt_path}")


if __name__ == "__main__":
    main()
