Every test command below runs with `MUD_TEST_SETTINGS=1` supplied through the Bash tool's `env`
input — an inline prefix is rejected by the Evennia test guard.

## 1. Assortment identity

- [x] 1.1 Create the `world/lore/settlements/` package with `assortments.py` holding a frozen
  `AssortmentDefinition` (key, `display_name_zh`, `item_keys`) and `ASSORTMENT_REGISTRY`. Verify
  the module imports and the registry is keyed by definition key.
- [x] 1.2 Add the four capital assortments — weapons, armour, food, remaining sundries — covering
  exactly the 58 keys `altoria_general_store` offers today, with no key in two assortments.
  Verify no key is lost or duplicated relative to the pre-change offered set.

## 2. Tunable rules

- [x] 2.1 Create `world/rules/rulebook/commerce.yaml` with an `assortments:` section carrying each
  assortment's per-item offer rules, transcribed from the existing `guild_economy.yaml` values, and
  a `shops:` section carrying only each shop's hours. Verify the rulebook loads.
- [x] 2.2 Remove the `shops:` block from `world/rules/rulebook/guild_economy.yaml`, leaving merit
  thresholds, exam profiles, quest rewards and the service-host roster in place. Verify the guild
  catalog still loads.

## 3. The join

- [x] 3.1 Split `validate_shop_configs` in `world/rules/guild_config.py` into assortment validation
  (item/offer alignment, money, band and stock rejections, evaluated once per assortment) and shop
  resolution (assortment lookup, union, hours). Verify the resolved `ShopConfig` shape is unchanged
  so `world/rules/economy.py` and `commands/economy.py` need no edit.
- [x] 3.2 Reject a shop referencing an unknown assortment, and reject an item key appearing in two
  of one shop's referenced assortments, each naming the shop and the offender.
- [x] 3.2a Reject an assortment containing a keepsake (`relic`) band item at any price, naming the
  assortment and the item. Cover it with a behavior test over a SYNTHETIC item registry carrying a
  file-local keepsake-band fixture item, not a shipped keepsake.
- [x] 3.3 Re-key the shops-completeness check on `shop_key` and delete
  `ShopDefinition.merchant_component_key`. Cover the defect with a behavior test over a SYNTHETIC
  two-shop registry where the second shop has no rules, and verify with
  `uv run --locked evennia test --settings test_settings.py --keepdb world.rules.tests.test_shop_economy`.
- [x] 3.4 Replace `ShopDefinition.offered_item_keys` with `assortment_keys` in
  `world/lore/shops.py`, deriving the offered set at load. Verify the existing authored-identity and
  cross-registry uniqueness validators still run over the derived rows.

## 4. Fixtures and handoff

- [x] 4.1 Update the shop factories in `world/tests/synthetic_data/` to build assortment-shaped
  rows, and verify with
  `uv run --locked evennia test --settings test_settings.py --keepdb world.lore.tests.test_shops`.
- [x] 4.2 Verify a purchase and a sale against the capital store settle exactly as before with
  `uv run --locked evennia test --settings test_settings.py --keepdb commands.tests.test_guild_economy_commands`.
- [x] 4.3 Run `uv run --locked python -m tools.test_data_lint check` and
  `openspec validate commerce-assortment-registry --strict`.
