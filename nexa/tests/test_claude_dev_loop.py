from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = REPO_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import claude_dev_loop as module  # type: ignore


def test_strip_optional_code_fence():
    body = """```python
print("hello")
```"""
    assert module.strip_optional_code_fence(body) == 'print("hello")'


def test_parse_claude_response_multiple_files():
    raw = """FILE: src/a.py
```python
print("a")
```

FILE: tests/test_a.py
```python
def test_a():
    assert True
```"""
    patches = module.parse_claude_response(raw)
    assert [p.rel_path for p in patches] == ["src/a.py", "tests/test_a.py"]
    assert 'print("a")' in patches[0].content


def test_validate_rel_path_rejects_parent():
    try:
        module.validate_rel_path("../bad.py")
        assert False, "Expected ValueError"
    except ValueError:
        assert True


def test_validate_rel_path_rejects_protected_prefix():
    try:
        module.validate_rel_path("src/contracts/spec_versions.py")
        assert False, "Expected ValueError"
    except ValueError:
        assert True
