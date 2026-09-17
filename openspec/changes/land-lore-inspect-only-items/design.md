## Context

See `proposal.md` — Why. Three constraints shape everything below.

`ITEM_REGISTRY` is a Python dict of frozen dataclasses, not a data file. "Data change" therefore still means editing `world/lore/items.py`, and two already-registered data-contract tests pin the roster by hand: `world/lore/tests/test_items.py` asserts the exact key set, and `world/rules/tests/test_guild_config.py` asserts a literal registry count. Both must move with the roster, and both are the reason the codex slices cannot land in parallel.

Shop offers are validated by a two-sided join. `world/lore/shops.py` holds the offered keys, `world/rules/rulebook/guild_economy.yaml` holds the numbers, and `world/rules/guild_config.py` rejects a key present in one and absent from the other, a buy price outside the item's `PRICE_TABLE` band, a sell price above buy, and stock outside `0 <= initial <= max`. Adding an offer is always a paired edit, and the loader is the gate.

`AGENTS.md` governs what may be tested and how: behavior tests resolve game data through the synthetic test-data kit or file-local synthetic fixtures, only tagged and frozen data-contract tests may name shipped content, and assertions must establish mechanics rather than echo registry content.

## Goals / Non-Goals

**Goals:**
- Land the inspect-only slice of the codex as identity data with zero behavioral surface.
- Establish the shape-derived behavioral invariants that the later slices rely on, using synthetic fixtures.

**Non-Goals:**
- **New game-data contract tests.** No test added by this change parses `docs/lore/items.md`, enumerates shipped item keys, or asserts that a named item carries a particular price or rarity. The codex stays a design document reviewed by humans; the machine-checked guarantees are the loader's, and the new behavior tests use synthetic items.
- Growing the existing data-echo assertions beyond the mechanical update they need. The two registered contract tests get their literals moved and nothing more.
- Any new closed-vocabulary member, rulebook verb, or settlement path. If a task needs one, it belongs to a later slice.
- New storefronts. The codex routes several goods through the 聖所器具商店 and 精靈村商店, neither of which exists; that is its own change.
- Re-tuning or re-texting the 58 shipped entries. `replace-temp-item-data` runs first and finalises them; this change only adds.

## Decisions

**Inspect-only first, and only inspect-only.** The 48 uncatalogued items split cleanly by mechanical shape: 24 declare neither `use_mechanics` nor `equipment_slot`, 17 are equipment, 7 are usable. The inspect-only 24 are the only group that touches no vocabulary and no rulebook, so they land as a self-contained slice before any mechanics are involved. Alternative considered: one change for all 48. Rejected — it would exceed a day, and it would mix a front-end icon change and two rulebook files into what is otherwise a registry edit.

**The codex is not checked by a test.** An earlier draft of this design had a test parse `docs/lore/items.md` and diff it against `ITEM_REGISTRY`. That is precisely the game-data contract test `AGENTS.md` steers away from: it would echo registry content, name shipped keys, and need a ledger entry, and it would have added a Markdown grammar to maintain. It is dropped. The codex↔registry agreement is a review responsibility, and the properties that actually matter mechanically — a resolvable price band, an in-band shop price, a complete equipment binding, a budget-legal adjustment — are all already enforced by loaders that fail closed at startup. A wrong item name is a lore bug a reader catches; a wrong number is a startup failure nobody can ship past.

**The capability specifies shape, not roster.** `lore-item-catalog` — opened by `replace-temp-item-data` with the retirement invariant — gains here what follows from an item declaring no mechanics, from declaring itself non-sellable, and from being registered but unstocked. Every one of those requirements is satisfiable and testable with a synthetic item, so the capability's tests never name a shipped key. The roster itself — which 24 items exist — is implementation work in `tasks.md`, not a requirement.

**Curios land as non-sellable on the keepsake band.** The codex says the 雜物 category has no trade meaning and publishes no reference price for it, but `price_table_key` is mandatory. The shipped `guild_recruit_badge` already sets the precedent: non-sellable on the `relic` band, where the 999999 floor reads as "not a market price". The alternative — inventing a zero-value band — would create a band that no reference price ever uses. The behavioral consequence is specified: non-sellability, not band choice, is what blocks the trade.

**古龍心臟 stays sellable but unstocked.** The codex assigns the whole 素材 category the open-ended `material` band and separately says the heart has no trade record. Those are two different statements: the first is about pricing, the second about distribution. Modelling the second as non-sellable would contradict the category rule and imply a mechanical restriction the codex never states, so it keeps `material` and simply appears in no shop — which the third requirement makes a fully supported state.

**精靈之淚 and 精靈體液 are deliberately unstocked.** The codex is explicit that elven fluids reach human society by gift in very small numbers and that the villages do not sell them. A general store with a restock schedule would contradict the lore. They stay registry-only alongside the heart.

**Rarity drives stock depth, not price.** Rarity is presentation-only by contract, so it must not feed a price. It may guide the hand-authored stock numbers: common goods get deeper stock and larger restocks, `rare` and above get a single unit and a single-unit restock. This is an authoring convention recorded here so the numbers do not look arbitrary, not a computed rule and not something a test asserts.

## Risks / Trade-offs

- **Without a codex-diffing test, the document and the registry can drift.** → Accepted deliberately. Drift in a display name or a summary is a lore bug with no mechanical consequence, and the mechanical properties are loader-enforced. The cost of the alternative — a Markdown grammar plus a ledger entry plus a data-echo test — is higher than the defect it prevents.
- **Twenty new shop offers make the Altoria store the continent's everything-store.** → Already true of the shipped store, which stocks black-market lingerie and elven spider silk. The lore-correct storefronts are named as follow-up work in the codex's own 未來擴充方向, and this change tightens rather than loosens the principle by keeping six items off the shelf on stated lore grounds.
- **`elven_essence` is priced far above any current player's wallet.** → Intended; the codex prices it as a treasure. It is one of the items that stays out of the store, so no purchase path exists to be unbalanced.
- **Three new behavior requirements need traceability coverage.** → Each is covered by a synthetic-fixture test written with the behavior, annotated with `covers_requirement`, and checked locally with the traceability gate. No new test module is created, so the shard manifest is untouched.

## Migration Plan

Not applicable. The project is pre-release with no live data: new registry keys cannot collide with stored inventory, and no save contains an item key this change removes, because it removes none.
