
#!/usr/bin/env python3
"""
Spec migration tool for Nexa docs/specs reorganization.

Purpose
- normalize legacy filenames
- move root-level stray specs into category folders or history
- preserve duplicates safely under docs/specs/history/redundant/
- consolidate registry file location to docs/specs/indexes/_active_specs.yaml

Usage
  python scripts/migrate_specs.py --root . --dry-run
  python scripts/migrate_specs.py --root . --apply
"""
from __future__ import annotations

import argparse
import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import List


@dataclass
class Action:
    kind: str
    src: str | None
    dst: str | None
    reason: str


def rel(path: Path, root: Path) -> str:
    return str(path.relative_to(root)).replace("\\", "/")


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def build_actions(root: Path) -> List[Action]:
    specs = root / "docs" / "specs"
    actions: List[Action] = []

    # Safety directories
    history_redundant = specs / "history" / "redundant"

    # 1) Normalize foundation filenames
    foundation_renames = {
        "foundation/architectural Doctrine.md": "foundation/architectural_doctrine.md",
        "foundation/definition Registry.md": "foundation/definition_registry.md",
        "foundation/definition Versioning & Migration Strategy.md": "foundation/definition_versioning_and_migration_strategy.md",
        "foundation/runtime Responsibility.md": "foundation/runtime_responsibility.md",
    }

    # 2) Normalize policies filenames
    policy_renames = {
        "policies/Observability & Metrics.md": "policies/observability_and_metrics.md",
        "policies/Policy Engine.md": "policies/policy_engine.md",
        "policies/Static Validation Rules.md": "policies/static_validation_rules.md",
    }

    # 3) Move stray root-level specs into history/redundant for safe preservation
    stray_to_history = {
        "Provider Abstraction Contract.md": "history/redundant/provider_abstraction_contract.md",
        "circuit_savefile_contract.md": "history/redundant/circuit_savefile_contract.md",
        "engine_savefile_contract.md": "history/redundant/engine_savefile_contract.md",
        "execution_config_prompt_binding_contract.md": "history/redundant/execution_config_prompt_binding_contract.md",
        "execution_config_registry_contract.md": "history/redundant/execution_config_registry_contract.md",
        # Root copy conflicts with contracts/execution_environment_contract.md
        "execution_environment_contract.md": "history/redundant/execution_environment_contract_root_legacy.md",
        # Root duplicates of policies/*
        "validation_rule_catalog.md": "history/redundant/validation_rule_catalog_root_duplicate.md",
        "validation_rule_lifecycle.md": "history/redundant/validation_rule_lifecycle_root_duplicate.md",
    }

    # 4) Consolidate active spec registry file
    active_root = specs / "_active_specs.yaml"
    active_index = specs / "indexes" / "_active_specs.yaml"
    if active_root.exists():
        if active_index.exists():
            actions.append(Action(
                kind="archive_duplicate",
                src=rel(active_root, root),
                dst=rel(history_redundant / "_active_specs_root_duplicate.yaml", root),
                reason="indexes/_active_specs.yaml is canonical registry location; preserve root duplicate under history/redundant",
            ))
        else:
            actions.append(Action(
                kind="move_registry",
                src=rel(active_root, root),
                dst=rel(active_index, root),
                reason="canonical active spec registry location is docs/specs/indexes/_active_specs.yaml",
            ))

    for mapping in (foundation_renames, policy_renames, stray_to_history):
        for src_rel, dst_rel in mapping.items():
            src = specs / src_rel
            dst = specs / dst_rel
            if src.exists():
                actions.append(Action(
                    kind="move",
                    src=rel(src, root),
                    dst=rel(dst, root),
                    reason="spec migration normalization",
                ))

    return actions


def apply_actions(root: Path, actions: List[Action]) -> None:
    for action in actions:
        src = root / action.src if action.src else None
        dst = root / action.dst if action.dst else None

        if action.kind in {"move", "archive_duplicate", "move_registry"}:
            assert src is not None and dst is not None
            if not src.exists():
                continue
            ensure_parent(dst)
            if dst.exists():
                # Never overwrite; preserve both.
                backup = dst.with_name(dst.stem + "__preexisting" + dst.suffix)
                shutil.move(str(dst), str(backup))
            shutil.move(str(src), str(dst))
        else:
            raise ValueError(f"Unknown action kind: {action.kind}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".", help="repository root")
    parser.add_argument("--apply", action="store_true", help="apply changes")
    parser.add_argument("--dry-run", action="store_true", help="print planned changes only")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    actions = build_actions(root)

    report = {
        "root": str(root),
        "action_count": len(actions),
        "actions": [action.__dict__ for action in actions],
    }

    print(json.dumps(report, indent=2, ensure_ascii=False))

    if args.apply:
        apply_actions(root, actions)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
