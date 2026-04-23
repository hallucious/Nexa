# Plugin Runtime Loading / Installation Contract v1.1-b

## Recommended save path
`docs/specs/plugins/plugin_runtime_loading_installation_contract.md`

## 1. Purpose

This document defines the canonical runtime loading and installation contract for plugins in Nexa.

It establishes:
- how a registry-visible or artifact-local plugin becomes installable
- how an installed plugin becomes runtime-loadable
- how runtime decides whether a plugin may be enabled
- how installation, loading, activation, suspension, and removal differ
- how policy, verification, compatibility, and dependency posture are enforced at runtime intake

## 2. Core Decision

1. Registry visibility is not the same thing as installation.
2. Installation is not the same thing as runtime loading.
3. Runtime loading is not the same thing as activation.
4. Runtime must make explicit, policy-bounded acceptance decisions before a plugin becomes usable.
5. Activation must depend on artifact identity, verification posture, namespace policy, compatibility, and environment readiness.
6. Deactivation, suspension, and removal must not erase prior installation truth or historical traceability.

## 3. Core Vocabulary

- Installable
- Installed
- Loadable
- Loaded
- Active
- Suspended
- Removed

## 4. Canonical Lifecycle

Registry Entry or Local Artifact
-> Installation Eligibility Check
-> Installation
-> Runtime Load Preflight
-> Loaded
-> Activation Decision
-> Active Use
-> Suspend / Deactivate / Remove

## 5. Canonical Installation State Object

PluginInstallationState
- installation_id: string
- plugin_id: string
- artifact_ref: string
- manifest_ref: string
- target_runtime_ref: string
- installation_scope: enum("local_private", "workspace_bound", "runtime_local", "internal_shared", "other")
- install_status: enum("not_installed", "installed", "install_failed", "removed")
- load_status: enum("not_loaded", "loadable", "loaded", "load_failed")
- activation_status: enum("inactive", "active", "activation_failed", "suspended")
- installed_at: string | null
- last_loaded_at: string | null
- last_activated_at: string | null
- notes: string | null

## 6. Installation Eligibility Rules

A plugin may be installable only if runtime can determine:
- canonical artifact identity exists
- canonical manifest exists
- compatibility posture is acceptable
- verification posture is acceptable for target scope
- namespace policy is referenceable and enforceable
- dependency/environment requirements are satisfiable or explicitly tolerated
- no blocking governance or publication restriction remains

## 7. Relationship to Registry and Manifest

Registry publication does not guarantee installation.
Runtime must resolve artifact_ref, manifest_ref, entrypoint, compatibility, verification, policy, and dependencies.

## 8. Runtime Load Preflight

Runtime must perform:
- artifact integrity check
- entrypoint check
- compatibility check
- verification posture check
- policy enforcement readiness check
- dependency readiness check
- governance/scope check

### 8.1 MCP-aware classification preflight

Loading/install must consume approved classification explicitly rather than by implication.

Minimum MCP-aware preflight rules:
- if approved classification is `internal_native`, no MCP-facing capability preflight is required by default
- if approved classification is `mcp_native`, runtime must verify that the MCP-facing capability surface or required adapter surface is available and coherent
- if approved classification is `hybrid`, runtime must verify both Nexa runtime constraints and MCP-surface coherence
- if approved classification is `adapter`, runtime must verify both sides of the translation boundary or reject activation readiness

Plugin type resolution rule:
- installation/load acceptance must not proceed to activation with `plugin_type` unresolved
- if the artifact manifest carries `plugin_type`, runtime may use that value directly
- if the artifact manifest leaves `plugin_type` null, the loading stage must resolve it through an explicit loading/install rule
- acceptable resolution sources include builder/template metadata, discovery metadata, or an operator-supplied resolution rule
- a plugin with unresolved runtime-facing `plugin_type` must not proceed as activation-ready

Approved classification consumption rule:
- loading/install must consume approved classification from artifact/manifest truth or its explicit classification reference
- proposal-only classification must not be used as activation-ready truth

## 9. Activation Rules

Loading and activation are separate.

A plugin may be loaded but not activated if:
- governance blocks use
- stronger verification is required
- credentials are missing
- namespace enforcement cannot be guaranteed
- the plugin is suspended
- the target workflow/runtime profile disallows that plugin class

## 10. Suspension and Deactivation

- Deactivation: remains installed, not currently active.
- Suspension: intentionally blocked from use.
- Removal: no longer installed in the target runtime scope.

None of these erase historical installation truth.

## 11. Canonical Findings Categories

Examples:
- INSTALL_ARTIFACT_NOT_FOUND
- INSTALL_MANIFEST_INVALID
- INSTALL_SCOPE_NOT_ALLOWED
- INSTALL_VERIFICATION_INSUFFICIENT
- INSTALL_POLICY_REFERENCE_MISSING
- INSTALL_COMPATIBILITY_MISMATCH
- INSTALL_DEPENDENCY_UNAVAILABLE
- LOAD_ENTRYPOINT_RESOLUTION_FAILED
- LOAD_RUNTIME_BINDING_FAILED
- ACTIVATE_POLICY_ENFORCEMENT_UNAVAILABLE
- ACTIVATE_SCOPE_RESTRICTED
- ACTIVATE_PLUGIN_SUSPENDED

## 12. Explicitly Forbidden Patterns

- published therefore active
- installed therefore trusted
- loaded therefore active
- policy-blind activation
- verification-blind activation
- silent state transitions

## 13. Canonical Summary

- Registry visibility, installation, loading, and activation are distinct stages.
- A plugin becomes usable only through explicit, policy-bounded runtime acceptance.
- Runtime must enforce verification, compatibility, dependency, and namespace-policy constraints before activation.
- Installation and activation truth must remain observable and historically traceable.

## 14. Final Statement

A plugin should not become active merely because it was built or published.

It becomes usable only when a target runtime explicitly accepts, loads, and activates it under enforceable policy and verification boundaries.

That is the canonical meaning of Plugin Runtime Loading / Installation in Nexa.