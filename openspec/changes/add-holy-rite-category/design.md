# Design: add-holy-rite-category

## Context

`SkillCategory` is a frozen-order `StrEnum` (declaration order = display order; the
`skill-category-registry` main spec pins the exact member list, the exact partition, and the
closed per-category group vocabulary). The church block's 15 ACTIVE rows currently sit inside
`enhancement` (11) and `sexual_act` (4 placeholder rows), and two webclient panels plus a JS
protocol mirror enumerate the six-member set. The parent design
(`docs/superpowers/specs/2026-09-23-holy-rite-cast-rail-design.md` §3) approves the fourth
family `holy_rite` (神聖聖儀); its cast mechanics ship separately in
`implement-holy-rite-cast-rail`. This change is the taxonomy move only.

## Goals / Non-Goals

**Goals:**
- Append `HOLY_RITE = "holy_rite"` to `SkillCategory` and re-file the 15 church-block ACTIVE rows.
- Keep every moved row's other fields byte-identical (kind, cost, effects, element, target_spec,
  group) — including `rite_morning_devotion` staying ACTIVE.
- Move the closed presentation mirrors in lockstep: server category-label maps, the JS
  `SKILL_CATEGORY_KEYS` mirror, the character-panel group bound, panel label tests.

**Non-Goals:**
- No effects, no handlers, no parser prefixes (change 2's work).
- No UI feature work: the fourth menu is a later browser change; only existing closed-set
  constants grow so current panels keep validating.
- No Series C passive moves and no `rite_morning_devotion` kind change (both belong to change 2's
  honest re-judgement).

## Decisions

**D1 — Enum appended last.** `HOLY_RITE` is declared after `SEXUAL_ACT`. The frozen-order rule
makes any earlier position a display-order break for every existing category; last is the only
legal slot. Panels already omit empty categories, so players who never redeem see nothing new.

**D2 — The 15-row move is `category=` only.** The 11 `ENHANCEMENT` rows and the 4 `SEXUAL_ACT`
placeholder rows swap their category argument and nothing else. The Series D rows keep
`group="聖禮"`, which the re-pinned closed vocabulary `{None, "聖禮"}` now admits for `HOLY_RITE`
(same sub-group rule the combat/exploration panels already run for `enhancement`'s tags).
Alternative considered: drop the group to `None` — rejected, it would silently erase the
presentation metadata these rows were authored with and change offering-menu grouping semantics.

**D3 — Passives stay home.** The family names *invoked church acts*; Series C discipline
passives remain `ENHANCEMENT`. Changing kind or membership of anything outside the 15 rows is
change 2's scope.

**D4 — Mirror constants, not UI.** `CATEGORY_LABELS` in `world/rules/combat_view.py` and
`status_query.py` gain `SkillCategory.HOLY_RITE: "神聖聖儀"`;
`web/static/webclient/js/elosern/protocol/constants.js` `SKILL_CATEGORY_KEYS` gains
`"holy_rite"` (the combat validator's category-count bound follows from the array length);
`panels/character.js` `CHARACTER_MAX_CATEGORY_GROUPS` 7 → 8 mirrors Python's
`len(SkillCategory) + 1`. `SkillBook.vue`'s category-dot colors need no edit — the unknown
category simply falls through to the neutral default, and the fourth menu's styling is the UI
change's decision.

**D5 — Series D placeholder rows leave the registry-agreement exclusion list.** They are not in
`SEXUAL_ACT_REGISTRY`; once re-classified they fall out of the comparison set entirely, so
`world/skills/tests/test_skill_registry/_support.py` (or its sibling) loses exactly the four
named keys — the exclusion list shrinks, never grows.

## Risks / Trade-offs

- Panel/contract tests pin the six-member enumeration; each named anchor must move in this
  change or CI's classification/presentation tests fail on the next branch. Mitigation: the
  task list enumerates the anchor files, and `tools.spec_traceability check` runs while editing.
- The 4 Series D rows are now `HOLY_RITE` but their act-rail future content may later want
  sexual-act grouping again; the re-pin is data-driven (group vocabulary), so a future move is a
  row edit plus delta, not machinery.
- `rite_morning_devotion` stays ACTIVE in the menu this change (an honest "nothing happens when
  cast" until change 2's re-judgement); acceptable because the parent design sequences the two
  changes back-to-back, and this change alone must not change behavior.
