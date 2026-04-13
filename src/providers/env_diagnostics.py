from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

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


def _format_missing_key_header(var_name: str, aliases: tuple[str, ...]) -> str:
    accepted = (var_name, *aliases)
    if len(accepted) == 1:
        return f"[ERROR] {var_name} not found"
    return f"[ERROR] {var_name} not found (also accepts: {', '.join(aliases)})"


def _missing_dotenv_file_message(var_name: str, aliases: tuple[str, ...] = ()) -> str:
    return (
        f"{_format_missing_key_header(var_name, aliases)}\n\n"
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


def _missing_python_dotenv_message(var_name: str, dotenv_path: Path, aliases: tuple[str, ...] = ()) -> str:
    return (
        f"{_format_missing_key_header(var_name, aliases)}\n\n"
        "Cause:\n"
        f"- .env file exists: {dotenv_path}\n"
        "- python-dotenv is not installed, so Nexa cannot auto-load .env\n\n"
        "Fix:\n"
        "1. Install python-dotenv\n"
        "   pip install python-dotenv\n"
        "2. Re-run the same command\n"
    )


def _missing_key_message(var_name: str, dotenv_path: Path, aliases: tuple[str, ...] = ()) -> str:
    return (
        f"{_format_missing_key_header(var_name, aliases)}\n\n"
        "Cause:\n"
        f"- .env file was found: {dotenv_path}\n"
        f"- {var_name} is missing or empty\n\n"
        "Fix:\n"
        "1. Open the .env file\n"
        "2. Add:\n"
        f"   {var_name}=your_key_here\n"
    )


def _get_first_nonempty_env(var_names: tuple[str, ...]) -> str:
    for var_name in var_names:
        value = (os.environ.get(var_name) or "").strip()
        if value:
            return value
    return ""


def resolve_api_key_or_raise(var_name: str, *, aliases: tuple[str, ...] = ()) -> str:
    all_names = (var_name, *aliases)
    key = _get_first_nonempty_env(all_names)
    if key:
        return key

    dotenv_path = _find_existing_env_file()
    if dotenv_path is None:
        raise RuntimeError(_missing_dotenv_file_message(var_name, aliases))

    if not _dotenv_installed():
        raise RuntimeError(_missing_python_dotenv_message(var_name, dotenv_path, aliases))

    _try_load_env_file(dotenv_path)
    key = _get_first_nonempty_env(all_names)
    if key:
        return key

    raise RuntimeError(_missing_key_message(var_name, dotenv_path, aliases))


@dataclass(frozen=True)
class EnvSetupStatus:
    dotenv_installed: bool
    dotenv_file_found: bool
    dotenv_file_path: str | None = None


def read_env_setup_status() -> EnvSetupStatus:
    dotenv_path = _find_existing_env_file()
    return EnvSetupStatus(
        dotenv_installed=_dotenv_installed(),
        dotenv_file_found=dotenv_path is not None,
        dotenv_file_path=(str(dotenv_path) if dotenv_path is not None else None),
    )


class ProviderAccessPathType:
    SESSION_INJECTED = "session_injected"
    ENV_VAR = "env_var"
    DOTENV_FILE = "dotenv_file"
    UNAVAILABLE = "unavailable"


def _mask_key(api_key: str) -> str:
    if len(api_key) <= 8:
        return "****"
    return f"{api_key[:4]}...{api_key[-4:]}"


@dataclass(frozen=True)
class ProviderAccessPath:
    path_type: str
    resolved: bool
    key_hint: str | None = None
    source_label: str | None = None


@dataclass(frozen=True)
class ProviderKeyResolution:
    preset: str
    access_path: ProviderAccessPath
    api_key: str | None


def _resolve_from_env_mapping(env_var_names: tuple[str, ...], env: Mapping[str, str]) -> tuple[str, str] | None:
    for var_name in env_var_names:
        value = (env.get(var_name) or "").strip()
        if value:
            return var_name, value
    return None


def resolve_provider_key(
    preset: str,
    env_var_names: tuple[str, ...],
    *,
    session_key: str | None = None,
    env: Mapping[str, str] | None = None,
) -> ProviderKeyResolution:
    """Resolve a provider API key through layered priority.

    Priority:
      1. session_key — API key supplied directly by the UI.
      2. env var     — key in the provided env mapping or current process env.
      3. .env file   — only when `env is None`; explicit env mappings stay isolated.
      4. unavailable — no key found anywhere.

    Important isolation rule:
      When `env` is passed explicitly, it is treated as the full environment
      snapshot for this resolution. We must not fall back to the process
      environment or load a real `.env` file, otherwise tests and UI preview
      state become polluted by machine-local configuration.
    """

    if session_key and session_key.strip():
        key = session_key.strip()
        return ProviderKeyResolution(
            preset=preset,
            access_path=ProviderAccessPath(
                path_type=ProviderAccessPathType.SESSION_INJECTED,
                resolved=True,
                key_hint=_mask_key(key),
                source_label="entered in UI",
            ),
            api_key=key,
        )

    effective_env: Mapping[str, str] = env if env is not None else os.environ
    env_match = _resolve_from_env_mapping(env_var_names, effective_env)
    if env_match is not None:
        var_name, value = env_match
        return ProviderKeyResolution(
            preset=preset,
            access_path=ProviderAccessPath(
                path_type=ProviderAccessPathType.ENV_VAR,
                resolved=True,
                key_hint=_mask_key(value),
                source_label=f"env:{var_name}",
            ),
            api_key=value,
        )

    if env is None:
        dotenv_path = _find_existing_env_file()
        if dotenv_path is not None and _dotenv_installed():
            _try_load_env_file(dotenv_path)
            env_match = _resolve_from_env_mapping(env_var_names, os.environ)
            if env_match is not None:
                var_name, value = env_match
                return ProviderKeyResolution(
                    preset=preset,
                    access_path=ProviderAccessPath(
                        path_type=ProviderAccessPathType.DOTENV_FILE,
                        resolved=True,
                        key_hint=_mask_key(value),
                        source_label=f".env:{var_name}",
                    ),
                    api_key=value,
                )

    return ProviderKeyResolution(
        preset=preset,
        access_path=ProviderAccessPath(
            path_type=ProviderAccessPathType.UNAVAILABLE,
            resolved=False,
            key_hint=None,
            source_label=None,
        ),
        api_key=None,
    )


__all__ = [
    "EnvSetupStatus",
    "NEXA_DOTENV_INSTALLED",
    "NEXA_DOTENV_PATH",
    "ProviderAccessPath",
    "ProviderAccessPathType",
    "ProviderKeyResolution",
    "publish_dotenv_status",
    "read_env_setup_status",
    "resolve_api_key_or_raise",
    "resolve_provider_key",
]
