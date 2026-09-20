Every test command below runs with `MUD_TEST_SETTINGS=1` supplied through the Bash tool's `env`
input — an inline prefix is rejected by the Evennia test guard.

## 1. Settlement and place records

- [ ] 1.1 Add `world/lore/settlements/settlements.py` with `SettlementArchetype` (the six lore
  archetypes), a frozen `SettlementDefinition` (key, archetype, zcoord) and `SETTLEMENT_REGISTRY`
  holding `capital_altoria`. Verify each settlement key resolves in `ANCHOR_REGISTRY`.
- [ ] 1.2 Add `world/lore/settlements/places.py` with `PlaceKind`, a frozen `PlaceDefinition`
  carrying the fields listed in the design, and a `PLACE_REGISTRY` assembled from per-settlement
  modules in the manner `world/lore/items/assembly.py` concatenates its slices.
- [ ] 1.3 Add `world/lore/settlements/places_altoria.py` holding the capital's guild hall and
  general store, transcribed from the constants in `world/maps/bootstrap.py` and the roster rows in
  `guild_economy.yaml`. Verify the derived values equal the pre-change ones.
- [ ] 1.4 Register the new registries in `world/lore/sync.py::_ALL_REGISTRIES`.

## 2. Derivation

- [ ] 2.1 Add `world/lore/settlements/shops.py` deriving `SHOP_REGISTRY` from the places that
  declare a `shop_key`, and move `validate_shop_npc_identities` and
  `validate_registry_identity_uniqueness` into it unchanged. Delete `world/lore/shops.py` and
  repoint `world/rules/guild_config.py`.
- [ ] 2.2 Derive the service-host roster from `PLACE_REGISTRY` in `world/rules/guild_config.py`,
  keeping every existing rejection (missing field, unknown profession, blueprint coverage, dead
  kwarg, person-bound component on an anchored row). Remove the `service_hosts:` block from
  `world/rules/rulebook/guild_economy.yaml`.
- [ ] 2.3 Reject a place that declares assortments without a shop identity or a shop identity
  without assortments, and a place naming an unknown settlement. Verify with
  `uv run --locked evennia test --settings test_settings.py --keepdb world.rules.tests.test_guild_config`.

## 3. Host identity

- [ ] 3.1 Add `host_race`, `host_subrace` and `host_sex` to `PlaceDefinition` with load-time
  validation against `RACE_REGISTRY`, `SUBRACE_REGISTRY` and `SEX_VALUES`, including the rule that
  a subrace's own race must match the declared race.
- [ ] 3.2 In `world/rules/guild_economy.py::_sync_service_host`, replace the hard-coded
  `host.race = "human"` with the authored values written inside the `host is None` branch beside
  `npc_title`, before `apply_race_baseline()`. Verify a re-sync leaves an existing host's race,
  subrace and sex untouched.

## 4. Registry-driven interiors and naming

- [ ] 4.1 Replace the two interior constant blocks and their call sites in
  `world/maps/bootstrap.py::sync_service_interiors` with a loop over `PLACE_REGISTRY` grouped by
  settlement, resolving each exterior in its settlement's zcoord. Keep the warn-and-skip path for
  an unresolvable exterior and verify one bad place does not stop the others.
- [ ] 4.2 Add `display_name_zh` to `ShopConfig`, populated during shop resolution from the owning
  place's `room_name_zh`, and print it in the stock listing header in `commands/economy.py`.
  `CmdShopStock` already holds the `ShopConfig`, so it needs no registry lookup of its own. Verify
  with
  `uv run --locked evennia test --settings test_settings.py --keepdb commands.tests.test_guild_economy_commands`.

## 5. Handoff

- [ ] 5.1 Verify the two shipped hosts are recreated bit-for-bit against an emptied database with
  `uv run --locked evennia test --settings test_settings.py --keepdb world.rules.tests.test_guild_economy`,
  and that a repeated sync duplicates nothing.
- [ ] 5.2 Run `uv run --locked python -m tools.test_data_lint check` and
  `openspec validate settlement-place-registry --strict`.
