Spec ID: context_key_schema
Version: 1.0.0
Status: Partial
Category: architecture
Depends On:

# Nexa Context Key Schema

<context-domain>.<resource-id>.<field>

Example:

input.text  
prompt.summary.rendered  
provider.openai.output  
plugin.format.text  
output.value

## Domains

input  
User or external inputs.

prompt  
Rendered prompt outputs.

provider  
AI provider outputs.

plugin  
Plugin execution results.

system  
Runtime internal values.

output  
Final node output.

## Benefits

- deterministic dependency graph
- readable execution traces
- safe namespace isolation