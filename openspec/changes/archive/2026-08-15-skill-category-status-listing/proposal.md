## Why

The out-of-combat `character` panel's `passives` field is sourced from `world/rules/status_query.py`'s
`_read_passive_keys()`, which reads the raw `entity.db.skills["passive"]` attribute directly instead
of `SkillHandler.owned_keys()`. Because `INNATE_SKILL_KEYS` (`flee`, `basic_attack`) are contributed
by `owned_keys()` and are never written into `entity.db.skills`, **both innate skills are invisible
in the out-of-combat character panel today**, despite appearing correctly in the combat panel. Both
are also ACTIVE, not passive, skills — so even fixing the data source cannot surface them under the
existing schema, which has no field for active skills at all. The panel needs a genuine new surface,
not just a corrected read.

Separately, once `skill-category-registry` lands, every skill carries a `category`/`group` the same
way the combat panel now groups by (`skill-category-combat-panel`). Leaving the out-of-combat panel
as an ungrouped, passive-only list would be the one remaining place in the game where the taxonomy
does nothing.

## What Changes

- Add `active_keys: tuple[str, ...]` to `CharacterReadModel` in `world/rules/status_query.py`,
  sourced from `actor.skills.owned_keys()` filtered to `SkillDef.kind is SkillKind.ACTIVE`.
- Change `passive_keys`'s source from raw `entity.db.skills["passive"]`
  (`_read_passive_keys()`) to `actor.skills.owned_keys()` filtered to `SkillKind.PASSIVE` — a
  **behavior fix**, not just a rename: `owned_keys()` is the single source of truth for what an
  entity owns (imported skills plus innate grants), and reading it directly instead of the raw
  attribute is what the shipped `universal-action-ownership` capability already expects every
  consumer to do.
- Bump the `character` panel's `CHARACTER_SCHEMA_VERSION` from `2` to `3` in
  `web/webclient/presentation/character.py`. `passives` changes from a flat bounded list of
  `{key, label}` rows to the same category-grouped structure `skill-category-combat-panel` introduced
  for the combat panel (`{category, label, groups: [{group, label, skills: [{key, label}, ...]}]}`).
  A new `actives` field is added with the identical grouped structure, carrying the same
  `{key, label}` row shape as `passives` (out of combat, cost/target/enabled data is not needed —
  this panel is a read-only summary, not an action dock; casting still goes through the `cast`
  command, unaffected by this change).
- Add a small, self-contained `group_skill_keys()` helper in `world/rules/status_query.py`, applying
  the same canonical ordering rules `skill-category-combat-panel` establishes for the combat panel
  (`SkillCategory` declaration order; `ELEMENT_REGISTRY` declaration order within `elemental_magic`;
  first-seen order within `sexual_act`) to the simpler `{key, label}` row shape this panel needs. This
  is a deliberate, bounded duplication of the *ordering rule* rather than a reuse of
  `combat_view.py`'s `group_skill_views()`: that helper is coupled to the full `SkillDescriptorView`
  shape (cost, target spec, enabled state — irrelevant to a read-only out-of-combat summary), and
  keeping this proposal's only dependency on `skill-category-registry` (not on
  `skill-category-combat-panel`) preserves the two panel proposals as independently implementable and
  reviewable, matching the parallel-batch plan in the shared implementation-sequence document. Both
  helpers read the same canonical constants (`SkillCategory`, `ELEMENT_REGISTRY`), so they cannot
  disagree on *order*, only potentially on shape — which they are supposed to have different shapes
  of by design.
- Update the client-side parity validator (`web/static/webclient/js/elosern/protocol.js`) and its
  dual-direction parity test for the new nested shape and the new `actives` field.
- Update `web/static/webclient/js/elosern/character_menu.js`'s `buildMenu()`, which currently reads
  `panel.passives` as a flat array of `{label}` rows (`passives.forEach(row => row.label)`) to build
  the "被動技能" menu section — it has no equivalent handling for `actives` today, and would read
  `undefined` off each category-group object once `passives` nests, breaking that menu section
  outright. This is updated to flatten (or render category/group-aware) both `actives` and `passives`
  into their own menu sections.

**BREAKING**: `character` schema version 2 clients cannot parse a version-3 payload. This project has
no released users; no compatibility shim is added.

## Capabilities

### Modified Capabilities
- `webclient-exploration-menu`: the "The character panel is an exact read-only version-2 panel"
  requirement changes to version 3, `passives`'s field shape becomes category-grouped, and a new
  `actives` field is added with the same grouped shape — sourced from `owned_keys()` for the first
  time, which is what makes `flee` and `basic_attack` visible out of combat.

## Impact

- **Code**: `world/rules/status_query.py` (`_read_passive_keys()` → `owned_keys()`-based read, new
  `active_keys` field on `CharacterReadModel`), `web/webclient/presentation/character.py` (schema
  bump, grouped serialization and validation for both `passives` and `actives`),
  `web/static/webclient/js/elosern/protocol.js` (parity validator),
  `web/static/webclient/js/elosern/character_menu.js` (menu section construction for both `actives`
  and `passives`) — the full set of production JS consumers of the character panel's skill fields.
- **Tests**: `world/rules/tests/test_status_query.py` (or equivalent) gains a regression test
  asserting `flee` and `basic_attack` are now present in `active_keys` for a freshly created
  character — pinning the bug fixed here so it cannot regress; Node tests in
  `web/static/webclient/js/tests/character_menu.test.js` and `protocol.test.js` for the v3 payload
  shape.
- **Downstream**: depends only on `skill-category-registry` (supplies `SkillCategory`,
  `category`/`group`). Independent of `skill-category-combat-panel` — the two panels are separate
  presentation surfaces with separate schemas, each with its own grouping helper reading the same
  canonical ordering constants, and can be implemented and reviewed in parallel once
  `skill-category-registry` has landed.
