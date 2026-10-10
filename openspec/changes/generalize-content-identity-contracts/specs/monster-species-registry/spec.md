# Spec Delta

## REMOVED Requirements

### Requirement: Numeric combat profiles and danger grades are balance-gated slots, never invented values
**Reason**: Content identity belongs to authored data; general behavior is retained.
**Migration**: Use Authored profile requirements are declared per variant. Retarget substantive tests in this change.

### Requirement: Special abilities are narrative boundaries with a named mechanics prerequisite, never fake skills
**Reason**: Content identity belongs to authored data; general behavior is retained.
**Migration**: Use Narrative and executable monster configurations remain separate. Retarget substantive tests in this change.

### Requirement: Approved bestiary narrative lands as zh-TW display strings and synchronizes idempotently
**Reason**: Content identity belongs to authored data; general behavior is retained.
**Migration**: Use Authored monster narratives synchronize without a fixed roster. Retarget substantive tests in this change.

### Requirement: The approved first-batch profiles and grades are user-approved literals
**Reason**: Content identity belongs to authored data; general behavior is retained.
**Migration**: Use Shipped profile completeness follows authored declarations. Retarget substantive tests in this change.

## ADDED Requirements

### Requirement: Authored profile requirements are declared per variant
Combat profiles SHALL retain complete explicit seven-field records or optional absence, valid authored grades and established tier/grade checks. Whether a shipped variant requires a populated profile and grade SHALL be declared in its registry data. Required records SHALL reject absence; optional absence SHALL retain the existing individual-construction fallback semantics. Names, prose and other variants SHALL infer no values.

#### Scenario: Complete required rows
- **WHEN** every shipped variant is checked from its profile-required declaration
- **THEN** required profiles have all seven typed fields and a valid grade; optional None is absence and only construction may use its reported tier fallback

#### Scenario: Valid content edit
- **WHEN** a valid variant is added, renamed or retired together with its references
- **THEN** integrity follows the registry without changing a named roster in the spec or tests; established bounds remain unchanged

#### Scenario: Live state
- **WHEN** an existing individual reloads after a registry edit
- **THEN** identity and stored bases/kit/current gauges are preserved without automatic migration or refill

### Requirement: Narrative and executable monster configurations remain separate
Executable abilities SHALL require authored validated skill kits and behavior references through the shared engine. Rows with no delivered kit SHALL retain innate actions and tier-default behavior. Narrated abilities SHALL grant no ownership, resources or effects. Delivery status SHALL follow the authored kit data without a species allowlist, and future executable content SHALL require its own owning implementation.

#### Scenario: No fake seam
- **WHEN** a kit-less row has ecological ability text
- **THEN** no runtime effect or owned skill is inferred; configured kits validate through the same shared engine

#### Scenario: Delivered identity edit
- **WHEN** a configured species or variant display is renamed
- **THEN** its stable-key kit binding remains usable and player eligibility remains unchanged

### Requirement: Authored monster narratives synchronize without a fixed roster
Shipped species and variants SHALL carry non-empty public Traditional Chinese narrative fields and stable identities, with registry membership as the content authority. Synchronization SHALL mirror the authored registries idempotently through the observability facade and SHALL leave runtime monsters, rooms, quests and art untouched. Documentation SHALL satisfy the keyed public-content relationship contract without fixing species counts or narrative sentences.

#### Scenario: Idempotent entity-safe sync
- **WHEN** startup synchronization runs twice with runtime entities present
- **THEN** mirror state and object counts are unchanged after the second run and runtime monsters/rooms/quests/art remain unchanged; one registry-scoped facade boundary event is emitted per step

### Requirement: Shipped profile completeness follows authored declarations
Every variant declared profile-required SHALL ship a complete explicit profile and valid grade. All shipped rows SHALL satisfy identity/default membership and independent tier-axis/grade constraints; MP/SP SHALL remain explicit authored pools. Ability-kit delivery SHALL remain independent of profile completeness. New construction SHALL use current declarations without baked multipliers, and registry edits SHALL preserve live state.

#### Scenario: Complete required rows
- **WHEN** every shipped variant is checked from its profile-required declaration
- **THEN** required profiles have all seven typed fields and a valid grade; optional None is absence and only construction may use its reported tier fallback

#### Scenario: Valid content edit
- **WHEN** a valid variant is added, renamed or retired together with its references
- **THEN** integrity follows the registry without changing a named roster in the spec or tests; established bounds remain unchanged

#### Scenario: Live state
- **WHEN** an existing individual reloads after a registry edit
- **THEN** identity and stored bases/kit/current gauges are preserved without automatic migration or refill

## MODIFIED Requirements

### Requirement: Variant skill kits and behavior references are immutable authored configuration
Variants SHALL optionally carry ordered active/passive skill keys and a behavior-profile reference. Referenced skills SHALL resolve with matching kinds, compatible identity and usable prerequisites/effects; behavior references SHALL resolve in the existing behavior vocabulary before individual persistence.

#### Scenario: Invalid configuration creates nothing
- **WHEN** a variant references an unknown skill/profile, wrong kind, identity-ineligible skill, unusable prerequisite chain or unavailable effect
- **THEN** formal construction fails before persistence with no partial ownership/configuration

#### Scenario: No invented progression
- **WHEN** a synthetic variant authors a prerequisite-free active kit
- **THEN** its declared active order precedes innate actions without fabricated prerequisites or passives

