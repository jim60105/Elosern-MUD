## Why

The capital has no seat of government. 「王都仍然不夠大，缺了很多王都該有的東西，例如王宮」 was the note that opened this whole build, and the replan put a 王宮前庭 at the top of the climb precisely so the palace would have somewhere to be.

Three more of the document's 治理與防衛 locations are also missing. 衛兵駐所與城門 is 「有」 for every settlement archetype except elven villages and is the one location type the capital already half-has — the gates exist, the guardhouse behind them does not. 訓練場 is where `practice` and `guild exam` are meant to happen. 貴族區 is the document's designated 「限制進入」 scene, the natural home of a future political questline.

## What Changes

- Add **聖潔王都王宮** behind 王宮前庭 as a **host-less** place: a throne approach a player can walk into with nobody standing in it. The document is clear that a noble quarter's value is 「劇情門檻」 — a stage for events that have not been written. A caretaker NPC would be filler standing in a room whose point is that it is waiting.
- Add three `attendant` places with their dialogue tables:
  - **聖潔王都貴族區衛所** off 貴族區前, hosted by 古利安·鷹守, 聖潔王都貴族區衛隊長.
  - **聖潔王都衛兵駐所** off 南門, hosted by 托瓦德·鄧堡, 聖潔王都衛兵隊隊長.
  - **聖潔王都校場** off 校場外, hosted by 伊沃·高丘, 聖潔王都訓練場教頭.
- Introduce **no access control**. The palace and the noble quarter are open. The document marks their restriction as a story device for a questline that does not exist, and a lock with nothing behind it is a dead end, not a mystery.
- Introduce **no bounty board**. The document rules it out explicitly at line 410: a guardhouse wanting to post work should use the guild or a private commission, 「不宜另開一套平行的懸賞系統」.

## Capabilities

### New Capabilities
- `altoria-crown-and-watch`: the capital's palace, noble quarter, guardhouse and drill yard, the rule that the crown's rooms stand open until a story gates them, and the rule that the watch posts no work of its own.

## Dependencies

This change lands after `place-attendant-profession`, `hostless-places`, `altoria-capital-replan`, `altoria-place-slices` and `place-kind-vocabulary`.

## Impact

- `world/lore/settlements/places_altoria_upper.py` (palace, noble watch, drill yard) and `places_altoria_lower.py` (guardhouse) — four rows, one of them host-less.
- `world/lore/dialogue/altoria.py` — three dialogue tables.
- `docs/lore/settlement-locations.md` — lines 395, 412 and 433: three placeholder host names.
- No rulebook, no commerce, no runtime code.
