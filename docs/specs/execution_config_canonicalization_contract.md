# ExecutionConfig Canonicalization Contract v1

ExecutionConfig ID is the hash of canonical execution meaning.

Included fields:
- config_schema_version
- inputs
- pre_plugins
- prompt_ref
- provider_ref
- post_plugins
- validation_rules
- output_mapping
- policy
- runtime_config.execution

Excluded fields:
- config_id
- label
- description
- notes
- created_at
- updated_at
- version
- runtime_config.metadata

Canonicalization rules:
- sort keys
- remove whitespace
- drop null fields
- preserve list order
- keep empty lists/objects

ID format:

    ec_<short_sha256>
