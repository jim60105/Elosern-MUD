## 1. Schema

- [ ] 1.1 Add optional `polarity: debuff | buff` field to `buffs.yaml`'s schema (default `buff`)
- [ ] 1.2 Add `polarity: debuff` to `poisoned`, `paralysis`, `fear`

## 2. Typed effect

- [ ] 2.1 Add `CleanseEffect(scope: Literal["status"])` to `world/skills/effects.py`'s dispatch table
      (depends on `skill-effects-typed-model`)

## 3. Handler

- [ ] 3.1 Implement `_handle_cleanse` in `world/rules/buffs.py`, iterating the target's active buffs and
      calling `entity.buffs.remove()` for each `polarity == "debuff"` entry
- [ ] 3.2 Register it via `register_effect_handler("cleanse", _handle_cleanse, ...)` in `action.py`

## 4. Tests

- [ ] 4.1 Cleansing removes an active debuff (`poisoned`)
- [ ] 4.2 Cleansing does not remove a beneficial buff (`focus`)
- [ ] 4.3 Cleansing with no active debuffs is a no-op that does not error

## 5. Downstream

- [ ] 5.1 Update `spell-catalog-light`'s `proposal.md`/`design.md` dependency list to name this change
      explicitly (it was written before this change existed) and confirm `purify`'s
      `effects=["cleanse:status"]` matches this change's final grammar exactly
