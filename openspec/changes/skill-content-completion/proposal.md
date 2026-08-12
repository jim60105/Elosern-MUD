## Why

Several character-sheet-described skills already have a near-exact existing registry entry that only
needs its Traditional-Chinese label/description aligned to the character-sheet wording — no new
mechanism. One skill (悠花's "宗師級" 雙刀流) is described as a distinctly higher tier than the existing
`dual_wield_style` stance and has no registry entry at all. Per the approved design doc §7, this change
does the small label-alignment edits and adds the one missing attack skill, closing out the
character-sheet content-completion table that isn't otherwise covered by a more specific proposal in
this batch.

## What Changes

- `guardian_instinct`'s label/description updates to read as 護主本能 (莉茲婭's card wording) rather
  than the more generic 守護直覺 — no effect-string change.
- `blade_art_mastery`'s description updates to explicitly cover 刀術 (sword-arts, per 悠花's 刀術強化)
  in addition to 劍術 (blade-arts) — no effect-string change.
- Add `dual_blade_mastery` (雙刀流·宗師級, `ACTIVE`, `SINGLE` target, `damage:dark:physical` — matching
  悠花's established dark-elemental physical attack pattern already used by her `shadow_slash`, SP 30),
  a higher-tier sibling to `dual_wield_style` rather than a replacement — 悠花's card lists both a
  stance-like baseline capability and a named "宗師級" combat art.

## Capabilities

### New Capabilities
(none)

### Modified Capabilities
- `skill-registry`: two label/description edits (no effect-string change), one new skill.

## Impact

- `world/skills/registry.py` only.
- Depends on `skill-effects-typed-model` (typed effects for the new `dual_blade_mastery` skill's
  `effects` list — though it uses the already-working `damage` prefix, so this is a light dependency).
- No other proposal in this batch depends on this change; it can land any time after
  `skill-effects-typed-model`.
