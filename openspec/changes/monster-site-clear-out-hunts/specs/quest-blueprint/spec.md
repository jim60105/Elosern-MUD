## MODIFIED Requirements

### Requirement: Registration validates every runtime-critical objective field
`register_quest_definition()` SHALL treat re-registering equal content under the same key as an
idempotent no-op and SHALL reject conflicting content under an existing key. It SHALL reject empty
stages, non-contiguous stage indices starting anywhere other than zero, non-positive quantities,
invalid destination shapes, unknown static location keys, and invalid objective parameters. DEFEAT
SHALL declare exactly one selector family: a known `monster_tier`; or `requires_bound_targets=True` with
no site key; or a bound clear-out over an authored site (`requires_bound_targets=True` together with a
known `site_key`, whose quantity SHALL NOT exceed that site's authored capacity); or the complete
regional species-hunt selector (a known region key, a known species key, and a non-empty
countable-variant tuple owned by that species). A partial hunt selector, a hunt combined with the tier or
with the bound selector, a site key without the bound flag, a site key combined with the tier or with the
hunt selector, and an unknown site key are each invalid. REACH SHALL declare
a destination; ESCORT SHALL declare a destination and SHALL be unable to complete until protected
runtime entities are bound. `deadline_hours` SHALL be either `None`, meaning no deadline, or a positive
integer.

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
- **WHEN** an ESCORT objective has no destination, a DEFEAT objective has no selector, or a quantity is
  zero
- **THEN** registration raises `QuestDefinitionError` rather than deferring failure to event handling

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

## ADDED Requirements

### Requirement: A site clear-out names an authored site and binds that site's own living individuals
A site clear-out objective SHALL name a key of the authored site registry and SHALL remain a hand-written
content form: the deterministic compile boundary SHALL NOT author a site key from a generative proposal,
and the stored payload SHALL round-trip the key with an absent-key default rather than inventing one.
Registration SHALL also reject a definition declaring a site key that another registered definition
already declares: two clear-outs over one site would bind the same living individuals, so each would
credit the same defeats.
The objective SHALL bind the site's own individuals — the site's authored variant set, placed at its
authored coordinate under its ownership marker — and SHALL NOT cause any individual to be spawned,
moved, populated, or recovered: a clear-out never becomes a second population owner. The bound set SHALL
be exactly the living individuals the site owns at binding time, so a later recovery's fresh individuals
are strangers to an existing binding and can only be bound by a clear-out issued after their creation.

#### Scenario: The selector names a registered site
- **WHEN** a site clear-out names an authored site key
- **THEN** registration accepts it, and the same definition with an unregistered site key is rejected before play

#### Scenario: The generative boundary cannot author a clear-out
- **WHEN** a compiled proposal's DEFEAT stage is mapped to a runtime objective
- **THEN** it carries no site key, and the stored payload of every generated quest decodes with the key absent

#### Scenario: A second clear-out over one site is rejected
- **WHEN** a definition declares a site key an already registered definition declares
- **THEN** registration raises `QuestDefinitionError` naming the colliding definition and the registry is unchanged

#### Scenario: The clear-out spawns nothing
- **WHEN** a clear-out's individuals are bound
- **THEN** the number of individuals the site owns is unchanged by the binding, and no ambient, quest-owned, or other-site-owned individual is touched

#### Scenario: A recovered site's newcomers are not an old clear-out's targets
- **WHEN** a clear-out's bound individuals are defeated and the site later recovers fresh individuals
- **THEN** the old record's bound set is unchanged, and only a clear-out issued after the recovery binds the newcomers
