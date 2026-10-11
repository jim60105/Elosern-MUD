# Spec Delta

## MODIFIED Requirements

### Requirement: Registration validates every runtime-critical objective field
Registration SHALL retain immutable contiguous stages, positive quantity, deadline validation, idempotent equal registration and conflicting-content refusal. DEFEAT SHALL retain its closed mutually exclusive selector families and registry/quantity checks. REACH SHALL require an existing supported destination. ESCORT SHALL declare quantity one, a nonempty exact protected-role set, and exactly one closed completion discriminator `destination` or `rendezvous`. Destination mode SHALL use an existing anchor, XYZ or bound-instance locator and carry no rendezvous fields. Rendezvous SHALL declare nonempty exact meeting-role references and any required validated typed relation, with no destination requirement or incompatible destination fields. Definitions SHALL remain deeply immutable and JSON-safe through compilation/restoration. Other objective families SHALL reject escort-only fields.

#### Scenario: Destination and rendezvous definitions register
- **WHEN** two synthetic definitions declare complete destination and rendezvous contracts respectively
- **THEN** each registers and round-trips its exact role references and closed predicate without conflating quest classification and objective kind

#### Scenario: Missing or mixed predicates are rejected
- **WHEN** an escort omits its discriminator, declares both completion modes, omits a required role, mixes destination and rendezvous fields, or has quantity two
- **THEN** registration rejects before mutation with a named definition error

#### Scenario: Existing objective validation remains intact
- **WHEN** a definition has a noncontiguous stage, invalid deadline, unknown locator or DEFEAT selector, overlapping selector families, or impossible bound-target quantity
- **THEN** registration raises the existing definition error and retains the registry unchanged

#### Scenario: Equal content remains idempotent
- **WHEN** equal content is re-registered and conflicting content is then submitted under the same key
- **THEN** equal content is a no-op and conflicting content refuses without replacement

#### Scenario: A complete hand-written definition registers
- **WHEN** a definition has contiguous stages and every objective supplies its required typed fields
- **THEN** `QUEST_DEFINITION_REGISTRY[definition.key]` is that immutable definition

#### Scenario: Non-contiguous stages are rejected
- **WHEN** stages carry indices 0 and 2
- **THEN** registration raises `QuestDefinitionError` and leaves the registry unchanged

#### Scenario: Equal registration is idempotent and conflicting registration is rejected
- **WHEN** equal content is registered twice and different content is then registered under the same key
- **THEN** the equal registration is a no-op, the conflicting registration raises
  `QuestDefinitionError`, and the original definition remains registered

#### Scenario: Objective fields are validated before play
- **WHEN** an ESCORT objective has no complete discriminator-specific predicate/protected roles, a DEFEAT selector is absent, or quantity is zero
- **THEN** registration raises the existing definition error before event handling

#### Scenario: Structural field validation happens at registration
- **WHEN** a definition has empty stages, non-contiguous stage indices starting anywhere other than
  zero, a non-positive quantity, an invalid destination shape, an unknown static location key, or
  invalid objective parameters
- **THEN** registration raises `QuestDefinitionError` and leaves the registry unchanged

#### Scenario: A complete site clear-out registers
- **WHEN** a DEFEAT objective declares `requires_bound_targets=True`, a registered site key, and a quantity at or below that site's capacity
- **THEN** the definition registers and the selector is preserved unchanged and deeply immutable

#### Scenario: A site key without the bound flag is rejected
- **WHEN** a DEFEAT objective declares a site key without `requires_bound_targets=True`
- **THEN** registration raises `QuestDefinitionError` and the registry is unchanged

#### Scenario: A site key beside another selector family is rejected
- **WHEN** a DEFEAT objective declares a site key together with `monster_tier` or with the regional species-hunt selector
- **THEN** registration raises `QuestDefinitionError`

#### Scenario: A quantity beyond the site's capacity is rejected
- **WHEN** a site clear-out declares more targets than the authored site holds
- **THEN** registration raises `QuestDefinitionError`, because no acceptance could ever bind that many

#### Scenario: Deadline None has one meaning
- **WHEN** a definition registers with `deadline_hours=None`
- **THEN** acceptance creates no deadline and no implicit default is applied

#### Scenario: A partial hunt selector is rejected
- **WHEN** a DEFEAT objective supplies a species key without a region key, or a species/variant pair without any countable variant
- **THEN** registration raises `QuestDefinitionError` and the registry is unchanged

#### Scenario: The four DEFEAT selector families
- **WHEN** DEFEAT objective selectors are enumerated for validity
- **THEN** exactly one family must be declared: a known `monster_tier`; or `requires_bound_targets=True`
  with no site key; or a bound clear-out over an authored site (`requires_bound_targets=True` together
  with a known `site_key`, whose quantity SHALL NOT exceed that site's authored capacity); or the
  complete regional species-hunt selector (a known region key, a known species key, and a non-empty
  countable-variant tuple owned by that species)

#### Scenario: A hunt beside the bound selector is rejected
- **WHEN** a DEFEAT objective combines the regional species-hunt selector with `requires_bound_targets=True`
- **THEN** registration raises `QuestDefinitionError`

#### Scenario: A site key beside the hunt selector is rejected
- **WHEN** a DEFEAT objective declares a site key together with the regional species-hunt selector
- **THEN** registration raises `QuestDefinitionError`

#### Scenario: An unknown site key is rejected
- **WHEN** a DEFEAT objective declares a site key that is not a registered authored site
- **THEN** registration raises `QuestDefinitionError`

#### Scenario: REACH and ESCORT must declare a destination
- **WHEN** REACH omits its destination, destination-mode ESCORT omits its locator, or rendezvous-mode ESCORT omits its meeting roles
- **THEN** registration rejects; a complete rendezvous needs no fixed destination, and every escort still needs exact protected bindings

### Requirement: ESCORT quests require a bound protected entity path
Generated escort publication SHALL remain refused until this change's production acceptance, exact role binding, actual movement evaluation and settlement flow is implemented and proved. Thereafter every proposal/service, semantic validation, deterministic compilation and generated registration boundary SHALL require the complete protected-role/completion contract and a real executable binding path. Directly constructed compiled values SHALL receive the same check. Unsupported templates SHALL remain refused without fabricated nearby NPCs, a special-case family payload or relabeled objective.

#### Scenario: Unsupported request is refused before transport
- **WHEN** `server/ai_director_service.py` receives an escort request lacking a supported complete role-binding context/template
- **THEN** `EscortUnavailableError` is surfaced before transport work and no registration or actor creation occurs

#### Scenario: Supported generated escort executes through real owners
- **WHEN** a complete synthetic package passes the implemented service/semantic/compiler/registration path and its authorized offer is accepted, moved and completed
- **THEN** the exact protected NPC joins temporarily, the real predicate completes the record, registered settlement pays once and reload preserves the terminal result

#### Scenario: Every rejection boundary rejects incomplete contracts
- **WHEN** a missing protected path or ambiguous completion payload is presented separately to semantic validation, compiler and generated registration, including a forged compiled object
- **THEN** each reports its named rejection before durable or registry publication

#### Scenario: Unbindable ESCORT proposal is rejected

- **WHEN** a proposal's ESCORT stage has no production path to bind a protected entity (e.g. a permanent location with no NPC requirement)
- **THEN** the proposal is rejected and never reaches the guild board

#### Scenario: Quantity-one ESCORT is still rejected without a binding path

- **WHEN** a proposal declares an ESCORT objective with `quantity: 1` but no protected-entity binding path
- **THEN** the proposal is rejected at validation and no quest is registered

#### Scenario: Currently, ESCORT requests are refused with a clear message
- **WHEN** an escort request lacks the complete implemented protected-role/completion path
- **THEN** the existing clear named refusal registers no quest; complete proved contracts use the owning flow
