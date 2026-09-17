## Why

The intimacy system is one of this game's load-bearing mechanics, but nothing in the item catalog serves it directly. Arousal-bearing gear exists only as a side effect of clothing — a maid dress, lace lingerie, vestments — and there is no item category for the devices the world's own institutions openly sell. That is a setting gap as much as a mechanical one: the Church of Light runs the 聖所 and treats pleasure as worship, and the elves treat sex as unremarkable, so in-world these goods sit on a shelf next to a magic lamp, not in a back alley.

This is the third slice of `docs/lore/items.md` and the only one that needs a vocabulary change. The codex's 性玩具 category has no presentation kind to land on: `ItemKind` and `ItemIconKey` are closed enums mirrored by a client icon map, and `toy` is the one member the codex names that the code lacks. This change opens that category and lands its five wearable pieces; the usable ones follow in their own change.

## What Changes

- Add `toy` to `ItemKind` and `ItemIconKey`, and add the matching entry to the client's local icon map so the inventory panel renders the category instead of falling back to the unknown-item glyph.
- Add an `intimacy_tool` price band (50–20000 copper) to `PRICE_TABLE`, covering both the wearable pieces landing here and the usable ones landing next.
- Register 5 wearable accessories — 花蒂銀夾, 暖蜜魔導珠, 恆溫魔法卵, 尖銳觸感之飾, 恆振晶 — each with an `EquipmentModifierKey` member and an `equipment_effects.yaml` entry whose `pleasure_gain` is the mechanical form of sustained stimulation, and whose negative columns are the cost of being distracted.
- Amend the Church-of-Light doctrine requirement so it covers the 聖所 devices this change adds. The doctrine currently demands every named Church item provide `heal_gain` or an immunity, which is right for vestments and emblems and wrong for a censer; the amendment splits the named set into 聖職服儀與聖徽 and 聖所器具 with the healing clause bound to the former.
- Keep all 5 registry-only: the codex routes them through the 聖所器具商店 and the 精靈村商店, neither of which exists.
- No behavior change beyond the vocabulary member: no new adjustment field, no new budget column, no settlement path touched.

## Capabilities

### Modified Capabilities
- `item-presentation-metadata`: the closed presentation vocabularies gain a member, and the requirement gains the cross-boundary rule that the client icon map must stay aligned member-for-member with the server icon vocabulary — the contract that makes adding a member a two-sided edit rather than a silent fallback.
- `lore-registries`: the `PRICE_TABLE` requirement gains the intimacy-device band.
- `lore-item-catalog`: the roster contract gains the wearable intimacy slice.
- `equipment-effects`: the Church-of-Light doctrine requirement is amended so its healing-or-immunity clause binds the vestment-and-emblem set rather than every Church item.

## Impact

- `world/lore/items.py` — two enum members, 5 `EquipmentModifierKey` members, 5 `ItemDefinition` entries.
- `world/lore/economy.py` — one new `PriceEntry`.
- `world/rules/rulebook/equipment_effects.yaml` — 5 new effect entries.
- `web/webclient-app/components/item-icons.js` — one new icon entry, which also supplies the category's Traditional Chinese label through the existing derived `KIND_LABELS`.
- Tests: the closed-vocabulary assertions in `world/lore/tests/test_items.py`, the icon-map alignment test in `web/webclient-app/tests/world/item_icons.test.js`, the two roster assertions, and the Church doctrine coverage test.
- Depends on `land-lore-inspect-only-items` for the catalog contract test, and shares `world/lore/items.py` with `land-lore-regional-equipment`.
