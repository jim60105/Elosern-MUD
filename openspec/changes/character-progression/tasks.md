## 1. Package layout and constants

- [ ] 1.1 Confirm `world/rules/` exists with changes 3/6/11's modules (`traits.py`, `buffs.py`,
      `combat_modifiers.py`, `clock.py`, `skip_safety.py`) importable; create
      `world/rules/progression.py` as an empty module with a docstring referencing design doc §3.2
      and this change.
- [ ] 1.2 Create `world/rules/rulebook/progression.yaml` with `magic_xp_per_level: 600`,
      `study_base_xp_per_hour: 1.0`, `combat_kill_xp: {low: 20, mid: 60, high: 150, calamity: 500}`,
      `skill_proficiency_xp_per_level: 50`, `skill_practice_xp_per_use: 1.0` — per design.md D-4/D-5/
      D-6/D-7. Every constant's docstring/comment states it is an invented placeholder flagged for a
      future balance pass, per this project's established discipline.
- [ ] 1.3 Confirm the exact `CounterTrait` attribute names (`.value`, `.max`) against the installed
      Evennia 6.1.0 `evennia.contrib.rpg.traits` package before wiring `_apply_level_ups()` (design.md
      Open Questions) — no code in this change should assume an unverified attribute name before this
      step.

## 2. Magic-level growth multiplier (`effective_magic_growth_multiplier`)

- [ ] 2.1 Implement `_self_magic_growth_multiplier(entity) -> float` per design.md D-3: scans
      `entity.skills.owned_keys()` against `world.skills.registry.SKILL_REGISTRY`, folding in every
      owned skill's `magic_growth_multiplier:<N>` effect entry multiplicatively; returns `1.0` if none
      match.
- [ ] 2.2 Implement `effective_magic_growth_multiplier(entity) -> float` per design.md D-3: multiplies
      `RaceProfile.learning_multiplier` (via `world.lore.races.RACE_REGISTRY`, `1.0` if the entity has
      no `race` attribute or an unset one), `_self_magic_growth_multiplier(entity)`, and change 6's
      `world.rules.buffs.growth_rate_multiplier(entity)`. Pure query — no attribute writes.
- [ ] 2.3 Write the golden-value test proving hard requirement 1: construct a human entity, call
      `world.rules.buffs.grant_conferred_growth_rate(entity, source_key="elosia", scale=0.5)`, assert
      `effective_magic_growth_multiplier(entity) == 0.5`.
- [ ] 2.4 Write a test constructing an entity with `race="elf"`, an owned synthetic `PASSIVE` skill
      fixture carrying `effects=["magic_growth_multiplier:100"]`, and an active `conferred_growth_rate`
      buff at `scale=0.5`; assert `effective_magic_growth_multiplier(entity) == 500.0` (multiplicative
      combination of all three sources, per design.md D-3's requirement).
- [ ] 2.5 Write a test asserting `effective_magic_growth_multiplier(entity) == 1.0` for an entity with
      no race, no owned `magic_growth_multiplier:` skill, and no active buff.

## 3. Magic XP accrual and level-up (`accrue_magic_study`, `grant_combat_kill_xp`, `_apply_level_ups`)

- [ ] 3.1 Implement `_apply_level_ups(entity) -> None` per design.md D-4: closed-form floor-division
      of `entity.db.magic_xp` by `MAGIC_XP_PER_LEVEL`, `min()`-clamped against
      `entity.traits.magic_level.max`, discarding surplus XP once the cap is reached. No while-loop
      bounded by XP magnitude.
- [ ] 3.2 Implement `accrue_magic_study(entities, seconds, source) -> None` per design.md D-2: no-ops
      entirely unless `source is AdvanceSource.SKIP` (imported from `world.rules.clock`); otherwise
      grants `(seconds / 3600) * STUDY_BASE_XP_PER_HOUR * effective_magic_growth_multiplier(entity)` to
      each entity's `entity.db.magic_xp`, then calls `_apply_level_ups(entity)`. Closed-form — no
      per-second or per-quantum iteration.
- [ ] 3.3 Implement `grant_combat_kill_xp(entity, monster_tier_key) -> None` per design.md D-7: looks
      up `COMBAT_KILL_XP_TABLE[monster_tier_key]` (raises on an unknown key), multiplies by
      `effective_magic_growth_multiplier(entity)`, adds to `entity.db.magic_xp`, calls
      `_apply_level_ups(entity)`.
- [ ] 3.4 Write tests for `accrue_magic_study`: a `SKIP`-sourced call grants the documented XP amount;
      a `COMMAND`-sourced call and a `COMBAT`-sourced call both grant nothing; an 8-hour (`28800`
      second) `SKIP` call produces the same result as computed by a single closed-form multiplication
      (no iteration-count assertion needed, since there is no loop to count).
- [ ] 3.5 Write tests for `grant_combat_kill_xp`: a known tier grants the scaled XP amount; an unknown
      tier key raises and leaves `entity.db.magic_xp` unchanged; `COMBAT_KILL_XP_TABLE`'s four values
      are strictly increasing in severity order (`low < mid < high < calamity`).
- [ ] 3.6 Write the cap-enforcement tests per design.md D-4/hard requirement 2: an elf entity given an
      enormous `entity.db.magic_xp` surplus ends at `entity.traits.magic_level.value == 900` exactly
      (never higher) with `entity.db.magic_xp == 0.0`; an entity already at its cap gains no further
      level and has its XP accumulator reset to `0.0` on the next grant; a `Monster` entity (`max ==
      0`) never leaves level `0` regardless of XP granted.

## 4. Calibration regression tests (design.md D-5)

- [ ] 4.1 Write `test_progression_calibration.py::test_violet_anchor_reproduces_20_levels_in_8_years`:
      given the documented assumption (~4 study-hours/day over 8 years = 11,680 hours) at
      `effective_magic_growth_multiplier == 1.0`, asserts the resulting level gain via
      `MAGIC_XP_PER_LEVEL` is `19` or `20` (rounds to the documented anchor within one level).
- [ ] 4.2 Write a secondary confirmation test for the "ordinary human 30-50" band: given ~2
      study-hours/day over 40 years (29,200 hours) at multiplier `1.0`, asserts the resulting level
      falls within `[30, 50]`.
- [ ] 4.3 Write `test_elosia_anchor_stays_under_elf_cap_with_casual_effort`: given a combined multiplier
      of `1000.0` (elf `learning_multiplier=10.0` times a `magic_growth_multiplier:100` self-multiplier
      fixture) and ~262 study-hours (a "casual," sub-9-month-equivalent input), asserts the resulting
      level is at or near `873` and strictly under the elf `magic_cap` of `900`.
- [ ] 4.4 Write a docstring-level (or comment-level) test/assertion documenting that no numeric
      divine-arts (神之秘法) trait exists anywhere in the entity model, so the 30-fold
      casual-vs-dedicated anchor for divine arts is explicitly out of this test suite's scope — a
      plain assertion that `world/rules/progression.py` defines no divine-arts-related trait or
      constant, mirroring this project's established "prove the boundary, not just document it"
      tripwire style.

## 5. Skill proficiency tracking

- [ ] 5.1 Implement `grant_skill_practice_xp(entity, skill_key, uses=1) -> None` per design.md D-6:
      adds `uses * SKILL_PRACTICE_XP_PER_USE * RaceProfile.learning_multiplier` (or `* 1.0` for an
      entity with no race) to `entity.db.skill_proficiency[skill_key]` (a new, additive
      `dict[str, float]` attribute, defaulting to `{}`). Does NOT read `growth_rate_multiplier()`.
- [ ] 5.2 Implement `skill_proficiency_level(entity, skill_key) -> int` per design.md D-6: pure
      `floor(xp / SKILL_PROFICIENCY_XP_PER_LEVEL)` query, `0` for an unpracticed skill, no upper bound.
- [ ] 5.3 Write tests: an elf's single-use practice gain equals `SKILL_PRACTICE_XP_PER_USE * 10.0`; a
      `conferred_growth_rate` buff's multiplier is NOT applied to a practice-XP grant (asserted against
      an entity with an active buff, confirming the gain matches the race-only formula); multiple
      `uses` accumulate linearly; `skill_proficiency_level()` returns `0` for an unpracticed key,
      returns the correct whole level for an exact multiple-plus-remainder XP value, and never writes
      to `entity.db.skill_proficiency`.
- [ ] 5.4 Write the structural-separation tests per the `skill-proficiency-tracking` capability:
      granting skill practice XP leaves `entity.traits.magic_level`/`entity.db.magic_xp` unchanged;
      granting magic study or combat-kill XP leaves `entity.db.skill_proficiency` unchanged.

## 6. Verification

- [ ] 6.1 Run the full `world/rules/tests/test_progression*.py` suite and confirm every test passes.
- [ ] 6.2 Confirm no function in `world/rules/progression.py` imports or references
      `world.rules.clock.WorldClock`, a settlement-stage registry, or any scheduler — this change
      builds `accrue_magic_study()` as a plain, standalone callable per design.md D-2/Non-Goals,
      exactly mirroring change 6's `tick_buffs()` treatment before change 11 existed to call it. A
      grep-based tripwire test, matching this project's established style (change 3's D-9, change 6's
      D-4's own equivalent check).
- [ ] 6.3 Confirm `grant_skill_practice_xp()`'s source contains no reference to
      `growth_rate_multiplier` (design.md D-6's explicit exclusion) — a grep-based assertion.
- [ ] 6.4 Confirm `world/rules/progression.py` defines no new `tick_interval`/`interval_seconds`-style
      constant that would participate in change 11's `SETTLEMENT_QUANTUM_SECONDS` GCD derivation
      (design.md D-2) — a grep-based assertion that no such constant is exported from this module.
- [ ] 6.5 Confirm this change makes no edit to any file under `openspec/changes/skills-equipment/`,
      `openspec/changes/buffs-rulebook/`, `openspec/changes/world-clock/`, or
      `openspec/changes/entity-traits/` — a `git diff --stat` check against those four directories,
      matching this project's "no edits to another change's artifacts" constraint.
- [ ] 6.6 Run `openspec validate character-progression --strict` and confirm it passes.
