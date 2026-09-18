## Why

The conferral store is write-only. `entity.db.skill_grants` and the `conferred_growth_rate` buff can be
written but never removed, so a grant is permanent by accident rather than by design: an opposing
caster's buff on a boss stays for the rest of the game, and a player who wants to undo a conferral has
no move. The divine-mystery 統御線 makes this an explicit gameplay pole — 權能收回, "解除目標身上的一切
授予，不論來源是誰" (`docs/lore/skill-trees/divine-mystery.md` §2) — which is the answer to an enemy elf
lending its power to something else. The verb needs a removal primitive before that node can exist.

## What Changes

- Add a deterministic-core revocation primitive beside the conferral write: it clears the target's
  recorded skill grants and removes every `conferred_growth_rate` buff instance on that target,
  whatever their source, and touches nothing else.
- Add a `revoke_grants` effect prefix — a payload-free typed marker dataclass, its `parse_effect`
  branch, and a handler declaring the `skill_grants` and `buffs` surfaces — so a skill can reach the
  primitive.
- Revocation is total, not selective: no source filter, no skill filter.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `skill-handler`: ADDED — the revocation primitive, its totality, its non-interference with the
  target's own skills and unrelated buffs, and its rollback behavior.
- `skill-effect-model`: MODIFIED — `revoke_grants` joins the recognized prefix set as a bare prefix
  whose payload forms fail at registry load.

## Impact

`world/skills/effects.py` (marker dataclass + parse branch); `world/rules/buffs.py` (clear every
`conferred_growth_rate` instance regardless of source); `world/rules/skill_effects.py` (the revocation
write); `world/rules/action.py` (handler + registration); tests plus `.github/evennia-shards.json`. No
registry data and no catalog node lands here.

## Batch

- depends-on: conferral-grant-store
  (Reads that change's store semantics — a revocation that clears a replace-by-key store is a
  different contract from one that clears an append-only list — and edits the same
  `register_effect_handler` tail of `world/rules/action.py`. The two touch different `skill-handler`
  requirements, so neither rebases the other's spec text. `divine-veil-reveal` also MODIFIES the
  `skill-effect-model` recognized-prefix requirement: whichever of the two lands second rebases its
  copy onto the synced main spec so the recognized set names both new prefixes.)
