## 1. Schema

- [x] 1.1 Add optional `polarity: debuff | buff` field to `buffs.yaml`'s schema (default `buff`)
- [x] 1.2 Add `polarity: debuff` to `poisoned`, `paralysis`, `fear`

## 2. Typed effect

- [x] 2.1 Add `CleanseEffect(scope: Literal["status"])` to `world/skills/effects.py`'s dispatch table
      (depends on `skill-effects-typed-model`)

## 3. Handler

- [x] 3.1 Implement `_handle_cleanse` in `world/rules/buffs.py`, iterating the target's active buffs and
      calling `entity.buffs.remove()` for each `polarity == "debuff"` entry
- [x] 3.2 Register it via `register_effect_handler("cleanse", _handle_cleanse, ...)` in `action.py`

## 4. Tests

- [x] 4.1 Cleansing removes an active debuff (`poisoned`)
- [x] 4.2 Cleansing does not remove a beneficial buff (`focus`)
- [x] 4.3 Cleansing with no active debuffs is a no-op that does not error
- [x] 4.4 Cleansing removes only debuffs when both kinds are active; multi-target staging is one entry
      per target (rubber-duck follow-up)
- [x] 4.5 Paused and expired debuffs are neither removed nor counted (rubber-duck follow-up)
- [x] 4.6 A commit failure after cleansing restores the removed debuff (rubber-duck follow-up)
- [x] 4.7 End-to-end `ActionResolver.resolve()` cast of a registered `cleanse:status` skill succeeds
      and emits the `buffs_cleansed` event entry (rubber-duck follow-up)

## 5. Downstream

- [x] 5.1 Update `spell-catalog-light`'s `proposal.md`/`design.md` dependency list to name this change
      explicitly (it was written before this change existed) and confirm `purify`'s
      `effects=["cleanse:status"]` matches this change's final grammar exactly
