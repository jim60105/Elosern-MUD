## Context

See `proposal.md` — Why. Three constraints shape this slice.

`ItemKind` and `ItemIconKey` are closed `StrEnum`s in `world/lore/items.py`, mirrored by `ITEM_ICONS` in `web/webclient-app/components/item-icons.js` and mirrored a second time by the hand-typed `ICON_KEYS` array inside `web/webclient-app/tests/world/item_icons.test.js`. That test pins the map against the array — both JavaScript, neither derived from the Python enum — so today nothing in the repository compares the client vocabulary against the server's. `InventoryPanel.vue` falls back to a neutral unknown glyph for any icon key it does not know. So a server-only enum addition does not break the client and does not fail any test; it silently degrades every item of the new category to 未知, which is exactly the failure this change must not ship.

The equipment seam needs nothing new. `pleasure_gain` and `sp_cost` already exist as adjustment fields, `pleasure_gain` is already budgeted against the looser `soft_percent` column, and `world/rules/pleasure.py` already owns the single write path. A wearable device is an ordinary accessory whose numbers happen to be arousal-shaped.

`equipment-effects` carries a doctrine requirement that binds every named 光明教會 item to "at least one of `heal_gain` or an immunity". Three of the five devices in this slice come from the 聖所 and would fail it.

## Goals / Non-Goals

**Goals:**
- Open the 性玩具 category end to end — server vocabulary, client icon, price band — so the usable slice that follows is pure data.
- Land the five wearable devices with their codex numbers and their stated drawbacks.
- Make the doctrine requirement say what it actually means, rather than quietly exempting the new items from it.

**Non-Goals:**
- **New game-data contract tests.** The cross-language check added here compares the client icon vocabulary against the server icon enum — two vocabularies, not item content — and no test added by this change asserts that a named device carries a particular price, rarity, or adjustment.
- The usable devices and their `item_effects.yaml` entries. They are the next change.
- Any new status key. The codex's earlier 「催情霧」 status was retired in favour of a plain pleasure gain, and nothing in this slice reintroduces it.
- Storefronts. Same reasoning as the regional equipment slice.
- Any coupling between presentation kind and mechanics. A `toy` item is an accessory because it declares a slot, never because of its kind.

## Decisions

**The vocabulary member and the wearables ship together; the usables ship separately.** `toy` is worthless without at least one item carrying it, and shipping the enum alone would leave a member no test exercises. But the usable devices bring `item_effects.yaml`, the two-sided rulebook close, and the first shipped `pleasure` item effect — a different risk surface that deserves its own change. Splitting after the wearables keeps both changes inside a day and puts the front-end edit in the smaller one. Alternative considered: all twelve devices in one change. Rejected on size and on mixing a client change with a settlement-adjacent one.

**One `intimacy_tool` band spanning 50–20000 copper, declared here and used by both slices.** The twelve devices span 50 copper bath salts to a 15000-copper elven resonance crystal. Splitting them across `potion`, `jewelry`, and `magic_accessory` would have left 600- and 900-copper items with no band that fits (`potion` caps at 500) and put a 12000-copper censer in a gap between `jewelry`'s 5000 ceiling and `magic_accessory`'s 10000 floor. One wide band matching the `material` precedent is simpler and keeps the category's pricing coherent. The band is declared in this change even though only five items use it yet, because declaring it twice would be worse.

**The doctrine requirement is split by function, not relaxed.** The straightforward fix — drop the healing clause — would let a future 修女聖袍 ship with no healing at all, losing a real guarantee. Splitting the named set into 聖職服儀與聖徽 and 聖所器具 keeps the clause exactly where it earns its keep and states why the devices are exempt: a censer serves the rite, a vestment channels the Light. Sub-set membership stays a named list in the requirement rather than a rulebook-asserted property, so the rulebook cannot move an item between sub-sets to dodge an obligation. `暖蜜魔導珠`'s `defense: -1` is permitted as an ordinary combat trade-off, which the requirement already allowed.

**`恆振晶` is elven and therefore not in the Church sub-set.** Only `nymph_buds_clamp`, `warm_honey_orb`, and `hyperesthesia_charm` carry 聖所 provenance in the codex. `warmth_rune_egg` is an Imperial enchanter's product and `tremor_crystal` is elven craft; both stay outside the doctrine set entirely, which is why the amended requirement names three keys and not five.

**The icon is authored, not borrowed.** `ITEM_ICONS` entries are inline 24×24 stroke paths in the same idiom as the existing nine. The `toy` entry gets its own path and the label 情趣道具, which `KIND_LABELS` then derives automatically — the existing code already builds kind labels from the icon map, so no second table needs editing there.

**A fourth vocabulary copy exists and is deliberately left alone.** `web/browser_support/browser_fixtures_data.py` keeps its own `_ITEM_KIND_WORDS` and `_ITEM_RARITY_WORDS` dictionaries for browser end-to-end fixtures. Nothing in this change wires a `toy` item into a shipped browser fixture, and the lookup raises `KeyError` rather than degrading silently, so it is left untouched rather than pulled into the cross-language check. It is recorded here so a future fixture author meets a documented gap instead of an unexplained `KeyError`.

## Risks / Trade-offs

- **A server-only enum addition degrades silently on the client.** → This is the headline risk, and the existing coverage does *not* close it: `item_icons.test.js` compares `ITEM_ICONS` against `ICON_KEYS`, a hand-typed JavaScript array in the test file itself, so it only proves the JS map agrees with a second JS list. Nothing in the repository compares either against `ItemIconKey`. There are therefore three independent hand-maintained mirrors of one vocabulary, and adding `toy` to only two of them passes every test while every toy renders as 未知. The mitigation is a new Python-side test that extracts `ITEM_ICONS`'s keys from `item-icons.js` with a narrow regex over the object literal and diffs them against `ItemIconKey`, failing loud on an unparseable file or a zero-key extraction rather than passing empty. This is a vocabulary-to-vocabulary check, not a game-data contract test: it names no item, no price, and no rarity, and it is the single cross-language check that makes the presentation requirement's alignment scenario real rather than aspirational.
- **`pleasure_gain` on an accessory is a real balance lever, and five of them stack.** → The accessory slot caps at five, so a maximally stacked arousal build is bounded at the sum of five `soft_percent` values, all inside their rarity ceilings. That ceiling is the existing budget model's job, not this change's; the codex numbers here (8–10%) sit well under the 15–20% their rarities allow.
- **The doctrine amendment widens who may be a Church item.** → It does not change membership, which is still a hand-maintained named list; it only changes what each sub-set must prove. A future Church item must still be added to the requirement by name, which is the same gate as before.
- **Five more unstocked items.** → Same trade-off and the same follow-up as the regional equipment slice, recorded there.

## Migration Plan

Not applicable. Pre-release. The new enum member cannot appear in stored data, because no item carried it before this change.
