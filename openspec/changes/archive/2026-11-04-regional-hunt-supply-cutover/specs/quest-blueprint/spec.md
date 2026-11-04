# Spec Delta

## MODIFIED Requirements

### Requirement: Species-hunt objectives carry a validated region/species/variant selector
`QuestObjective` SHALL support the approved regional species-hunt semantics as a deterministic, deeply
immutable selector: a region key naming a key of `WILDERNESS_REGION_REGISTRY`, a species key naming a
key of `MONSTER_SPECIES_REGISTRY`, a positive quantity, and a non-empty tuple of countable variant
keys owned by that species. Display names SHALL NOT participate in selector resolution.

#### Scenario: A valid hunt registers
- **WHEN** a definition's DEFEAT stage declares region, species, quantity, and countable variant keys all owned by that species including at least one ordinary variant
- **THEN** the definition registers and the selector is preserved unchanged and deeply immutable

#### Scenario: A foreign variant key is rejected
- **WHEN** a hunt's countable variants include a variant owned by a different species
- **THEN** registration raises `QuestDefinitionError` and the registry is unchanged

#### Scenario: An unknown region or species key is rejected
- **WHEN** a hunt names a region key absent from `WILDERNESS_REGION_REGISTRY` or a species key absent
  from `MONSTER_SPECIES_REGISTRY`
- **THEN** registration raises `QuestDefinitionError`

#### Scenario: Two selectors at once is rejected
- **WHEN** a hunt objective also declares `monster_tier` or `requires_bound_targets=True`
- **THEN** registration raises `QuestDefinitionError`

#### Scenario: Names are never selectors
- **WHEN** a hunt is authored with a species display name instead of a species key
- **THEN** registration rejects it: only the shared stable-key form is a valid selector

#### Scenario: A hunt with no ordinary baseline variant is rejected
- **WHEN** a hunt's countable variants include no ordinary baseline variant of that species
- **THEN** registration raises `QuestDefinitionError`, because the selector must include an ordinary eligible variant with a lawful authored source, without guaranteeing current living supply

#### Scenario: Bulk tier sweeps are not expressible
- **WHEN** content attempts to represent an ordinary hunt as "count every variant of every species in
  a tier"
- **THEN** no selector form represents it

## REMOVED Requirements

### Requirement: Published regional species hunts are legally provisionable in their authored region
**Reason**: Immediate provisionability and one-cell quantity ceilings are explicitly removed in favor of source legality without current-supply guarantees.

**Migration**: Cut all callers and substantively matching test annotations to the replacement contract using tool-generated canonical IDs; retain no legacy behavior, alias or data migration.

## ADDED Requirements

### Requirement: Published regional hunts require lawful authored sources
Published regional species hunts SHALL reference valid region/species/variant selectors and at least one lawful authored ecological or explicit supply source, without limiting total quantity to one cell's current or potential supply.

#### Scenario: Quantity spans encounters
- **WHEN** a valid source-backed hunt quantity exceeds one cell, site or wave quantity
- **THEN** publication accepts it without promising immediate targets or completion before its existing deadline

#### Scenario: No lawful source
- **WHEN** a selector names no permitted ecological or explicit authored source
- **THEN** publication rejects without promoting habitat prose, visual examples or unknown species to supply

#### Scenario: Current shortage
- **WHEN** a lawful source currently has zero living targets or blocked automatic headroom
- **THEN** the definition remains valid and acceptance does not invoke provisioning

