## Why

The Church of Light is what 聖潔王都 is named for, and the capital has no temple. The map has had a 光明神殿外 node since the first scaffold; nothing was ever behind the door.

The source document is unusually insistent about how this location works, because it is easy to get wrong. Line 326: 「聖所」「神殿」「教堂」「禮拜堂」are one building, not a public shell around a private core. Worship, the sanctum's sexual ministry, and the shop that supplies it all operate openly in the same place, and this is 社會常識 — everyone on the continent knows what a sanctum does, 「就像知道酒館賣酒一樣」. Writing it as a hidden inner sanctum that outsiders discover is called out by name as a misreading.

There is also a concrete inventory reason. All twelve `intimacy_tool` goods exist in the item registry, fully defined, and **not one of them is sold anywhere**. The sanctum shop is the counter they were written for.

## What Changes

- Add two places behind 大神殿前, because the document describes two counters, not two buildings:
  - **聖潔王都光明神殿**, hosted by 艾莉安娜·寒水, 聖潔王都光明神殿主祭. An `attendant`: the sanctuary is where blessing and preaching happen, and the document calls `talk` the natural affinity channel there.
  - **聖潔王都聖所**, hosted by 羅海西亞·芬威克, 聖潔王都聖所執事. A `merchant` running the attached shop.
- Add the `sanctum_wares` assortment: the twelve `intimacy_tool` goods, plus 受洗聖水 moved out of the general store's shelf and onto the counter it belongs to. Thirteen keys, every price carried over unchanged.
- Author the sanctuary's dialogue table. Its greeting and keywords state plainly what the building offers, in the register of a place that has nothing to be coy about.

## Capabilities

### New Capabilities
- `altoria-sanctum`: the capital's temple as one building with an open ministry and an attached shop, and the rule that its goods are reachable through the ordinary trade path with no special case.

## Dependencies

This change lands after `place-attendant-profession`, `altoria-capital-replan`, `altoria-place-slices`, `place-kind-vocabulary`, `altoria-adornments-and-remedies` (which leaves 受洗聖水 for this change to move), `commerce-rulebook-slices` and `merchant-dialogue`.

## Impact

- `world/lore/settlements/assortments.py` — one bundle of thirteen.
- `world/rules/rulebook/commerce/altoria.yaml` — twelve new offer rows, 受洗聖水's row moved verbatim, one `shops:` row.
- `world/lore/settlements/places_altoria_upper.py` — two rows sharing the 大神殿前 exterior.
- `world/lore/dialogue/altoria.py` — one dialogue table.
- `docs/lore/settlement-locations.md` — lines 335 and 146: the two placeholder host names, and the note that 受洗聖水 has left the sundries.
- No runtime code.
