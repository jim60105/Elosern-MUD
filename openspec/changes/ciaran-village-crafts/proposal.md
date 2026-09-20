## Why

暗影谷村 covers four of the six location types the applicability matrix marks 「變」 for an elven village. Two are missing, and the document describes both precisely.

首飾店 (line 214): 「村中有鍾愛飾品匠作的精靈，三稜晶符、月牙耳環等作品多在族人間以贈禮流通，玩家上門也能用通用貨幣交換到」. 三稜晶符 is `prism_charm`, which exists in the registry and is sold nowhere.

鍊金坊與藥舖 (line 232): 「有對藥草與調合有興趣的精靈在家中兼營這類事務：精靈雖然免疫疾病，魔力回復與強效治療類藥劑對魔法種族同樣有效」.

The village map has no room for either. All four of its non-plaza, non-entrance nodes already carry a dwelling.

## What Changes

- Grow the village map from six nodes to ten, staying a **tree**: 銀葉坡 above the weaving slope, 長老古樹下 north of the old tree, 藥草園 east of the training ground, and 溪畔下游 downstream as scenery. The village's own design rule — 「這個聚落刻意沒有十字路口」, because a hundred-person village laid out like a town reads as a small town — is preserved: four new nodes, four new links, no cycle.
- Add two `merchant` places, both homes, both hosted by women, matching the four already there:
  - **格威娜拉的家** off 銀葉坡, hosted by 格威娜拉·希爾維爾莉夫, 暗影谷村綴飾者.
  - **妮瑞斯的家** off 藥草園, hosted by 妮瑞斯·米斯特瓦勒, 暗影谷村調藥者.
- Add two elven-craft assortments: `elven_adornments` (三稜晶符 and 月牙耳環) and `elven_remedies` (the restorative potions an elf would keep).
- Move `crescent_earring` out of `elven_sundries` and into `elven_adornments`. The collector kept it because nobody else sold it; now the adornment-maker does.
- 長老古樹下 and 溪畔下游 land as map nodes here and stay empty until the commons change fills them.

## Capabilities

### New Capabilities
- `ciaran-village-crafts`: the village's adornment-maker and herbalist, and the rule that an elven-made good sold in the village prices as an everyday thing regardless of how rare it is elsewhere.

### Modified Capabilities
- `village-ciaran-map`: the node count and layout change from six to ten; the tree property and the no-crossroads rule are kept and restated as deliberate.

## Dependencies

This change lands after `place-kind-vocabulary`, `commerce-rulebook-slices` and `merchant-dialogue`.

## Impact

- `world/maps/village_ciaran.py` — four new prototypes, new `MAPSTR`.
- `world/lore/settlements/assortments.py` — two bundles; `elven_sundries` loses a key.
- `world/rules/rulebook/commerce/ciaran.yaml` — new offer rows, one moved verbatim, two `shops:` rows.
- `world/lore/settlements/places_ciaran.py` — two rows.
- `docs/lore/settlement-locations.md` — lines 214 and 232 gain the authored host names.
- No runtime code. Both are `merchant` places.
