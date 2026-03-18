from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
from typing import List

MODEL_MAP = {
    "simple_edit": "Claude Haiku",
    "test_generation": "Claude Haiku",
    "formatter": "Claude Haiku",
    "multi_refactor": "Claude Sonnet",
    "contract_change": "Claude Sonnet",
    "debug": "Claude Sonnet",
}


def select_model(task_type: str) -> str:
    if task_type not in MODEL_MAP:
        raise ValueError("Unknown task type: {0}".format(task_type))
    return MODEL_MAP[task_type]


def get_latest_commit() -> str:
    try:
        output = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            stderr=subprocess.DEVNULL,
        )
        return output.decode("utf-8").strip()
    except Exception:
        return "unknown"


def build_session_state(step: str, goal: str) -> str:
    commit = get_latest_commit()
    return """
[SESSION STATE CARD]

Mode: IMPLEMENT

Current Step:
{step}

Single Objective:
{goal}

Latest Stable Commit:
{commit}

In Scope:
- provided target files

Out of Scope:
- runtime architecture
- plugin namespace
- unrelated modules

Must Preserve:
- contract compatibility
- deterministic execution
""".strip().format(step=step, goal=goal, commit=commit)


def build_task_capsule(goal: str, files: List[str], tests: List[str]) -> str:
    files_list = "\n".join("- {0}".format(file_path) for file_path in files)
    tests_list = "\n".join("- {0}".format(test_path) for test_path in tests)

    return """
[TASK CAPSULE]

Goal:
- {goal}

Modify:
{files_list}

Do:
1. implement required logic
2. preserve architecture rules

Do Not:
- modify unrelated modules

Tests:
{tests_list}

Done When:
- expected behavior implemented
- pytest passes
""".strip().format(goal=goal, files_list=files_list, tests_list=tests_list)


def assemble_prompt(model: str, reason: str, session_card: str, task_capsule: str) -> str:
    return """
[CLAUDE TASK — NEXA]

Claude Model: {model}
Reason: {reason}

--------------------------------
{session_card}

--------------------------------
{task_capsule}

--------------------------------

[OUTPUT FORMAT]

Return only:

1. change summary
2. modified file list
3. full updated file contents
4. test updates
5. implementation done checklist result

Do not include long narrative explanations.
""".strip().format(
        model=model,
        reason=reason,
        session_card=session_card,
        task_capsule=task_capsule,
    )


def write_prompt(prompt: str, output_path: Path) -> None:
    output_path.write_text(prompt, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Claude coding prompt")
    parser.add_argument("--step", required=True)
    parser.add_argument("--goal", required=True)
    parser.add_argument("--files", nargs="+", required=True)
    parser.add_argument("--tests", nargs="*", default=[])
    parser.add_argument("--type", required=True)
    parser.add_argument("--out", default="claude_task_prompt.txt")

    args = parser.parse_args()

    model = select_model(args.type)
    reason = "task type = {0}".format(args.type)

    session = build_session_state(args.step, args.goal)
    task = build_task_capsule(args.goal, args.files, args.tests)

    prompt = assemble_prompt(model, reason, session, task)

    write_prompt(prompt, Path(args.out))

    print("Prompt generated -> {0}".format(args.out))


if __name__ == "__main__":
    main()
