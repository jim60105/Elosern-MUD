## Why

A shop's goods are declared twice and validated pairwise. `SHOP_REGISTRY`
(`world/lore/shops.py`) lists every offered item key; `guild_economy.yaml`'s
`shops:` block repeats each of those keys with its buy/sell/stock/restock
numbers; and `world/rules/guild_config.py` rejects the catalog if the two
lists disagree in either direction.

That fail-closed contract is correct and worth keeping. What is wrong is
that it is paid **per shop**. The one shipped shop carries 58 items, so its
YAML block is 58 × 6 lines. `docs/lore/settlement-locations.md` describes
eight trading place types across six settlement archetypes; under this model
the same 雜貨 baseline would be re-declared, re-priced and re-validated once
per shop that stocks it.

There is also no way to say that two shops sell *the same thing*. Two shops
stocking `healing_potion` are two unrelated coincidences of key, so a change
to the baseline supply has to be made everywhere by hand and nothing detects
a miss.

### A defect the second shop would expose

`world/rules/guild_config.py:227`:

```python
known_parents = {definition.merchant_component_key: definition.key
                 for definition in SHOP_REGISTRY.values()}
```

`merchant_component_key` is `"merchant"` for every shop, so this dict holds
exactly one entry no matter how many shops exist — later rows overwrite
earlier ones. The loop's `known_parents.pop(...)` then clears it on the first
shop, and the closing "shops is missing rules for …" completeness check
becomes a no-op. With one shop the bug is invisible. With two, a shop whose
entire YAML rule block is absent loads silently.

The field carries no information — its value is constant — so it is removed
rather than repaired.

## What Changes

- Introduce **assortments**: named, reusable bundles of goods. An assortment
  declares which item keys it contains (immutable identity) and what each
  costs and stocks (tunable numbers). The existing item/offer alignment
  contract is preserved verbatim but now binds an assortment to its own
  offers, so ten shops referencing one assortment pay the alignment cost
  once.
- A shop's offered goods become the union of the assortments it references.
  `ShopDefinition` gains `assortment_keys` and loses its hand-listed
  `offered_item_keys`, which is now derived.
- **BREAKING** (authored data): the 58-item monolith shipped as
  `altoria_general_store` is redistributed into four non-overlapping
  assortments — weapons, armour, food, and the remaining sundries. The
  capital's total item coverage is unchanged; only the grouping is new.
  Shops for the first three do not exist yet, so the general store
  references all four until `altoria-trading-places` splits them apart.
- **BREAKING** (authored data): commerce numbers move out of
  `guild_economy.yaml` into a new `commerce.yaml` rulebook. Guild merit,
  exam profiles, quest rewards and the service-host roster stay where they
  are.
- **BREAKING**: `ShopDefinition.merchant_component_key` is removed and the
  shops-completeness check is re-keyed on `shop_key`, fixing the defect
  above.
- Reject an assortment containing an item in the keepsake (`relic`) band.
  `masterwork-gear-price-band` states that rule; this change owns the
  validator it belongs in, and an assortment is the only route by which an
  item reaches a shelf, so one check closes it for every shop.

## Capabilities

### New Capabilities

- `commerce-assortments`: named reusable goods bundles, the item/offer
  alignment contract at assortment granularity, and the rule that a shop's
  offered goods are derived from the assortments it references.

### Modified Capabilities

- `shop-economy`: the "Item and shop identities are immutable while numeric
  trade rules are YAML and lore-constrained" requirement changes on three
  points — a shop's offered keys are derived from assortments rather than
  hand-listed, the numeric source file is `commerce.yaml` rather than
  `guild_economy.yaml`, and the per-shop completeness check is keyed on shop
  identity rather than on a constant component key.

## Impact

- `world/lore/settlements/` — new package; `assortments.py` holds
  `AssortmentDefinition` and `ASSORTMENT_REGISTRY`.
- `world/lore/shops.py` — `ShopDefinition` gains `assortment_keys`, loses
  `merchant_component_key` and its literal `offered_item_keys`.
- `world/rules/rulebook/commerce.yaml` — new file: assortment offers plus
  per-shop hours.
- `world/rules/rulebook/guild_economy.yaml` — the `shops:` block is removed.
- `world/rules/guild_config.py` — `validate_shop_configs` splits into
  assortment validation and shop resolution; the completeness check is
  re-keyed; the keepsake-band rejection lands in the assortment validator.
- `world/rules/economy.py`, `commands/economy.py`,
  `typeclasses/components.py` — unchanged. Shops still resolve to a flat
  `ShopConfig` with a tuple of offers, so trade, stock, restock and the
  player commands see no difference.
- `world/tests/synthetic_data/` — the shop factories gain assortment-shaped
  fixtures.
- **Relationship to `masterwork-gear-price-band`**: that change is confined
  to `world/lore/economy.py` and the item data modules and deliberately does
  not touch `world/rules/guild_config.py`, precisely so it does not collide
  with the `validate_shop_configs` split here. The two share no file and
  either order works. No `relic`-band item appears in the 58-item monolith,
  so the redistribution is unaffected either way; if that change lands first,
  its six migrated items are simply no longer keepsakes.
