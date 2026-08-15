## Why

`skill-category-registry` gives every skill a required `category` and optional `group`, but nothing
reads those fields yet. The combat panel (`context_actions` schema version 2) still lists every owned
active skill as one flat, unsorted array. A high-level caster who owns most of the 79-entry elemental
spell catalog already has an unwieldy list; a forthcoming sexual-act catalog change adds ~69 more
skills, which would make the flat list unusable. This change makes the combat panel — WebClient and
Telnet alike — render the categorized, grouped structure the registry now provides.

## What Changes

- Add `SkillDescriptorView.category: str` and `.group: str | None` in `world/rules/combat_view.py`,
  read from `SKILL_REGISTRY[key].category.value` / `.group` at descriptor construction, alongside the
  existing fields.
- Add one shared grouping helper in `world/rules/combat_view.py`,
  `group_skill_views(skills: tuple[SkillDescriptorView, ...]) -> tuple[CategoryGroupView, ...]`,
  consumed by both the WebClient presenter and the Telnet command so there is exactly one
  implementation of the grouping and ordering rule. It:
  - Groups the already-`owned_keys()`-ordered flat skill tuple by `category`, preserving
    `owned_keys()` order **within** each group (no alphabetical reordering, inherited from the
    existing flat-list requirement).
  - Orders categories by `SkillCategory`'s enum declaration order, regardless of ownership order.
  - Within `elemental_magic`, further groups by `group` (the element key) in `ELEMENT_REGISTRY`
    declaration order; within `sexual_act`, groups by `group` (the line name) in first-seen order
    among the entity's owned skills (there is no project-wide canonical line ordering yet — this
    change does not introduce one, since no `sexual_act` skill exists in the shipped registry beyond
    the three already present, and defining catalog-wide line order is out of scope here).
  - Omits any category with zero owned skills, and omits the `group` wrapper entirely (using a single
    ungrouped list) for the six categories that never carry a `group`.
- Bump `CONTEXT_ACTIONS_SCHEMA_VERSION` from `2` to `3` in
  `web/webclient/presentation/combat_panel.py`. The `skills` field changes shape from a flat array of
  skill descriptors to an ordered array of category groups, each optionally containing element/line
  sub-groups; the individual skill descriptor object is byte-identical to schema version 2.
- Update `validate_context_actions()` and `context_actions_presenter()` in
  `web/webclient/presentation/combat_panel.py` for the new nested shape, preserving every existing
  validation (participant target-ID cross-reference, unique skill keys across the whole payload,
  session/participant/action-key validation) unchanged.
- Update `commands/combat.py`'s `CmdCombatActions` to render category (and, where present, group)
  headings in Telnet output, using the same `group_skill_views()` helper and the same ordering rule —
  full parity with the WebClient panel.
- Update the production WebClient JS that parses and renders this payload, all three of which
  currently assume `payload.skills` is a flat array of skill descriptors and would break outright on
  a nested v3 payload:
  - `web/static/webclient/js/elosern/protocol.js`'s `validateContextActionsPanel()` — currently
    hard-codes `schema_version !== 2` and iterates `skills.forEach(validateSkill)` over a flat array;
    becomes the client-side mirror of `_validate_category_group()`/`_validate_skill_group()`.
  - `web/static/webclient/js/elosern/combat_menu.js`'s `panelSkills()`/`skillItems()` — currently
    returns `panel.skills` as-is and reads `.key`/`.label`/`.enabled` directly off each array entry;
    must flatten the nested structure (or add category/group navigation) before building menu items.
  - `web/static/webclient/js/plugins/combat_dock.js`'s `panelSignature()` — currently maps
    `panel.skills` to `skill.key`/`.enabled`/`.targets` directly to build a change-detection string;
    must traverse the nested structure to build an equivalent flattened signature.
- Update Node tests (`web/static/webclient/js/tests/`, including `protocol.test.js`) and the browser
  acceptance suite for the new payload shape.

**BREAKING**: `context_actions` schema version 2 clients cannot parse a version-3 payload (the
`skills` field's shape changes from array-of-descriptors to array-of-groups). This project has no
released users; there is no compatibility shim and none is added.

## Capabilities

### Modified Capabilities
- `webclient-combat-menu`: `context_actions` schema version bumps to 3; the "Combat presentation
  enumerates complete deterministic choices" requirement's ordering rule is restated for the nested
  shape (still `owned_keys()` order, now scoped within each group rather than across the whole flat
  list); no other requirement in this capability changes, since freeform-casting and scale-choice
  requirements reference individual skill descriptors generically and do not assume a flat top-level
  array.

## Impact

- **Code**: `world/rules/combat_view.py` (two new `SkillDescriptorView` fields, one new grouping
  helper and its `CategoryGroupView`/`SkillGroupView` dataclasses), `web/webclient/presentation/
  combat_panel.py` (schema bump, nested validation and serialization), `commands/combat.py`
  (`CmdCombatActions` grouped rendering), `web/static/webclient/js/elosern/protocol.js`
  (client-side parity validator), `web/static/webclient/js/elosern/combat_menu.js` (menu-item
  construction), `web/static/webclient/js/plugins/combat_dock.js` (change-detection signature) — the
  full set of production JS consumers of `context_actions.skills`, none of which can be skipped
  without breaking the WebClient combat panel outright on the v3 rollout.
- **Tests**: Node payload-shape tests, browser acceptance for the grouped panel (the most
  runtime-expensive part of this change — each combat browser test boots its own Evennia server,
  ~35–70s each), Telnet parity assertions on heading order and membership, a Python test for
  `group_skill_views()`'s ordering and omission rules.
- **Downstream**: this change depends on `skill-category-registry` (must land first — it supplies
  `SkillCategory` and the `category`/`group` fields this change reads). It does not depend on and is
  not depended on by `skill-category-status-listing` (out-of-combat listing), which reads the same
  registry fields through an entirely separate presentation surface.
