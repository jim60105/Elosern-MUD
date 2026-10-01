# npc-persona-offline-bundles Specification

## Purpose
Provide authored, coherent whole-card persona bundles for NPC roles and races, and a deterministic selection by stable identity, so an NPC without an authored profile can receive a complete compact card offline that is chosen once and never rerolled.

## Requirements

### Requirement: Offline persona bundles are authored whole cards grouped into pools
Offline persona bundles SHALL be immutable authored records, each holding a stable key, one complete compact NPC card that satisfies the card contract, and the race it is written for. Bundles SHALL be grouped into read-only pools: one pool per registered NPC role tier, and a generic pool for every race that no tier pool serves. Every pool SHALL hold at least two bundles, every bundle SHALL be eligible for its pool's race, no two bundles in one pool SHALL share a personality or speech-style text, and bundle cards SHALL carry empty hidden identity and social connection. Any violation SHALL fail import naming the pool and bundle. A card SHALL never be assembled from independently selected fragments.

#### Scenario: Every tier and race resolves to a pool of at least two voices
- **WHEN** the shipped pools are validated against the NPC tier and race registries
- **THEN** every tier and every race resolves to a pool holding at least two valid bundles

#### Scenario: A malformed bundle fails import by name
- **WHEN** a synthetic pool holds a bundle whose card is over the total budget or whose race differs from the pool's race
- **THEN** importing the bundle registry raises naming the pool and the bundle

#### Scenario: A one-voice pool is rejected
- **WHEN** a synthetic pool holds a single bundle
- **THEN** import fails naming the pool

### Requirement: Pool resolution prefers the role tier and falls back to the race
Resolving the offline pool for an NPC SHALL return the pool of its recorded role tier when that tier is registered and bound to the NPC's race, and otherwise the generic pool of the NPC's race. A race with no resolvable pool SHALL be a load error.

#### Scenario: A scene occupant resolves to its tier pool
- **WHEN** the pool is resolved for a human NPC whose recorded tier is `bandit`
- **THEN** the `bandit` pool is returned

#### Scenario: An NPC without a tier resolves to its race pool
- **WHEN** the pool is resolved for a beastfolk NPC with no recorded tier
- **THEN** the beastfolk generic pool is returned

### Requirement: Offline selection is deterministic by stable identity and persisted once
Selecting a bundle SHALL be a pure function of the pool key and a caller-supplied stable seed, identical across processes and Python versions, and SHALL return the chosen bundle key and its card without writing state. The same pool and seed SHALL always select the same bundle; distinct seeds SHALL be able to select different bundles of one pool. A caller SHALL persist the selected card once with `offline_bundle` provenance naming the pool and bundle, and SHALL never re-select for an NPC that already carries an initialized card.

#### Scenario: Distinct identities can receive different voices
- **WHEN** a synthetic two-bundle pool is selected with a fixed set of distinct seeds
- **THEN** the selections include both bundles, and each selected card's speech-style text is the specific authored text of its bundle

#### Scenario: Selection is stable across calls
- **WHEN** the same pool and seed are selected twice, including in a fresh interpreter
- **THEN** both calls return the same bundle key and card

#### Scenario: Selection writes nothing
- **WHEN** a bundle is selected
- **THEN** no persona or metadata record of any entity changes
