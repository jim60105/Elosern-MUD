## Why

These are the capital's last three unbuilt location types, and the two staffed ones are the ones only a capital gets. 魔法學院與圖書館 is 「有」 for 都城 and 「無」 for every other archetype — the document calls it 「全大陸唯二真正夠格稱作『學院』的設施」, and the Kingdom's is 薇歐蕾特·阿爾托利亞's old school. 商會與貿易行 is the designated future source of escort commissions, the hook `guild request` already names when it reports that escort work is not yet open.

市場街 is the third and is different in kind: the document says at line 374 that it needs no fixed functional NPC, because its trade hangs on individual stallholders. It is the clearest case in the whole document for a room with nobody in it.

## What Changes

- Add two `attendant` places with their dialogue tables:
  - **聖潔王都王立魔法學院** off 學院前, hosted by 奧德溫·薩契, 聖潔王都魔法學院院長.
  - **聖潔王都商會公所** off 東市, hosted by 尤斯汀·柯德溫, 聖潔王都商會會長.
- Add **聖潔王都市集棚** off 市場街 as a **host-less** place: the covered stalls, walkable and empty of permanent staff.
- The academy is the capital's lore-reveal location. Its dialogue answers on magic ranks and elements, which is what the document says an academy is for: 「知識圖鑑『魔法等級』『元素』等分類條目最自然的揭露場景，透過與駐院學者、教師的 `talk` 對話觸發」.
- Introduce **no apprenticeship mechanism**. The document marks 「拜師習得新技能」 〔提案〕 at line 454 and states that skill acquisition runs through the lineage tree's proficiency accumulation, with mentorship as narrative framing only.
- Introduce **no escort commissions**. The merchant hall is the hook for them, not their arrival; escort work needs the quest type first.

## Capabilities

### New Capabilities
- `altoria-learning-and-exchange`: the capital's academy, merchant hall and market stalls, the academy's role as a lore-reveal location, and the rule that neither location implements the system it is the designated future home of.

## Dependencies

This change lands after `place-attendant-profession`, `hostless-places`, `altoria-capital-replan`, `altoria-place-slices` and `place-kind-vocabulary`.

## Impact

- `world/lore/settlements/places_altoria_upper.py` (academy) and `places_altoria_middle.py` (merchant hall, stalls) — three rows, one host-less, two sharing exteriors with existing shops.
- `world/lore/dialogue/altoria.py` — two dialogue tables.
- `docs/lore/settlement-locations.md` — lines 245 and 456: two placeholder host names.
- No rulebook, no commerce, no runtime code.
