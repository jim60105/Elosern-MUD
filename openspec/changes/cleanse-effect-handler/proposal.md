## Why

While writing `spell-catalog-light` (part of the skill-system redesign batch), a second undeclared gap
surfaced alongside the already-known `heal:` gap: `purify` (淨化術, 解除異常狀態) has no cleanse/dispel
mechanism anywhere in the codebase. `BuffHandler.remove()` exists per the `buff-handler-integration`
spec, but nothing calls it from a cast-time effect. Without this change, `purify` — and any future
spell/skill with a cleanse flavor — would either ship dead or force a guessed-correct effect grammar
into a content-only proposal that has no business inventing new mechanism.

## What Changes

- Add a new `cleanse` effect-ID convention: `cleanse:<scope>` where `<scope>` is `status` (removes all
  active buffs matching a "debuff" classification) for now — mirroring `heal-effect-handler`'s
  `<shape>` pattern rather than inventing a different grammar shape for a sibling effect.
- Add a cast-time handler in `world/rules/combat.py` (or `world/rules/buffs.py`, whichever already owns
  `BuffHandler` interaction — see design.md) registered via `register_effect_handler`, calling
  `entity.buffs.remove()` for every currently-active buff whose `buffs.yaml` definition is tagged as a
  debuff (see design.md for how "debuff" is determined — reuses existing data, does not invent a new
  classification field if one already exists).
- Add `CleanseEffect(scope: Literal["status"])` to `world/skills/effects.py`'s typed-effect dispatch.

## Capabilities

### New Capabilities
- `cleanse-effect-handler`: the `cleanse:` effect convention, its typed representation, and its
  cast-time resolution behavior (removing debuff-classified active buffs).

### Modified Capabilities
(none)

## Impact

- New code in `world/rules/combat.py` or `world/rules/buffs.py` (handler) and `world/skills/effects.py`
  (typed effect).
- Depends on `skill-effects-typed-model` (must land first).
- Blocks `spell-catalog-light` (its `purify` spell's `effects=["cleanse:status"]` is provisional until
  this change lands and settles the final grammar) — this dependency was not known when
  `spell-catalog-light` was first drafted and should be added to that change's Impact section before
  either lands.
