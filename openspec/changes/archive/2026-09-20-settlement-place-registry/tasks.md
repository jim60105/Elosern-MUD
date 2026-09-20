Every test command below runs with `MUD_TEST_SETTINGS=1` supplied through the Bash tool's `env`
input — an inline prefix is rejected by the Evennia test guard.

## 1. Settlement and place records

- [x] 1.1 Add `world/lore/settlements/settlements.py` with `SettlementArchetype` (the six lore
  archetypes), a frozen `SettlementDefinition` (key, archetype, zcoord) and `SETTLEMENT_REGISTRY`
  holding `capital_altoria`. Verify each settlement key resolves in `ANCHOR_REGISTRY`.
- [x] 1.2 Add `world/lore/settlements/places.py` with `PlaceKind`, a frozen `PlaceDefinition`
  carrying the fields listed in the design — including `host_race`, `host_subrace` and `host_sex`,
  which stay unread until `place-driven-service-sync` — and a `PLACE_REGISTRY` assembled from
  per-settlement modules the way `world/lore/items/assembly.py` concatenates its slices.
- [x] 1.3 Validate the record: unknown settlement, unknown race, unknown sex, a subrace whose own
  race disagrees with `host_race`, and assortments declared without a shop identity or vice versa.
  Verify with
  `uv run --locked evennia test --settings test_settings.py --keepdb world.lore.tests.test_settlements`.
- [x] 1.4 Add `world/lore/settlements/places_altoria.py` holding the capital's guild hall and
  general store, transcribed from the constants in `world/maps/bootstrap.py` and the roster rows in
  `guild_economy.yaml`. Author `host_subrace=None` for both unless the neutrality comparison in
  `place-driven-service-sync` is extended to stats (see the design's risk note).
- [x] 1.5 Register the new registries in `world/lore/sync.py::_ALL_REGISTRIES`.

## 2. Derivation

- [x] 2.1 Add `world/lore/settlements/shops.py` deriving `SHOP_REGISTRY` from the places that
  declare a `shop_key`, and move `validate_shop_npc_identities` and
  `validate_registry_identity_uniqueness` into it unchanged. Delete `world/lore/shops.py` and
  repoint `world/rules/guild_config.py`. Keep lore's imports of `world/rules/*` function-local.
- [x] 2.2 Derive the service-host roster from `PLACE_REGISTRY` in `world/rules/guild_config.py`,
  keeping every existing rejection (missing field, unknown profession, blueprint coverage, dead
  kwarg, person-bound component on an anchored row). Remove the `service_hosts:` block from
  `world/rules/rulebook/guild_economy.yaml`.
- [x] 2.3 Verify the cross-registry authored-name uniqueness rule still fires on a planted
  collision between a derived row and a guild registry row, with
  `uv run --locked evennia test --settings test_settings.py --keepdb world.rules.tests.test_guild_config`.

## 3. Neutrality

- [x] 3.1 Verify the derived roster rows equal the removed YAML rows field for field — same names,
  titles, professions, room tags, `service_id`s and component kwargs — and that
  `world/rules/guild_economy.py`, `world/maps/bootstrap.py` and `commands/economy.py` are
  unmodified by this change.
- [x] 3.2 Verify startup still creates the two interiors and the two hosts unchanged with
  `uv run --locked evennia test --settings test_settings.py --keepdb world.rules.tests.test_guild_economy_sync`.
- [x] 3.3 Run `uv run --locked python -m tools.test_data_lint check` and
  `openspec validate settlement-place-registry --strict`.
