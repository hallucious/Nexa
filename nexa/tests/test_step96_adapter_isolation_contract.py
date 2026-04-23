from __future__ import annotations

import ast
from pathlib import Path
from typing import Iterable, List

REPO_ROOT = Path(__file__).resolve().parents[1]
ADAPTERS_DIR = REPO_ROOT / "src" / "providers" / "adapters"

# Adapter는 "번역기" 레이어다. 플랫폼(Engine/Worker/Registry/Trace) 침범을 금지한다.
FORBIDDEN_IMPORT_PREFIXES = (
    "src.engine",
    "src.platform",
    "src.registry",
    "src.trace",
)

# 환경/프로세스 직접 제어는 안정성/재현성에 리스크. (네트워크 호출은 adapter 역할이므로 허용)
FORBIDDEN_MODULES = {
    "subprocess",
    "importlib",
}

# 파일 I/O 금지 (adapter는 외부 API 번역/호출만 담당)
FORBIDDEN_CALL_NAMES = {
    "open",  # builtins.open
}


def _iter_py_files(root: Path) -> Iterable[Path]:
    if not root.exists():
        return []
    return sorted(p for p in root.rglob("*.py") if p.is_file())


def _analyze_file(path: Path) -> List[str]:
    errors: List[str] = []
    rel = path.relative_to(REPO_ROOT)

    try:
        src = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return [f"{rel}: non-utf8 file encoding is not allowed in adapters"]

    try:
        tree = ast.parse(src, filename=str(rel))
    except SyntaxError as e:
        return [f"{rel}: syntax error: {e}"]

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                name = alias.name
                if name in FORBIDDEN_MODULES:
                    errors.append(f"{rel}: forbidden import '{name}'")
                if name.startswith(FORBIDDEN_IMPORT_PREFIXES):
                    errors.append(f"{rel}: forbidden platform import '{name}'")

        if isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            if mod in FORBIDDEN_MODULES:
                errors.append(f"{rel}: forbidden import-from '{mod}'")
            if mod.startswith(FORBIDDEN_IMPORT_PREFIXES):
                errors.append(f"{rel}: forbidden platform import-from '{mod}'")

        if isinstance(node, ast.Call):
            fn = node.func
            if isinstance(fn, ast.Name) and fn.id in FORBIDDEN_CALL_NAMES:
                errors.append(f"{rel}: forbidden call '{fn.id}(...)' (file I/O not allowed)")
            if isinstance(fn, ast.Attribute) and fn.attr == "open":
                errors.append(f"{rel}: forbidden call '*.open(...)' (file I/O not allowed)")

    return errors


def test_step96_adapter_isolation_contract():
    assert ADAPTERS_DIR.exists(), "src/providers/adapters directory must exist"

    files = list(_iter_py_files(ADAPTERS_DIR))
    assert files, "No adapter python files found; expected at least one adapter module"

    all_errors: List[str] = []
    for f in files:
        all_errors.extend(_analyze_file(f))

    assert not all_errors, "Adapter isolation contract violated:\n" + "\n".join(all_errors)
