## Context

See `proposal.md` — Why. Two constraints shape everything below.

`ITEM_REGISTRY` is a Python dict of frozen dataclasses, not a data file. "Data change" therefore still means editing `world/lore/items.py`, and two test suites pin the roster by hand: `world/lore/tests/test_items.py` asserts the exact key set, and `world/rules/tests/test_guild_config.py` asserts `len(ITEM_REGISTRY) == 58`. Both must move with the roster, and both are the reason the four codex slices cannot land in parallel.

Shop offers are validated by a two-sided join. `world/lore/shops.py` holds the offered keys, `world/rules/rulebook/guild_economy.yaml` holds the numbers, and `world/rules/guild_config.py` rejects a key present in one and absent from the other, a buy price outside the item's `PRICE_TABLE` band, a sell price above buy, and stock outside `0 <= initial <= max`. Adding an offer is therefore always a paired edit.

## Goals / Non-Goals

**Goals:**
- Land the inspect-only slice of the codex as identity data with zero behavioral surface.
- Establish the `lore-item-catalog` contract that the equipment and sex-toy slices extend.
- Make the codex↔registry agreement machine-checked rather than a matter of reviewer diligence.

**Non-Goals:**
- Any new closed-vocabulary member, rulebook verb, or settlement path. If a task needs one, it belongs to a later slice.
- New storefronts. The codex routes several goods through the 聖所器具商店 and 精靈村商店, neither of which exists; that is its own change.
- Re-tuning the 17 equipment entries already in `equipment_effects.yaml`. Where the codex and the rulebook disagree on a number, `docs/lore/items.md` line 7 already declares the rulebook authoritative for tuned values.

## Decisions

**Inspect-only first, and only inspect-only.** The 48 uncatalogued items split cleanly by mechanical shape: 24 declare neither `use_mechanics` nor `equipment_slot`, 17 are equipment, 7 are usable. The inspect-only 24 are the only group that touches no vocabulary and no rulebook, so they land as a self-contained slice that proves the catalog contract before any mechanics are involved. Alternative considered: one change for all 48. Rejected — it would exceed a day, and it would mix a front-end icon change and two rulebook files into what is otherwise a registry edit.

**A dedicated `lore-item-catalog` capability rather than growing `shop-economy`.** `shop-economy` owns the *shape* of an item identity and the join to trade numbers; `item-presentation-metadata` owns the *vocabulary*; `equipment-effects` owns *bindings*. None of them owns "which items the world contains". Putting roster facts in `shop-economy` would also wrongly imply that registering an item means selling it, which the fourth requirement explicitly denies. The precedent for a roster requirement living beside its mechanics — `equipment-effects`'s "The new equipment roster is registered and tradeable" — is what this capability generalises, and later slices amend it in one place.

**The codex is checked as data, not read by the server.** The catalog contract test parses `docs/lore/items.md` at test time and compares key, display name, kind, icon key, rarity, and price band against `ITEM_REGISTRY`. The runtime never opens the document. This keeps the doc authoritative without adding a startup dependency on a Markdown file, and it turns the hand-maintained key-set assertion in `test_items.py` into something that fails loudly when the two drift. Alternative considered: generating `items.py` from the Markdown. Rejected — the registry carries Python-typed enum members and validation that a generator would have to reproduce, for a catalog that changes a few times a year.

**Curios land as non-sellable on the keepsake band.** The codex says the 雜物 category has no trade meaning and publishes no reference price for it, but `price_table_key` is mandatory. The shipped `guild_recruit_badge` already sets the precedent: `sellable=False` on the `relic` band, where the 999999 floor reads as "not a market price". The alternative — inventing a zero-value band — would create a band that no reference price ever uses.

**古龍心臟 stays sellable but unstocked.** The codex assigns the whole 素材 category the open-ended `material` band and separately says the heart has no trade record. Those are two different statements: the first is about pricing, the second about distribution. Modelling the second as `sellable=False` would contradict the category rule and imply a mechanical restriction the codex never states, so it keeps `material` and simply appears in no shop — which already makes it unpurchasable and unsellable, because selling requires the merchant to list the key.

**精靈之淚 and 精靈體液 are deliberately unstocked.** The codex is explicit that elven fluids reach human society by gift in very small numbers and that the villages do not sell them. A general store with a restock schedule would contradict the lore we just finished reconciling. They stay registry-only alongside the heart.

**Rarity drives stock depth, not price.** Rarity is presentation-only by contract, so it must not feed a price. It may, however, guide the hand-authored stock numbers: common goods get deeper stock and larger restocks, `rare` and above get `max_stock: 1` with `restock_quantity: 1`. This is an authoring convention recorded here so the numbers do not look arbitrary, not a computed rule.

## Risks / Trade-offs

- **The two hand-maintained roster assertions drift again.** → The new catalog contract test compares the registry against the codex directly, so the exact-key-set assertion in `test_items.py` stops being the only guard. The count assertion in `test_guild_config.py` is updated in the same commit and is the first thing to fail if an item is added without the codex.
- **Parsing Markdown in a test is brittle.** → The parser targets one narrow shape: table rows whose first cell contains exactly one backticked key. Rows without a key (the data-model tables, the price-band table) are skipped by that rule alone. A codex formatting change that breaks the parser fails the test loudly rather than silently passing.
- **20 new shop offers make the Altoria store the continent's everything-store.** → Already true of the shipped store, which stocks black-market lingerie and elven spider silk. The lore-correct storefronts are named as follow-up work in the codex's own 未來擴充方向, and this change tightens rather than loosens the principle by keeping six items off the shelf on stated lore grounds.
- **`elven_essence` is priced at 80000 copper, above any current player's wallet.** → Intended; the codex prices it as a treasure. It is one of the items that stays out of the store, so no purchase path exists to be unbalanced.

## Migration Plan

Not applicable. The project is pre-release with no live data: new registry keys cannot collide with stored inventory, and no save contains an item key this change removes, because it removes none.
