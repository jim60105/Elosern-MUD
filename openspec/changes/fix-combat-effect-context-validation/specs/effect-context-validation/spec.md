## ADDED Requirements

### Requirement: Effect handlers declare their required event context

Every registered effect handler SHALL declare the `event_context` keys it requires, as part of its registration metadata.

#### Scenario: Context requirements are declared per handler

- **WHEN** the `set_disguise` and `confer_skill_partial` handlers are registered
- **THEN** each declares its required context keys (`disguise`/`overrides`; `confer_skill_key`/`confer_scale`/`confer_trait_keys`)
