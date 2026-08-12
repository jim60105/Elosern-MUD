# effect-context-validation Specification

## Purpose

TBD - created by archiving change fix-combat-effect-context-validation. Update Purpose after archive.

## Requirements

### Requirement: Effect handlers declare their required event context

Every registered effect handler SHALL declare the `event_context` keys it requires, as part of its registration metadata.

#### Scenario: Context requirements are declared per handler

- **WHEN** the `set_disguise` and `confer_skill_partial` handlers are registered
- **THEN** each declares its required context keys (`disguise`; `confer_skill_key`/`confer_scale`/`confer_trait_keys`)
