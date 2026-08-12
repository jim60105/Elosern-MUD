## Why

The skill-system redesign (`docs/superpowers/specs/2026-08-12-skill-system-redesign-design.md`, §4.4)
defines a full eight-element, five-tier spell catalog, but `SKILL_REGISTRY` today only carries one
seed spell for 雷 magic. Without the
other 10 雷-element spells, players who invest in 雷 magic have no tier progression to
grow into, and the new `can_cast_spell_tier` cast-gate (from `element-mastery-cast-gate`) has nothing
to gate for this element beyond its single existing spell.

## What Changes

- Add the ten `雷`-element spells from design doc §4.4 to `world/skills/registry.py`'s `SKILL_REGISTRY` (10 new keys).
- Add 2 new rows to `world/rules/rulebook/buffs.yaml` (rate/bounds/decay shape only, per the `buff-handler-integration` spec's existing constraints) backing the status-effect and shield spells in this set.
- Reuse 1 existing `buffs.yaml` row as-is (no new row) where an exact semantic match already exists.

## Capabilities

### New Capabilities

*(none — this change only extends the existing `skill-registry` capability's seed content)*

### Modified Capabilities

- `skill-registry`: `SKILL_REGISTRY` gains an ADDED requirement declaring the full ten-key 雷-element
  spell set (tier, target, MP cost, and typed `effects`), and the pre-existing 雷 anchor skill(s)
  (`n/a`) are recosted per §4.3's table rather than duplicated.

## Impact

- **Affected code**: `world/skills/registry.py` (10 new `_skill(...)` entries), `world/rules/rulebook/buffs.yaml` (2 new rows, 1 existing row reused).
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
