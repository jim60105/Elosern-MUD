# Tasks

Test commands follow AGENTS.md: run each command on its own, with nothing piped after it.
`EV` below stands for
`uv run --locked --env-file=.env.evennia-test evennia test --settings test_settings.py --keepdb`.

## 1. Lore registry (design D1, D7)

- [ ] 1.1 Create `world/lore/start_locations.py`, starting with a module docstring that
  names this change. Add the `SubraceStartLocation` frozen dataclass,
  `SUBRACE_START_LOCATION_REGISTRY` (exactly the 15 rows of the design D7 table, in
  `SUBRACE_REGISTRY` order) and `validate_start_locations(registry, subraces)` with the
  five error messages, in the order D1 gives. Call it at module bottom against
  `SUBRACE_REGISTRY`. Add `__all__`.
- [ ] 1.2 Add the `start_locations` `_spec(...)` line from D1 to
  `world/lore/registry_index.py`, right after the `starting_kits` line.
- [ ] 1.3 Create `world/lore/tests/test_start_locations.py` (`unittest.TestCase`; build
  synthetic subraces with `world.tests.synthetic_data.make_subrace`, never shipped
  keys). Add one test for each of the five rejection branches and one acceptance test.
  Annotate them with
  `@covers_requirement("character-start-location::every-subrace-declares-exactly-one-start-settlement")`.
  Get the exact ID from `uv run --locked python -m tools.spec_traceability list` after
  the archive sync. Until then, use the ID that command prints for the change.
  Acceptance: `EV world.lore.tests.test_start_locations` passes, and
  `uv run --locked python -m tools.test_data_lint check` is clean.

## 2. Adoption-time closure (design D2)

- [ ] 2.1 In `world/maps/static_references.py`, add the `start_locations` field to
  `StaticWorld` after `place_rooms`. Add the problems loop and the fingerprint part
  exactly as in D2. Pass the field from `published_static_world()` and from
  `static_world_for_candidate()`.
- [ ] 2.2 In `world/maps/tests/test_static_map_references.py`, add tests that build a
  `StaticWorld` with `dataclasses.replace(published_static_world(), ...)` on the
  published shipped world:
  (a) a start row pointing at an anchor key absent from `anchor_placements` gives a
  problem string containing the subrace and the anchor, and `validate_static_world`
  raises `StaticReferenceError`;
  (b) the published world has no `start location` problem;
  (c) changing one row's anchor key changes `fingerprint`.
  Use synthetic keys (`t_` prefix) for the injected subrace and anchor. Annotate with
  `character-start-location::start-settlements-resolve-before-map-world-adoption`.
  Acceptance: `EV world.maps.tests.test_static_map_references` passes.

## 3. Resolver (design D3)

- [ ] 3.1 Create `world/rules/start_location.py` with `StartLocationError` and
  `resolve_start_room`, exactly as in D3. Add a row for it to the "Character creation,
  traits, identity" line of `world/rules/AGENTS.md`.
- [ ] 3.2 Create `world/rules/tests/test_start_location.py` (`EvenniaTest`). Call
  `publish_shipped_map_world()` in `setUpModule`. Use the scope
  `synthetic_registries("subraces", "start_locations", "anchor_placements")`. Read the
  map id from `SYNTH_ANCHOR_PLACEMENTS[SYNTH_START_LOCATIONS[k].anchor_key].node.map_id`
  and call `sync_test_settlements((map_id,))` in `setUpTestData`. Tests:
  (a) resolution returns the `GridRoom` at `anchor_entrance_xyz(placement)`;
  (b) with `extra={"anchor_placements": {anchor: AnchorPlacement(anchor, _SYNTH_SECOND_GATE_REF)}}`,
  materialized through the same map, resolution returns the room at the second ref's
  coordinate;
  (c) an unknown subrace, an anchor with no placement (an extra row naming `t_nowhere`),
  and a placement whose room was deleted each raise `StartLocationError`.
  Annotate with `character-start-location::a-subrace-s-start-room-is-its-settlement-s-anchor-room`
  (take the exact ID from the traceability list).
  Acceptance: `EV world.rules.tests.test_start_location` passes.

## 4. Activation (design D4)

- [ ] 4.1 In `world/rules/character_creation.py`: add `"map_knowledge"` to
  `_CREATION_ATTRIBUTE_KEYS`, add `from world.rules import start_location`, add the
  pre-transaction resolution and `origin` capture, the in-transaction placement block
  (between the `creation_draft` removal and the starting-companions block), the
  `restore_activation_placement` helper, the updated `except` order, and the
  `character_start_placed` info event. All of it is verbatim from D4. Update the
  docstring of `activate_player_character` with one sentence on placement.
- [ ] 4.2 In `world/rules/creation_wizard.py::activate_draft`, capture `origin` before
  the `try` and call `restore_activation_placement(character, origin)` first in the
  `except`.
- [ ] 4.3 Add placement tests to
  `world/rules/tests/test_character_creation/test_activation_rollback.py`, using the
  synthetic scope from 3.2 plus the module's existing registries:
  (a) replace `test_successful_activation_leaves_the_shell_in_place` with
  `test_successful_activation_places_the_character_in_its_start_room`. A custom
  activation of `t_duskmari_evensong` ends with `location` and `home` equal to the
  resolved room, `map_knowledge["visited"]` containing the key
  `encode_grid(room.xyz[2], int(room.xyz[0]), int(room.xyz[1]))`
  (`world.rules.map_knowledge.encode_grid(z_map_key, x, y)`), the same dbref and
  puppet, and an unchanged clock tick;
  (b) a preset activation of a synthetic preset with that subrace lands in the same room;
  (c) with `resolve_start_room` patched to raise `StartLocationError`, activation raises
  `CharacterCreationError`, and the character is still pending, at `old_location`, with
  the old `home` and no `map_knowledge`;
  (d) the shell sits in a room created as `create_object(LimboRoom, key="t_birth")`,
  the stub start room is used, and a `write_observer` raises at stage `start_location`
  and, in a second subtest, at `portrait_policy`. Afterwards the character is in
  `t_birth`, `home` is unchanged, `map_knowledge` is absent, and it is still pending.
  Keep the existing all-stage rollback test. It now also iterates `start_location`.
  Make sure it asserts location and `home`.
  Annotate (a) to (d) with
  `player-character-creation::activation-places-the-character-in-its-subrace-s-start-room`
  and keep the existing `activation-is-an-all-or-nothing-deterministic-core-operation`
  annotations on the rollback tests. Annotate (a) also with
  `map-knowledge::arrival-recording-happens-only-at-existing-successful-arrival-seams`.
- [ ] 4.4 In `world/rules/tests/test_creation_wizard.py`, add a test where
  `activate_draft`'s outer commit fails. Patch `transaction.atomic` in
  `world.rules.creation_wizard` with a context manager whose `__exit__` raises after
  the inner activation succeeds, and use the stub start room. Afterwards the character is
  back at its origin, pending, with its old `home`.
- [ ] 4.5 In `world/rules/tests/test_starting_companions.py`, using the stub start room,
  assert that every built companion's `location` equals the player's `location`, which
  equals the stub start room. Annotate with the 4.3 placement requirement ID.
- [ ] 4.6 In `web/webclient/actions/tests/test_creation_actions/test_fingerprint_activate.py`,
  update the activation hand-off test, using the stub start room: after
  `creation.activate`, the character's `location` and `home` are the stub room and the
  mode is `exploration`. The rollback test asserts the original `location` and `home`.
  Keep the `webclient-character-creation-ui::activation-is-all-or-nothing-and-hands-off-to-exploration`
  annotation.

## 5. Test seams (design D6)

- [ ] 5.1 Create `world/tests/start_room_fixture.py` exactly as in D6.
- [ ] 5.2 Add `SYNTH_START_LOCATIONS` to `world/tests/synthetic_data/data_characters.py`.
  Register it in `targets.py` (content table and `REGISTRY_TARGETS`) and export it from
  `world/tests/synthetic_data/__init__.py`. Acceptance:
  `EV world.tests.test_synthetic_data` passes.
- [ ] 5.3 Apply `stub_start_room()` (class decorator, or `self.enterContext(...)` in
  `setUp`) to every test class that activates a character and is not covered by section
  4. To find them, run
  `rg -l "activate_player_character|activate_draft|_creation_activate_adapter|creation\.activate|character preset|_activate_creation" commands server typeclasses web/webclient world tests --glob '*/tests/*'`.
  On master that is: `commands/tests/test_background.py`,
  `commands/tests/test_character_creation/{_support,test_concept_command,test_concept_prefill,test_pending_gate,test_wizard_activation_flow}.py`,
  `commands/tests/test_command_branch_behaviour.py`,
  `commands/tests/test_persona_commands.py`,
  `server/conf/tests/test_ui_action_integration.py`,
  `typeclasses/tests/{test_account_capacity,test_account_login,test_npc_dialogue}.py`,
  `web/webclient/actions/tests/test_creation_actions/{_support,test_adapter,test_affinity_and_dispatch,test_concept,test_name_roll,test_payload_validation}.py`,
  `web/webclient/actions/tests/test_dispatcher/test_registry.py`,
  `web/webclient/presentation/tests/test_creation_panel/test_presenter.py`,
  `world/lore/tests/test_saintess_vessel_grant.py`,
  `world/rules/tests/test_character_creation/*.py`, `world/rules/tests/test_party.py`.
  Where a `_support.py` base class exists, decorate the base class once. Skip a file
  that only names the command and never activates (for example `tests/test_command_docs.py`).
  When an existing assertion pins the pre-change location after a successful activation,
  change it to the stub room. Change nothing else.
- [ ] 5.4 In `web/tests/browser/seed/runner.py` (both `activate_player_character`
  calls) and `web/tests/browser/seed/npc_persona_fixture.py`, wrap the activation in the
  seed patch from D6, returning the room the seed just placed the character in.
- [ ] 5.5 Extend `web/tests/browser/fixtures.py::journey_settlement_scope` with the
  creation-only union from D6, and add one sentence to its docstring.

## 6. Verification

- [ ] 6.1 Run each module touched in sections 4 and 5 with `EV <dotted.module>`, one at
  a time. Each must pass.
- [ ] 6.2 `uv run --locked python -m tools.shard_register fix` (two new test modules),
  then `uv run --locked python -m tools.contract_gate --change subrace-start-settlements`.
  It must exit 0.
- [ ] 6.3 `uv run --locked python -m tools.observability_lint check` is clean, including
  the new `log_warn` and `log_info` calls.
- [ ] 6.4 Run `pnpm run build`, then
  `uv run --locked python -m web.tests.browser.unittest_driver web.tests.browser.test_browser_creation_preset`
  and `... web.tests.browser.test_browser_creation_custom`. Then run
  `EV web.webclient.actions.tests.test_party_management_acceptance_fixture` (the
  synthetic boot path). All must pass.
- [ ] 6.5 Add a short "Start location" paragraph to
  `docs/development/adding-player-presets.md`: a preset starts in its subrace's row of
  `world/lore/start_locations.py`, a new subrace must add a row, and the row names the
  settlement's anchor key only.
- [ ] 6.6 `openspec validate subrace-start-settlements --strict` passes.
