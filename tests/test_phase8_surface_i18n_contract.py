from __future__ import annotations

import ast
from pathlib import Path

from src.ui.i18n import _TRANSLATIONS

_TARGET_FILES = [
    "src/ui/circuit_library.py",
    "src/ui/result_history.py",
    "src/ui/feedback_channel.py",
    "src/ui/execution_panel.py",
    "src/ui/validation_panel.py",
    "src/ui/designer_panel.py",
    "src/ui/top_bar.py",
]


def _ui_text_keys(path: str) -> set[str]:
    tree = ast.parse(Path(path).read_text(encoding="utf-8"))
    keys: set[str] = set()

    class Visitor(ast.NodeVisitor):
        def visit_Call(self, node: ast.Call) -> None:
            func = node.func
            func_name = None
            if isinstance(func, ast.Name):
                func_name = func.id
            elif isinstance(func, ast.Attribute):
                func_name = func.attr
            if func_name == "ui_text" and node.args:
                first = node.args[0]
                if isinstance(first, ast.Constant) and isinstance(first.value, str):
                    keys.add(first.value)
            self.generic_visit(node)

    Visitor().visit(tree)
    return keys


def test_phase8_surface_ui_text_keys_exist_in_english_and_korean() -> None:
    en_keys = set(_TRANSLATIONS["en"].keys())
    ko_keys = set(_TRANSLATIONS["ko"].keys())
    missing_by_file: dict[str, dict[str, list[str]]] = {}

    for path in _TARGET_FILES:
        refs = _ui_text_keys(path)
        missing_en = sorted(refs - en_keys)
        missing_ko = sorted(refs - ko_keys)
        if missing_en or missing_ko:
            missing_by_file[path] = {"en": missing_en, "ko": missing_ko}

    assert missing_by_file == {}
