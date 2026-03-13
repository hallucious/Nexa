
DOCUMENT
module_map.md

Purpose

This document provides a file-level map of the Nexa codebase.
It explains the responsibility of each important module so that
developers and AI coding agents know exactly where modifications
should occur.

AI agents must read this document together with:
- repo_map.md
- runtime_flow.md
- execution_invariants.md

before performing any code modification.


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. CORE ENGINE MODULES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

src/engine/engine.py

Role
Main execution entrypoint of Nexa.

Responsibilities
- Initialize runtime
- Load circuit
- Coordinate node execution
- Manage execution lifecycle


src/engine/node_execution_runtime.py

Role
Core runtime responsible for executing a single node.

Responsibilities
- Resolve execution config
- Prepare prompt
- Call provider
- Run plugins
- Generate artifact
- Write trace events


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
2. CIRCUIT SYSTEM
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

src/circuit/node.py

Role
Defines the Node abstraction.

Responsibilities
- Node structure
- Node configuration
- Node metadata


src/circuit/node_execution.py

Role
Defines node execution stages and orchestration rules.

Responsibilities
- Execution stages
- Stage transitions
- Execution state management


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
3. PLATFORM LAYER
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

src/platform/provider_registry.py

Role
Registry for AI providers.

Responsibilities
- Register provider implementations
- Resolve provider references


src/platform/plugin_registry.py

Role
Registry for runtime plugins.

Responsibilities
- Plugin registration
- Plugin lookup
- Plugin lifecycle management


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
4. CONTRACT SYSTEM
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

src/contracts/spec_versions.py

Role
Maintains spec version synchronization.

Responsibilities
- Track versions of documentation specs
- Ensure spec-version sync with code


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
5. TEST SYSTEM
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

tests/

Role
pytest test suite validating Nexa functionality.

Test categories

engine tests
execution tests
contract tests
step tests

Naming convention

test_stepXXX_*.py


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
6. DOCUMENTATION SYSTEM
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

docs/BLUEPRINT.md

Role
High-level architecture description.


docs/CODING_PLAN.md

Role
Implementation roadmap with step numbers.


docs/specs/

Role
Contract and architecture specifications.


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
7. EXAMPLES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

examples/

Role
Example circuits demonstrating Nexa usage.

Examples may include

hello circuit
multi-node circuits
plugin examples


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
8. TOOLS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

tools/

Role
Developer tooling.

Examples

Nexa Coding Kit
build scripts
utility scripts


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
9. MODIFICATION GUIDELINES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Before modifying any module:

1. Identify the correct module from this map
2. Confirm responsibility of the module
3. Avoid cross-layer modification
4. Update related tests
5. Verify architecture invariants


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
END
