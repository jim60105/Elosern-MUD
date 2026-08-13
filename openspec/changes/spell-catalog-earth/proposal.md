## Why

The skill-system redesign (`docs/superpowers/specs/2026-08-12-skill-system-redesign-design.md`, §4.4)
defines a full eight-element, five-tier spell catalog, but `SKILL_REGISTRY` today carries no seed
spell for 土 magic. Without the
10 土-element spells, players who invest in 土 magic have no tier progression to
grow into, and the new `can_cast_spell_tier` cast-gate (from `element-mastery-cast-gate`) has nothing
to gate for this element.

## What Changes

- Add the ten `土`-element spells from design doc §4.4 to `world/skills/registry.py`'s `SKILL_REGISTRY` (10 new keys).
- Add 5 new rows to `world/rules/rulebook/buffs.yaml` (rate/bounds/decay shape only, per the `buff-handler-integration` spec's existing constraints) backing the status-effect and shield spells in this set.
- Add 5 matching rows to `world/rules/rulebook/status_display.yaml` — `status_display.py`'s fail-closed coverage requires every buff key to have exactly one display entry.

## Capabilities

### New Capabilities

*(none — this change only extends the existing `skill-registry` capability's seed content)*

### Modified Capabilities

- `skill-registry`: `SKILL_REGISTRY` gains an ADDED requirement declaring the full ten-key 土-element
  spell set (tier, target, MP cost, and typed `effects`). All ten keys are new — 土 has no
  pre-existing anchor skill to recost.

## Impact

- **Affected code**: `world/skills/registry.py` (10 new spell entries via the `_elemental_spells` builder), `world/rules/rulebook/buffs.yaml` (5 new rows), `world/rules/rulebook/status_display.yaml` (5 new rows).
- **Dependencies (blocking prerequisites)**:
- `skill-effects-typed-model` (**must land first**) — defines `world/skills/effects.py`'s typed
  effect dataclasses (e.g. `StatMultiplyEffect`) that every skill's parsed `effects` list must resolve
  to; also removes the stale "`stat_multiply` is the only interpreted convention" docstring claim in
  `world/skills/registry.py`. This change's new spells declare `effects` strings that must parse
  cleanly under that typed dispatch table.
- `element-mastery-cast-gate` (**must land first**) — defines `can_cast_spell_tier(entity, element,
  tier)` in `world/rules/progression.py` and the four new `<element>_mastery` skills for
  water/earth/lightning/ice (fire/dark/wind/light already have theirs). This change's spells are
  gated by that function once it lands; until then the ten new keys exist in the registry but are not
  yet tier-gated.
- **Parallel-safety**: this change does **not** depend on any of the other seven `spell-catalog-<element>`
  changes (fire/water/wind/earth/lightning/ice/light/dark are mutually independent). Once the two (or
  three, for fire/water/light) prerequisite changes above land, all eight `spell-catalog-<element>`
  changes are safe to implement in parallel by different people/agents without coordination between them.
- **Systems touched**: none beyond registry content and rulebook data — no new effect-handler code, no
  new combat-formula variant, no new `RejectReason`. `can_cast_spell_tier` and the `heal:`/`damage:`
  handlers are consumed, not reimplemented, by this change.
