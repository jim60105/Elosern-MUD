## 1. Confirmations before writing code

- [x] 1.1 Confirm change 12 (`map-anchor-grid`) is implemented: `typeclasses/rooms.py::GridRoom`/
      `AnchorRoom` exist, `world/maps/altoria_capital.py::XYMAP_DATA` exists, and
      `sync_grid()` spawns the thirteen-room sample city. Do not proceed past task group 4 if this is
      not true yet.
- [x] 1.2 Confirm change 13 (`map-wilderness`) is implemented: `typeclasses/exits.py::
      WildernessGateExit`/`WildernessReturnExit` exist matching its own design.md D-6 (as this change
      will have amended it — task group 6), and `rulebook/clock.yaml::command_defaults.
      wilderness_move == 9000`. Do not proceed past task group 5 if this is not true yet.
- [x] 1.3 Confirm no module named `world/rules/movement.py` exists yet, and that
      `typeclasses/exits.py::Exit` has no `MovementCostMixin` in its bases and no class named
      `CostedXYZExit` exists.
- [x] 1.4 Re-verify (do not merely trust design.md) the two Evennia facts this change's whole design
      leans on, against whatever Evennia version is actually installed at implementation time: (a)
      `DefaultExit.at_traverse` has no `return` statement in either branch; (b) `at_post_traverse` is
      called only from `at_traverse`'s successful-`move_to()` branch. Re-run
      `tmp/probe_movement_clock/test_probe.py` (`uv run --locked evennia test --settings settings.py
      tmp.probe_movement_clock`) and confirm all eleven tests still pass before writing any shipped
      code; if Evennia has been upgraded since this proposal was written, re-derive design.md D-2
      against the new source rather than assuming it still holds.

## 2. Shared movement-cost function (`world/rules/movement.py`)

- [x] 2.1 Create `world/rules/movement.py`. Implement `charge_movement(traversing_object, cost_key:
      str) -> None` per design.md D-2/D-8: resolve `CLOCK_YAML["command_defaults"][cost_key]`, and
      call `world.rules.clock.get_world_clock().advance(cost, AdvanceSource.COMMAND,
      [traversing_object])` only when `isinstance(traversing_object,
      typeclasses.characters.PlayerCharacter)` — a no-op otherwise. Import `PlayerCharacter` lazily
      (inside the function body) to avoid a circular import with `typeclasses/characters.py`, matching
      this project's existing lazy-import precedent (`world/rules/clock.py::_try_accrue_magic_study`).
- [x] 2.2 Test: `charge_movement(player_character, "move")` advances `get_world_clock().tick` by
      exactly `CLOCK_YAML["command_defaults"]["move"]`.
- [x] 2.3 Test: `charge_movement(npc, "move")` (an `NPC`-typeclassed, non-`PlayerCharacter` traverser)
      leaves the clock unchanged.
- [x] 2.4 Test: `charge_movement()` always passes `AdvanceSource.COMMAND` to the underlying
      `WorldClock.advance()` call, for any registered `cost_key`.
- [x] 2.5 Test: `charge_movement(player_character, "wilderness_move")` advances the clock by
      `CLOCK_YAML["command_defaults"]["wilderness_move"]`, proving the function is cost-key-generic,
      not hardcoded to `"move"`.

## 3. Exit typeclasses (`typeclasses/exits.py`)

- [x] 3.1 Add `MovementCostMixin` per design.md D-2/D-3: a class attribute `movement_cost_key: str =
      "move"` and an `at_post_traverse(self, traversing_object, source_location, **kwargs)` override
      that calls `super().at_post_traverse(...)` then `world.rules.movement.charge_movement(
      traversing_object, self.movement_cost_key)`. Do not override `at_traverse`.
- [x] 3.2 Change `Exit`'s base classes from `(ObjectParent, DefaultExit)` to `(MovementCostMixin,
      ObjectParent, DefaultExit)`. Do not change any other line of `Exit`'s body (it remains
      otherwise empty).
- [x] 3.3 Add `CostedXYZExit(MovementCostMixin, evennia.contrib.grid.xyzgrid.xyzroom.XYZExit)` with no
      additional members beyond what the mixin and `XYZExit` already provide.
- [x] 3.4 Test: a `PlayerCharacter` traversing a plain `Exit` instance advances the clock by exactly
      `CLOCK_YAML["command_defaults"]["move"]`.
- [x] 3.5 Test: a locked `Exit` (`locks.add("traverse:false()")`) traversal attempt leaves both the
      traverser's location and the clock unchanged.
- [x] 3.6 Test: a traverser whose `at_pre_move` returns `False` leaves both the traverser's location
      and the clock unchanged when attempting to traverse an `Exit` instance.
- [x] 3.7 Test: `CostedXYZExit.create(key=..., location=..., destination=...)` produces a working
      exit — `isinstance(exit_obj, evennia.contrib.grid.xyzgrid.xyzroom.XYZExit)` holds, a successful
      traversal moves the traverser to the destination, and the clock advances by exactly
      `CLOCK_YAML["command_defaults"]["move"]`.
- [x] 3.8 Test: an `NPC`-typeclassed traverser successfully traverses a `MovementCostMixin`-carrying
      exit (its location changes) but the clock does not advance.
- [x] 3.9 Test: `traversing_object.move_to(destination, move_type="teleport")`, called directly with
      no `Exit` involved, leaves the clock unchanged even though the move succeeds.
- [x] 3.10 Test: `traversing_object.move_to(destination, quiet=True)`, called directly (the exact
      shape change 14's `_relocate_to_default_home()` uses), leaves the clock unchanged even though
      `at_post_move` still fires on the moved object.

## 4. Wire CostedXYZExit into the sample city's map data (`world/maps/altoria_capital.py`, change 12)

- [x] 4.1 Add exactly one entry to `XYMAP_DATA["prototypes"]`: `("*", "*", "*"): {
      "prototype_parent": "xyz_exit", "typeclass": "typeclasses.exits.CostedXYZExit"}`. Do not modify
      any node-coordinate entry, any room prototype, or the map string itself.
- [x] 4.2 Test: against a **fresh, empty** test database, after `sync_grid()` runs once, every one of
      the sample city's twelve intra-city exits is a `CostedXYZExit` instance. This exercises the
      `Typeclass.create()` branch only — it deliberately does not, by itself, prove anything about
      retyping an already-existing exit; task 4.2b below covers that separately.
- [x] 4.2b Test (retype path, scoped per design.md D-4's own verified finding — do not assume this
      "just works" the way 4.2 does): against a database where `sync_grid()` has **already run once
      without** this task group's `("*", "*", "*")` entry (bare `XYZExit` instances exist), running
      `sync_grid()` again **after** adding the entry updates every existing exit's
      `db_typeclass_path` to `typeclasses.exits.CostedXYZExit` (confirm by re-querying
      `db_typeclass_path` directly on each row), but assert — do not merely note — that the
      already-loaded Python objects from the first `sync_grid()` call are unaffected in the current
      process (`type(exit_obj).__name__ == "XYZExit"`, still, on the object reference held from
      before the second call) and that a traversal through one of them still does not charge. This
      test exists to catch a **regression in either direction**: if a future Evennia upgrade changes
      `batch_update_objects_with_prototype()` to call `swap_typeclass()` (making the retype work
      in-process after all), this test's second assertion should be revisited and likely loosened,
      not silently left asserting a now-outdated limitation.
- [x] 4.2c Confirm (development-environment task, not a `pytest`-style test): the implementer's own
      local/CI database is fresh (migrated from empty) before running the integration/round-trip
      tests in task group 8, rather than reused from a database that predates this task group's map
      data edit — per design.md D-4's fallback, this project's zero-user posture means "discard the
      dev database" is the correct operational answer to the retype limitation 4.2b documents, not a
      migration script.
- [x] 4.3 Test: the sample city still has exactly thirteen rooms and twelve exits in the identical
      topology change 12's own `sample-city-altoria` tests already assert — re-run those tests
      unmodified and confirm they still pass, proving this edit is topology-preserving.
- [x] 4.4 Test: a `PlayerCharacter` successfully traversing any one of the twelve intra-city exits
      (spawned fresh, per task 4.2) advances the clock by exactly `CLOCK_YAML["command_defaults"][
      "move"]`.
- [x] 4.5 Test: the Limbo↔South-Gate bridging `Exit` pair (change 12 D-7, `typeclasses.exits.Exit`,
      unmodified by this task group) also advances the clock on a successful traversal — confirming
      the "free" consequence design.md D-5 claims, not merely asserting it.
- [x] 4.6 Test (update to an already-landed change-13 test): change 13's own
      `world/maps/tests/test_city_wilderness_roundtrip.py::test_intra_city_grid_traversal_does_not_advance_clock`
      asserts the OPPOSITE of what this task group does — it traverses an intra-city exit and asserts
      `tick` is unchanged, which is exactly the "grid traversal remains unwired" posture this change
      deliberately retires. Update this test to assert the new behavior (the intra-city exit, now a
      `CostedXYZExit` via the wildcard prototype, advances the clock by exactly
      `CLOCK_YAML["command_defaults"]["move"]`) and rename it accordingly. This is the one intentional
      edit to a landed change-13 test; every other test in change 13's suite passes unmodified (see
      task 9.2).
- [x] 4.7 Test (update to an already-landed change-12 test helper): change 12's own
      `world/maps/tests/test_bootstrap.py::_count_city_exits` counts intra-city exits via
      `XYZExit.objects.all().count()`, which filters on the exact typeclass path. Once this task
      group's wildcard override makes every intra-city exit a `CostedXYZExit` subclass, that helper
      returns 0 and five of change 12's grid-bootstrap tests fail. Update the helper to
      `XYZExit.objects.all_family().count()` so it keeps counting all intra-city exits regardless of
      their exact typeclass, exactly as it did before. This is the second intentional edit to a
      landed test; both are recorded so task 9.2's "unmodified" claim names them explicitly.

## 5. Fold change 13's wilderness clock wiring into charge_movement (`typeclasses/exits.py`)

- [x] 5.1 In `WildernessGateExit.at_traverse`'s successful branch, replace the inline
      `get_world_clock().advance(CLOCK_YAML["command_defaults"]["wilderness_move"],
      AdvanceSource.COMMAND, [traversing_object])` call with `world.rules.movement.charge_movement(
      traversing_object, "wilderness_move")`. Change no other line of this method.
- [x] 5.2 In `WildernessReturnExit.at_traverse`, replace **both** inline `get_world_clock().advance(...)`
      calls (the special-cased return branch and the `super().at_traverse()` fallback branch) with
      `world.rules.movement.charge_movement(traversing_object, "wilderness_move")`. Change no routing
      logic.
- [x] 5.3 Re-run change 13's own `wilderness-gateway` test suite unmodified (entry cost, unsuccessful
      traversal charges nothing, vetoed `at_pre_move` charges nothing, the eight-leg round-trip totals
      `8 * 9000`) and confirm every test still passes — the concrete proof this fold is
      behavior-preserving, not just claimed.
- [x] 5.4 Test (new): `WildernessGateExit.at_traverse`'s source, inspected directly, calls
      `world.rules.movement.charge_movement`, not `world.rules.clock.get_world_clock().advance`.
      Repeat for both branches of `WildernessReturnExit.at_traverse`.

## 6. Change 13's own artifacts: design.md consistency edits (not this change's code)

- [x] 6.1 Confirm `openspec/changes/map-wilderness/design.md` has already been updated (this proposal
      ships the edit alongside itself, not as a deferred task) so that: D-8 no longer claims "no
      roadmap item ... is scoped to give it one" for `move: 30`; the "No change to the grid layer's
      own movement-clock posture" Non-Goal is corrected to reflect that `map-movement-clock` now
      wires `move: 30`; and D-6's two code samples each carry a dated amendment note explaining that
      they **still show, unedited, the raw `get_world_clock().advance(...)` calls change 13 itself
      builds and tests** — that is deliberate, not stale. Change 13 is implemented before this change
      exists in roadmap order, so its own artifacts must describe code an implementer can build
      without importing a `world.rules.movement` module that does not exist yet. **Do not edit change
      13's code samples to call `charge_movement()` — that edit belongs to task group 5 of *this*
      change, applied directly to `typeclasses/exits.py` once it is real code**, not to
      `map-wilderness/design.md`'s prose. This task is a verification checkpoint, not new writing —
      see this change's own proposal/design for the actual edited text and for why the replacement
      happens in task group 5, not here.

## 7. Design document amendment

- [x] 7.1 Confirm `docs/superpowers/specs/2026-07-29-ai-mud-engine-design.md` §11's Phase 3 table has
      a new row for this change (`map-movement-clock`, depends on `12, 13`), positioned between
      change 13 and change 14, with an inline dated amendment note explaining why (mirrors the
      existing 2026-08-01 amendment note for change 14's own dependency row) — shipped alongside this
      proposal, not a deferred task.

## 8. Full round-trip verification across every lineage

- [x] 8.1 Write one `EvenniaTest`-based integration test that: runs `sync_all()`, `sync_grid()`,
      `sync_wilderness()` against a fresh test database; walks a `PlayerCharacter` from Limbo through
      the South Gate bridge, across several intra-city `CostedXYZExit` links, to the North Gate;
      traverses into the wilderness and takes a few steps; returns to the grid; and separately, spawns
      a synthetic origin/return `Exit` pair via `typeclasses.exits.Exit.create()` (mirroring
      `spawn_instance_room()`'s own call shape) and traverses it. Assert the clock's total advance
      equals the exact sum of every individual leg's expected cost (`move` for grid/Limbo/
      instance-style legs, `wilderness_move` for wilderness legs) — not merely a nonzero total. This is
      the concrete test for the "traverse every lineage and assert the totals" requirement, not an
      isolated per-lineage test alone.
- [x] 8.2 Test: within the same integration test, confirm at least one deliberately failed traversal
      (a locked exit, or an `at_pre_move` veto) contributes exactly `0` to the running total, proving
      the failure-exclusion behavior holds inside a realistic multi-lineage walk, not only in
      isolation.

## 9. Contrib matrix and cross-suite regression coverage

- [x] 9.1 Add `charge_movement`, `MovementCostMixin`, `CostedXYZExit` to `tests/
      test_contrib_matrix.py::MATRIX_IMPORTS` if that module's own convention covers project-authored
      (not contrib) symbols this change adds; otherwise confirm no addition is needed and record why.
- [x] 9.2 Run `world/rules/tests/test_clock.py`, `commands/tests/test_cmd_cast.py` (or equivalent),
      change 12's own `world/maps/tests/` suite, and change 13's own `typeclasses/tests/`/`world/maps/
      tests/` suites, and confirm every one still passes unmodified — with two recorded exceptions,
      both intentionally updated by this change: `test_intra_city_grid_traversal_does_not_advance_clock`
      (task 4.6, asserts the new charging behavior this change introduces) and
      `test_bootstrap.py::_count_city_exits` (task 4.7, uses `all_family()` so the count still sees
      `CostedXYZExit`). All other tests passing unmodified proves this change's edits are additive,
      not regressions.

## 10. Verification

- [x] 10.1 Run the full test suite added or touched by this change and confirm every test passes.
- [x] 10.2 Confirm (via `git diff`) that every edit to an already-landed file (`typeclasses/exits.py`)
      is additive (new classes, one base-class-list edit to `Exit`, plus task group 5's own explicitly
      mandated fold of the two inline wilderness `get_world_clock().advance(...)` calls onto
      `charge_movement(...)` — behavior-preserving by design, D-1) and removes no existing behavior.
- [x] 10.3 Confirm no file added or edited by this change contains a reference to `world/ai/` or an
      LLM call.
- [x] 10.4 Confirm `rulebook/clock.yaml`'s `converse` entry is unchanged and unconsumed by this
      change.
- [x] 10.5 Delete or leave in place (per reviewer preference) the scratch verification probe
      `tmp/probe_movement_clock/`; it is not part of the shipped suite either way.
- [x] 10.6 Run `openspec validate map-movement-clock --strict` and `openspec validate --all --strict`
      and confirm both pass.
