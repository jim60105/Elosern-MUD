## Why

`SKILL_REGISTRY` holds 118 skills (117 in `world/skills/registry.py` plus `flee`, injected at import
time by `world/rules/disengage.py`) with no notion of presentational grouping. The combat panel and
the out-of-combat listing both render every owned skill as one flat, unsorted list. That is already
marginal for a high-level caster who owns most of the 79-entry elemental spell catalog, and a planned
follow-on change adds a further ~69 sexual-act skills — which would push the flat list past usable.

This change adds a required `category` classification (plus an optional second-level `group`) to
every skill in the registry, so a later presentation change can group the panel without inventing a
derivation heuristic. No heuristic works: several existing skills carry data that would misclassify
under any inferred rule (see design.md D-2), so classification must be declared, not derived.

## What Changes

- Add `SkillCategory` (a `StrEnum`) to `world/skills/registry.py`, with eight members:
  `elemental_magic`, `martial_arts`, `enhancement`, `innate_gift`, `movement`, `divine_mystery`,
  `utility`, `sexual_act`.
- Add two fields to `SkillDef`: `category: SkillCategory` (required, no default) and
  `group: str | None` (optional second-level key, `None` when the category has no second level).
- `SkillDef.__post_init__` validates `group`: when present, it must be a non-empty string.
- Give `_skill()` and `_spell()` a required `category` parameter and an optional `group` parameter.
- Classify all 117 skills built in `world/skills/registry.py`:
  - `_elemental_spells()` sets `category=SkillCategory.ELEMENTAL_MAGIC` and `group=<element key>`
    for its whole set (covers 75 spells in one edit; verified per-element counts: fire 10, water 10,
    earth 9, wind 8, lightning 8, ice 10, light 10, dark 10).
  - `_body_multiplier()` sets `category=SkillCategory.ENHANCEMENT` for its 3 rows in one edit.
  - The 8 element-mastery passives, 4 individually built elemental extras (`hardened_skin`,
    `gale_step`, `static_ward`, `thunder_gods_haste` — ACTIVE self-buff skills carrying an element
    tag but not built through `_elemental_spells()`), and the remaining ~28 individually built skills
    each take an explicit `category` (and `group` where applicable) argument.
  - `divine_sexual_arts`, `divine_sexual_mastery`, and `reincarnation_boon_yuna` are classified
    `sexual_act` (group `神之秘法` / `精通` / `精通` respectively) rather than their current implicit
    home among the other divine mysteries and innate gifts — a pure presentation move; their
    acquisition paths (`requires_divine_arts`, race/reincarnation) are unchanged.
- Classify `flee`'s `SkillDef` (constructed directly in `world/rules/disengage.py`, outside the
  registry) as `category=SkillCategory.MOVEMENT`. Because `category` has no default, this is a
  required, not optional, edit — `disengage.py` fails to import until it supplies one.
- Add structural tests proving the 118-skill partition is exact: every registry key has a valid
  category, the union of per-category member sets equals `SKILL_REGISTRY.keys()` exactly, every
  `elemental_magic` member's `group` is a key of `ELEMENT_REGISTRY`, every `sexual_act` member has a
  non-null `group`, and every member of the other six categories has `group is None`.

**BREAKING**: `SkillDef` gains a required constructor field. Any code that builds a `SkillDef`
directly (not through `_skill()`/`_spell()`) must be updated in the same change. A repo-wide search
found `flee` in `world/rules/disengage.py` (updated above) plus **thirteen test-only construction
sites across seven test files** — `world/quests/tests/test_action_events.py`,
`world/quests/tests/test_planner.py` (2 sites), `world/rules/tests/test_friendly_fire.py` (2 sites),
`world/rules/tests/test_heal_effect_handler.py`, `world/rules/tests/test_effect_handlers.py`, and
`world/skills/tests/test_registry.py` (6 of its 7 `SkillDef(...)` sites; one existing site already
expects `TypeError` for a different missing-argument reason and needs no change) — each gaining an
explicit `category` argument in the same commit (see tasks.md). Several of these are module-level
constants evaluated at import time, so leaving any unaddressed would break test *collection* for
that file, not just one assertion. This project has no released users and no backward-compatibility
obligation (per repository convention).

## Capabilities

### New Capabilities
- `skill-category-registry`: the `SkillCategory` enum, the `category`/`group` fields and their
  validation on `SkillDef`, and the exact 118-skill classification partition.

### Modified Capabilities
- `universal-action-ownership`: `flee`'s `SkillDef` now declares `category=SkillCategory.MOVEMENT` at
  its construction site in `world/rules/disengage.py`, consistent with that capability's existing
  requirement that `world/skills/` never depend on `world/rules/` (the dependency runs the other
  way, so `flee`'s classification cannot live in the registry itself).

## Impact

- **Code**: `world/skills/registry.py` (new enum, two new `SkillDef` fields, ~30 explicit
  classification call sites, two bulk classifications via existing builders), `world/rules/
  disengage.py` (one explicit classification).
- **Tests**: new structural tests in `world/skills/tests/` proving the classification partition is
  exact and complete; no existing test's *assertions* change (no skill's `kind`, `cost`, `effects`,
  `element`, or `target_spec` changes), but thirteen test-only `SkillDef(...)` construction sites
  (see BREAKING above) each gain a `category` argument so their modules keep importing and their
  intended pass/fail paths keep exercising what they were written to test.
- **Downstream**: this change deliberately does not touch presentation. `world/rules/combat_view.py`,
  `web/webclient/presentation/combat_panel.py`, and `world/rules/status_query.py` read the new fields
  in follow-on changes (`skill-category-combat-panel`, `skill-category-status-listing`), which this
  change unblocks but does not implement.
