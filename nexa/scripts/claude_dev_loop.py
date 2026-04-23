"""
claude_dev_loop.py

Minimal local automation for the Nexa Claude coding workflow.

This script does NOT call Claude directly.
Instead, it automates the safe local loop after you obtain Claude's response:

1. Validate build/Nexa.zip, build/Nexa_AI_CONTEXT.md, build/task_prompt.txt
2. Parse Claude's response file
3. Apply modified files safely
4. Run pytest
5. Roll back automatically if tests fail
6. Optionally commit if tests pass

Expected Claude response format:

FILE: src/cli/nexa_cli.py
```python
<full file content>
```

FILE: tests/test_cli_info_command.py
```python
<full file content>
```
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Iterable, List

REPO_ROOT = Path(__file__).resolve().parents[1]
BUILD_DIR = REPO_ROOT / "build"
REQUIRED_BUILD_FILES = [
    BUILD_DIR / "Nexa.zip",
    BUILD_DIR / "Nexa_AI_CONTEXT.md",
    BUILD_DIR / "task_prompt.txt",
]
BACKUP_ROOT = REPO_ROOT / ".claude_dev_loop_backup"

PROTECTED_PREFIXES = (
    ".git/",
    "build/",
    "src/contracts/",
    "docs/specs/",
)

DEFAULT_PYTEST_CMD = ["pytest", "-q"]


@dataclass(frozen=True)
class FilePatch:
    rel_path: str
    content: str


def ensure_build_artifacts() -> None:
    missing = [str(p.relative_to(REPO_ROOT)) for p in REQUIRED_BUILD_FILES if not p.exists()]
    if missing:
        raise FileNotFoundError(
            "Required build artifacts are missing. Run tools/build_coding_kit.py first. "
            f"Missing: {', '.join(missing)}"
        )


def strip_optional_code_fence(body: str) -> str:
    text = body.strip("\n")
    if not text.startswith("```"):
        return text

    lines = text.splitlines()
    if not lines:
        return text

    # Drop opening fence
    lines = lines[1:]

    # Drop trailing fence if present
    while lines and not lines[-1].strip():
        lines.pop()

    if lines and lines[-1].strip().startswith("```"):
        lines.pop()

    return "\n".join(lines).rstrip("\n")


def parse_claude_response(raw: str) -> List[FilePatch]:
    pattern = re.compile(
        r"(?ms)^FILE:\s*(?P<path>[^\n]+)\n(?P<body>.*?)(?=^FILE:\s*[^\n]+\n|\Z)"
    )
    patches: list[FilePatch] = []
    for match in pattern.finditer(raw):
        rel_path = match.group("path").strip()
        body = strip_optional_code_fence(match.group("body"))
        if not rel_path:
            continue
        patches.append(FilePatch(rel_path=rel_path, content=body + "\n"))
    if not patches:
        raise ValueError("No FILE: blocks were found in Claude response.")
    return patches


def validate_rel_path(rel_path: str) -> PurePosixPath:
    normalized = rel_path.replace("\\", "/").strip()
    pure = PurePosixPath(normalized)

    if pure.is_absolute():
        raise ValueError(f"Absolute paths are forbidden: {rel_path}")

    if any(part in ("", ".", "..") for part in pure.parts):
        raise ValueError(f"Invalid relative path: {rel_path}")

    path_str = pure.as_posix() + ("/" if normalized.endswith("/") else "")
    for prefix in PROTECTED_PREFIXES:
        if pure.as_posix().startswith(prefix):
            raise ValueError(f"Protected path is not writable: {rel_path}")

    return pure


def validate_patches(patches: Iterable[FilePatch]) -> List[FilePatch]:
    validated: list[FilePatch] = []
    seen: set[str] = set()
    for patch in patches:
        pure = validate_rel_path(patch.rel_path)
        rel = pure.as_posix()
        if rel in seen:
            raise ValueError(f"Duplicate file patch detected: {rel}")
        seen.add(rel)
        validated.append(FilePatch(rel_path=rel, content=patch.content))
    return validated


def create_backup_dir() -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = BACKUP_ROOT / stamp
    backup_dir.mkdir(parents=True, exist_ok=True)
    return backup_dir


def backup_existing_files(patches: Iterable[FilePatch], backup_dir: Path) -> None:
    for patch in patches:
        target = REPO_ROOT / patch.rel_path
        if target.exists():
            backup_target = backup_dir / patch.rel_path
            backup_target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(target, backup_target)


def apply_patches(patches: Iterable[FilePatch]) -> None:
    for patch in patches:
        target = REPO_ROOT / patch.rel_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(patch.content, encoding="utf-8", newline="\n")


def restore_from_backup(backup_dir: Path, patches: Iterable[FilePatch]) -> None:
    for patch in patches:
        target = REPO_ROOT / patch.rel_path
        backup_target = backup_dir / patch.rel_path
        if backup_target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(backup_target, target)
        else:
            if target.exists():
                target.unlink()


def run_command(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=str(cwd),
        text=True,
        capture_output=True,
        check=False,
    )


def git_commit(commit_message: str) -> subprocess.CompletedProcess[str]:
    add_result = run_command(["git", "add", "."], REPO_ROOT)
    if add_result.returncode != 0:
        raise RuntimeError(f"git add failed:\n{add_result.stdout}\n{add_result.stderr}")

    commit_result = run_command(["git", "commit", "-m", commit_message], REPO_ROOT)
    return commit_result


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="claude-dev-loop",
        description="Apply Claude output safely, test it, and optionally commit it.",
    )
    parser.add_argument(
        "--response-file",
        required=True,
        help="Path to the text file containing Claude's FILE: ... response.",
    )
    parser.add_argument(
        "--pytest-cmd",
        default="pytest -q",
        help='Pytest command to run after applying patches. Default: "pytest -q"',
    )
    parser.add_argument(
        "--commit-message",
        default="",
        help="Optional git commit message. If omitted, no commit is created.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse and validate only. Do not write files or run tests.",
    )
    args = parser.parse_args()

    ensure_build_artifacts()

    response_path = Path(args.response_file).resolve()
    if not response_path.exists():
        raise FileNotFoundError(f"Response file not found: {response_path}")

    raw = response_path.read_text(encoding="utf-8")
    patches = validate_patches(parse_claude_response(raw))

    if args.dry_run:
        print(json.dumps({
            "mode": "dry-run",
            "patch_count": len(patches),
            "files": [p.rel_path for p in patches],
        }, ensure_ascii=False, indent=2))
        return 0

    backup_dir = create_backup_dir()
    backup_existing_files(patches, backup_dir)

    try:
        apply_patches(patches)
        pytest_cmd = args.pytest_cmd.split()
        test_result = run_command(pytest_cmd, REPO_ROOT)

        if test_result.returncode != 0:
            restore_from_backup(backup_dir, patches)
            print(json.dumps({
                "status": "rolled_back",
                "reason": "tests_failed",
                "files": [p.rel_path for p in patches],
                "pytest_stdout": test_result.stdout,
                "pytest_stderr": test_result.stderr,
            }, ensure_ascii=False, indent=2))
            return test_result.returncode

        payload = {
            "status": "applied",
            "files": [p.rel_path for p in patches],
            "pytest_stdout": test_result.stdout,
            "pytest_stderr": test_result.stderr,
            "backup_dir": str(backup_dir),
        }

        if args.commit_message:
            commit_result = git_commit(args.commit_message)
            payload["git_commit_stdout"] = commit_result.stdout
            payload["git_commit_stderr"] = commit_result.stderr
            payload["git_commit_returncode"] = commit_result.returncode
            payload["status"] = "committed" if commit_result.returncode == 0 else "applied"

        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    except Exception as exc:
        restore_from_backup(backup_dir, patches)
        print(json.dumps({
            "status": "rolled_back",
            "reason": "exception",
            "error": str(exc),
        }, ensure_ascii=False, indent=2))
        return 1


if __name__ == "__main__":
    sys.exit(main())
