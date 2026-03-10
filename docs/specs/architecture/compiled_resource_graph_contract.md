Spec ID: compiled_resource_graph_contract
Version: 1.0.0
Status: Partial
Category: architecture
Depends On:

# Nexa Compiled Resource Graph Contract

## Purpose

ExecutionConfig is declarative.  
Before execution it is compiled into a Resource Graph.

ExecutionConfig → compile → CompiledResourceGraph → runtime execution

## Structure

resources: dict[str, ResourceNode]

dependencies: dict[str, set[str]]

dependents: dict[str, set[str]]

final_candidates: set[str]

## ResourceNode

id: resource identifier

type: prompt | provider | plugin

reads: context keys read

writes: context keys written

executor: callable used for execution

## Dependency Rule

A → B if

A.writes ∩ B.reads ≠ ∅

## Output Resolution

final output = produced keys − consumed keys