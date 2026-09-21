## Why

The deep-dive section names exactly four kinds of location an elven village actually needs, at line 490: 「匠人住宅、共食棚、視分支而定的武術訓練場、長老居所」. The village has the artisan dwellings. It has none of the other three as places you can enter.

The training ground matters most for 基亞蘭族 specifically. Line 441: 「基亞蘭族有濃厚的刀術文化，村中設有戰士導師駐守的練刀場」, and 悠花's biography uses it as a core setting. There is a 練刀場 node with nobody on it.

The elder's dwelling is the village's answer to 貴族區／統治機構, and the document is careful about its weight: elves 「很少有『重要事務』」, so the elder council is 「更接近一個象徵性場所」 rather than a working government.

共食棚 is where the village eats together, and the document is explicit that 「族人之間不存在『點餐付錢』」 — so it is a room with nobody selling anything, which is precisely what it should be.

## What Changes

- Add **共食棚** off 村中廣場 as a **host-less** place: the communal shelter, open, with nobody behind a counter, because the document says eating together is not a transaction.
- Add two `attendant` places with their dialogue tables:
  - **泰莉爾的家** off 練刀場, hosted by 泰莉爾·菲溫德, 暗影谷村刀術導師. She shares the training ground with 海莉爾 the blade-smith, which is what a training ground is: the person who makes them and the person who teaches them.
  - **艾莉妮斯的家** off 長老古樹下, hosted by 艾莉妮斯·達恩斯特瑞德爾, 暗影谷村長老.
- Author the elder as a keeper of memory, not an administrator. Her dialogue answers about the branch, the forest and the village's past; it offers no council business, no petition, no permission, because the document says there is rarely anything to decide.
- Introduce **no mechanism**. Sword instruction is `practice`, which works anywhere; the instructor's dialogue points at it and adds nothing.

## Capabilities

### New Capabilities
- `ciaran-village-commons`: the village's shared spaces — the communal shelter, the sword instructor and the elder — and the rule that an elven village's non-trading locations carry no institution, no counter and no gate.

## Dependencies

This change lands after `place-attendant-profession`, `hostless-places`, `place-kind-vocabulary` and `ciaran-village-crafts` (whose map expansion provides 長老古樹下).

## Impact

- `world/lore/settlements/places_ciaran.py` — three rows, one host-less.
- `world/lore/dialogue/ciaran.py` — two dialogue tables.
- `docs/lore/settlement-locations.md` — the elven-village notes in the 訓練場 and 貴族區 sections gain the authored names.
- No rulebook, no commerce, no runtime code.
