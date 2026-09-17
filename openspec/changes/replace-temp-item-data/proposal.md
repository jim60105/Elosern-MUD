## Why

`docs/lore/items.md` says it plainly: the 58 entries in `ITEM_REGISTRY` are provisional data authored early to get the economy running, and the codex — not the registry — is the source of truth. They have since diverged, and some of the registry's text is not merely thinner but **wrong**. Four shipped summaries still name races the setting retired: 灰燼彎刀 is credited to 基亞蘭族, 三稜晶符 to 伊歐拉斯族, 雙手巨斧 to 熊人, 鋼牙短刀 to 貓科獵手. The codex calls all four 精靈 or 獸人. A player reading an item description today is told about a race the world no longer has.

The other three slices of this work all *add* items. None of them fixes what is already there, and adding 48 correct entries beside 17 stale ones would leave the catalog permanently half-migrated. This change replaces the provisional data first, so every later slice extends a catalog that is already true.

## What Changes

- Replace 17 summaries with their codex text, retiring the four obsolete race names and giving the Church vestments, the royal relics, and the elven village goods the descriptions the codex actually writes for them.
- Rename 5 items to their codex names: 黑暗精靈傳統服飾 → 精靈短袍傳統服飾, 黑暗精靈戰鬥服飾 → 精靈戰鬥服飾, 王室薔薇紋章輕劍 → 薇歐蕾特親刻薔薇輕劍, 王室紋章細金戒指 → 薇歐蕾特的誕生細金戒, 銀羽耳環 → 十二歲的銀羽. The keys do not change.
- Correct 2 rarities the codex disagrees with — 修女聖袍 `uncommon` → `rare`, 聖女聖袍 `epic` → `legendary` — and apply the codex adjustments those rarities make budget-legal. 修女聖袍's codex numbers are **not** authorable at `uncommon`, so the rarity is the blocker, not a preference.
- Correct 修女聖袍's shop price to the codex reference, which its new rarity and band both allow.
- **Delete every registry item the codex does not catalogue, together with every reference to it.** The current orphan set is empty — all 58 keys appear in the codex — so this change performs the sweep, records the result, and establishes the removal procedure and the closure guarantee that make a future deletion safe.
- Leave the 39 summaries that differ only by the registry's trailing 。 convention alone. That is house style, not drift.

## Capabilities

### New Capabilities
- `lore-item-catalog`: the behavioral invariants that follow from an item's declared mechanical shape rather than from which items exist. This change opens it with the one invariant that makes catalog cleanup safe — retiring a key must leave no dangling reference anywhere, and every loader that names items must fail closed on one rather than silently skipping it.

## Impact

- `world/lore/items.py` — 17 summaries, 5 display names, 2 rarities. No key changes, so no stored inventory is affected.
- `world/rules/rulebook/equipment_effects.yaml` — the two vestment entries gain the adjustments their corrected rarities permit.
- `world/rules/rulebook/guild_economy.yaml` — one corrected offer price.
- `docs/superpowers/specs/2026-08-29-equipment-combat-effects-design.md` — one prose line still naming two items by their old titles.
- `world/lore/tests/test_items.py` and any test asserting a renamed display name.
- Reference surfaces a deletion would have to sweep, verified as part of establishing the procedure: `world/lore/shops.py`, `guild_economy.yaml`, `equipment_effects.yaml`, `item_effects.yaml`, `world/lore/starting_kits.py`, `world/lore/player_presets.py`, and the quest definition and compile validators.
- Runs before all three catalog-addition changes, which share `world/lore/items.py` with it.
