# Plugin Registry Contract

## 1. Status

Spec ID: plugin_registry_contract

Version: 1.0.0

Scope: versioned plugin registration + deterministic resolution (in-memory v1)

Related: `docs/specs/plugin_contract.md`, `docs/specs/execution_model.md`

## 2. Purpose

This spec defines a versioned plugin registry that:
1) registers plugins with a stable plugin_id and SemVer plugin_version,
2) resolves deterministically by exact version or "latest",
3) supports compatibility checks against minimum required platform spec versions,
4) enables reproducibility (trace/savefile can record plugin_id + plugin_version).

## 3. Terminology

- plugin_id: globally unique identifier for a plugin.
- plugin_version: SemVer string (e.g., 1.2.3).
- manifest: metadata describing stages allowed, default timeout, and compatibility minima.
- registry: runtime component that stores entries and resolves requests.

## 4. Manifest fields

Required (v1.0.0):
- plugin_id: string
- plugin_version: string (SemVer)
- description: string
- stages_allowed: array of ["pre","core","post"] (subset)
- default_timeout_ms: integer
- side_effects: array[string] (may be empty)
- requires:
  - node_exec_min: string (SemVer)
  - plugin_contract_min: string (SemVer)

Optional:
- tags: array[string]
- metadata: object (JSON-serializable; MUST NOT contain secrets)

## 5. Registry API (v1.0.0)

Registration:
- register(manifest, entrypoint)
  - MUST reject duplicate (plugin_id, plugin_version).
  - MUST validate manifest.

Resolution:
- resolve(plugin_id, version)
  - version may be exact SemVer (e.g. "1.2.3") or "latest".
  - "latest" MUST resolve to the highest SemVer among registered versions.
  - MUST be deterministic given the same registry state.

Listing:
- list(plugin_id=None) -> manifests

## 6. Compatibility check (v1.0.0)

Before execution, runtime SHOULD verify:
- current NODE-EXEC version >= manifest.requires.node_exec_min
- current PLUGIN-CONTRACT version >= manifest.requires.plugin_contract_min

If compatibility fails, runtime MUST treat as plugin execution failure with reason_code:
- PLUGIN.incompatible

## 7. Observability and Trace

When a plugin call is recorded, meta SHOULD include:
- plugin_id
- plugin_version

## 8. Non-goals (v1.0.0)

- remote registries / marketplace
- signed plugin packages
- dependency graphs between plugins
- external plugin installation flows
