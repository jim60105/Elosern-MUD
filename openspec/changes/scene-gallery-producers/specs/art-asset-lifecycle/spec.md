## ADDED Requirements

### Requirement: Startup synchronization requests gallery art for every registered scene and species
`world/art/service.py::art_sync_all()` SHALL be called from
`server/conf/at_server_startstop.py::at_server_start` and SHALL cover every entry of
`SCENE_ARCHETYPE_REGISTRY` and every registered visual species (species-keyed monster subjects),
routing each subject by whether its kind declares a gallery.

#### Scenario: Every registered subject has a record after startup sync
- **WHEN** startup art synchronization runs against a fresh database
- **THEN** each scene archetype and each visual species with no card, in-flight job or satisfying official default receives one gallery request, and no classic scene or monster record is created

#### Scenario: A seed-carded tier survives the ordered startup unchanged
- **WHEN** the startup steps run in catalog order (prune, then seed synchronization, then this
  synchronization) with a seed image present for a registered visual species, and the queue is later drained
- **THEN** no gallery generation is requested for that species and its seed card and stored file are never replaced

#### Scenario: Sync leaves existing pending, in-progress, and done records untouched
- **WHEN** `art_sync_all()` runs after records were already created, claimed, or completed
- **THEN** the existing `pending`, `in_progress`, and `done` records are not reset, not duplicated, and
  not overwritten

#### Scenario: A pre-existing classic monster record is left alone
- **WHEN** startup synchronization encounters a valid classic species record or a retired tier record
- **THEN** valid species output remains read-only and resolvable; retired tier records are never applied, served, requeued or converted into species records

#### Scenario: Duplicate records for one subject are consolidated
- **WHEN** startup sync finds more than one record for the same subject key
- **THEN** exactly one record remains (the most advanced) and the rest are removed

#### Scenario: A monster gallery request failure never aborts startup
- **WHEN** a monster visual species's gallery request raises during startup synchronization
- **THEN** a bounded diagnostic is logged, the remaining subjects still synchronize, and startup completes

#### Scenario: A carded scene requests nothing
- **WHEN** startup synchronization meets a scene archetype whose gallery already holds a card or an in-flight job
- **THEN** no gallery request is made for it and the sync is idempotent

#### Scenario: Records are created only under the queue lock
- **WHEN** the sync needs to create a record for a subject that has none
- **THEN** the record is created only through an atomic find-or-create under the queue lock, so
  per-subject uniqueness holds

#### Scenario: A gallery-kind subject routes through the gallery request
- **WHEN** `art_sync_all()` ensures a subject whose kind declares a gallery — the scene kind and the species-keyed monster kind
- **THEN** it routes through the gallery generation request under the shared automatic-generation
  guard, and startup does not create a classic asset record for it

#### Scenario: Pre-existing classic monster records require no migration
- **WHEN** startup encounters old tier-keyed classic monster records
- **THEN** they remain unreachable under current membership validation; no compatibility path or migration makes them usable

#### Scenario: Any startup synchronization failure stays bounded
- **WHEN** any failure occurs during startup synchronization
- **THEN** it stays bounded and never aborts startup

#### Scenario: Seed synchronization and the orphan prune run first
- **WHEN** the startup steps run in order
- **THEN** the gallery orphan prune and the bulk seed synchronization run BEFORE this
  synchronization, so a seed card already occupies a subject's gallery — and the prune has already
  swept — before any automatic gallery request is enqueued; an operator seed card is therefore never
  displaced by a startup-time generation


## MODIFIED Requirements

### Requirement: Successful room entry ensures the scene asset for a validated archetype
On successful entry of a room whose class carries `SceneArchetypeMixin`, the art lifecycle SHALL call
`ensure_scene_asset()` for the room's validated `scene_archetype`, covering dynamic registry content
added after startup. A room with a `None` or unresolvable archetype SHALL be a side-effect-free no-op.

#### Scenario: Entering a scene-bearing room ensures its asset
- **WHEN** a player enters a grid or instance room whose `scene_archetype` resolves in the registry
- **THEN** the scene subject's gallery is ensured through the shared automatic-generation guard: one
  gallery request when it holds no card and no in-flight job, nothing otherwise, and no classic record
  is created

#### Scenario: A room without a resolvable archetype is a no-op
- **WHEN** a player enters a room with a `None` or unresolvable `scene_archetype`
- **THEN** no record or job is created and no error propagates to the player's move


## REMOVED Requirements

### Requirement: Startup synchronization idempotently ensures scene and generic-monster records
**Reason**: Scenes are gallery-bearing; startup no longer writes classic scene records.
**Migration**: Replaced by "Startup synchronization requests gallery art for every registered scene and species"; retarget its tests.
