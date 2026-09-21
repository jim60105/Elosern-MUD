## Why

`AGENTS.md` says to 「use Traditional Chinese for player-facing game prose」. The `village-ciaran-map` capability says it outright: 「Room keys and descriptions SHALL be Traditional Chinese」. Every room description in the game is in English.

That is not a style quibble — it is a spec the code violates, and the traceability gate is green over it, which means the covering test never checked. A player walking through 聖潔王都 reads Chinese room names and English room bodies.

The rest of the game already got this right. `LIMBO_DESC` is Chinese, every `SceneArchetype.scene_sentence` is Chinese, every item's presentation text is Chinese. Rooms are the one surface that was never converted, and the field is even named `room_desc_zh`.

## What Changes

- Convert the nine authored interior descriptions in `places_altoria.py` and `places_ciaran.py` to Traditional Chinese.
- State the rule once, as a requirement on `grid-room-sync`, covering both grid rooms and the interiors attached to them — so it applies to every room rather than only to the elven village, which is the only capability that happens to say it today.
- Add a regression guard: a test that every authored room description is Traditional Chinese prose. The reason the current violation survived is that nothing looked.
- The map modules are **not** touched here. `altoria-capital-replan` rewrites all twenty-one capital rooms and `ciaran-village-crafts` rewrites the village's, both authoring in Chinese from the start. Converting them here as well would mean writing the same prose twice and colliding on both files.

## Capabilities

### Modified Capabilities
- `grid-room-sync`: gains the requirement that authored room prose is Traditional Chinese, and that a room's description and its name are in the same language.

## Dependencies

This change lands after `altoria-capital-replan`, `altoria-place-slices` and `ciaran-village-crafts`.

## Impact

- the three `places_altoria_*.py` terrace slices and `places_ciaran.py` — nine descriptions.
- A new regression test over the authored room prose.
- `world/maps/altoria_capital.py`, `world/maps/village_ciaran.py` — untouched; their rewrites carry their own conversion.
- No runtime code. Descriptions are data.
