"""
prompt_builder.py

Builds Claude coding prompts from a Step.

NOTE: All string literals use ASCII-only characters to ensure safe output
on Windows cp949 and other non-UTF-8 console environments.
"""
from __future__ import annotations

from src.devtools.claude_task_generator.generator import Step

_ARCHITECTURE_HEADER = """\
PROJECT
Nexa (Hyper-AI Execution Engine)

Core structure:
Circuit -> Node -> Runtime -> Prompt / Provider / Plugin -> Artifact -> Trace

Core invariants:
1. Node is the only execution unit
2. graph/dependency execution, not pipeline
3. artifact append-only
4. deterministic execution
5. plugin write restriction maintained
6. Working Context key schema contract maintained
"""


def build_prompt(step: Step) -> str:
    """Return a Claude coding prompt for the given Step.

    The prompt includes:
    - PROJECT section with Nexa architecture context
    - STEP section with id, name, description
    - FILES TO MODIFY section
    - TEST REQUIREMENTS section

    Output is ASCII-safe for all console environments.
    """
    files_section = "\n".join(f"- {f}" for f in step.files) if step.files else "(TBD)"

    return f"""{_ARCHITECTURE_HEADER}
---

STEP
{step.id}: {step.name}

Description:
{step.description}

---

FILES TO MODIFY
{files_section}

---

TEST REQUIREMENTS
- All existing pytest tests must continue to pass.
- Add tests for: {step.name}
- Use deterministic, isolated test cases.
- Follow existing test naming conventions.

---

IMPLEMENTATION DONE CHECKLIST
[ ] All new files created
[ ] pytest passes
[ ] No existing tests broken
[ ] No architectural invariants violated
[ ] Changes stay scoped to the listed files
"""
