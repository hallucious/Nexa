
# NEXA_AI_CONTEXT.md

This document is the **single AI context file** provided to coding agents (Claude, GPT, etc.)
when they perform implementation or refactoring tasks on the Nexa codebase.

It merges the essential architectural rules, execution invariants, repository map,
module map, testing map, and decision log.

AI agents MUST read this document before modifying the codebase.

---------------------------------------------------------------------
SECTION 1 — ARCHITECTURE CONSTITUTION
---------------------------------------------------------------------

Core invariant principles of Nexa:

1. Node is the sole execution unit.
2. Execution follows dependency graph ordering.
3. Artifact storage is append‑only.
4. Runtime execution must be deterministic.
5. Plugin writes are restricted to namespace:

   plugin.<plugin_id>.*

6. Contract‑driven architecture:
   All architecture behavior is defined through versioned specifications.

---------------------------------------------------------------------
SECTION 2 — EXECUTION INVARIANTS
---------------------------------------------------------------------

Execution rules that MUST NOT be broken:

• Node executes exactly once per run.
• Node execution generates artifacts.
• Artifacts are never overwritten.
• Trace events are always recorded.
• Providers are resolved via provider registry.
• Plugins execute after provider call.
• Runtime must remain deterministic.

---------------------------------------------------------------------
SECTION 3 — RUNTIME FLOW
---------------------------------------------------------------------

Standard node execution lifecycle:

1. Engine loads circuit
2. Resolve node dependencies
3. Prepare prompt
4. Resolve provider
5. Call provider
6. Execute plugins
7. Generate artifacts
8. Write trace events
9. Persist run state

---------------------------------------------------------------------
SECTION 4 — REPOSITORY MAP
---------------------------------------------------------------------

Core directories:

src/
    engine/
    circuit/
    platform/
    contracts/

tests/
    pytest suite validating functionality

docs/
    BLUEPRINT.md
    CODING_PLAN.md
    specs/

examples/
    example circuits

tools/
    coding_kit

---------------------------------------------------------------------
SECTION 5 — MODULE MAP
---------------------------------------------------------------------

Important modules and their responsibilities.

src/engine/engine.py
Main execution entrypoint.

src/engine/node_execution_runtime.py
Runtime for executing a node.

src/circuit/node.py
Node definition.

src/circuit/node_execution.py
Node execution orchestration.

src/platform/provider_registry.py
AI provider registry.

src/platform/plugin_registry.py
Plugin registry.

src/contracts/spec_versions.py
Spec‑version synchronization.

---------------------------------------------------------------------
SECTION 6 — TEST MAP
---------------------------------------------------------------------

tests/test_engine_*
Engine execution validation.

tests/test_node_execution_runtime.py
Node runtime behavior.

tests/test_circuit_node.py
Node structure.

tests/test_provider_registry.py
Provider registration.

tests/test_plugin_registry.py
Plugin system.

tests/test_spec_version_sync.py
Spec‑version contract validation.

tests/test_stepXXX_*
Incremental regression protection.

---------------------------------------------------------------------
SECTION 7 — DECISION LOG (CORE DECISIONS)
---------------------------------------------------------------------

D‑001 Node as sole execution unit
D‑002 Pipeline execution removed
D‑003 Artifact append‑only storage
D‑004 Plugin namespace isolation
D‑005 Contract‑driven architecture

---------------------------------------------------------------------
SECTION 8 — CHANGE RULES
---------------------------------------------------------------------

Before making changes:

1. Identify correct module.
2. Respect architecture constitution.
3. Ensure execution invariants remain valid.
4. Update tests if required.
5. pytest must pass.
6. spec‑version sync must pass.

---------------------------------------------------------------------
END OF FILE
