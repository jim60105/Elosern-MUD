# effect-context-validation Specification

## Purpose

Requires every registered effect handler to declare the event_context keys it needs as part of its registration metadata, making required handler context explicit at registration time.

## Requirements

### Requirement: Effect handlers declare their required event context

Every registered effect handler SHALL declare the `event_context` keys it requires, as part of its
registration metadata. A handler that derives everything it needs from the actor, the targets, the
skill's own declared policy and the lore registries SHALL declare an EMPTY required set, so preflight
and the shared preview never advertise and then refuse it.

#### Scenario: Context requirements are declared per handler

- **WHEN** an effect handler that genuinely needs caller-supplied material is registered
- **THEN** it declares exactly the `event_context` keys it reads

#### Scenario: The disguise handler requires no context

- **WHEN** the `set_disguise` handler is registered
- **THEN** it declares an empty required set, because the veil's values are derived from the race
  registry rather than supplied by a caller

#### Scenario: A disguise skill is not rejected for missing context

- **WHEN** the shared action preview is asked about the disguise skill on an entity that owns it, with
  an `event_context` carrying no `disguise` key
- **THEN** the preview reports no missing-effect-context failure

#### Scenario: The conferral handlers require no context

- **WHEN** the `confer_skill_partial` and `confer_growth_rate` handlers are registered
- **THEN** each declares an empty required set, because the scale comes from the skill's own
  per-occurrence policy and the conferred set is derived from the caster's direct ownership

#### Scenario: A conferral skill is not rejected for missing context

- **WHEN** the shared action preview is asked about a conferral skill on an entity that owns it, with
  an `event_context` carrying no conferral keys
- **THEN** the preview reports no missing-effect-context failure
