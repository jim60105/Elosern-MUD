# Proposal: use-driven-skill-lineage

## Why

With the magic-XP engine retired (`magic-xp-engine-retirement`), the game has
exactly one growth currency left — per-skill practice proficiency — but it
still has no mechanical consumer: `skill_proficiency_level()` is read only by
tests, practice accrues only on the spell-cast seam, the conferred
growth-rate buff has no live reader, and the interim cast gate (ownership + MP
alone) lets a fresh character with `fire_mastery` and 30 MP hold `firestorm`
with zero fundamentals. Design
`docs/superpowers/specs/2026-08-30-use-driven-progression-design.md` §8–§10
(D4/D5/D6) specifies the replacement: use-driven accrual for every ACTIVE
skill, a registry-declared prerequisite DAG as the single use gate, tip caps
plus per-tick dedupe as the anti-grinding rules, and the proficiency-anchored
freeform scale ladder.

## What Changes

- BREAKING: `SkillDef` gains `prerequisites: tuple[SkillPrerequisite, ...]`
  (frozen dataclass, `min_proficiency >= 1`); registry load validation fails
  closed on unknown prereq keys, cycles, and invalid thresholds, and caches
  the reverse-edge map that derives tip caps.
- BREAKING: the first-round lineage content ships: the linear fire tree
  (`fire_arrow` → `fire_ball` → `scorching_wave` → `firestorm` → `lava_burst`
  → `dragon_flame` → `phoenix_eternal_flame`, plus edges for
  `infernal_wrap`/`hellfire`/`world_ending_blaze`). The structure is an n-ary
  DAG from day one; branching edges are future content, not future code.
- BREAKING: one shared side-effect-free predicate `can_use_skill(entity,
  skill)` (ownership + all prerequisite edges) becomes THE use gate:
  `ActionResolver` step 1, shared preview, submission revalidation, both
  skill menus, and `default_attack_policy` all consume it. The interim
  ownership+MP-only gate is replaced. Mastery tier overrides are not
  reintroduced — 主宰 access is now just the prerequisite path.
- BREAKING: practice accrual generalizes from the magic-cast seam to every
  successful ACTIVE skill resolution (physical and magical identical):
  `SKILL_PRACTICE_XP_PER_USE × race learning_multiplier × element-affinity
  multiplier × growth_rate_multiplier(entity)` (the conferred buff regains its
  live reader). PASSIVE skills never accrue; `nonlethal` contexts (guild
  exams, simulated battles) accrue nothing.
- BREAKING: per-consumer tip caps: `cap(S)` = max `min_proficiency` over all
  edges consuming S, else `PROFICIENCY_TIP_CAP` (yaml, 10); XP saturation at
  cap. One `(actor, skill_key, target)` accrual per world-clock tick via a
  transient module-level dict (cleared on tick change, never persisted or
  snapshotted).
- The freeform scale ladder re-anchors from mastery key-presence-only to
  mastery key-presence eligibility plus the skill's own proficiency
  (0.25 unconditional, 0.5 ≥1, 1.0 ≥3, 2.0 ≥6, 4.0 ≥10), interacting
  deliberately with derived caps.
- Import auto-seed: an imported or scene-built entity owning a deep skill gets
  its prerequisite proficiencies seeded to exactly the required value (never
  above); explicit imported `skill_proficiency` always wins.
- Capability `skill-proficiency-tracking` is REMOVED; the new `skill-lineage`
  capability absorbs and extends its contract.

## Capabilities

### New Capabilities

- `skill-lineage`: prerequisite DAG on `SkillDef`, fail-closed load
  validation, the shared `can_use_skill` gate, use-driven practice accrual
  with affinity/growth multipliers, tip caps, per-tick dedupe, the
  proficiency-anchored freeform ladder, and import auto-seed.

### Modified Capabilities

- `action-resolution-pipeline`: preview gains the lineage gate; a new
  requirement makes the resolver reject prerequisite-unsatisfied use.
- `monster-action-policy`: the policy consumes `can_use_skill`.
- `buff-handler-integration`: the conferred growth-rate query regains its live
  reader (practice-XP formula).
- `element-affinity`: the multiplier gains its practice-XP consumer anchor.
- `element-mastery`: freeform entitlement gains the proficiency ladder.
- `freeform-casting`: the scaled-cast gate, preview/facade, and `cast`
  command honor the ladder.
- `webclient-combat-menu`: the scale selector reflects the ladder.
- `guild-rank-exams`: exams accrue no practice XP (strengthens the existing
  no-growth guarantee).
- `import-loader` / `scene-builder`: prerequisite auto-seed inside the
  all-or-nothing import transaction and the NPC spawn path.

### Removed Capabilities

- `skill-proficiency-tracking`: folded into `skill-lineage` (its storage and
  level-derivation contract survive verbatim inside the new requirements).

## Impact

- Code: `world/skills/registry.py` (field + validation + fire edges),
  `world/rules/progression.py` (accrual formula, caps, dedupe, ladder,
  `can_use_skill`), `world/rules/action.py`, `world/rules/combat.py`,
  `world/rules/cast_settlement.py`, `world/imports/loader.py`,
  `world/quests/scene_builder.py`, `world/rules/rulebook/progression.yaml`
  (`PROFICIENCY_TIP_CAP`, ladder constants), freeform surfaces in
  `commands/` and `web/webclient/`.
- Specs: `skill-proficiency-tracking` removed; `skill-lineage` added; nine
  requirement edits across seven capabilities.
- Tests: new lineage test modules registered in `.github/evennia-shards.json`;
  existing practice/freeform tests re-pinned to the ladder.
- No backward-compatibility or migration work: the project is unreleased with
  zero users.
