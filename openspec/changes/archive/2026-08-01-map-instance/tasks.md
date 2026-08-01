## 1. Confirmations before writing code

- [x] 1.1 Confirm whether change 12 (`map-anchor-grid`) and change 13 (`map-wilderness`) have been
      implemented yet. Design doc §11's Phase 3 table now lists this change as depending on both 12
      and 13 (amended by this change itself). If change 13 has **not** landed, add
      `typeclasses/rooms.py::SceneArchetypeMixin` first, exactly as specified by change 13's own
      `scene-archetype-mixin` capability (design.md's Context section explains this dependency). Do
      not invent a different `scene_archetype` seam.
- [x] 1.2 Confirm, by source inspection, that no class named `InstanceRoom` exists anywhere in the
      repository yet, and that `world/maps/` (if change 12 has landed) contains no `instance.py`.
- [x] 1.3 Confirm `world/rules/clock.py::_STAGE_ORDER`, `register_event_source`, `ScheduledEvent`, and
      `AdvanceSource` still match the shapes design.md's Context section describes (change 11,
      archived), and that `_EVENT_SOURCES` has no registered source for any of the four existing
      world-event kinds yet.
- [x] 1.4 Confirm, by import, that `evennia.prototypes.spawner.spawn` resolves against the installed
      Evennia version and returns a list for a single prototype argument — re-run design.md's
      Verification-section probe (or an equivalent) if the pinned Evennia version has changed since
      this proposal was written.

## 2. InstanceRoom typeclass (`typeclasses/rooms.py`)

- [x] 2.1 Add `InstanceRoom(SceneArchetypeMixin, DefaultRoom)` per design.md D-1, with the six
      persistent attributes (`expire_tick`, `named`, `interacted`, `pin_reasons`, `owned_entities`,
      `origin_room`) and their documented defaults.
- [x] 2.2 Implement `at_object_receive` setting `interacted = True` only for `PlayerCharacter`
      instances, never unsetting it once `True`.
- [x] 2.3 Implement `at_object_delete` refusing deletion (returning `False`) while `pin_reasons` is
      non-empty or a `PlayerCharacter` is among `self.contents` — **not** while any `LivingEntity`
      (including an `NPC`/`Monster`) is present; per design.md D-1/D-6's rubber-duck-review
      correction, gating on any `LivingEntity` here made NPC-occupied rooms permanently
      undeletable, which is the blocking defect this task must not reintroduce.
- [x] 2.4 Test: `InstanceRoom.__mro__` includes `SceneArchetypeMixin` and excludes `XYZRoom`/
      `WildernessRoom`; `scene_archetype` defaults to `None` and accepts an arbitrary string.
- [x] 2.5 Test: all six persistent attributes default correctly on a freshly created `InstanceRoom`,
      and persist across a re-fetch from the database.
- [x] 2.6 Test: `at_object_receive` sets `interacted` for a `PlayerCharacter` entering, does not for an
      `NPC`/`Monster` entering, and never unsets it once `True`.
- [x] 2.7 Test: `at_object_delete` refuses deletion (room still exists, `.delete()` returns `False`)
      while pinned, and separately while a `PlayerCharacter` is present; succeeds once neither
      condition holds.
- [x] 2.8 Test (regression guard for the corrected rule): `at_object_delete` does **not** refuse
      deletion when the room's only occupants are an `NPC` and/or a `Monster` with no
      `PlayerCharacter` present and no pin — `.delete()` returns `True` and the room is gone
      afterward. This is the test that would have caught the original blocking defect.

## 3. Prototype whitelist (`world/prototypes.py`, `world/maps/instance.py`)

- [x] 3.1 Add `world/prototypes.py::INSTANCE_ROOM = {"typeclass": "typeclasses.rooms.InstanceRoom",
      "desc": "..."}` with no explicit `prototype_key`, per design.md D-7.
- [x] 3.2 Create `world/maps/instance.py` (if `world/maps/__init__.py` does not already exist from
      change 12, confirm it does before adding this module) and declare
      `INSTANCE_PROTOTYPE_WHITELIST: tuple[str, ...] = ("instance_room",)`.
- [x] 3.3 Test: after Evennia's module-prototype loading runs, a prototype with `prototype_key ==
      "instance_room"` is registered and resolves to `typeclasses.rooms.InstanceRoom`.
- [x] 3.4 Test: `INSTANCE_PROTOTYPE_WHITELIST == ("instance_room",)` exactly.

## 4. spawn_instance_room (`world/maps/instance.py`)

- [x] 4.1 Implement `_validate_prototype_parent(prototype)`, raising `ValueError` for a
      `prototype_parent` not in `INSTANCE_PROTOTYPE_WHITELIST`, per design.md D-7. **Also** reject an
      explicit `typeclass` that is not exactly `"typeclasses.rooms.InstanceRoom"` — the whitelist must
      gate the actually-spawned type, since the exact-typeclass reclamation query would silently skip
      a differently-typed spawn (rubber-duck review, design.md D-7).
- [x] 4.2 Implement `spawn_instance_room(origin_room, prototype, *, exit_key, return_key,
      ttl_seconds=None, named=False, caller=None) -> InstanceRoom` per design.md D-2: **first** raise
      `ValueError` if `origin_room` is an `InstanceRoom` (Fix 2 — the nested-instance orphaning guard),
      then validate the prototype, call `spawner.spawn(prototype, caller=caller)`, raise `RuntimeError`
      if the returned list is empty (the defensive check for `spawn()`'s internal `if not prot:
      continue` branch — Fix 4; unreachable for a whitelist-validated prototype today, but not a
      formal guarantee `spawn()` itself makes), then set `expire_tick`/`named`/`origin_room`, and
      create the two plain `Exit` objects (no custom `at_traverse`). **Also (rubber-duck review):**
      reject a non-`InstanceRoom` spawn result, reject non-`int`, negative, or `bool` `ttl_seconds`,
      and run the whole spawn-plus-attach inside one `transaction.atomic()` so a failed second exit
      rolls back the room and both exits together (design.md D-2's correction note).
- [x] 4.3 Load `world/rules/rulebook/instance.yaml` into an `INSTANCE_YAML` module-level dict, mirroring
      `clock.py`'s own `CLOCK_YAML` loading pattern (task group 6 creates the YAML file itself).
- [x] 4.4 Test: a whitelisted prototype spawns an `InstanceRoom`; a non-whitelisted one raises
      `ValueError` before `spawner.spawn()` is ever called (assert via a spy/mock or by asserting no
      new object was created).
- [x] 4.5 Test: `expire_tick` equals `get_world_clock().tick + INSTANCE_YAML["default_ttl_seconds"]`
      when `ttl_seconds` is omitted, and `get_world_clock().tick + ttl_seconds` when given explicitly.
- [x] 4.6 Test: `named` reflects the caller-supplied value, defaulting to `False`.
- [x] 4.7 Test: exactly one `Exit` is created at `origin_room` (keyed `exit_key`, destination the new
      room) and exactly one at the new room (keyed `return_key`, destination `origin_room`); both are
      plain `typeclasses.exits.Exit` instances.
- [x] 4.8 Test: a character can traverse from `origin_room` into the spawned room and back to
      `origin_room` using ordinary Evennia exit-traversal commands, ending up in the identical
      `origin_room` object.
- [x] 4.9 Test (Fix 2): `spawn_instance_room()` called with `origin_room` set to an existing
      `InstanceRoom` raises `ValueError`, and creates no new room and no `Exit`.

## 5. Pin/unpin and owned-entity registration API (`world/maps/instance.py`)

- [x] 5.1 Implement `pin_instance_room(room, reason: str)` and `unpin_instance_room(room, reason: str)`
      per design.md D-8, operating on `room.db.pin_reasons` as a de-duplicated list.
- [x] 5.2 Test: pinning twice with the same reason leaves exactly one entry; pinning with two distinct
      reasons leaves both.
- [x] 5.3 Test: unpinning removes only the matching reason, leaving any other reason intact.
- [x] 5.4 Test: unpinning an absent reason does not raise and leaves `pin_reasons` unchanged.
- [x] 5.5 Implement `register_owned_entity(room, entity)` per design.md D-6/D-8, appending `entity` to
      `room.db.owned_entities` if not already present.
- [x] 5.6 Test: registering the same entity twice leaves it in `owned_entities` exactly once.
- [x] 5.7 Test: an entity never passed to `register_owned_entity()` is absent from `owned_entities`.

## 6. default_ttl_seconds rulebook data (`world/rules/rulebook/instance.yaml`)

- [x] 6.1 Create `world/rules/rulebook/instance.yaml` with `default_ttl_seconds: 345600`, per
      design.md D-9's arithmetic (`4 * hours_per_day * seconds_per_hour`).
- [x] 6.2 Test: `INSTANCE_YAML["default_ttl_seconds"] == 345600`, and equals
      `4 * CLOCK_YAML["hours_per_day"] * CLOCK_YAML["seconds_per_hour"]` computed independently in the
      test (not merely re-asserting the literal).

## 7. reclaim_due_instances routing logic (`world/maps/instance.py`)

- [x] 7.1 Implement `reclaim_due_instances(start_tick, end_tick) -> list[ScheduledEvent]` per
      design.md D-6: query `InstanceRoom.objects.all()` (not `search_object` — design.md D-9 records
      why), filter to rooms with `expire_tick is not None and expire_tick <= end_tick`, then route each
      to defer / promote / reclaim per the precise rules in the `instance-reclamation` spec. The
      occupancy check gating defer/promote is `PlayerCharacter` presence, **not** any `LivingEntity` —
      see task 2.3's own correction note; do not reintroduce the blocking defect here. The reclaim
      branch consults `InstanceRoom.at_object_delete()` as a pre-flight check **before** despawn or
      relocate, so a refused delete defers with contents intact (rubber-duck review correction —
      design.md D-6's addendum).
- [x] 7.2 Implement `_relocate_to_default_home(entity)` per design.md D-6: resolve
      `settings.DEFAULT_HOME` via `ObjectDB.objects.get(id=int(settings.DEFAULT_HOME.lstrip("#")))`
      (the identical lookup `DefaultObject.clear_contents()` itself uses) and call
      `entity.move_to(that_object, quiet=True)`.
- [x] 7.3 Implement `_clear_non_player_entities(room)` per design.md D-6: for every
      `typeclasses.entities.LivingEntity` in `room.contents` (guaranteed no `PlayerCharacter` at this
      point), delete it if present in `room.db.owned_entities`, otherwise relocate it via
      `_relocate_to_default_home()`; then reset `room.db.owned_entities` to an empty list. Call this
      from `reclaim_due_instances()` immediately before `room.delete()` on the reclaim branch only
      (never on the promote branch).
- [x] 7.4 Test: a due room with a `PlayerCharacter` present is deferred — still exists afterward,
      `expire_tick` unchanged, a `ScheduledEvent("instance_reclaim_deferred", ...)` is emitted.
- [x] 7.5 Test: a due, unpinned room with no `PlayerCharacter` present is deferred identically when
      pinned.
- [x] 7.6 Test (regression guard, task's own named blocking defect): a due, unpinned room containing
      only an `NPC` (no `PlayerCharacter`) is **not** deferred — it is routed to promotion or
      reclamation in that same call, per whichever of `named`/`interacted` it satisfies.
- [x] 7.7 Test: a due room with no `PlayerCharacter` present and no pin, with `named == True and
      interacted == True`, is promoted — still exists afterward, `expire_tick is None`, a
      `ScheduledEvent("instance_promoted", ...)` is emitted, its attach-exit pair is unchanged, and any
      `NPC` inside it is left in place (neither despawned nor relocated).
- [x] 7.8 Test: a due room with no `PlayerCharacter` present and no pin, with only one of
      `named`/`interacted` `True` (both combinations), is reclaimed, not promoted.
- [x] 7.9 Test: a due, unpinned, unnamed room with no `PlayerCharacter` present is reclaimed — no
      longer exists afterward, a `ScheduledEvent("instance_reclaimed", ...)` is emitted, and a dropped
      item that was inside it still exists in the database afterward (relocated, not destroyed).
- [x] 7.10 Test (the blocking defect's own regression check, required by the review): a due, unpinned,
      unnamed room containing **only an `NPC`** (no `PlayerCharacter`) is reclaimed within that single
      `reclaim_due_instances()` call — the room no longer exists afterward, proving the room resolves
      rather than deferring forever.
- [x] 7.11 Test: within the reclamation in 7.10, an `NPC` previously passed to
      `register_owned_entity(room, npc)` no longer exists in the database afterward (despawned); a
      second `NPC` in the same room that was never registered still exists afterward, relocated to
      `settings.DEFAULT_HOME` (not destroyed).
- [x] 7.12 Test: a promoted room is skipped entirely (no event emitted for it) on a subsequent
      `reclaim_due_instances()` call.
- [x] 7.13 Test: every `ScheduledEvent` returned contains only plain, JSON-compatible payload values —
      no live object reference.
- [x] 7.14 Test (defense in depth): monkeypatch or subclass a room so `at_object_delete` still returns
      `False` at the moment `reclaim_due_instances()` attempts a delete on a room its own pre-check
      believed was safe (after `_clear_non_player_entities()` has already run); confirm the function
      emits `"instance_reclaim_deferred"` instead of raising.

## 8. Settlement-stage wiring (`world/rules/clock.py`, registration call site)

- [x] 8.1 Append `"instance_reclamation"` to the end of `world/rules/clock.py::_STAGE_ORDER`, per the
      `MODIFIED settlement-stage-order` delta spec. Do not otherwise modify `_settle_boundary_stages()`
      — its existing `_STAGE_ORDER[5:]` iteration already covers the new entry.
- [x] 8.2 Implement `world/maps/instance.py::register_instance_reclamation()`, calling
      `world.rules.clock.register_event_source("instance_reclamation", reclaim_due_instances)`.
- [x] 8.3 Call `register_instance_reclamation()` from the same startup flow that already invokes change
      12's grid provisioning (`world/maps/bootstrap.py`'s function that `at_server_start()` calls) —
      an edit to change 12's already-landed implementation file, not to its OpenSpec artifacts.
- [x] 8.4 Test: `world.rules.clock._STAGE_ORDER` is exactly the ten-entry tuple the delta spec pins,
      with `"instance_reclamation"` last.
- [x] 8.5 Test: before `register_instance_reclamation()` runs, `WorldClock.advance()` across a due
      room's `expire_tick` boundary does not reclaim or promote it (unregistered-stage no-op,
      unchanged from the existing four kinds' behavior).
- [x] 8.6 Test: after `register_instance_reclamation()` runs, `WorldClock.advance()` across a due,
      unoccupied, unpinned, unnamed room's `expire_tick` boundary reclaims it within that single call.
- [x] 8.7 Test (source-order / integration): simulating a server start results in
      `register_instance_reclamation()` having run, alongside whatever change 12/13 provisioning already
      runs, with no exception raised.

## 9. The quest_deadlines-before-instance_reclamation existence-differs proof

- [x] 9.1 Write the test the `settlement-stage-order` delta spec's own scenario names: register a
      synthetic `quest_deadlines` source that calls `unpin_instance_room()` on a target room when its
      synthetic deadline comes due within the settled range; set up a due, unoccupied, unnamed room
      pinned by exactly that reason; call `advance()` once across both boundaries under the real,
      declared stage order; assert the room no longer exists after that single call.
- [x] 9.2 In the same test module, construct the transposed order in isolation (calling the two
      registered sources directly in reverse, without touching the shipped `_STAGE_ORDER`) and assert
      the room still exists after an equivalent single pass — proving the two orders produce different
      final states, not merely documented-but-inert different call sequences.

## 10. Full-suite integration test

- [x] 10.1 Write one `EvenniaTest`-based integration test that: builds an `origin_room`, calls
      `spawn_instance_room()` with a short `ttl_seconds` and `named=True`, has a `PlayerCharacter`
      traverse in (setting `interacted`), traverse back out (vacating the room), advances
      `WorldClock` past `expire_tick`, and confirms the room is promoted (still exists, `expire_tick is
      None`) — exercising spawn, traversal, occupancy-driven interaction tracking, and the full
      reclamation stage together, not each in isolation.
- [x] 10.2 Write a second integration test with `named=False` for the same setup, confirming the room
      is instead reclaimed (deleted) after the identical sequence, and that the exit at `origin_room`
      pointing to it is also gone (Evennia's own `clear_exits()` behavior, verified in design.md).
- [x] 10.3 Write a third integration test that is the end-to-end version of the review's own named
      use case: build an `origin_room`, call `spawn_instance_room()`, spawn an `NPC` into the new room
      and call `register_owned_entity()` on it (simulating what change 21's `SceneBuilder` will do),
      call `pin_instance_room()` (simulating an active quest stage), advance `WorldClock` past
      `expire_tick` and confirm the room is deferred (still exists, still pinned) despite having no
      `PlayerCharacter` present, then call `unpin_instance_room()` (simulating stage completion) and
      advance again, confirming the room is now reclaimed and the NPC is despawned — the full quest
      lifecycle this change's headline feature exists to serve, not a synthetic stand-in for it.

## 11. Verification

- [x] 11.1 Run the full test suite added by this change and confirm every test passes.
- [x] 11.2 Confirm (via `git diff`) that every edit to an already-landed file (`world/rules/clock.py`,
      `world/prototypes.py`, `world/maps/bootstrap.py`, `typeclasses/rooms.py`) is additive and does
      not remove or alter any behavior a prior change's own tests depend on; run change 11's own
      `world/rules/tests/test_clock.py` (or equivalent) and change 12/13's own test modules (if
      implemented) and confirm they still pass unmodified.
- [x] 11.3 Confirm no file added or edited by this change contains a reference to `world/ai/` or an LLM
      call, per this project's single-writer discipline (this change touches no `world/ai/` file at
      all, but the check costs nothing).
- [x] 11.4 Confirm `tests/test_contrib_matrix.py::MATRIX_IMPORTS` already covers `evennia.prototypes.
      spawner.spawn` (added by change 1) and needs no new row from this change.
- [x] 11.5 Confirm `docs/superpowers/specs/2026-07-29-ai-mud-engine-design.md` §11's Phase 3 table
      (row 14) already reads `Depends on: 12, 13` with the inline amendment note present — this was
      edited as part of this change's own proposal, not deferred to implementation time.
- [x] 11.6 Run `openspec validate map-instance --strict` and `openspec validate --all --strict` and
      confirm both pass.
