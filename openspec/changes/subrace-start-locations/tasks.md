# Tasks

Test commands follow AGENTS.md: run each command on its own, with nothing piped after it.
`EV` below stands for
`uv run --locked --env-file=.env.evennia-test evennia test --settings test_settings.py --keepdb`.
Requirement IDs: take the exact strings from
`uv run --locked python -m tools.spec_traceability list`.

## 1. Lore registry (design D1, D5)

- [x] 1.1 Create `world/lore/start_locations.py`, starting with a module docstring that
  names this change. Add the `SubraceStartLocation` frozen dataclass,
  `SUBRACE_START_LOCATION_REGISTRY` (exactly the 15 rows of the design D5 table, in
  `SUBRACE_REGISTRY` order) and `validate_start_locations(registry, subraces)` with the
  five error messages, in the order D1 gives. Call it at module bottom against
  `SUBRACE_REGISTRY`. Add `__all__`.
- [x] 1.2 Add the `start_locations` `_spec(...)` line from D1 to
  `world/lore/registry_index.py`, right after the `starting_kits` line.
- [x] 1.3 Create `world/lore/tests/test_start_locations.py` (`unittest.TestCase`; build
  synthetic subraces with `world.tests.synthetic_data.make_subrace`, never shipped
  keys). Add one test for each of the five rejection branches and one acceptance test,
  all annotated with
  `character-start-location::every-subrace-declares-exactly-one-start-settlement`.
  Acceptance: `EV world.lore.tests.test_start_locations` passes, and
  `uv run --locked python -m tools.test_data_lint check` is clean.

## 2. Adoption-time closure (design D2)

- [x] 2.1 In `world/maps/static_references.py`, add the `start_locations` field to
  `StaticWorld` after `place_rooms`. Add the problems loop and the fingerprint part
  exactly as in D2. Pass the field from `published_static_world()` and from
  `static_world_for_candidate()`.
- [x] 2.2 In `world/maps/tests/test_static_map_references.py`, add tests that build a
  `StaticWorld` with `dataclasses.replace(published_static_world(), ...)` on the
  published shipped world:
  (a) a start row pointing at an anchor key absent from `anchor_placements` gives a
  problem string containing the subrace and the anchor, and `validate_static_world`
  raises `StaticReferenceError`;
  (b) the published world has no `start location` problem;
  (c) changing one row's anchor key changes `fingerprint`.
  Use `t_` keys for the injected subrace and anchor. Annotate the tests with
  `character-start-location::start-settlements-resolve-before-map-world-adoption`.
  Acceptance: `EV world.maps.tests.test_static_map_references` passes.

## 3. Resolver (design D3)

- [x] 3.1 Create `world/rules/start_location.py` with `StartLocationError` and
  `resolve_start_room`, exactly as in D3. Add `start_location.py` to the "Character
  creation, traits, identity" row of `world/rules/AGENTS.md`.
- [x] 3.2 Create `world/rules/tests/test_start_location.py` (`EvenniaTest`):
  - Call `publish_shipped_map_world()` in `setUpModule`.
  - Use the scope `synthetic_registries("subraces", "start_locations", "anchor_placements")`.
  - Read the map id from `SYNTH_ANCHOR_PLACEMENTS[SYNTH_START_LOCATIONS[k].anchor_key].node.map_id`,
    and call `sync_test_settlements((map_id,))` in `setUpTestData`.

  Tests:
  (a) resolution returns the `GridRoom` at `anchor_entrance_xyz(placement)`;
  (b) with `extra={"anchor_placements": {anchor: AnchorPlacement(anchor, _SYNTH_SECOND_GATE_REF)}}`,
  resolution returns the room at the second ref's coordinate (same map, already
  materialized);
  (c) each of these raises `StartLocationError`: an unknown subrace, an anchor with no
  placement (an extra start row naming `t_nowhere`), and a placement whose room was
  deleted.

  Annotate the tests with
  `character-start-location::a-subrace-s-start-room-is-its-settlement-s-anchor-room`.
  Acceptance: `EV world.rules.tests.test_start_location` passes.

## 4. Synthetic kit (design D4)

- [x] 4.1 Add `SYNTH_START_LOCATIONS` to `world/tests/synthetic_data/data_characters.py`.
  Register it in `targets.py` (in the content table and in `REGISTRY_TARGETS`), export
  it from `world/tests/synthetic_data/__init__.py`, and add the coupling note from D4 to
  that module's docstring. Acceptance: `EV world.tests.test_synthetic_data` passes.
- [x] 4.2 Run
  `rg -n "synthetic_registries\([^)]*anchor_placements" --glob '*.py' commands server typeclasses web world tests`.
  For each scope that swaps `anchor_placements`, check whether the same test calls
  `sync_grid`, `sync_all`, `sync_interiors` or `runtime.adopt` inside the scope. If one
  does, add `"start_locations"` to that scope. On e076e764 no such scope exists, so this
  is a check.

## 5. Verification

- [x] 5.1 `uv run --locked python -m tools.shard_register fix` (two new test modules),
  then `uv run --locked python -m tools.contract_gate --change subrace-start-locations`.
  It must exit 0.
- [x] 5.2 Run `EV world.maps.tests.test_settlement_reload` and
  `EV world.lore.tests.test_registry_index_contract`. Both must pass.
- [x] 5.3 `openspec validate subrace-start-locations --strict` passes.
