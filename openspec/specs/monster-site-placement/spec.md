# monster-site-placement Specification

## Purpose
Author where species actually appear: deterministic regional ambient placement rules plus explicit
camps, nests, and boss sites with owned individuals, authored one-shot or in-game-time recoverable
lives, and reconciliation that never crosses ownership boundaries. Habitat tags constrain what may be
authored, never what spawns.

## Requirements

### Requirement: Ambient and site placement are frozen keyed lore data validated at construction
`world/lore/monster_placement.py` SHALL define frozen `AmbientPlacementRule` and `MonsterSite` values
held in module-level keyed registries following the existing lore discipline: construction-time
validation, idempotent startup mirror, no runtime mutation from `world/lore/`. Registry construction
SHALL reject invalid authoring data — unknown keys and recovery-condition violations — and never
publish a partial registry.

#### Scenario: An unknown variant reference is rejected at import time
- **WHEN** a site or ambient rule names a variant key absent from the variant registry
- **THEN** registry construction raises a named placement-registry error and no partial registry is published

#### Scenario: Habitat-incompatible authoring fails at construction, not at runtime
- **WHEN** an authored site names a variant whose species' habitat tags do not include the site's habitat
- **THEN** placement-registry construction rejects it, and at runtime no spawn decision anywhere reads habitat tags

#### Scenario: Recovery must be expressible
- **WHEN** a site is authored as recoverable with no recovery condition, or with a free-text condition outside the closed vocabulary
- **THEN** registry construction raises the named error

#### Scenario: Ambient rules are frozen values with the authored fields
- **WHEN** an `AmbientPlacementRule` is constructed
- **THEN** it is frozen and carries the region key, eligible variant keys, quantity, capacity, and determinism parameters

#### Scenario: Sites are frozen values with the authored fields
- **WHEN** a `MonsterSite` is constructed
- **THEN** it is frozen and carries `key`, a kind from the closed vocabulary `camp | nest | boss_site`, variant keys, a host anchor or coordinate, capacity, the `one_shot` flag, and — for recoverable sites — a recovery condition drawn from a closed in-game-time/approved-deterministic vocabulary

#### Scenario: An unknown region reference is rejected at construction
- **WHEN** an ambient rule names a region key absent from the region registry
- **THEN** registry construction raises the named placement-registry error and no partial registry is published

### Requirement: Every placed individual carries its owner marker and reconciliation stays inside the owner domain
Individuals created by ambient placement SHALL carry the existing ambient ownership marker, and
individuals created by a site SHALL carry a persistent site-ownership marker naming its site key.
Each owner's reconciliation SHALL act only on individuals bearing its own marker and SHALL never
delete, move, replace, or modify an individual owned by another owner.

#### Scenario: Ambient cleanup leaves site-owned monsters untouched
- **WHEN** ambient reconciliation runs at a coordinate hosting a site-owned individual
- **THEN** the site-owned individual is neither deleted nor moved, and only ambient-marked individuals are reconciled

#### Scenario: Site recovery never reconciles ambient individuals
- **WHEN** a site's recovery or cleanup pass runs
- **THEN** it acts only on individuals carrying that site's marker, and ambient individuals in the same room are unchanged

#### Scenario: Quest-owned targets are foreign to both owners
- **WHEN** an individual bound to an accepted quest record stands inside a site's footprint and either owner reconciles
- **THEN** the quest-bound individual is untouched by both reconciliation passes

#### Scenario: All foreign owners are protected
- **WHEN** either reconciliation pass encounters an individual owned by a quest, story, combat session, or another site
- **THEN** that individual is not deleted, moved, replaced, or modified

#### Scenario: Ambient maintenance never stands in for site lifecycle
- **WHEN** ambient maintenance runs
- **THEN** it never resumes, respawns, clears, or otherwise stands in for a site's lifecycle

### Requirement: One-shot sites stay cleared and recoverable sites recover only on approved conditions
A site authored one-shot SHALL remain cleared after its individuals are defeated until an author-side
re-issue. A recoverable site SHALL recover only when its registered in-game-clock condition or approved
deterministic condition is satisfied, evaluated by the `world/maps/` site owner through the existing
world-clock settlement seam, creating fresh individuals with fresh persistent identities through the
construction owner. Whether a site has recovered SHALL be visible state.

#### Scenario: A one-shot nest does not come back on its own
- **WHEN** a one-shot site's individuals are defeated and the in-game clock advances, the room is re-entered, and a quest is accepted
- **THEN** the site remains cleared and no individual is created for it

#### Scenario: A recoverable camp recovers at its in-game condition with fresh identities
- **WHEN** a recoverable site's in-game-time condition matures
- **THEN** its fresh individuals exist, each with a persistent identity distinct from every previously defeated individual of that site

#### Scenario: Clear state survives re-entry
- **WHEN** a cleared recoverable site whose condition has not matured is re-entered by the player
- **THEN** no individual appears and the cleared state is unchanged

#### Scenario: Wall-clock time never revives a one-shot site
- **WHEN** wall-clock time elapses after a one-shot site's individuals are defeated, with no author-side re-issue
- **THEN** the site remains cleared regardless of how much real time has passed

#### Scenario: Recovery never reuses defeated identities
- **WHEN** a recoverable site recovers after its previous individuals were defeated
- **THEN** none of the defeated individuals is resurrected, re-bound to the site, or reused; every standing individual has a fresh persistent identity

#### Scenario: Recovery state is visible to the quest layer
- **WHEN** the quest layer consults whether a cleared recoverable site has recovered
- **THEN** it reads the site's visible recovery state rather than inferring it, so republish decisions and site lifecycle agree

### Requirement: Placement honors capacity and determinism
Ambient reconciliation SHALL maintain quantities up to, but never beyond, the authored regional quantity
and capacity, and site passes SHALL respect site capacity. Ambient selection SHALL be a pure
deterministic function of coordinates and authored parameters, and repeated reconciliation of unchanged
state SHALL be a no-op.

#### Scenario: Capacity is a ceiling, not a reshuffle
- **WHEN** a coordinate or site already holds its authored capacity of living individuals
- **THEN** reconciliation creates nothing and deletes nothing to "swap" individuals

#### Scenario: Same coordinate, same species selection
- **WHEN** ambient selection is evaluated twice for the same coordinate
- **THEN** the same variant is selected both times, across process restarts, with no random or clock input read

#### Scenario: Selection stays inside the authored variant set
- **WHEN** ambient reconciliation creates an individual for a rule
- **THEN** the individual's species/variant is one of the rule's authored variant set

#### Scenario: Determinism reuses the coordinate-hash discipline
- **WHEN** ambient selection is evaluated
- **THEN** it reads no RNG, no database state, and no wall clock, reusing the existing coordinate-hash discipline

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
SHALL create, populate, recover, move, delete, or modify nothing and SHALL emit no lifecycle decision event
(it decides nothing).

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

#### Scenario: A quest clear-out binds only from the site read
- **WHEN** a quest needs its bound set of targets
- **THEN** it takes that set from this read alone, and neither quest acceptance nor the quest board populates, recovers, or spawns an individual for the quest

#### Scenario: Site population and recovery stay the site owner's decisions
- **WHEN** a site is first populated or later recovers
- **THEN** the change is the site owner's clock-settled lifecycle decision, never a quest-driven action

#### Scenario: An unprovisioned world or unknown site key is answered without side effects
- **WHEN** the read is taken for a world that is not provisioned, or for a site key absent from the registry
- **THEN** it answers without treating either case as a recovery opportunity, and no individual or site surface changes
