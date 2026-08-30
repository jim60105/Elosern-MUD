# Tasks: magic-xp-engine-retirement

## 1. Progression engine deletion

- [x] 1.1 In `world/rules/progression.py`, delete `MAGIC_XP_PER_LEVEL`,
  `STUDY_BASE_XP_PER_HOUR`, `COMBAT_KILL_XP_TABLE`, `_stored_magic_xp()`,
  `_apply_level_ups()`, `accrue_magic_study()`, `grant_combat_kill_xp()`, and
  `effective_growth_multiplier()`. Keep `grant_skill_practice_xp`,
  `SKILL_PRACTICE_XP_PER_USE`, `skill_proficiency_level`, the race-learning /
  passive-multiplier helpers only if still referenced (delete otherwise), and
  `element_affinity_multiplier` (survives as a pure multiplier).
- [x] 1.2 In `world/rules/rulebook/progression.yaml`, delete the `magic_xp_per_level`,
  `study_base_xp_per_hour`, and `combat_kill_xp` keys; keep whatever practice keys exist.
- [x] 1.3 Grep-audit the repo for `magic_xp`, `accrue_magic_study`,
  `grant_combat_kill_xp`, `effective_growth_multiplier` — zero non-test hits after §3.

## 2. World-clock stage rename + placeholder

- [x] 2.1 In `world/rules/clock.py`, rename the `magic_study` stage entry to
  `practice_settlement` (same tuple position) and replace the self-arming lazy import
  with an inline zero-growth stage function documented as the
  `declared-practice-skip` insertion point; keep the COMBAT-source stage skip.
- [x] 2.2 Drop `("magic_xp", None)` from the advance snapshot registry.

## 3. Snapshot / restore surfaces

- [x] 3.1 `world/rules/action.py`: remove the `magic_xp` snapshot/restore pair from the
  action rollback snapshot; remove the deferred kill-XP staging check so defeat staging
  emits EventLog entries and quest planners only.
- [x] 3.2 `world/rules/cast_settlement.py`: drop `("magic_xp", None)` from
  `_SETTLEMENT_ATTRS`.
- [x] 3.3 `world/rules/upkeep.py`: keep `source_pk` attribution, defeat EventLogs, and
  quest planner effects; delete `grant_combat_kill_xp()` staging entirely.
- [x] 3.4 `world/rules/character_creation.py`: remove `"magic_xp"` from the activation
  attribute list and the `"magic_xp": 0` initial write.

## 4. Skills: effect class + registry rows

- [x] 4.1 `world/skills/effects.py`: delete `ElementMasteryRankEffect` and its
  `element_mastery_rank` parse branch (prefix now fails closed at parse).
- [x] 4.2 `world/skills/registry.py`: switch every `<element>_mastery` row's
  `effects=["element_mastery_rank:主宰"]` to `effects=["passive_trait:element_mastery"]`
  (all eight elements). Do NOT touch `sexual_magic_mastery` or
  `reincarnation_boon_yuna`.

## 5. Cast gate removal (interim: ownership + MP)

- [x] 5.1 `world/rules/progression.py` (with §1): `can_cast_spell_tier`,
  `can_cast_skill`, `_element_effective_magic_level` deleted.
- [x] 5.2 `world/rules/action.py`: delete the elemental tier rejection from
  `preflight`/`resolve` and the spell-tier check from the shared preview + submission
  revalidation + `build_combat_view` descriptors.
- [x] 5.3 `world/rules/combat.py` `default_attack_policy`: propose the first affordable
  resolver-backed damage skill (no tier gating).
- [x] 5.4 `world/rules/element_affinity` docs/docstrings: multiplier survives; delete
  element-effective-level wording.

## 6. Test re-pinning

- [x] 6.1 `world/rules/tests/test_progression.py`: delete engine tests (study XP, kill
  XP, cap, multiplier-folding); keep/repair proficiency + affinity tests; re-pin
  skill-proficiency independence scenarios per the delta (absence assertions).
- [x] 6.2 `test_upkeep_settlement.py`: XP assertions become no-progression-write
  assertions; defeat-entry/quest assertions unchanged.
- [x] 6.3 `test_guild_exams.py`, `test_combat_session_recovery.py`,
  `test_character_creation.py`: drop `db.magic_xp` pins per §1–§4.
- [x] 6.4 Webclient cast fixtures: delete the `traits.magic_power.base = 30` override
  rows in `web/webclient/actions/tests/test_combat_actions.py`,
  `web/webclient/actions/tests/test_combat_dispatcher.py`,
  `commands/tests/test_combat_actions.py` (gate retired; static trait needs no pin).
- [x] 6.5 No new test modules → `.github/evennia-shards.json` untouched.

## Verification

- [x] V1 `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb world.rules world.skills world.imports typeclasses commands web.webclient`
- [x] V2 `uv run --locked python -m tools.spec_traceability check` (0 errors)
- [x] V3 `uv run --locked python -m compileall -q world typeclasses commands server`
- [x] V4 `openspec validate magic-xp-engine-retirement --strict`
- [x] V5 `git diff --check`

## Post-sync traceability (during archive/sync)

- [x] P1 After this change's deltas sync into `openspec/specs/`, run
  `uv run --locked python -m tools.spec_traceability list` and re-pin
  `covers_requirement` IDs whose slugs changed (RENAMED titles in
  `settlement-stage-order` ×2, `monster-action-policy` ×1; all
  `magic-level-progression` IDs retire with the capability removal — delete their
  annotations from tests when the sync lands).
