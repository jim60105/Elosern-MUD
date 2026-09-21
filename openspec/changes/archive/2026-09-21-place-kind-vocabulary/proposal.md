## Why

`PlaceKind` is a closed six-member vocabulary — `GUILD_HALL`, `GENERAL_STORE`, `WEAPONSMITH`, `OUTFITTER`, `EATERY`, `HOME` — written when six places existed and every one of them fitted. Eighteen more are coming, and none of the six describes a palace, a cathedral, a bathhouse, a drill yard, an academy, a merchant hall, covered market stalls or a communal eating shelter.

The field is required on every place, so each of those locations will be forced to pick a wrong value. Nothing will stop it: `kind` has no consumer outside the registry modules themselves, so a bathhouse declared `GENERAL_STORE` validates, loads and runs. The error would be silent, permanent and spread across six separate changes, each author picking a different wrong answer.

That is the case for fixing the vocabulary before the content lands rather than after.

## What Changes

- Extend `PlaceKind` with the members the remaining locations need: `JEWELLER`, `ALCHEMIST`, `TEMPLE`, `SANCTUM_SHOP`, `TAVERN`, `LODGING`, `BATHHOUSE`, `PALACE`, `WATCH_POST`, `TRAINING_GROUND`, `ACADEMY`, `MERCHANT_HALL`, `MARKET`, `COMMONS`.
- State what the vocabulary is for, because it currently has no stated purpose and that is why it was easy to outgrow: a kind names **what the location is in the world**, not what mechanism its host carries. A village dwelling that sells blades is a `HOME`, not a `WEAPONSMITH` — which is already how the four elven homes are authored, and which only reads as deliberate once the rule is written down.
- **No shipped place changes its kind.** The six existing members keep their meanings and their rows.

## Capabilities

### Modified Capabilities
- `settlement-place-registry`: the record-shape requirement gains the rule that a place's kind describes the location rather than its host's capability, and that the vocabulary covers the location types the world document defines.

## Dependencies

This change lands after `hostless-places`, whose text its `settlement-place-registry` delta is written against.

## Impact

- `world/lore/settlements/places.py` — the enum.
- No other module. `kind` has no reader outside the registry modules, which is both why this is safe and why it needed saying.
