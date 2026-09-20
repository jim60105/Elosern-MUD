Every test command below runs with `MUD_TEST_SETTINGS=1` supplied through the Bash tool's `env`
input — an inline prefix is rejected by the Evennia test guard.

## 1. Registry-driven interiors

- [x] 1.1 Replace the two interior constant blocks and their bespoke call sites in
  `world/maps/bootstrap.py::sync_service_interiors` with a loop over `PLACE_REGISTRY` grouped by
  `settlement_key`, resolving each group's exterior coordinates in that settlement's zcoord.
- [x] 1.2 Keep the existing behaviour for an unresolvable exterior — warn naming the row, skip it,
  continue with the remaining places — and verify one bad place does not stop the others.
- [x] 1.3 Verify a repeated run reuses the tagged room, re-applies the authored description in
  place, and duplicates no doorway, with
  `uv run --locked evennia test --settings test_settings.py --keepdb world.maps.tests.test_bootstrap world.maps.tests.test_service_interiors`.

## 2. Authored host identity

- [x] 2.1 In `world/rules/guild_economy.py::_sync_service_host`, replace the hard-coded
  `host.race = "human"` with the place's authored `host_race`, `host_subrace` and `host_sex`,
  written inside the `host is None` branch beside `npc_title` and before `apply_race_baseline()`.
- [x] 2.2 Verify a re-sync leaves an existing host's race, subrace and sex untouched when the
  authored values change, matching the never-rename/never-retitle contract.

## 3. Shop naming

- [x] 3.1 Add `display_name_zh` to `ShopConfig` in `world/rules/guild_config.py`, populated during
  shop resolution from the owning place's `room_name_zh`.
- [x] 3.2 Print it in the stock listing header in `commands/economy.py` so two shops are
  distinguishable by their listing alone, and verify with
  `uv run --locked evennia test --settings test_settings.py --keepdb commands.tests.test_guild_economy_commands`.

## 4. Handoff

- [x] 4.1 Verify the two shipped hosts are recreated correctly against an emptied database with
  `uv run --locked evennia test --settings test_settings.py --keepdb world.rules.tests.test_guild_economy_sync`.
  If `places_altoria.py` authors a subrace for them rather than `None`, compare stats too, not just
  identity fields.
- [x] 4.2 Verify adding a place row produces its interior, both doorways, its host and its
  purchasable goods with no module constant added for it.
- [x] 4.3 Run `uv run --locked python -m tools.test_data_lint check` and
  `openspec validate place-driven-service-sync --strict`.
