## MODIFIED Requirements

### Requirement: Startup synchronization idempotently ensures scene and generic-monster records
`world/art/service.py::art_sync_all()` SHALL be called from
`server/conf/at_server_startstop.py::at_server_start` and SHALL cover every entry of
`SCENE_ARCHETYPE_REGISTRY` and every entry of `MONSTER_TIER_REGISTRY` (generic monster subjects),
routing each subject by whether its kind declares a gallery.

A subject whose kind declares NO gallery — the scene kind — SHALL be ensured as a classic asset record
exactly as today: the sync SHALL be idempotent, an existing `pending`, `in_progress`, or `done` record
is untouched, a `missing` or `failed` record is made `pending`, records SHALL be created only through
an atomic find-or-create under the queue lock, and the sync SHALL consolidate any duplicate records
found for one subject (keeping the most-advanced record) so per-subject uniqueness holds.

A subject whose kind declares a gallery — the generic monster kind — SHALL instead route through the
gallery generation request under the shared automatic-generation guard, and startup SHALL NOT create a
classic asset record for it. Pre-existing classic monster records SHALL be left in place: they are not
deleted, not reset, and keep resolving through the display chain's classic step, so no migration is
required. Every failure SHALL stay bounded and SHALL never abort startup.

The startup step order SHALL run the gallery orphan prune and the bulk seed synchronization BEFORE
this synchronization, so a seed card already occupies a subject's gallery — and the prune has already
swept — before any automatic gallery request is enqueued; an operator seed card is therefore never
displaced by a startup-time generation.

#### Scenario: Every registered subject has a record after startup sync
- **WHEN** `art_sync_all()` runs against a fresh database
- **THEN** every `SCENE_ARCHETYPE_REGISTRY` key has exactly one classic asset record in `missing` or
  `pending` state, every `MONSTER_TIER_REGISTRY` key has one gallery generation requested, and no
  classic asset record is created for any monster tier

#### Scenario: A seed-carded tier survives the ordered startup unchanged
- **WHEN** the startup steps run in catalog order (prune, then seed synchronization, then this
  synchronization) with a seed image present for a monster tier, and the queue is later drained
- **THEN** no gallery generation is requested for that tier and its seed card and stored file are never replaced

#### Scenario: Sync leaves existing pending, in-progress, and done records untouched
- **WHEN** `art_sync_all()` runs after records were already created, claimed, or completed
- **THEN** the existing `pending`, `in_progress`, and `done` records are not reset, not duplicated, and
  not overwritten

#### Scenario: A pre-existing classic monster record is left alone
- **WHEN** `art_sync_all()` runs against a store that already holds a `done` classic monster record
- **THEN** that record is not deleted, not reset, and still resolves through the display chain's classic step

#### Scenario: Duplicate records for one subject are consolidated
- **WHEN** startup sync finds more than one record for the same subject key
- **THEN** exactly one record remains (the most advanced) and the rest are removed

#### Scenario: A monster gallery request failure never aborts startup
- **WHEN** a monster tier's gallery request raises during startup synchronization
- **THEN** a bounded diagnostic is logged, the remaining subjects still synchronize, and startup completes
