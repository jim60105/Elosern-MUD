## Why

Design doc D3 names four map layers — Anchor / Grid / Virtual (wilderness) / Instance — and roadmap
item 14 (§11, depends on 12, 13 — the dependency list amended by this change itself, see below) is the
change that builds the last of them. Change 12 (`map-anchor-grid`)
deliberately did **not** forward-declare `InstanceRoom`, on the explicit grounds that a stub would be
a fake implementation rather than a seam ("change 14 adds it fresh, with no seam from this change to
build on beyond `GridRoom` itself"). Without this change, §7.2's `SceneBuilder` (change 21) and §4's
"Map · instance layer ... `evennia.prototypes.spawner.spawn()`" contrib call have nowhere to write to,
and change 15 (`quest-runtime`, which depends on this change) has no location type for a quest stage's
"reach_location" objective to happen in. This change builds `InstanceRoom` itself, the TTL that keeps
ephemeral scene content from accumulating forever, and the promotion rule D3 states in one sentence —
"Named instance rooms the player interacted with are promoted to permanent" — given a precise,
testable, operational definition instead of being left as prose.

## What Changes

- Add `typeclasses/rooms.py::InstanceRoom(SceneArchetypeMixin, DefaultRoom)` — the third consumer of
  change 13's `SceneArchetypeMixin` seam (after `GridRoom` and `TerrainRoom`), adopted rather than
  reinvented. Unlike `GridRoom`/`TerrainRoom`, `InstanceRoom` carries no coordinate of any kind — per
  design doc §4, the instance layer is spawned through core `evennia.prototypes.spawner.spawn()`, not
  `xyzgrid`, and is reached purely by ordinary Evennia exit traversal, exactly like the stock `Room`
  typeclass already is. `InstanceRoom` adds six persistent attributes: `expire_tick: int | None` (the
  absolute `WorldClock` tick at which this room becomes eligible for reclamation; `None` means
  promoted, TTL permanently disabled), `named: bool`, `interacted: bool`, `pin_reasons: list[str]`,
  `owned_entities: list` (entities despawned rather than merely relocated when this room reclaims —
  see the `reclaim_due_instances()` bullet below), and `origin_room` (the room this instance is
  reachable from). It overrides `at_object_delete()` to refuse deletion while a `PlayerCharacter` is
  present or while `pin_reasons` is non-empty (a typeclass-level safety net, verified against the
  installed Evennia 6.1.0 to actually abort `.delete()` when it returns `False` — see design.md), and
  overrides `at_object_receive()` to set `interacted = True` the first time a `PlayerCharacter` enters.
  `spawn_instance_room()` also raises `ValueError` when asked to attach a new instance room to an
  `origin_room` that is itself an `InstanceRoom`, since Evennia's own exit-cleanup behavior would
  otherwise let a later-reclaimed origin silently orphan a promoted room's only path back to it.
- Add `world/prototypes.py::INSTANCE_ROOM` (`prototype_key` resolves to `"instance_room"` by Evennia's
  own module-prototype naming rule, verified directly) and `world/maps/instance.py::
  INSTANCE_PROTOTYPE_WHITELIST` — a closed, explicit tuple of sanctioned `prototype_parent` values a
  caller of `spawn_instance_room()` may chain from. This is the concrete answer to design doc §7.2's
  anti-hallucination rule ("`prototype_parent` must come from a whitelist") for this layer, without
  inventing change 21 (`scene-builder`)'s own content — this change populates the whitelist with
  exactly one entry, `"instance_room"`, and leaves it open for change 21 to extend, mirroring the
  "declare a keyed registry/whitelist, populate later" idiom `map-anchor-grid`'s
  `ANCHOR_PLACEMENT_REGISTRY` and `map-wilderness`'s `WILDERNESS_ENTRY_REGISTRY` already established.
- Add `world/maps/instance.py::spawn_instance_room(origin_room, prototype, *, exit_key, return_key,
  ttl_seconds=None, named=False, caller=None) -> InstanceRoom` — the sanctioned entry point for
  creating an instance room. Validates the prototype's `prototype_parent` against
  `INSTANCE_PROTOTYPE_WHITELIST`, calls `spawner.spawn()`, sets `expire_tick` from
  `world.rules.rulebook.instance.yaml`'s `default_ttl_seconds` (overridable per call), and creates one
  ordinary, ungated `Exit` pair between `origin_room` and the new room — the instance layer's own
  version of `map-anchor-grid`'s Limbo bridge and `map-wilderness`'s gateway-exit-pair idiom, made
  simpler than either because `InstanceRoom` needs no coordinate-aware exit subclass at all (see
  design.md D-2 for why).
- Add `world/rules/rulebook/instance.yaml::default_ttl_seconds: 345600` (4 in-game days, arithmetic
  shown in design.md) — a new rulebook data file, following D9's "balance numbers are YAML" convention.
- Add `world/maps/instance.py::pin_instance_room(room, reason)` / `unpin_instance_room(room, reason)`
  — a general reference-holding seam any future subsystem can use to keep a due room alive without
  this change needing to know who's asking. This is part of the concrete contract offered to change 15
  (`quest-runtime`), which depends on this change: a quest stage pins the room it is using for its
  duration and unpins it on completion, failure, or abandonment.
- Add `world/maps/instance.py::register_owned_entity(room, entity)` — the companion seam to the pin
  API: whoever spawns an NPC (per design doc §7.2, that is change 21's `SceneBuilder`) into an
  instance room for that scene's own use registers it here, so reclamation knows to despawn it rather
  than leaking it into `DEFAULT_HOME` forever.
- Add `world/maps/instance.py::reclaim_due_instances(start_tick, end_tick) -> list[ScheduledEvent]` —
  the registered event-source function for a new `instance_reclamation` settlement stage. For every
  `InstanceRoom` whose `expire_tick` is due (`<= end_tick`): rooms with a `PlayerCharacter` present or
  a non-empty `pin_reasons` are deferred (retried on the next settlement pass); rooms with neither that
  are both `named` and `interacted` are **promoted** (`expire_tick` set to `None`, room, exits, and any
  NPCs inside all left exactly as they are); everything else is reclaimed — every registered
  (`register_owned_entity()`) non-player entity still present is despawned, every unregistered one is
  relocated to `settings.DEFAULT_HOME` (never destroyed, matching Evennia's own verified item-relocation
  behavior), and only then is `room.delete()` called, which Evennia's own verified `clear_exits()`
  behavior handles safely for the room's own attach-exit pair — see design.md D-6, including the
  rubber-duck-review correction recorded there: an earlier draft deferred reclamation whenever *any*
  `LivingEntity` (including an NPC) was present, which made the change's headline feature never resolve
  for a room containing the exact `npc_req` content design doc §7.1/§7.2 describes as the normal case.
  Registered via `world/rules/clock.py::register_event_source("instance_reclamation",
  reclaim_due_instances)`, called from `world/maps/bootstrap.py`'s existing `at_server_start()`-invoked
  flow (an edit to change 12's already-landed implementation file, following the established
  "downstream change touches upstream code, not upstream artifacts" pattern).
- Extend `world/rules/clock.py::_STAGE_ORDER` with one new, final entry, `"instance_reclamation"`,
  after `"npc_schedules"` — an edit to change 11's (`world-clock`, archived) already-landed
  implementation file, paired with a **MODIFIED `settlement-stage-order`** delta spec (see Capabilities
  below), following the exact precedent `map-wilderness`'s own `MODIFIED grid-room-typeclasses` delta
  set for retrofitting `GridRoom` onto `SceneArchetypeMixin`: an already-shipped, spec-pinned exact
  sequence is being extended, which change 12's own design.md D-1 reasoning treats as needing a new
  artifact, not a same-file-only edit.
- **Amend the design document.** `docs/superpowers/specs/2026-07-29-ai-mud-engine-design.md` §11's
  Phase 3 table, row 14, `Depends on` cell: `12` → `12, 13`, with an inline dated amendment note. This
  change genuinely cannot build `InstanceRoom` without change 13's `SceneArchetypeMixin` (see design.md
  Context), and AGENTS.md permits a change to explicitly amend the design document rather than leaving
  the architectural source of truth silently out of date. This is the one edit made outside this
  change's own directory.

## Capabilities

### New Capabilities
- `instance-room-typeclass`: `InstanceRoom`, its adoption of `SceneArchetypeMixin`, its six
  persistent attributes, and the `at_object_delete`/`at_object_receive` safety and tracking hooks.
- `instance-spawn`: `INSTANCE_ROOM` prototype, `INSTANCE_PROTOTYPE_WHITELIST`,
  `spawn_instance_room()` (including its nested-instance `origin_room` guard), and the bidirectional
  attach-exit idiom connecting an instance room to its origin.
- `instance-reclamation`: `default_ttl_seconds`, `pin_instance_room()`/`unpin_instance_room()`,
  `register_owned_entity()`, `reclaim_due_instances()`, and the reclaim/defer/promote routing rule —
  the precise, testable operational definition of design doc D3's "named instance rooms the player
  interacted with are promoted to permanent," including how a due room's non-player occupants are
  resolved (despawned or relocated), not merely how player occupancy defers it.

### Modified Capabilities
- `settlement-stage-order` (change 11, archived): the fixed nine-stage sequence becomes a fixed
  ten-stage sequence, with `instance_reclamation` appended after `npc_schedules`. The delta spec
  reproduces change 11's pinned-tuple requirement text with the tenth entry added, and adds a
  transposition-detection scenario proving the position is load-bearing: reclaiming before
  `quest_deadlines` settle can leave a room whose pin was released by that same settlement pass
  incorrectly un-reclaimed for one extra `advance()` call, not merely reclaimed "in the wrong order."

## Impact

- New files: `typeclasses/rooms.py` gains `InstanceRoom` (edit to change 13's already-landed file —
  now a formal dependency per the design-doc amendment above, not merely a same-Phase sibling; see
  design.md's Context section for the implementation-time fallback if 13 has somehow not landed
  first), `world/maps/instance.py`, `world/rules/rulebook/instance.yaml`, plus their test modules.
- Edits to already-landed implementation files (not their OpenSpec artifacts): `world/prototypes.py`
  (`INSTANCE_ROOM` added), `world/maps/bootstrap.py` (one call added to whatever function
  `at_server_start()` already invokes for map provisioning), `server/conf/at_server_startstop.py` (no
  further edit needed beyond what change 12 already wired, since the new call lives inside
  `world/maps/bootstrap.py`'s own provisioning function — see design.md), `world/rules/clock.py`
  (`_STAGE_ORDER` gains one entry).
- Reads change 13's `SceneArchetypeMixin` (`typeclasses/rooms.py`) and change 11's
  `register_event_source()`/`ScheduledEvent`/`AdvanceSource` (`world/rules/clock.py`).
- No database migration concerns (project is unreleased, zero users). No sample instance-room content
  is authored by this change (unlike change 12's sample city or change 13's gateway) — the roadmap
  slot for this change is the mechanism itself ("Instance TTL reclamation, promotion of named rooms"),
  not a content demonstration; change 21 (`scene-builder`) is the first real content producer.
