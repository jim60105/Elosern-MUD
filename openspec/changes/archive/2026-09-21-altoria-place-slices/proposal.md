## Why

Two things become true once the capital replan lands, and both point at the same file.

`places_altoria.py` will hold nineteen places by the time the capital is finished — roughly five hundred lines in one module. More pressingly, the four remaining capital content changes have no dependency on each other and yet all append rows to it, so they can only be worked one at a time for a reason that has nothing to do with their content.

The replan also makes shared exteriors normal. 工匠巷 carries the forge and the tailor, 市場街 will carry three doors, 大神殿前 two. Two places on one exterior with the same doorway name collide into a single exit, and nothing checks for it — the replan creates that hazard and hand-checks it once.

## What Changes

- Split `places_altoria.py` into three terrace slices — `places_altoria_lower.py`, `places_altoria_middle.py`, `places_altoria_upper.py` — assembled by `places.py` exactly as the two settlement slices already are. The terraces are how the city is described, so a place's file is the first thing that locates it.
- Reject two places that share an exterior and a doorway name, naming both. This is a real hazard now rather than a hypothetical one.
- **No row's content changes.** The five landed places move between files and nothing else about them moves.

## Dependencies

This change lands after `altoria-capital-replan`, whose terraces it splits along, and before any of the four capital content changes, which write to the slices it creates.

## Capabilities

### Modified Capabilities
- `settlement-place-registry`: the record-shape requirement gains the rule that two places sharing an exterior must not share a doorway name.

## Impact

- `world/lore/settlements/places_altoria.py` — deleted, split three ways.
- `world/lore/settlements/places.py` — the assembly gains two slices; `validate_place_registry` gains the collision check.
- No runtime code.
