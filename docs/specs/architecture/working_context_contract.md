Spec ID: working_context_contract
Version: 1.0.0
Status: Partial
Category: architecture
Depends On:

# Nexa Working Context Contract

## Purpose
The Working Context is the shared data space used by all execution resources inside a Node.

## Principle
All resources interact through the context:

reads context → transforms → writes context

## Structure
<context-domain>.<resource-id>.<field>

Domains:
- input
- prompt
- provider
- plugin
- system
- output

Example:
input.text  
prompt.main.rendered  
provider.openai.output  
plugin.search.results  
output.value

## Rules

1. Resources must declare reads and writes.
2. Context is the only communication channel between resources.
3. Runtime is responsible for integrity and final output resolution.