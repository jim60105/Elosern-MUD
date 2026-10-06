# monster-site-placement Specification

## Purpose
Author where species actually appear: deterministic regional ambient placement rules plus explicit
camps, nests, and boss sites with owned individuals, authored one-shot or in-game-time recoverable
lives, and reconciliation that never crosses ownership boundaries. Habitat tags constrain what may be
authored, never what spawns.

## Requirements

### Requirement: Ambient and site placement are frozen keyed lore data validated at construction
`world/lore/monster_placement.py` SHALL define frozen `AmbientPlacementRule` values (region key,
eligible variant keys, quantity, capacity, determinism parameters) and frozen `MonsterSite` values
(`key`, kind from the closed vocabulary `camp | nest | boss_site`, variant keys, host anchor or
coordinate, capacity, `one_shot` flag, and a recovery condition for recoverable sites drawn from a
closed in-game-time/approved-deterministic vocabulary), with module-level keyed registries following the
existing lore discipline: construction-time validation, idempotent startup mirror, no runtime mutation
from `world/lore/`. Validation SHALL reject an unknown region key, an unknown variant key, a placement
whose species' habitat tags are incompatible with the target habitat (an authoring-data error, since
tags constrain authoring only), a missing recovery condition on a non-one-shot site, and a recovery
condition outside the closed vocabulary.

#### Scenario: An unknown variant reference is rejected at import time
- **WHEN** a site or ambient rule names a variant key absent from the variant registry
- **THEN** registry construction raises a named placement-registry error and no partial registry is published

#### Scenario: Habitat-incompatible authoring fails at construction, not at runtime
- **WHEN** an authored site names a variant whose species' habitat tags do not include the site's habitat
- **THEN** placement-registry construction rejects it, and at runtime no spawn decision anywhere reads habitat tags

#### Scenario: Recovery must be expressible
- **WHEN** a site is authored as recoverable with no recovery condition, or with a free-text condition outside the closed vocabulary
- **THEN** registry construction raises the named error

### Requirement: Every placed individual carries its owner marker and reconciliation stays inside the owner domain
Individuals created by ambient placement SHALL carry the existing ambient ownership marker, and
individuals created by a site SHALL carry a persistent site-ownership marker naming its site key.
Ambient reconciliation SHALL act only on ambient-marked individuals; site reconciliation SHALL act only
on individuals marked for that site. Neither SHALL delete, move, replace, or modify a monster owned by
another owner — including quest-, story-, combat-session-, or other-site-owned individuals — and ambient
maintenance SHALL never resume, respawn, clear, or otherwise stand in for a site's lifecycle.

#### Scenario: Ambient cleanup leaves site-owned monsters untouched
- **WHEN** ambient reconciliation runs at a coordinate hosting a site-owned individual
- **THEN** the site-owned individual is neither deleted nor moved, and only ambient-marked individuals are reconciled

#### Scenario: Site recovery never reconciles ambient individuals
- **WHEN** a site's recovery or cleanup pass runs
- **THEN** it acts only on individuals carrying that site's marker, and ambient individuals in the same room are unchanged

#### Scenario: Quest-owned targets are foreign to both owners
- **WHEN** an individual bound to an accepted quest record stands inside a site's footprint and either owner reconciles
- **THEN** the quest-bound individual is untouched by both reconciliation passes

### Requirement: One-shot sites stay cleared and recoverable sites recover only on approved conditions
A site authored one-shot SHALL remain cleared after its individuals are defeated until an author-side
re-issue; no player action (re-entering a room, accepting a quest) and no elapsed wall-clock time SHALL
recover it. A recoverable site SHALL recover only when its registered in-game-clock condition or approved
deterministic condition is satisfied, evaluated by the `world/maps/` site owner through the existing
world-clock settlement seam. Recovery SHALL create fresh individuals with fresh persistent identities
through the construction owner; it SHALL NOT resurrect, re-bind, or reuse the defeated individuals'
identities. Whether a site has recovered SHALL be visible state, so quest republish decisions and site
lifecycle cannot contradict each other.

#### Scenario: A one-shot nest does not come back on its own
- **WHEN** a one-shot site's individuals are defeated and the in-game clock advances, the room is re-entered, and a quest is accepted
- **THEN** the site remains cleared and no individual is created for it

#### Scenario: A recoverable camp recovers at its in-game condition with fresh identities
- **WHEN** a recoverable site's in-game-time condition matures
- **THEN** its fresh individuals exist, each with a persistent identity distinct from every previously defeated individual of that site

#### Scenario: Clear state survives re-entry
- **WHEN** a cleared recoverable site whose condition has not matured is re-entered by the player
- **THEN** no individual appears and the cleared state is unchanged

### Requirement: Placement honors capacity and determinism
Ambient reconciliation SHALL maintain quantities up to, but never beyond, the authored regional quantity
and capacity, and SHALL create no individual whose species/variant differs from the rule's authored
variant set. Site passes SHALL respect site capacity. Ambient selection over a rule's variant set SHALL
be a pure deterministic function of coordinates and authored parameters — no RNG, no database state, no
wall clock — reusing the existing coordinate-hash discipline, and repeated reconciliation of unchanged
state SHALL be a no-op.

#### Scenario: Capacity is a ceiling, not a reshuffle
- **WHEN** a coordinate or site already holds its authored capacity of living individuals
- **THEN** reconciliation creates nothing and deletes nothing to "swap" individuals

#### Scenario: Same coordinate, same species selection
- **WHEN** ambient selection is evaluated twice for the same coordinate
- **THEN** the same variant is selected both times, across process restarts, with no random or clock input read

### Requirement: Placement decisions are boundary-observable through the facade
Ambient creation/removal decisions, site clearing, site recovery, and rejected recovery attempts SHALL
each emit one boundary info or warn event through the `world.observability` named-import facade with
`region`, `site`, `species`, `variant`, and coordinate context keys; player-facing prose SHALL NOT enter
logs, and reconciliation passes that change nothing SHALL stay silent.

#### Scenario: Recovery logs one decision event
- **WHEN** a recoverable site matures and repopulates
- **THEN** one boundary event names the site, its variant keys, and the clock context, and no prose text is logged

### Requirement: A site's living individuals are the quest layer's binding source and no quest may create or recover a site
The site owner SHALL expose a read that answers, for one authored site key, which of that site's own living
individuals currently stand and what the site's durable lifecycle state is. The read SHALL be pure: it
SHALL create, populate, recover, move, delete, or modify nothing, it SHALL emit no lifecycle decision event
(it decides nothing), and repeating it SHALL leave every surface equal. It SHALL answer for a world that is
not provisioned, for an unknown site key, for a never-populated site, and for a cleared site, without
treating any of those as a recovery opportunity. A quest clear-out SHALL take its bound set from that read
alone: neither acceptance nor the board SHALL populate, recover, or spawn an individual for a quest, and a
site's first population and its recovery SHALL remain the site owner's clock-settled lifecycle decisions.
Binding a quest to a site's individuals SHALL NOT change the site's ownership markers, its durable state,
or the number of individuals it owns.

#### Scenario: The read answers with the site's own living individuals
- **WHEN** a populated site's read is taken
- **THEN** it returns exactly the living individuals carrying that site's ownership marker, and no ambient, quest-owned, other-site-owned, or dead individual

#### Scenario: A cleared site offers no targets and stays cleared
- **WHEN** a cleared site's read is taken
- **THEN** it returns no living individual, and the site's durable state, its cleared-at tick, and every individual it owns are unchanged

#### Scenario: A never-populated site is not populated by the read
- **WHEN** a site the world has not yet populated is read
- **THEN** it returns no living individual and creates none, and the site remains in its unpopulated state until the world clock's settlement populates it

#### Scenario: A quest binding changes no site surface
- **WHEN** a quest binds a site's living individuals as its targets
- **THEN** each individual keeps its site ownership marker, the site's durable state is unchanged, and no individual is created or removed

#### Scenario: Reading twice changes nothing
- **WHEN** the read is taken twice in one process for the same site
- **THEN** both answers are equal and no persistent surface differs between them
