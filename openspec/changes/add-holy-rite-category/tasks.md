## 1. Taxonomy move

- [ ] 1.1 Append `HOLY_RITE = "holy_rite"` as the last member of `SkillCategory` in
      `world/skills/registry/vocab.py` (no existing member moves).
- [ ] 1.2 Swap `category=SkillCategory.ENHANCEMENT` → `CHURCH_RITE` on the 11 church rows and
      `category=SkillCategory.SEXUAL_ACT` → `CHURCH_RITE` on the 4 Series D rows in
      `world/skills/registry/data_church.py` — nothing else in any row; Series C passives and
      every non-church row untouched.
- [ ] 1.3 Update `CATEGORY_LABELS` / `_CATEGORY_LABELS` in `world/rules/combat_view.py` and
      `world/rules/status_query.py` with `SkillCategory.HOLY_RITE: "神聖聖儀"`, and verify the
      shared grouping functions emit the fixed `null`-then-`"聖禮"` sub-group order for
      `HOLY_RITE` the same way `enhancement` orders its tags.

## 2. Mirror constants

- [ ] 2.1 Add `"holy_rite"` to `SKILL_CATEGORY_KEYS` in
      `web/static/webclient/js/elosern/protocol/constants.js` and bump
      `CHARACTER_MAX_CATEGORY_GROUPS` 7 → 8 in `panels/character.js`; run the dependency-free
      Node gate `node --test web/static/webclient/js/tests/*.test.js` (the bound tests read the
      constants dynamically).

## 3. Contract tests follow

- [ ] 3.1 Update `world/skills/tests/test_skill_registry/` classification anchors: the exact
      member-set scenario (seven, order), the partition pin, the group-vocabulary pin
      (`HOLY_RITE ⊆ {None, "聖禮"}` with the four Series D keys named), and the no-other-field pin
      (the 15 rows keep kind/cost/effects/element/target_spec).
- [ ] 3.2 Shrink the registry-agreement exclusion list in the `_support.py` sibling by the four
      Series D keys (they leave the `SEXUAL_ACT` comparison set by category).
- [ ] 3.3 Add the combat-panel scenario (owned `rite_lamb_mark` + `rite_martyrdom_vow` →
      `holy_rite`/神聖聖儀 group, last, single null sub-group) and the character-panel scenario
      (null-then-聖禮 ordering, `poverty_vow` stays under `enhancement` passives) to the panel
      tests; keep `pnpm test`'s touched fixtures honest (no UI feature work).
- [ ] 3.4 Run `uv run --locked python -m tools.spec_traceability check` and the focused Evennia
      labels for `world.skills`, `world.rules` combat-view/status tests, `--keepdb`.

## 4. Docs sweep

- [ ] 4.1 Update any `docs/lore/skill-trees/*` or `docs/game/*` wording that names the church
      rites' presentation family (no command surface changes — the docs trio itself is untouched).
- [ ] 4.2 `git diff --check` clean; every changed requirement's anchor test green.
