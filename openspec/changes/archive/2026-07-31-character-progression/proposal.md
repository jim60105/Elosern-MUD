## Why

Design doc §3.2 lists `rules/progression` as a module, but no roadmap item owned it until change 6
(`buffs-rulebook`) surfaced the gap: it built `growth_rate_multiplier(entity)` and
`grant_conferred_growth_rate(...)` specifically for Elosia's conferred magic-growth-rate buff on
Violet, and named this change (`character-progression`, 11b) as their consumer. Without this change,
`magic_level` is a `CounterTrait` that starts at 0 and never moves — no code path anywhere in the
project increases it, and `growth_rate_multiplier()` returns a number nothing ever reads.

## What Changes

- Add `world/rules/progression.py` — the sole place `magic_level` growth and per-skill proficiency
  growth are computed, matching design doc §3.2's forward-declared module.
- **Magic-level growth**, driven by a documented combination of study time and combat experience:
  - `accrue_magic_study(entities, seconds, source)` — a settlement-stage-shaped callable that grants
    magic XP proportional to elapsed `AdvanceSource.SKIP` time only (ambient study/practice during
    deliberate downtime — `rest`/`sleep`/`wait`), no-op for `COMMAND`/`COMBAT`-sourced advances.
  - `grant_combat_kill_xp(entity, monster_tier_key)` — a declared seam a future combat-completion
    consumer (change 9/10's battle resolution, or the eventual top-level combat command named by
    change 11's `settle_combat_result()`) calls once per kill.
  - Every magic-XP gain is scaled by `effective_magic_growth_multiplier(entity)`, which multiplies
    three independent sources: `RaceProfile.learning_multiplier` (change 2), a self-multiplier read
  from the entity's own owned passive skills via change 5's existing `growth_rate:magic:<N>` effect-ID
  convention (for "reincarnation boon"-style
    passives such as Elosia's), and change 6's `growth_rate_multiplier(entity)` (conferred buffs).
  - `magic_level` is hard-capped at `RaceProfile.magic_cap` (or a `Monster`'s tier-driven cap of `0`):
    the multiplier accelerates *rate*, never the ceiling. Surplus XP at the cap is discarded, not
    banked.
- **Skill proficiency**, kept structurally separate from character-level `magic_level`:
  - `entity.db.skill_proficiency: dict[str, float]` — a new, additive raw attribute (the same
    "additive attribute, no edit to the owning change's typeclass" pattern change 5's
    `entity.db.skill_grants` and change 4's `entity.db.inventory` already use).
  - `grant_skill_practice_xp(entity, skill_key, uses=1)` — a declared seam called once per successful
    use of that skill (a future `ActionResolver` integration point), scaled only by
    `RaceProfile.learning_multiplier` — not by `growth_rate_multiplier()`, since change 6's
    `conferred_growth_rate` buff's own YAML definition names its target as `magic_level_growth`
    specifically, not skill practice.
  - `skill_proficiency_level(entity, skill_key)` — a pure derived query, no upper bound.
- `world/rules/rulebook/progression.yaml` — every invented rate constant in one place (XP-per-level,
  XP-per-study-hour, per-tier combat-kill XP, XP-per-skill-level, XP-per-practice), following the
  project's "recompute/derive from data, flag invented numbers" convention.
- Integrate `grant_skill_practice_xp()` and deferred `grant_combat_kill_xp()` checks into ActionResolver's
  atomic commit. The combat check evaluates unique, resolved, initially living tiered targets only after
  damage is committed, so each newly defeated monster grants XP exactly once.
- **Not built**: guild merit/rank (change 16's), quests (change 15's), a new player-facing command
  (study/training reuses world-clock's existing `rest`/`sleep`/`wait` commands instead), and any edit
  to change 11's own settlement-stage artifacts — this proposal names exactly what change 11 needs (a
  new `magic_study` stage) for the coordinator to carry over, per this task's explicit instruction not
  to edit another change's artifacts directly.

## Capabilities

### New Capabilities
- `magic-level-progression`: `magic_level` growth from study time and combat-kill XP,
  `effective_magic_growth_multiplier()` folding in race/self/conferred multipliers, the hard race-cap
  ceiling, and the settlement-stage-shaped `accrue_magic_study()` callable.
- `skill-proficiency-tracking`: per-skill practice-XP accrual, kept independent of `magic_level`,
  scaled only by `RaceProfile.learning_multiplier`.

### Modified Capabilities
- `action-resolution-pipeline`: permit its otherwise caller-neutral pipeline to stage tiered monster
  kill XP only when a battlefield-backed context resolved a `Monster` target from positive HP to zero.

## Impact

- **New files**: `world/rules/progression.py`, `world/rules/rulebook/progression.yaml`,
  `world/rules/tests/test_progression.py` (and sibling test modules per capability).
- **New, additive attribute**: `entity.db.magic_xp` (float accumulator) and
  `entity.db.skill_proficiency` (`dict[str, float]`) — raw Evennia attributes, no edit to
  `typeclasses/entities.py` or any other change's typeclass.
- **Reads, without modifying**: change 2's `RACE_REGISTRY`/`RaceProfile.learning_multiplier`/
  `magic_cap`, change 3's `entity.traits.magic_level` (`CounterTrait`), change 5's `SKILL_REGISTRY`/
  `entity.skills.owned_keys()`, change 6's `growth_rate_multiplier(entity)`/`entity.buffs`, change 11's
  `AdvanceSource` enum.
- **Existing world-clock integration**: change 11 has already added its `magic_study` stage between
  `sexual_decay` and `daily_resets`. It lazily imports and calls this change's
  `accrue_magic_study(entities, seconds, source)` after the combat gate; this change supplies the
  callable and verifies SKIP-only accrual end to end.
- Growth-rate scales and calculated magic-growth multipliers must be finite and non-negative. Invalid
  persisted legacy state fails before a progression write and, when invoked through ActionResolver,
  rolls the full action back.
- **Named, not built**: guild merit/rank progression (change 16), quest reward XP (change 15 — the
  attachment point is declared, not populated), and any change to the map layers or generative layer.
- No database migration concerns — the project is unreleased with zero users.
