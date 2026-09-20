## Why

Once shops share assortments, they share prices. That is the point of an
assortment for a baseline supply, and wrong for everything else.

The world requires the same goods to cost different amounts in different
places. `docs/lore/settlement-locations.md` makes this concrete: elven
villages do not trade outward, so what an elf sells at home for pocket change
is scarce anywhere else; a frontier outpost supplied by an occasional caravan
is dearer across the board than a capital on a trade road; a port city's
chandlery undercuts an inland forge on rope and nails.

None of that is expressible. An assortment's offer is the price, everywhere
it is referenced. The only workaround is to clone the assortment per
settlement — which duplicates the goods list to vary one number, and makes
"is this the same thing?" unanswerable.

Crucially, the goods must stay *the same goods*. A blade bought in an elven
village and the same blade bought in a capital must be one item key backed by
one item definition; only the price differs. Cloning assortments cannot
guarantee that, and would let the two drift.

A place also cannot stock anything outside its assortments. A general store
that carries one imported curiosity has no way to say so short of authoring a
one-item assortment for it.

## What Changes

- Add a **price scale**: an integer percentage applied to an assortment's
  base prices. A settlement declares a default; a place may declare its own.
  `100` is par. Scaling is integer arithmetic with half-up rounding, so no
  float enters the copper path.
- Add **per-item overrides**: a place may replace an assortment's rule for
  one item outright. An override is absolute — it is not scaled — which keeps
  the resolved price to a single multiplication and removes any
  rounding-order question.
- An override is **complete or rejected**: all five fields (buy, sell, max
  stock, initial stock, restock quantity) or none. A partially specified rule
  implies a silent merge, which is exactly what the fail-closed loader exists
  to prevent.
- Add **per-place item additions and removals**: a place may stock an item
  outside its assortments, or decline one inside them. An addition belongs to
  no assortment and therefore has no base rule, so it SHALL carry a complete
  override; overrides are the supply route for additions as well as the
  variation route for assortment items.
- Validation runs **after** scaling: the scaled buy price must still sit in
  the item's price band, the scaled sell price must not exceed the scaled buy
  price, and the scale must be a sane integer. A violation fails catalog load
  at startup rather than surfacing at trade time.

## Capabilities

### New Capabilities

- `place-price-scaling`: how a place's final offer is resolved from an
  assortment base, a settlement or place scale, and per-item overrides,
  additions and removals — and what is rejected at load.

### Modified Capabilities

None. `shop-economy`'s rules are unchanged: prices are still exact integer
copper, still band-checked, still reject sell-above-buy. This change changes
where the number being checked comes from, not what is checked.

## Impact

- `world/rules/rulebook/commerce.yaml` — a `price_scales:` section, and
  optional `price_scale` and `overrides` on each shop row.
- `world/lore/settlements/places.py` — `PlaceDefinition` gains
  `extra_item_keys` and `excluded_item_keys`.
- `world/rules/guild_config.py` — offer resolution gains the scale-then-
  override pipeline and the post-scaling re-validation; the new rejections
  (partial override, override naming an unoffered item, addition without an
  override, out-of-range scale) live here.
- `world/rules/economy.py`, `commands/economy.py`,
  `typeclasses/components.py` — unchanged. Resolution still produces the
  same flat `ShopConfig`.
- **Depends on `settlement-place-registry`**: scales and overrides are
  authored per place, and additions and removals are place fields.
- **Conflicts with `altoria-trading-places` and `ciaran-village-commerce`**
  on `commerce.yaml`, in different sections. Land this first so both content
  changes author against the final schema.
