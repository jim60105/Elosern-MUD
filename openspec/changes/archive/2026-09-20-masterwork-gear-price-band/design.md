## Context

See `proposal.md` — Why, and
`docs/superpowers/specs/2026-09-20-settlement-shops-design.md` §5 for the
full item survey.

Two existing contracts shape the approach. `PRICE_TABLE`
(`world/lore/economy.py`) is a flat map from a band key to an inclusive
copper range, and `world/rules/guild_config.py::validate_shop_configs`
already rejects any offer whose `buy_copper` falls outside the band of
`ITEM_REGISTRY[item_key].price_table_key`. Rarity
(`item-presentation-metadata`) is explicitly presentation-only and never
feeds price, stock, or loot.

## Goals / Non-Goals

**Goals:**

- One band that legally holds both an in-community everyday price and an
  outside-world scarce price for the same item key.
- Make the keepsake band's trade prohibition enforced rather than implied.

**Non-Goals:**

- Location-scoped bands. A band stays a global property of the item. Whether
  that is sufficient long term is recorded as a limitation, not solved here.
- Re-banding non-elven items. `knight_platemail`, `archmage_mending_robe`
  and `saintess_vestments` are plausible future `masterwork_gear` residents
  but nothing in this change needs them moved, so they stay put.
- Any shop, place, or settlement content. This change only makes the goods
  legal to shelve.

## Decisions

**A single wide band rather than per-slot masterwork bands.** The
alternative was `masterwork_weapon` / `masterwork_armor` /
`masterwork_accessory`, mirroring the existing category axis
(`mundane_weapon`, `armor`, `jewelry`). Rejected: the band's purpose here is
not to separate slots but to widen the legal range, and all three variants
would carry the same bounds, so the split would add vocabulary without
adding a single rejection. One key keeps the table honest about what it is
saying.

**Floor 100, ceiling 500,000.** The floor matches `mundane_weapon` and
`jewelry` so an everyday village price is expressible. The ceiling is the
one number with a hard constraint: it must stay strictly below `relic`'s
999,999 floor, or the two bands would overlap and "never traded" would lose
its exclusive region. 500,000 copper is 50 gold — beyond a commoner's annual
income (5–10 gold per `PRICE_TABLE`) but inside an established adventurer's
(10–100 gold), which is the right shape for a scarce import.

**A race-neutral key.** `elven_craft` was considered and rejected: it would
put a *provenance* axis into a table whose every other key is a category
(`armor`, `jewelry`, `tool`, `material`). `masterwork_gear` states the
property that actually justifies the width — the price follows scarcity, not
materials — and admits human and beastfolk master work later without a
second near-duplicate band.

**The relic rejection is a loader rule, not a registry rule.** It could have
been enforced in `ItemDefinition.__post_init__` by forbidding
`sellable=True` alongside `price_table_key="relic"`. Rejected: the registry
does not know about shops, and the real invariant is about shelves, not
flags — an author could leave `sellable=False` and still list the key in a
shop's offers. Putting the check where offers are validated catches the
actual mistake.

**Rarity moves independently of the band.** `elven_forest_veil` already
ships LEGENDARY in the tradeable `armor` band, so the precedent that rarity
and band are orthogonal exists in the data. The three rarity bumps are
therefore free of mechanical consequence and are included here only because
they belong to the same authorial judgement — elves produce epic work as
daily output.

## Risks / Trade-offs

- **The band is wide enough to hide an authoring mistake.** A 100-copper
  legendary blade and a 500,000-copper one both validate, so the band
  catches far less than `mundane_weapon` did. → Accepted deliberately: the
  width *is* the feature. The narrowing pressure moves to review of the
  authored price, and the ceiling still blocks the runaway case.
- **500,000 may prove too low.** If a later change wants an elven blade at a
  true fortune in a human capital, the ceiling blocks it.
  → `docs/superpowers/specs/2026-09-20-settlement-shops-design.md` §4.2
  records this as a known limitation with two sanctioned exits (widen the
  band, or introduce location-scoped bands). Neither is to be worked around
  by bypassing the validator.
- **Six items become buyable that previously could not enter a wallet
  transaction at all.** → Nothing offers them yet; they become reachable only
  when a later change authors an assortment containing them.
