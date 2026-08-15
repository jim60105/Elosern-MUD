## 1. combat_view.py: descriptor fields and grouping helper

- [ ] 1.1 Add `category: str` and `group: str | None` to `SkillDescriptorView`, populated in
      `_build_skills()` from the already-guarded local `skill` variable (`skill.category.value`,
      `skill.group` — `_build_skills()` already binds `skill = SKILL_REGISTRY.get(key)` and
      `continue`s when `skill is None` before constructing any descriptor; do not re-index
      `SKILL_REGISTRY[key]` separately).
- [ ] 1.2 Add `SkillGroupView(group: str | None, label: str | None, skills: tuple[SkillDescriptorView, ...])`
      and `CategoryGroupView(category: str, label: str, groups: tuple[SkillGroupView, ...])` frozen
      dataclasses.
- [ ] 1.3 Add a category-key-to-label and element-key-to-label lookup (reuse `ELEMENT_REGISTRY`'s
      existing `Element.label`/display name for element sub-groups; add a small
      `SkillCategory`-to-Traditional-Chinese-label mapping for category headings, e.g.
      `元素魔法`/`武技`/`強化`/`天賦`/`移動`/`神之秘法`/`特殊`/`性愛行為`).
- [ ] 1.4 Implement `group_skill_views(skills: tuple[SkillDescriptorView, ...]) -> tuple[CategoryGroupView, ...]`:
      iterate `SkillCategory` in declaration order; for each category with at least one matching
      skill, build its sub-groups — `elemental_magic` iterates `ELEMENT_REGISTRY` order and one
      sub-group per element with owned skills, `sexual_act` groups by first-seen `group` value among
      the category's owned skills in `owned_keys()` order, every other category emits exactly one
      `group=None` sub-group; omit any category or element sub-group with zero owned skills.
- [ ] 1.5 Export `SkillGroupView`, `CategoryGroupView`, `group_skill_views` from `combat_view.py`'s
      `__all__`.

## 2. WebClient presenter: schema version 3

- [ ] 2.1 Bump `CONTEXT_ACTIONS_SCHEMA_VERSION` to `3` in `web/webclient/presentation/combat_panel.py`.
- [ ] 2.2 Add `_validate_skill_group()` (validates a `{group, label, skills}` object, co-nullability
      of `group`/`label`, reuses the existing `_validate_skill()` per-descriptor validator) and
      `_validate_category_group()` (validates a `{category, label, groups}` object) to
      `combat_panel.py`.
- [ ] 2.3 Update `validate_context_actions()` to validate `skills` as an array of category groups via
      `_validate_category_group()`, and to compute its whole-payload invariants against the
      **flattened** set of all descriptors across every category and sub-group: target-ID
      cross-reference against presented participants, unique skill keys, **and** the total flattened
      skill count not exceeding `MAX_SKILLS` (this last check does not carry over automatically from
      v2 — applying `len(skills) > MAX_SKILLS` to the new top-level array would instead bound the
      *category-group* count, a much weaker check; see design.md D-5). Also assert the top-level
      `skills` array itself has at most `len(SkillCategory)` entries.
- [ ] 2.4 Update `context_actions_presenter()` to call `group_skill_views(view.skills)` and serialize
      the resulting `CategoryGroupView` tuple into the nested JSON shape, preserving every existing
      per-descriptor field (including `freeform_scales` when present) unchanged.
- [ ] 2.5 Update the recovery-session branch's `skills: []` to remain a valid (empty) array under the
      new schema — no category groups for a recovery session, matching the existing "no cast/flee
      action" recovery contract.

## 3. Telnet parity: CmdCombatActions

- [ ] 3.1 Update `commands/combat.py`'s `CmdCombatActions.func()` to call `group_skill_views(view.skills)`
      and render each category label as a heading, each non-null sub-group label as a sub-heading (a
      category with a single `group=None` sub-group renders no sub-heading), and skills within a
      sub-group in the existing per-skill line format (key/label/status/targets), unchanged from
      today's per-skill rendering.

## 4. Production WebClient JS

These three files are the actual browser-side consumers of `context_actions.skills`. Skipping any of
them leaves the WebClient combat panel broken once the server ships schema version 3 — this is not
optional cleanup, it is required for the feature to function in the browser at all.

- [ ] 4.1 Update `web/static/webclient/js/elosern/protocol.js`'s `validateContextActionsPanel()`:
      accept `schema_version === 3`, validate `skills` as an array of category-group objects
      (mirroring `_validate_category_group()`/`_validate_skill_group()`), and re-implement the
      flattened `MAX_SKILLS` total-count check and unique-key check client-side, matching the
      server-side invariants in task 2.3.
- [ ] 4.2 Update `web/static/webclient/js/elosern/combat_menu.js`'s `panelSkills()` to flatten the
      nested `category → groups → skills` structure back into a flat list of skill descriptors (or
      add category/group-aware navigation if the menu should surface headings — confirm against the
      approved keyboard hierarchy spec before choosing), so `skillItems()` continues to receive plain
      skill objects with `.key`/`.label`/`.enabled`/`.disabledReason` as it does today.
- [ ] 4.3 Update `web/static/webclient/js/plugins/combat_dock.js`'s `panelSignature()` to traverse
      the nested structure when building its `skillKeys` change-detection string, producing an
      equivalent flattened signature (same information content: every skill's key, enabled state, and
      targets, in a stable order) so menu-refresh detection is unaffected by the schema change.

## 5. Telnet parity: CmdCombatActions

- [ ] 5.1 Update `commands/combat.py`'s `CmdCombatActions.func()` to call `group_skill_views(view.skills)`
      and render each category label as a heading, each non-null sub-group label as a sub-heading (a
      category with a single `group=None` sub-group renders no sub-heading), and skills within a
      sub-group in the existing per-skill line format (key/label/status/targets), unchanged from
      today's per-skill rendering.

## 6. Tests

- [ ] 6.1 Add tests to `world/rules/tests/test_combat_view.py` for `group_skill_views()`: category
      order follows `SkillCategory` declaration order independent of ownership order; `elemental_magic`
      sub-group order follows `ELEMENT_REGISTRY` order; a category with zero owned skills is omitted;
      a category whose members carry no `group` produces exactly one `group=None` sub-group; ordering
      within a sub-group matches `owned_keys()` order.
- [ ] 6.2 Add a test asserting `validate_context_actions()` rejects a hand-constructed nested payload
      whose flattened skill count exceeds `MAX_SKILLS` even though its category-group count is well
      under `len(SkillCategory)` — the check task 2.3/design.md D-5 exists specifically to catch.
- [ ] 6.3 Add/update Node tests in `web/static/webclient/js/tests/combat_menu.test.js` and
      `protocol.test.js` for the v3 nested payload shape, including the omitted-empty-category case,
      the single-null-group case, and the flattened `MAX_SKILLS` rejection from task 4.1.
- [ ] 6.4 Update `web/tests/browser/test_browser_combat.py` (and
      `test_browser_combat_rejection.py` if it asserts on `skills` shape) for the grouped panel.
      Prefer extending existing test classes over adding new server-boot cases, given the ~35–70s
      per-test cost of booting a fresh Evennia server for combat browser tests.
- [ ] 6.5 Add a Telnet parity test asserting `combat actions` output contains category headings in
      the documented order and, for an entity owning skills spanning two elements, both element
      sub-headings in `ELEMENT_REGISTRY` order.

## 7. Verification

- [ ] 7.1 Run `uv run --locked python -m compileall -q world typeclasses commands server`.
- [ ] 7.2 Run `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py world.rules.tests.test_combat_view commands`.
- [ ] 7.3 Run `node --test web/static/webclient/js/tests/combat_menu.test.js web/static/webclient/js/tests/protocol.test.js`.
- [ ] 7.4 Run the updated browser test file(s) from task 6.4 (prefer running just those files/classes
      over the full browser suite during iteration).
- [ ] 7.5 Run `openspec validate skill-category-combat-panel --strict`.
