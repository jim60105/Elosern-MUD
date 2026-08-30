# Proposal: magic-xp-engine-retirement

## Why

The growth redesign (`docs/superpowers/specs/2026-08-30-use-driven-progression-design.md`,
decision D3) establishes that **using a skill is the only source of growth**. The
magic-XP engine — a parallel level-grinding channel that quietly raised a second
stat (magic level) from skip time and monster kills — contradicts that model: it
grants progress for *not* using skills, double-counts kills the quest system already
credits, and is the sole reason the retired `magic_rank_title` ladder's numeric gate
(`can_cast_spell_tier`) ever existed. Its predecessor change
(`magic-power-static-rename`) has already demoted `magic_level` to the static
`magic_power` trait; this change deletes every writer that ever moved it, completing
design §7's deletion table.

## What Changes

- BREAKING: delete the magic-XP accumulator and every writer: `entity.db.magic_xp`,
  `_stored_magic_xp()` snapshot registration, `MAGIC_XP_PER_LEVEL` /
  `magic_xp_per_level`, `STUDY_BASE_XP_PER_HOUR` / `study_base_xp_per_hour`,
  `accrue_magic_study()`, `_apply_level_ups()`, `grant_combat_kill_xp()`, and
  `COMBAT_KILL_XP_TABLE` (design §7 rows 1–4).
- BREAKING: the world-clock stage `magic_study` is renamed `practice_settlement` in
  the same fixed tuple position and becomes a zero-growth placeholder implemented in
  `world/rules/clock.py` directly (the self-arming lazy import into
  `world.rules.progression` is removed with its target). `declared-practice-skip`
  later turns it into the declared-practice writer; stage order is untouched.
- BREAKING: delete the elemental cast-gate machinery: `can_cast_spell_tier()`,
  `can_cast_skill()`, `_element_effective_magic_level()`, and the effective-level
  concept (design §7 rows 6, 8). Interim cast eligibility is **ownership plus MP
  affordability only** — `use-driven-skill-lineage` lands the real `can_use_skill`
  lineage gate before any release, so the ungated interim never ships.
- BREAKING: delete the `element_mastery_rank` typed effect class and rewrite the
  nine `<element>_mastery` registry rows' effects to the inert
  `passive_trait:element_mastery` flavor form (design §7 row 7). The mastery skills
  themselves keep their identity — `sexual_magic_mastery` is explicitly untouched
  (its domain's ladder is counter-gated elsewhere).
- Upkeep kill credit keeps source attribution for defeat EventLogs and quest
  effects, but stages no XP; the deferred kill-XP staging check in the action
  pipeline is deleted; `magic_xp` leaves every snapshot/restore surface.
- The `magic-level-progression` capability is removed in its entirety (all six
  requirements).

## Capabilities

### New Capabilities

(None.)

### Modified Capabilities

- `magic-level-progression`: REMOVED — the whole capability (six requirements).
- `settlement-stage-order`: stage renamed to `practice_settlement` as a zero-growth
  placeholder; combat-source skip composition preserved.
- `world-clock`: the pinned stage tuple scenario carries the renamed stage.
- `cast-settlement-atomicity`, `skill-proficiency-tracking`,
  `player-character-creation`: `magic_xp` leaves snapshot/restore and the activation
  attribute list.
- `action-resolution-pipeline`: elemental tier rejection requirement removed; the
  kill-XP staging exception and the preview's spell-tier eligibility check are
  deleted (interim gate = ownership + MP).
- `monster-action-policy`: the delegated policy proposes the first affordable
  damage skill; the tier-block skip requirement is retitled and rewritten.
- `element-mastery`: `can_cast_spell_tier` and `can_cast_skill` requirements
  removed (freeform-scale entitlement is untouched).
- `element-affinity`: the multiplier survives; the element-effective-magic-level
  paragraph is deleted.
- `combat-upkeep-settlement`, `combat-resolution`, `player-combat-session`,
  `guild-rank-exams`: kill-XP wording removed from credit/atomicity/exam clauses.
- `skill-effect-model`: `element_mastery_rank` leaves the recognized prefix set and
  fails closed at parse.
- `skill-registry`: the eight spell-set requirements lose their cast-gate scenarios
  (tier grouping survives as a data label); the eight-elements-mastery effects row
  is rewritten to the flavor form.

## Impact

- Code: `world/rules/progression.py`, `clock.py`, `action.py`, `upkeep.py`,
  `combat.py`, `cast_settlement.py`, `character_creation.py`,
  `world/skills/effects.py`, `world/skills/registry.py`,
  `world/rules/rulebook/progression.yaml`, plus the pinned test suites
  (`test_progression.py`, `test_upkeep_settlement.py`, `test_guild_exams.py`,
  `test_combat_session_recovery.py`, `test_character_creation.py`).
- Specs: removes one main capability; its traceability IDs retire with it (the tool
  indexes main specs only, so no annotation debt is created here — see tasks).
- Depends on: `magic-power-static-rename` (trait already renamed; this change
  deletes the writers that interim still ran against).
- No backward-compatibility or migration work: the project is unreleased with zero
  users. No save data carries forward.
