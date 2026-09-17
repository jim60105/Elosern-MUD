## Why

The declarative item-effect model was built to make an item's effect pure rulebook data — a `stat: pleasure` entry routes through the intimacy system's single shared writer with no new verb, no new handler, and no enum extension. Nothing has ever exercised that path in shipped data. All four shipped usable items move `hp` or `mp` or clear a status; `pleasure` exists in the vocabulary and in synthetic tests only.

The lore codex's seven usable 性玩具 are exactly that path's first real users, and landing them also closes two other never-shipped shapes: an item that may not be used in combat, and an item that is used without being consumed. Both are already supported and neither has a shipped example, so each is currently a promise rather than a fact.

## What Changes

- Register 7 usable items in the intimacy-device category — 催情浴鹽, 史萊姆潤滑凝膠, 熱吻藥水, 微電跳蛋糖, 纏枝魔藤, 女神之吻聖霧, 情欲香爐 — each declaring use mechanics with `combat_allowed = false`, and three of them declaring `consumable = false` for devices the codex describes as reusable.
- Add the 7 matching `item_effects.yaml` profiles, each a single self-scoped positive `pleasure` adjustment at one of three magnitudes drawn from the existing `stimulus_applied` band: gentle `+8`, moderate `+11`, intense `+14`.
- Keep all 7 registry-only, for the same storefront reason as the wearable slice.
- No behavior change to the engine: the effect verb, the scope vocabulary, the pleasure writer, the non-consumable use path, and the combat gate all exist. This change is the data that first uses them together, plus the behavior requirements that make those never-shipped paths specified rather than merely available.
- **No new game-data contract test.** Nothing added here asserts that a named device costs a particular price or declares a particular amount; the magnitudes are checked as a property against the rulebook band, and the shapes are tested on synthetic items.

## Capabilities

### Modified Capabilities
- `lore-item-catalog`: gains three shape-derived behavior requirements that nothing has ever exercised in shipped data — a pleasure gain routes through the shared intimacy writer and needs no status, a non-consuming use settles without spending the item and rolls back cleanly, and an item barred from combat is refused at submission by name.

## Impact

- `world/lore/items.py` — 7 `ItemDefinition` entries carrying `ItemUseMechanics`.
- `world/rules/rulebook/item_effects.yaml` — 7 new profiles. The loader closes this file against the registry's usable set in both directions, so the two edits are inseparable.
- Tests: three behavior tests on synthetic items, the two existing roster literals, and any existing literal pinning the shipped usable-item set.
- Depends on `add-toy-item-category` for the `toy` presentation vocabulary and the `intimacy_tool` price band, and shares `world/lore/items.py` and the two roster literals with all three earlier slices.
