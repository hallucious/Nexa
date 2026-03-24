from __future__ import annotations

import os
from pathlib import Path

NEXA_DOTENV_INSTALLED = "NEXA_DOTENV_INSTALLED"
NEXA_DOTENV_PATH = "NEXA_DOTENV_PATH"


def publish_dotenv_status(*, installed: bool, loaded_path: str | None) -> None:
    os.environ[NEXA_DOTENV_INSTALLED] = "1" if installed else "0"
    os.environ[NEXA_DOTENV_PATH] = (loaded_path or "").strip()


def _candidate_env_files() -> list[Path]:
    candidates: list[Path] = []

    published_path = (os.environ.get(NEXA_DOTENV_PATH) or "").strip()
    if published_path:
        candidates.append(Path(published_path).expanduser())

    cwd = Path.cwd()
    candidates.append(cwd / ".env")

    try:
        current = cwd.resolve()
    except Exception:
        current = cwd

    for candidate in [current, *current.parents]:
        if (candidate / "src").exists() and (candidate / "examples").exists():
            candidates.append(candidate / ".env")
            break

    unique: list[Path] = []
    seen: set[str] = set()
    for candidate in candidates:
        try:
            key = str(candidate.resolve(strict=False))
        except Exception:
            key = str(candidate)
        if key in seen:
            continue
        seen.add(key)
        unique.append(candidate)
    return unique


def _find_existing_env_file() -> Path | None:
    for candidate in _candidate_env_files():
        try:
            if candidate.exists():
                return candidate
        except Exception:
            continue
    return None


def _dotenv_installed() -> bool:
    published = (os.environ.get(NEXA_DOTENV_INSTALLED) or "").strip()
    if published in {"0", "1"}:
        return published == "1"
    try:
        import dotenv  # noqa: F401
    except ModuleNotFoundError:
        return False
    return True


def _try_load_env_file(dotenv_path: Path | None) -> None:
    if dotenv_path is None or not _dotenv_installed():
        return
    try:
        from dotenv import load_dotenv
    except ModuleNotFoundError:
        return
    load_dotenv(dotenv_path=dotenv_path, override=False)


def _missing_dotenv_file_message(var_name: str) -> str:
    return (
        f"[ERROR] {var_name} not found\n\n"
        "Cause:\n"
        "- No API key is set in the current process environment\n"
        "- No .env file was found\n\n"
        "Fix:\n"
        "1. Create a .env file in project root\n"
        "2. Add:\n"
        f"   {var_name}=your_key_here\n\n"
        "OR\n\n"
        f"export {var_name}=your_key_here\n"
    )


def _missing_python_dotenv_message(var_name: str, dotenv_path: Path) -> str:
    return (
        f"[ERROR] {var_name} not found\n\n"
        "Cause:\n"
        f"- .env file exists: {dotenv_path}\n"
        "- python-dotenv is not installed, so Nexa cannot auto-load .env\n\n"
        "Fix:\n"
        "1. Install python-dotenv\n"
        "   pip install python-dotenv\n"
        "2. Re-run the same command\n"
    )


def _missing_key_message(var_name: str, dotenv_path: Path) -> str:
    return (
        f"[ERROR] {var_name} not found\n\n"
        "Cause:\n"
        f"- .env file was found: {dotenv_path}\n"
        f"- {var_name} is missing or empty\n\n"
        "Fix:\n"
        "1. Open the .env file\n"
        "2. Add:\n"
        f"   {var_name}=your_key_here\n"
    )


def resolve_api_key_or_raise(var_name: str) -> str:
    key = (os.environ.get(var_name) or "").strip()
    if key:
        return key

    dotenv_path = _find_existing_env_file()
    if dotenv_path is None:
        raise RuntimeError(_missing_dotenv_file_message(var_name))

    if not _dotenv_installed():
        raise RuntimeError(_missing_python_dotenv_message(var_name, dotenv_path))

    _try_load_env_file(dotenv_path)
    key = (os.environ.get(var_name) or "").strip()
    if key:
        return key

    raise RuntimeError(_missing_key_message(var_name, dotenv_path))
