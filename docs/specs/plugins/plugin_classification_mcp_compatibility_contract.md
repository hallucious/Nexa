# Nexa Plugin Classification & MCP Compatibility Contract v1.1-c

## Recommended save path
`docs/specs/plugins/plugin_classification_mcp_compatibility_contract.md`

## 1. Purpose

This document defines the canonical classification model for plugins in Nexa
and the official compatibility boundary between Nexa plugins and MCP-compatible systems.

Its purpose is to make the following explicit:

- not all Nexa plugins are the same kind of thing
- not all plugins should be modeled directly as MCP-native units
- MCP compatibility is important, but it must not replace Nexa's internal runtime contracts
- classification must follow the same layered truth grammar already used elsewhere in the plugin family
- Nexa needs a stable classification rule so that future implementation, loading, governance, and external interoperability do not drift

This document exists because the question is not merely:

- "Should Nexa support MCP?"

The correct question is:

- "Which plugin classes in Nexa should be MCP-native, MCP-compatible, MCP-adapted, or non-MCP by design?"

Without that distinction, Nexa risks one of two failures:

1. underusing MCP and losing ecosystem interoperability
2. overfitting the entire internal plugin system to an external protocol whose primary role is different from Nexa's internal execution discipline

## 2. Core Decision

The official Nexa direction is:

1. Nexa must support MCP compatibility as a first-class interoperability capability.
2. Nexa must not force every plugin to become MCP-native.
3. Nexa internal runtime plugin contracts remain the canonical engine truth for:
   - runtime loading and installation
   - execution binding
   - context I/O
   - namespace policy
   - failure / recovery
   - observability
   - governance
   - lifecycle state
4. MCP is the preferred interoperability surface for plugins whose primary job is exposing or consuming external tool/resource/prompt capabilities.
5. Where needed, Nexa may use adapter layers between internal plugin contracts and MCP surfaces.

In short:

Nexa should be MCP-compatible by design,
but not MCP-reduced in its internal plugin identity.

## 3. Non-Negotiable Boundaries

The following boundaries must remain unchanged.

### 3.1 Internal runtime boundary
Nexa internal plugin runtime truth remains governed by the Nexa plugin contract family.

MCP compatibility must not silently replace:
- runtime binding truth
- context I/O truth
- policy enforcement truth
- execution-stage truth
- runtime observability truth
- runtime governance truth

### 3.2 External interoperability boundary
MCP is the preferred standard surface for external interoperability where that surface is appropriate.

This includes cases where Nexa must:
- consume external tools
- expose tools outward
- connect to external resources
- integrate prompts/workflows across agent ecosystems

### 3.3 Adapter boundary
An adapter may translate between Nexa-native plugin structures and MCP surfaces.

An adapter must not erase:
- policy boundaries
- runtime type identity
- lifecycle truth
- observability truth

### 3.4 Classification boundary
Plugin classification must be explicit.
No plugin should be treated as "implicitly MCP" or "implicitly non-MCP" without declared classification.

## 4. Why Nexa Should Not Make Every Plugin MCP-Native

Nexa should not make every plugin MCP-native for the following reasons.

### 4.1 MCP and Nexa solve overlapping but non-identical problems
MCP standardizes how clients and servers exchange:
- tools
- resources
- prompts
through negotiated protocol capabilities and transport-level interactions.

Nexa internal plugins also need to participate in:
- runtime binding
- execution-stage placement
- context read/write discipline
- namespace policy enforcement
- failure / recovery semantics
- governance posture
- lifecycle state transitions

These are not identical concerns.

### 4.2 Internal engine truth should not be hostage to external protocol drift
MCP is a living standard with ongoing evolution.
Nexa should benefit from that ecosystem,
but Nexa core runtime contracts should not need to change every time MCP transport, authorization, or extension surfaces evolve.

### 4.3 External interoperability surface is not the same as internal execution identity
An MCP tool surface is often an excellent external-facing capability description.
That does not automatically make it a sufficient internal execution identity for Nexa.

## 5. Why Nexa Should Still Treat MCP as Important

Nexa should still treat MCP as strategically important.

### 5.1 MCP provides a strong external interoperability standard
MCP gives a common contract family for:
- tools
- resources
- prompts
and related client/server capability negotiation.

That makes it valuable for plugin ecosystems that must interact across agent platforms.

### 5.2 MCP reduces custom connector fragmentation
Without MCP, external integration often drifts into many one-off connector types.
MCP can reduce this fragmentation by providing one standard surface for many external-facing integrations.

### 5.3 MCP fits especially well for external capability exposure
Where a plugin primarily exposes:
- callable tool actions
- readable resources
- templated prompt/workflow surfaces

MCP is usually the right compatibility target.

## 6. Canonical Plugin Classification Model

The official plugin classification model has four primary classes.

### 6.1 Internal-Native Plugin
A plugin whose primary identity is internal to Nexa runtime.

Primary characteristics:
- optimized for Nexa runtime execution
- governed directly by Nexa plugin contract family
- may not need any MCP surface
- may exist entirely for internal execution discipline or internal node behavior

Examples:
- internal transformation plugins
- internal evaluation plugins tightly bound to Nexa runtime stages
- internal context-shaping plugins
- internal runtime utility plugins

### 6.2 MCP-Native Plugin
A plugin whose primary capability surface is natively modeled through MCP concepts.

Primary characteristics:
- external interoperability is primary
- tool/resource/prompt surface is central
- MCP-facing description is first-class
- still must satisfy Nexa loading, policy, and governance requirements when executed inside Nexa

Examples:
- external system connector plugins
- externally shared tool endpoints
- external resource bridge plugins
- prompt/workflow publication plugins

### 6.3 Hybrid Plugin
A plugin that has both:
- a strong Nexa-native internal runtime identity
- a meaningful MCP-compatible external surface

Primary characteristics:
- internal and external roles both matter
- requires explicit coexistence rules
- may expose MCP surfaces while preserving richer Nexa runtime semantics internally

Examples:
- a Nexa evaluation plugin that can also be exposed as an MCP tool
- an internal artifact-producing plugin with an MCP resource surface
- a workflow-oriented plugin whose preview or invocation surface is MCP-compatible

### 6.4 Adapter Plugin
A plugin or adapter layer whose purpose is translation.

Primary characteristics:
- bridges Nexa-native and MCP-native structures
- does not redefine canonical internal truth
- performs protocol/interface translation
- may be inbound, outbound, or bidirectional

Examples:
- Nexa plugin -> MCP server adapter
- MCP server -> Nexa plugin wrapper
- MCP resource surface -> Nexa context bridge
- MCP tool surface -> Nexa runtime invocation adapter

## 7. Canonical Classification Ownership Path

Classification must follow the same layered truth grammar already used elsewhere in the plugin family.

The official ownership path is:

1. Designer may propose classification at draft level
2. Builder validation/approval stage must approve, revise, or reject that proposal
3. approved classification must become artifact-visible truth through manifest embedding or manifest-linked reference
4. runtime loading/install may consume approved classification
5. runtime governance may constrain use, but must not silently rewrite approved classification truth

This means MCP classification is not:
- UI guesswork
- runtime-only inference
- registry-only overlay

It is approved plugin-family truth with a clear ownership path.

## 8. Canonical Classification Record

The classification structure must distinguish requested and approved truth.

PluginClassificationRecord
- plugin_id: string
- requested_class: enum(
    "internal_native",
    "mcp_native",
    "hybrid",
    "adapter"
  )
- approved_class: enum(
    "internal_native",
    "mcp_native",
    "hybrid",
    "adapter"
  )
- policy_version: string
- mcp_spec_baseline_version: string | null
- mcp_compatibility_level: enum(
    "none",
    "mcp_wrapped",
    "mcp_partial",
    "mcp_native"
  )
- runtime_authority_model: enum(
    "nexa_native",
    "nexa_native_with_mcp_surface",
    "mcp_surface_with_nexa_runtime_constraints"
  )
- exposed_mcp_capabilities: list[string]
- adapter_ref: string | null
- notes: string | null

Optional implementation fields:
- requested_by_stage_ref: string | null
- approved_by_stage_ref: string | null
- approval_basis_summary: string | null

Normative rules:
- requested_class and approved_class must not be collapsed into one unqualified field
- runtime and registry must consume approved truth, not proposal-only truth
- policy_version is mandatory because classification is a governed approval object
- mcp_spec_baseline_version should be recorded when MCP-facing compatibility meaning depends on a specific MCP baseline

## 9. MCP Compatibility Levels

The official compatibility levels are:

### 9.1 none
The plugin has no MCP-facing role.

### 9.2 mcp_wrapped
The plugin is not MCP-native,
but an adapter exposes selected MCP-compatible surfaces.

### 9.3 mcp_partial
The plugin supports some MCP-compatible surfaces,
but MCP is not its full primary identity.

### 9.4 mcp_native
The plugin is designed primarily around MCP-facing capability surfaces.


## 10. Classification Axis Interaction Matrix

The classification system intentionally keeps multiple independent axes:

- `plugin_category`
- `plugin_type`
- `requested_class`
- `approved_class`
- `mcp_compatibility_level`
- `runtime_authority_model`

These axes must not be collapsed into one composite enum.
Instead, legality and interaction rules must be explicit.

Minimum machine-readable legality table:

```yaml
classification_legality_rules:
  - when:
      approved_class: internal_native
    require:
      mcp_compatibility_level: [none, mcp_wrapped, mcp_partial]
      runtime_authority_model: [nexa_native, nexa_native_with_mcp_surface]
    forbid:
      mcp_compatibility_level: [mcp_native]
      runtime_authority_model: [mcp_surface_with_nexa_runtime_constraints]

  - when:
      approved_class: mcp_native
    require:
      mcp_compatibility_level: [mcp_native]
      runtime_authority_model: [mcp_surface_with_nexa_runtime_constraints]
    allow:
      plugin_type_required: true

  - when:
      approved_class: hybrid
    require:
      mcp_compatibility_level: [mcp_partial, mcp_native]
      runtime_authority_model:
        - nexa_native_with_mcp_surface
        - mcp_surface_with_nexa_runtime_constraints
    allow:
      plugin_type_required: true

  - when:
      approved_class: adapter
    require:
      mcp_compatibility_level: [mcp_wrapped, mcp_partial, mcp_native]
    forbid:
      adapter_ref_recursive: true
```

Interpretation rules:
- `plugin_category` remains the builder/artifact purpose axis
- `plugin_type` remains the runtime/platform-role axis
- classification legality must constrain, not replace, those existing axes
- builder validation should be able to enforce these combinations as structured rules rather than prose only

## 11. Canonical Rule for External-Facing Plugins

If a plugin's primary purpose is external system interoperability,
Nexa should prefer an MCP-compatible design unless there is a strong reason not to.

This applies especially when the plugin's visible capability is naturally expressible as:
- tools
- resources
- prompts

## 12. Canonical Rule for Internal Runtime Plugins

If a plugin's primary purpose is internal runtime participation,
Nexa must not force MCP-native modeling onto it by default.

Internal runtime plugins remain governed first by:
- Nexa runtime loading/install rules
- execution binding rules
- context I/O rules
- namespace policy rules
- runtime governance rules
- lifecycle rules

MCP may be added later through an adapter if useful.

## 13. Relationship to MCP Concepts

The current MCP specification defines servers as offering features such as:
- resources
- prompts
- tools

and clients may offer capabilities such as:
- sampling
- roots
- elicitation

MCP also includes protocol utilities such as:
- progress tracking
- cancellation
- error reporting
- logging

Nexa should use these concepts as interoperability guidance,
not as a wholesale replacement for its internal plugin lifecycle model.

## 14. Relationship to Nexa Plugin Contract Family

This document sits above the detailed Nexa plugin contract family and clarifies how MCP fits into that family.

The plugin contract family answers questions such as:
- how plugins are built
- how they are loaded
- how they are bound to runtime
- how they read/write context
- how they fail and recover
- how they are observed
- how they are governed
- how their lifecycle is modeled

This document answers:
- which plugin classes should or should not be primarily modeled as MCP-native

## 15. Relationship to Builder and Intake

Designer AI and Plugin Builder may propose or construct plugins that are:
- internal-native
- MCP-native
- hybrid
- adapter

But classification must be explicit in the builder-facing process.

The builder must not assume:
- every external-looking plugin is fully MCP-native
- every internal plugin must be exposed through MCP
- every MCP-compatible plugin is internally governed only by MCP


## 16. Relationship to Artifact / Manifest

Approved classification must become artifact-visible truth.

The canonical rule is:

- proposal-stage classification must not be used as runtime artifact truth
- approved classification must be embedded in, or explicitly referenced by, artifact/manifest truth
- runtime loading/install and registry summary layers must consume approved classification rather than raw proposal classification

This document therefore requires a paired manifest update so that approved MCP classification becomes visible at the artifact boundary.

## 17. Relationship to Runtime Loading / Installation

Runtime loading/install rules must remain able to distinguish classification.

Examples:
- an internal-native plugin may load with no MCP capability requirement
- an MCP-native plugin may require an MCP-facing capability manifest or adapter verification
- a hybrid plugin may require both Nexa runtime constraints and MCP-surface coherence checks
- an adapter plugin may require compatibility checks on both sides of the translation boundary

This document therefore requires a paired loading/install patch.
Classification must not affect loading/install behavior by implication only.
The loading/install contract must explicitly state how approved classification changes preflight behavior.

## 18. Relationship to Namespace Policy

MCP compatibility must not loosen Nexa namespace policy.

Even when a plugin is MCP-native or MCP-compatible:
- internal context reads remain governed
- internal context writes remain governed
- external target access remains explicit
- policy enforcement remains a Nexa responsibility inside Nexa runtime

Bridge rules mapping MCP capabilities to namespace/external-target policy are defined in `plugin_namespace_policy_contract.md` §15A.

## 19. Relationship to Observability and Governance

MCP compatibility must not erase internal runtime observability.

Nexa must still be able to observe:
- what the plugin did internally
- what external capability surface was used
- whether translation/adaptation occurred
- what failures happened
- what governance posture changed

A plugin being MCP-native does not exempt it from Nexa observability or governance.

## 20. Adapter Rules

Adapter layers must obey the following rules.

### 20.1 No truth replacement
Adapters translate surfaces.
They do not replace canonical Nexa runtime truth.

### 20.2 No silent policy widening
An adapter must not widen tool authority, context scope, or external target scope silently.

### 20.3 Explicit translation boundary
If a plugin is adapted into or out of MCP form,
that translation boundary should be explicit and inspectable.

### 20.4 Failure propagation
Adapter failures must remain observable as explicit failure states,
not vanish into generic external-protocol noise.

### 20.5 Transitional recursion stop
- adapter-of-adapter recursion is forbidden
- if `approved_class="adapter"`, then `adapter_ref` must be null
- a later family revision may reposition adapter as an architectural primitive rather than a plugin primary class

## 21. Recommended Default Strategy

The recommended default strategy for Nexa is:

1. Keep internal runtime plugin contracts as the canonical engine truth
2. Prefer MCP for external-facing interoperability surfaces
3. Use hybrid or adapter patterns when both worlds matter
4. Avoid forcing all plugins into one MCP-native mold
5. Preserve explicit classification in all builder/runtime/registry/governance layers

## 22. Explicitly Forbidden Patterns

The following patterns are forbidden.

### 22.1 MCP-by-default assumption
A plugin must not be treated as MCP-native unless classification says so.

### 22.2 Internal-runtime flattening
Nexa must not collapse internal runtime plugin identity into only MCP tool/resource/prompt vocabulary.

### 22.3 Silent adapter behavior
Translation between Nexa-native and MCP-facing forms must not happen invisibly.

### 22.4 Policy bypass through protocol translation
MCP compatibility must not be used as a reason to bypass internal policy or governance controls.

### 22.5 Ecosystem isolation by unnecessary custom protocol
For clearly external-facing plugins, Nexa should not insist on a bespoke surface when MCP is the rational interoperability choice.

## 23. Extensibility Rules

This contract must support future growth under the following rules.

### 23.1 New plugin classes may be added
if they remain explicit and do not blur current boundaries.

### 23.2 New MCP capability families may be supported
if they remain clearly separate from Nexa internal runtime truth.

### 23.3 New adapter forms may be added
if they preserve explicit translation boundaries.

### 23.4 New registry and builder metadata may be added
to track classification and compatibility more precisely.

## 24. Canonical Summary

The official Nexa position is:

- MCP is strategically important
- not all Nexa plugins should be modeled as MCP-native
- internal runtime truth remains governed by the Nexa plugin contract family
- external-facing interoperability plugins should usually prefer MCP-compatible design
- hybrid and adapter patterns are first-class solutions
- explicit classification is necessary to prevent architectural drift

## 25. Final Statement

Nexa should not choose between:
- "ignore MCP"
and
- "make everything MCP"

It should do something more precise:

keep Nexa-native runtime truth internally,
use MCP where interoperability is the primary goal,
and classify plugins explicitly so both systems remain coherent.
