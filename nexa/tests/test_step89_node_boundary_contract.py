from __future__ import annotations

import ast
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def _imports_in_file(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    mods: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                mods.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                mods.add(node.module)
    return mods


def test_step89_node_boundary_contract_static_imports():
    """Step89: Node/Circuit layer must not directly depend on provider/registry implementations.

    Rationale (non-dev explanation):
    - Node/Circuit are '작업장/동선' 선언·파이프라인 레이어
    - Provider(노동자) 및 Registry(도구창고)의 구체 구현은 Engine/Runtime이 소유
    - 이를 어기면 Node가 '미니 엔진'으로 커지면서 구조가 붕괴한다.
    """

    targets = [
        REPO_ROOT / "src" / "engine" / "node.py",
        REPO_ROOT / "src" / "circuit" / "model.py",
        REPO_ROOT / "src" / "circuit" / "node_execution.py",
    ]
    for p in targets:
        assert p.exists(), f"missing file: {p}"

    forbidden_prefixes = (
        "src.providers",  # provider implementations belong to runtime/engine
        "src.platform.plugin_version_registry",  # registry implementation belongs to platform/runtime
        "src.platform.injection_registry",  # injection registry is runtime/platform governance
    )

    for p in targets:
        imported = _imports_in_file(p)
        bad = sorted(
            m for m in imported if any(m == fp or m.startswith(fp + ".") for fp in forbidden_prefixes)
        )
        assert not bad, f"{p} imports forbidden runtime modules: {bad}"
