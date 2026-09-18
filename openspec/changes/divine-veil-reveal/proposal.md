## Why

The disguise layer can be written but never read through and never lifted by anyone but its wearer. The
lore has promised the opposite for a while: 真知鑑定, the ceiling of the mundane appraisal lineage, is
documented as **completely ineffective** against a divine veil, and
`docs/lore/skill-trees/utility.md` states that the only way through one is "另一名具神性者以神之秘法對神
之秘法". That sentence has had no node behind it. The divine-mystery 帷幕線 supplies the two nodes
(揭帷之眼 and 真名之視) that turn the class boundary from a narrative assertion into a mechanical rule,
and both need something the layer does not have today: a record of whether the veil on an entity is
divine.

## What Changes

- Add a `reveal_disguise` effect prefix with exactly two strengths: the bare form clears a target's
  veil only when its provenance is mundane, and `reveal_disguise:true_name` clears a veil of any
  provenance.
- A reveal against a veil it cannot pierce is a clean, reported no-op, not a rejection: failing to see
  through something is an outcome, not an invalid action.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `skill-handler`: ADDED — the provenance-scoped reveal primitive and its two strengths.
- `skill-effect-model`: MODIFIED — `reveal_disguise` joins the recognized prefix set with its closed
  two-form grammar.

## Impact

`world/skills/effects.py` (dataclass + parse branch); `world/rules/skill_effects.py` (the reveal
primitive beside the existing disguise write); `world/rules/action.py` (handler + registration
declaring the `traits` surface); tests plus `.github/evennia-shards.json`. The provenance record itself
already exists — `divine-veil-cast-path` writes it and registers it in every snapshot path — so this
change only reads it. The disguise writer ledger in `world/rules/tests/test_disguise_boundary.py` is
unchanged, because the reveal's clear stays in `world/rules/skill_effects.py`.

## Batch

- depends-on: divine-veil-cast-path
  (That change writes the provenance record this one consumes, because its own provenance-scoped
  self-toggle needs it; this change is the only reader. Both edit the same region of
  `world/rules/action.py`.
  `conferral-revocation` also MODIFIES the `skill-effect-model` recognized-prefix requirement:
  whichever of the two lands second rebases its copy onto the synced main spec so the recognized set
  names both new prefixes.)
