# Spec Delta

## REMOVED Requirements

### Requirement: Professions are one validated rulebook table with keyed frozen reads
**Reason**: Profession blueprints, expansion and implicit defaults are removed.
**Migration**: Use explicit capability declarations with complete per-capability configuration; no legacy reader or save migration.

### Requirement: Every malformed profession file is rejected by name before anything is cached
**Reason**: Profession blueprints, expansion and implicit defaults are removed.
**Migration**: Use explicit capability declarations with complete per-capability configuration; no legacy reader or save migration.

### Requirement: default_binding is a validated vocabulary consumed by the anchoring gate
**Reason**: Profession blueprints, expansion and implicit defaults are removed.
**Migration**: Use explicit capability declarations with complete per-capability configuration; no legacy reader or save migration.

### Requirement: The component-type vocabulary is contract-pinned to the component classes
**Reason**: Profession blueprints, expansion and implicit defaults are removed.
**Migration**: Use explicit capability declarations with complete per-capability configuration; no legacy reader or save migration.
