Spec ID: execution_environment_contract
Version: 1.4.0
Status: Active
Category: contracts
Depends On:

# Execution Environment Contract (No-IO v1)
Version: 1.4.0
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


----------------------------------------------------------------------
3) dependency_fingerprint Contract
----------------------------------------------------------------------

If requirements.txt exists at repo root, engine MUST compute:

dependency_fingerprint = SHA256(canonical_requirements_txt)

canonical_requirements_txt rules:
- Split into lines
- Strip whitespace
- Remove empty lines
- Remove comment lines starting with '#'
- Sort lines lexicographically
- Join with '\n'
- Hash via SHA256

If requirements.txt is missing, dependency_fingerprint MUST be SHA256("") (empty payload).


----------------------------------------------------------------------
4) plugin_registry_fingerprint Contract
----------------------------------------------------------------------

Engine MUST compute plugin_registry_fingerprint based on:

- Loaded plugin identifiers
- Plugin file SHA256
- Canonical lexicographic ordering

Algorithm:
1. For each plugin: "<plugin_id>:<file_sha256>"
2. Sort entries lexicographically
3. Join with '\n'
4. SHA256 over joined string


----------------------------------------------------------------------
5) provider_fingerprint Contract
----------------------------------------------------------------------

Engine MUST compute provider_fingerprint from provider configuration.

Included fields (if present):
- provider
- model
- endpoint
- temperature
- max_tokens
- adapter_version

Rules:
- Exclude keys with None values
- Canonical JSON (sort_keys=True, separators=(',', ':'))
- SHA256 over canonical string
