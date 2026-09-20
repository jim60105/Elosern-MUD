Every test command below runs with `MUD_TEST_SETTINGS=1` supplied through the Bash tool's `env`
input — an inline prefix is rejected by the Evennia test guard.

## 1. Scale

- [ ] 1.1 Add a `price_scales:` section to `world/rules/rulebook/commerce.yaml` keyed by settlement
  and an optional `price_scale` on each shop row, and validate both as integers in 1..1000, the
  place value overriding the settlement value. Verify an out-of-range or non-integer scale raises
  naming the declaring settlement or place.
- [ ] 1.2 Apply the scale in `world/rules/guild_config.py` offer resolution as
  `(base * scale + 50) // 100`, once per base value, for buy and sell independently. Verify the
  rounding boundary behavior with a behavior test over SYNTHETIC assortment rows.

## 2. Overrides, additions and removals

- [ ] 2.1 Add an `overrides:` list to each shop row requiring all five offer fields, wholly
  replacing the assortment rule and bypassing the scale. Verify a partial override raises naming
  the missing fields.
- [ ] 2.2 Add `extra_item_keys` and `excluded_item_keys` to `PlaceDefinition` in
  `world/lore/settlements/places.py`, resolving offered goods as assortment union plus additions
  minus removals.
- [ ] 2.3 Reject an override naming an item the place does not offer, an addition carrying no
  override, and a removal matching no assortment item — each naming the place and the item.
  Verify with
  `uv run --locked evennia test --settings test_settings.py --keepdb world.rules.tests.test_guild_config`.

## 3. Post-scaling validation

- [ ] 3.1 Move the price-band, sell-not-above-buy and non-negative-integer checks to run against
  the resolved values rather than the assortment bases, with errors naming the place, the item and
  the resolved value. Verify a base that is legal at par and illegal at a scale raises.
- [ ] 3.2 Verify the resolved `ShopConfig` shape is unchanged and that buying and selling settle as
  before with
  `uv run --locked evennia test --settings test_settings.py --keepdb world.rules.tests.test_shop_economy`.

## 4. Handoff

- [ ] 4.1 Verify the same item key offered at two places with different resolved prices yields one
  item definition at both, using SYNTHETIC places rather than shipped content.
- [ ] 4.2 Run `uv run --locked python -m tools.test_data_lint check` and
  `openspec validate place-price-scaling --strict`.
