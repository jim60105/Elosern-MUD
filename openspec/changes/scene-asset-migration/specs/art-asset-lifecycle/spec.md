## ADDED Requirements

### Requirement: Startup converts classic scene outputs into scene gallery cards
Before the gallery orphan prune, startup SHALL convert every settled classic scene record: a `done` record whose output is presentable becomes the archetype's scene gallery card when the gallery holds none; then the record and its classic output files SHALL be deleted. Unsettled records SHALL be left for a later startup. The step SHALL be idempotent, bounded per record, and leave no orphan file or record.

#### Scenario: A done classic scene becomes one card
- **WHEN** synthetic archetype `t_arch` has a `done` classic record with a presentable output and an empty scene gallery
- **THEN** after startup its gallery holds exactly one default card whose file holds the same bytes, and neither the classic record nor the classic output file remains

#### Scenario: An existing card wins
- **WHEN** `t_arch` already holds a scene gallery card and also a `done` classic record
- **THEN** the card is unchanged, and the classic record and its output files are deleted

#### Scenario: Failed and missing records are dropped
- **WHEN** a classic scene record is `failed`, `missing`, or `done` without a presentable output
- **THEN** it and any of its output files are deleted and no card is created

#### Scenario: An unsettled record waits
- **WHEN** a classic scene record is `pending` or `in_progress`
- **THEN** it is left unchanged

#### Scenario: Running twice changes nothing more
- **WHEN** the conversion runs a second time
- **THEN** it creates, deletes and moves nothing

#### Scenario: One bad record never aborts startup
- **WHEN** converting one record raises
- **THEN** a bounded diagnostic is logged, the other records are converted, and startup continues

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

#### Scenario: A scene emptied by deletion stays on its bundled image
- **WHEN** startup synchronization or a room entry meets a scene archetype whose gallery record exists with no card because its card was deleted
- **THEN** no gallery request is made, so the archetype keeps resolving its bundled image until a player requests a new one

#### Scenario: A failed first generation is retried
- **WHEN** an archetype's first scene generation failed, leaving a gallery record with no card and a recorded error, and the player enters one of its rooms
- **THEN** one new gallery request is made

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
  gallery request only when the subject has no card, no in-flight job, and either no gallery record
  or a record carrying a recorded error, nothing otherwise, and no classic record is created

#### Scenario: A room without a resolvable archetype is a no-op
- **WHEN** a player enters a room with a `None` or unresolvable `scene_archetype`
- **THEN** no record or job is created and no error propagates to the player's move


## REMOVED Requirements

### Requirement: Startup synchronization idempotently ensures scene and generic-monster records
**Reason**: Scenes are gallery-bearing; startup no longer writes classic scene records.
**Migration**: Replaced by "Startup synchronization requests gallery art for every registered scene and species"; retarget its tests.
