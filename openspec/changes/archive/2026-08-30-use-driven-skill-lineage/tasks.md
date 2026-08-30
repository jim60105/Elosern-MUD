# Tasks: use-driven-skill-lineage

## 1. Registry: prerequisite dataclass + validation + fire edges

- [x] 1.1 `world/skills/registry.py`: add frozen/slotted `SkillPrerequisite(skill_key:
  str, min_proficiency: int)` (validate `>= 1` in `__post_init__`) and
  `SkillDef.prerequisites: tuple[SkillPrerequisite, ...] = ()`.
- [x] 1.2 Load-time validation, fail-closed: all prereq keys exist; acyclic
  topological sort raising with the cycle named; int thresholds >= 1;
  no-prereq = root; build and cache the reverse-edge map (skill -> consuming
  edges) exposed for cap lookup.
- [x] 1.3 Author the fire edges: `fire_ball(fire_arrow,3)`,
  `scorching_wave(fire_ball,3)`, `firestorm(scorching_wave,3)`,
  `lava_burst(firestorm,5)`, `dragon_flame(lava_burst,8)`,
  `phoenix_eternal_flame(dragon_flame,8)`; edges for `infernal_wrap`,
  `hellfire`, `world_ending_blaze`. No mastery passive becomes a node.

## 2. Progression: gate, accrual, caps, dedupe, ladder

- [x] 2.1 `world/rules/progression.py`: add `can_use_skill(entity, skill)`
  (ownership + every edge owned-and-met), pure and side-effect-free.
- [x] 2.2 Rewrite practice accrual: `grant_skill_practice_xp(entity, skill_key,
  target=None, nonlethal=False)` applying
  `SKILL_PRACTICE_XP_PER_USE x learning x affinity x growth_rate_multiplier`,
  skipping PASSIVE and nonlethal. Route storage through one internal primitive
  `award_practice_xp(entity, skill_key, xp)` that clamps at `cap(S)` and is the
  ONLY accrual writer of `skill_proficiency` — `declared-practice-skip`'s hourly
  settlement must call the same primitive (named for it in that change).
- [x] 2.3 `world/rules/rulebook/progression.yaml`: add `PROFICIENCY_TIP_CAP: 10`
  and the freeform ladder rungs (`0.25@0, 0.5@1, 1.0@3, 2.0@6, 4.0@10`); keep
  the playtest-recalibration header note.
- [x] 2.4 Cap derivation `cap(S)` from the cached reverse-edge map, defaulting
  to yaml tip cap for canopy skills.
- [x] 2.5 Per-tick dedupe: transient module-level dict keyed
  `(actor_pk, skill_key, target_pk)`, cleared on world-clock tick change;
  never persisted, never snapshotted.
- [x] 2.6 Re-anchor `freeform_scales_for` / `freeform_scale_entries_for` onto
  the ladder (mastery key-presence entitlement + own-skill proficiency rungs).

## 3. Gate call-site cutover

- [x] 3.1 `world/rules/action.py`: `ActionResolver` step 1 / `preflight` /
  `resolve`, shared preview, submission revalidation, and combat-view
  descriptors consume `can_use_skill` (reason `UNKNOWN_SKILL`, detail names the
  missing prereq + required level from registry data).
- [x] 3.2 `world/rules/combat.py` `default_attack_policy`: skip skills failing
  `can_use_skill`.
- [x] 3.3 Out-of-combat cast settlement (`world/rules/cast_settlement.py`):
  accrue via the §2.5 dedupe path; the existing clock advance keeps consecutive
  casts on distinct ticks.
- [x] 3.4 Menus: Telnet skill/combat menus and the WebClient presenter
  (`freeform_scales` descriptor) reflect the ladder; delete any residual
  tier-band reads (`cost_tiers` is display label only).

## 4. Auto-seed

- [x] 4.1 `world/imports/loader.py` (or its shared helper): seed unsatisfied
  prerequisite proficiency to exactly `min_proficiency * 50`, before schema
  range validation, inside the all-or-nothing transaction; explicit imported
  `skill_proficiency` wins.
- [x] 4.2 `world/quests/scene_builder.py`: NPC spawn path calls the same
  helper.

## 5. Tests + shards + docs

- [x] 5.1 New pure tests `world/rules/tests/test_skill_lineage.py`: graph
  validation (cycle/dangling/root/`min >= 1`), `can_use_skill` matrix, cap
  derivation (canopy default, mid-tree max, branch case), dedupe semantics,
  ladder rungs. Register the module in `.github/evennia-shards.json` (same
  change).
- [x] 5.2 Integration tests: accrual commits/rolls back atomically; exam
  context accrues nothing; full combat proves kill-only usage accrual;
  auto-seed (satisfies, explicit wins, malformed import still all-or-nothing).
- [x] 5.3 Re-pin existing freeform tests (`freeform-casting`, webclient menu
  vitest fixtures) to ladder-derived scale sets.
- [x] 5.4 Player-visible prose: menu entries for gated skills show the
  missing-prereq reason; update `docs/game/commands.md` and
  `docs/game/command-reference.md` if wording changes; keep
  `tests/test_command_docs.py` green.

## Verification

- [x] V1 `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb world.rules world.skills world.imports world.quests commands web.webclient`
- [x] V2 `uv run --locked python -m tools.spec_traceability check` (0 errors)
- [x] V3 `uv run --locked python -m compileall -q world typeclasses commands server`
- [x] V4 `openspec validate use-driven-skill-lineage --strict`
- [x] V5 `git diff --check`

## Post-sync traceability (during archive/sync)

- [x] P1 On sync, `skill-proficiency-tracking` IDs retire (delete their
  annotations); `skill-lineage` IDs are born — obtain them from
  `uv run --locked python -m tools.spec_traceability list` and annotate the
  §5.1/§5.2 assertions that establish them; re-pin slugs for the
  `monster-action-policy` rename.
