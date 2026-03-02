# Execution Environment Contract (No-IO v1)
Version: 1.1.0
Status: Official Contract

Purpose:
Defines execution environment constraints for Hyper-AI v1.

---------------------------------------------------------------------
1. No-IO Principle (v1)
---------------------------------------------------------------------
- Engine execution MUST NOT perform external IO.
- Forbidden operations include:
  - file system access
  - network access
  - database access
  - subprocess execution
- Any detection of such behavior MUST be treated as ERROR at validation level.

---------------------------------------------------------------------
2. Side-Effect Prohibition
---------------------------------------------------------------------
- Node handlers must be pure functions of input_snapshot → output_snapshot.
- Shared mutable state mutation is forbidden.
- Global state mutation is forbidden.

---------------------------------------------------------------------
3. Determinism Preservation
---------------------------------------------------------------------
- Execution must remain deterministic under identical structure + handlers.
- No time-based branching allowed inside node logic (v1 policy).

---------------------------------------------------------------------
4. Versioning
---------------------------------------------------------------------
- Introduction of IO capabilities requires MAJOR version bump.
- This contract applies to Engine Execution Model v1.x.


----------------------------------------------------------------------
2) Environment v2 Contract
----------------------------------------------------------------------

trace.meta.environment MUST include:

- python_version (str)
- platform (str)
- dependency_fingerprint (str)
- plugin_registry_fingerprint (str)
- provider_fingerprint (str)
- environment_fingerprint (str)

environment_fingerprint MUST be calculated using canonical JSON
serialization (sorted keys) and hashed via SHA256.

If environment differs, execution MUST be considered different.
