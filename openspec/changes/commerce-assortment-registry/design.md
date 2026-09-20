## Context

See `proposal.md` — Why, and
`docs/superpowers/specs/2026-09-20-settlement-shops-design.md` §3.1 for the
layer sketch.

The constraint that shapes everything here is the repository's registry
split: immutable identity lives in `world/lore/*` as frozen dataclasses,
tunable numbers live in `world/rules/rulebook/*.yaml`, and
`world/rules/guild_config.py` joins them at load time and fails closed.
`world/rules/economy.py` and `commands/economy.py` consume the joined
result — a `ShopConfig` carrying hours and a tuple of `ItemOfferRule` — and
know nothing about where it came from.

## Goals / Non-Goals

**Goals:**

- Collapse the per-shop alignment cost to per-assortment.
- Keep the joined `ShopConfig` byte-identical in shape so nothing downstream
  changes.
- Fix the completeness-check defect as part of removing the field that
  caused it.

**Non-Goals:**

- Places, settlements, interiors, hosts. A shop is still a hand-written
  `ShopDefinition` row; `settlement-place-registry` derives it later.
- Price scaling and per-item overrides. `place-price-scaling` adds those.
- Splitting the general store into specialist shops. This change only
  regroups its goods into assortments; `altoria-trading-places` creates the
  shops that consume them.

## Decisions

**Assortment identity in lore, numbers in YAML — the same split as shops.**
The alternative was to put the item list in the YAML alongside the offers,
collapsing the two sources into one and removing the alignment check
entirely. Rejected: the alignment check is the project's only guard against
an item silently vanishing from a shelf during a rename, and the split is
what makes item sets reviewable as lore rather than as configuration. The
cost of keeping it is now paid once per assortment instead of once per shop,
which was the actual problem.

**A new `commerce.yaml` rather than growing `guild_economy.yaml`.**
`guild_economy.yaml` is already 473 lines and mixes four unrelated domains
(merit thresholds, exam profiles, quest rewards, shops, host roster). Moving
commerce out leaves the guild file coherent and gives later changes —
scaling, per-settlement content — a file whose contents are all one subject.
The rulebook loader reads files by name, so a second file is free.

**Shops keep a flat resolved view.** The union of assortments is computed at
load time and handed downstream as the existing `ShopConfig` shape. The
alternative — teaching `world/rules/economy.py` about assortments so it
could resolve lazily — would push the indirection into the trade transaction
for no benefit and would make a merchant's persisted stock keys depend on
resolution order.

**Union semantics, and duplicate keys across assortments are an error.**
Two referenced assortments both containing `healing_potion` would leave the
resolver choosing a price. Rather than pick a precedence rule nobody would
remember, the join rejects the overlap and names both assortments. Shops
that genuinely need one item from an otherwise-wrong bundle get
`extra_item_keys` in `place-price-scaling`; until then, the assortments
shipped here are deliberately non-overlapping.

**Four capital assortments, not one.** The 58-item monolith could have moved
into a single `altoria_stock` assortment, which would be a smaller diff.
Rejected: that would preserve the monolith under a new name and give
`altoria-trading-places` the same redistribution work with an extra
migration step in front of it. Splitting now by the axis the specialist
shops will use — weapons, armour, food, sundries — means the later change
adds shops and moves references, not items.

## Risks / Trade-offs

- **The general store temporarily references all four assortments**, so
  between this change and `altoria-trading-places` the capital looks exactly
  as it does today while the data underneath is already split. → Intended:
  it keeps this change behaviour-neutral for players and makes the later
  change a pure content move.
- **`merchant_component_key` removal touches the synthetic test fixtures**
  in `world/tests/synthetic_data/`, which construct `ShopDefinition`
  directly. → Mechanical; the field has no readers other than the broken
  check.
- **The completeness-check fix can only be proven with two shops**, and this
  change ships one. → The regression test builds a synthetic two-shop
  registry rather than relying on shipped content, which is also what the
  behaviour-test rule requires.
