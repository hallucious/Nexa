# Circuit Patch Contract v0.1

## 1. Purpose

This contract defines the canonical patch format used to transform:
- an existing circuit/savefile
or
- a new draft target

into
- a proposed next circuit state

A patch is a **proposal**, not a silent mutation.

## 2. Core Principles

1. Patch must be explicit.
2. Patch must be previewable.
3. Patch must be validator-checkable.
4. Patch must be bounded in scope.
5. Patch must not contain hidden runtime mutations.

## 3. Patch Plan Schema

```text
CircuitPatchPlan
- patch_id
- patch_mode
- target_savefile_ref
- target_circuit_ref
- based_on_revision
- summary
- intent_ref
- change_scope
- operations
- dependency_effects
- output_effects
- risk_report
- reversibility
- preview_requirements
- validation_requirements
```

## 4. Change Scope

```text
ChangeScope
- scope_level: minimal | bounded | broad
- touch_mode: read_only | append_only | structural_edit | destructive_edit
- touched_nodes
- touched_edges
- touched_outputs
- touched_metadata
```

## 5. Patch Operations

```text
PatchOperation
- op_id
- op_type
- target_ref
- payload
- rationale
- depends_on_ops
```

Canonical operation families:
- create_node
- delete_node
- update_node_metadata
- replace_node_component
- set_node_prompt
- set_node_provider
- attach_node_plugin
- detach_node_plugin
- connect_nodes
- disconnect_nodes
- insert_node_between
- move_output_binding
- define_output_binding
- remove_output_binding
- set_parameter
- rename_node
- annotate_node
- create_subgraph
- delete_subgraph

## 6. Dependency Effect Report

```text
DependencyEffectReport
- affected_upstream_nodes
- affected_downstream_nodes
- broken_paths_if_unapplied
- newly_created_paths
- removed_paths
- dependency_risks
```

## 7. Output Effect Report

```text
OutputEffectReport
- previous_outputs
- proposed_outputs
- added_outputs
- removed_outputs
- modified_outputs
- output_risks
```

## 8. Patch Risk Report

```text
PatchRiskReport
- risks
- requires_confirmation
- blocking_risks
```

## 9. Reversibility

```text
ReversibilitySpec
- reversible
- rollback_strategy
- rollback_requirements
- destructive_ops_present
```

## 10. Invariants

- no hidden mutation
- no implicit output change
- no silent destructive edit
- no unresolved dependency commit
- no contract-layer violation

## 11. Decision

Intent -> PatchPlan -> Preview -> Validation -> Commit

Direct savefile mutation is forbidden.
PatchPlan is the canonical mutation unit.
