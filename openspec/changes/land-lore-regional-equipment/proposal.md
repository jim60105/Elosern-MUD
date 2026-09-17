## Why

The shipped equipment roster is culturally lopsided. Of the 45 registered equipment items, the Beastfolk Kingdom owns five weapons and a single necklace and **no armor at all**, while the elven line is almost entirely village-shop clothing and jewelry with two weapons behind it. A player building a beastfolk warrior can arm them and then has to dress them in Kingdom chainmail; an elven archer has no bow of their own people above `uncommon`. The lore codex closes those gaps with 12 designed pieces — the tribal armoury's missing roles, the first beastfolk armor and totems, an elven longbow, a seasonal elven veil, and a dungeon trophy blade.

These 12 are the second slice of `docs/lore/items.md`. They are still data — the equipment shape, the binding rule, the budget check, and every consumer already exist — but unlike the inspect-only slice each piece needs a modifier-key enum member and a rulebook entry, and the budget ceilings make a mistyped number a startup failure rather than a silent imbalance.

## What Changes

- Register 12 equipment items from the codex: 7 weapons (5 beastfolk, 1 elven, 1 dungeon trophy), 3 armors (2 beastfolk, 1 elven), 2 beastfolk accessories.
- Add the 12 matching `EquipmentModifierKey` members and the 12 matching `equipment_effects.yaml` entries, keeping the enum member value equal to the item key as the loader requires.
- Keep all 12 registry-only: none is added to any shop. Their provenance is the Beastfolk Kingdom, the elven villages, and a dungeon, none of which the Altoria general store reaches.
- No behavior change to the engine: no new vocabulary member, no new adjustment field, no new budget column, no settlement path touched.
- **No new game-data contract test.** Budget legality is already enforced by the rulebook loader at startup, which fails the server on a wrong number; a test re-asserting the codex's published values would only echo registry content.

## Capabilities

### Modified Capabilities
- `equipment-effects`: the capability currently names one concrete roster ("the ten designed equipment items") and requires it to be tradeable, which reads as a general rule. It gains a requirement making registration and tradeability independent — a bound, budget-checked, unstocked piece is a valid shipped state, and each roster states its own stocking decision from its lore provenance.

## Impact

- `world/lore/items.py` — 12 `EquipmentModifierKey` members and 12 `ItemDefinition` entries.
- `world/rules/rulebook/equipment_effects.yaml` — 12 new effect entries.
- Tests with hard-coded roster assertions: `world/lore/tests/test_items.py`, `world/rules/tests/test_guild_config.py`, and the equipment-effect rulebook tests that pin the bound key set (`EquipmentModifierKey` goes from 45 members to 57).
- No shop file changes; `world/lore/shops.py` and `guild_economy.yaml` are untouched.
- Depends on `land-lore-inspect-only-items`, which introduces the `lore-item-catalog` capability this change builds on and moves the same two roster literals.
