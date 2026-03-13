
DOCUMENT
test_map.md

Purpose

This document maps Nexa system functionality to its corresponding test suites.
It allows developers and AI coding agents to understand which tests validate
which parts of the system before making modifications.

AI agents must consult this document before modifying any runtime component.


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. ENGINE EXECUTION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Component
src/engine/engine.py

Test Coverage
tests/test_engine_execution.py
tests/test_engine_runtime_flow.py

Validated Behavior
- Engine initialization
- Circuit loading
- Node execution coordination


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
2. NODE EXECUTION RUNTIME
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Component
src/engine/node_execution_runtime.py

Test Coverage
tests/test_node_execution_runtime.py

Validated Behavior
- prompt construction
- provider invocation
- plugin execution
- artifact generation
- trace emission


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
3. CIRCUIT GRAPH
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Component
src/circuit/node.py
src/circuit/node_execution.py

Test Coverage
tests/test_circuit_node.py
tests/test_node_execution.py

Validated Behavior
- node structure
- dependency resolution
- execution ordering


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
4. PROVIDER SYSTEM
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Component
src/platform/provider_registry.py

Test Coverage
tests/test_provider_registry.py

Validated Behavior
- provider registration
- provider resolution
- provider lookup errors


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
5. PLUGIN SYSTEM
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Component
src/platform/plugin_registry.py

Test Coverage
tests/test_plugin_registry.py

Validated Behavior
- plugin registration
- plugin discovery
- plugin lifecycle


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
6. CONTRACT SYSTEM
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Component
src/contracts/spec_versions.py

Test Coverage
tests/test_spec_version_sync.py

Validated Behavior
- documentation spec version synchronization
- contract validation


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
7. STEP TESTS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Component
Entire system

Test Coverage
tests/test_stepXXX_*.py

Validated Behavior
- incremental system evolution
- regression prevention
- compatibility validation


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
8. TEST EXECUTION RULE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Before accepting any change:

1. pytest must pass
2. contract tests must pass
3. spec-version sync must pass


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
END
