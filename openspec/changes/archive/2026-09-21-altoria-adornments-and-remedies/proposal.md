## Why

`docs/lore/settlement-locations.md` line 146 states the plan and the trigger in one sentence: 「飾品與藥劑仍隨雜貨販售，**直到首飾店與鍊金坊落地**」. Both are 「有」 for the capital in the applicability matrix, both have a named functional NPC, and both are still being sold out of the general store's back shelf.

The split is the same one the forge, the eatery and the tailor already went through, and it is the last of that family. After it, the general store sells what a general store sells — tools and raw materials — and nothing that has a specialist.

## What Changes

- Add two assortments. `capital_adornments` is **exactly the accessory-slot goods the capital sells** — all eleven of them, a rule the tests can check rather than a hand-drawn line. `capital_remedies` is the drinkable and applied remedies: six potions.
- Add two places. 聖潔王都首飾坊 off 市場街, hosted by 艾蓮娜·鴉丘; 聖潔王都鍊金坊 off 東市, hosted by 希碧拉·灰沼. Both are ordinary `merchant` places — no new mechanism.
- Shrink `general_sundries` from thirty-five item keys to eighteen. Every offer moves **verbatim**: the same buy and sell copper, the same stock and restock. An item's price must not depend on which shelf it sits on.
- `baptismal_holy_water` deliberately **stays** in the general store. It belongs to the sanctuary, and the sanctuary change moves it. Moving it here would make the capital stop selling it for however long the two changes are apart.

## Capabilities

### Modified Capabilities
- `sample-city-altoria`: the interiors requirement's count of capital places, and the scenario that the split never narrows what the capital sells, both cover two more shops.

## Dependencies

This change lands after `altoria-capital-replan` and `altoria-place-slices` (new exteriors and the terrace slices), `place-kind-vocabulary` (this change's two places are a jeweller and an alchemist), `commerce-rulebook-slices` (the rulebook directory) and `merchant-dialogue` (merchant places must author a dialogue key).

## Impact

- `world/lore/settlements/assortments.py` — two new bundles; `general_sundries` loses seventeen keys.
- `world/rules/rulebook/commerce/altoria.yaml` — the seventeen offer rows move between sections unchanged; two new `shops:` rows.
- `world/lore/settlements/places_altoria_middle.py` — two rows.
- `docs/lore/settlement-locations.md` — lines 146, 206 and 224: the two placeholder host names become the authored ones, and the sentence promising this split stops promising it.
- No runtime code. Both places are `merchant` places, which is the path the four existing capital shops already take.
