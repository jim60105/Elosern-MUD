## Context

Full rationale lives in `docs/superpowers/specs/2026-08-15-skill-category-system-design.md` §5.3;
this document covers only the implementation-level decisions needed to build this specific change.

`world/rules/status_query.py`'s `build_character_read_model()` builds a frozen `CharacterReadModel`
strictly from canonical state, consumed by `web/webclient/presentation/character.py`'s
`character_presenter()` to serialize the `character` panel (schema version 2, governed by the
`webclient-exploration-menu` capability's "The character panel is an exact read-only version-2
panel" requirement). Today `CharacterReadModel.passive_keys` is populated by `_read_passive_keys()`,
which reads `entity.db.skills["passive"]` directly — the raw imported-skill storage, not
`SkillHandler.owned_keys()`. This change depends on `skill-category-registry` having already landed
`SkillCategory` and `SkillDef.category`/`.group`.

## Goals / Non-Goals

**Goals:**
- `flee` and `basic_attack` become visible in the out-of-combat character panel for the first time —
  the bug this change exists to fix.
- Both active and passive owned skills are presented, grouped identically to the combat panel's
  category/group taxonomy.
- The fix is a genuine behavior change (reading `owned_keys()`), not merely a presentation reshuffle
  of the same wrong data.

**Non-Goals:**
- No cast/target/enabled/cost data in this panel. It is a read-only summary; casting remains the
  `cast` command's and the combat panel's concern.
- No sharing of `combat_view.py`'s `group_skill_views()` implementation — see Decision D-1.
- No change to which skills an entity owns. This change only changes what is *read* to build the
  presentation, never `SkillHandler.owned_keys()`'s own logic.
- No category/group heading rendering in the WebClient menu (task 3.3 flattens the nested payload
  back into one unheaded list per section, matching `skill-category-combat-panel`'s identical D-7
  choice). The wire payload carries the full taxonomy; visible heading rendering is deliberately
  deferred, so the player-facing change this proposal ships is the bug fix (innate actives becoming
  visible) — the taxonomy itself becomes visually apparent once a future change adds heading
  rendering to either or both menus.

## Decisions

**D-1: A separate, self-contained grouping helper, not a reuse of `combat_view.py`'s
`group_skill_views()`.** Alternatives considered: importing and reusing the combat panel's helper
directly. Rejected for two reasons. First, a type mismatch: `group_skill_views()` operates on
`tuple[SkillDescriptorView, ...]`, a shape carrying cost/target-spec/enabled/disabled-reason fields
this read-only summary panel has no use for and does not read (`CharacterReadModel` never builds a
`SkillDescriptorView`, since it never resolves targets or resource costs). Second, and more
important for sequencing: `skill-category-combat-panel` and this change were planned as independently
implementable, independently reviewable proposals, both depending only on `skill-category-registry`.
Importing `group_skill_views()` here would make this change depend on that one, collapsing two
parallel-batch proposals into a sequential pair for no functional gain — the *ordering rule* (not the
implementation) is what must stay identical between the two panels, and both proposals get that by
reading the same canonical constants (`SkillCategory`'s enum declaration order,
`ELEMENT_REGISTRY`'s dict declaration order), not by sharing code.

**D-2: `group_skill_keys(keys: Sequence[str]) -> tuple[CharacterCategoryGroupView, ...]` lives in
`world/rules/status_query.py`, taking plain skill keys (not descriptors) and looking up each key's
category/group/label via `SKILL_REGISTRY.get(key)`, never a direct index (see D-3 for why).** A key
absent from the registry is grouped into one synthetic fallback bucket —
`CharacterCategoryGroupView(category="unknown", label="未知技能", groups=(CharacterSkillGroupView(
group=None, label=None, skills=(<one row per unregistered key, key==label>,)),))` — appended *after*
every real `SkillCategory`-ordered group, not interleaved with them, since it has no position in that
enum's declaration order. `"unknown"` is a plain string sentinel, not a `SkillCategory` member — it
never enters that enum, keeping `SkillCategory` an exhaustive taxonomy of real registry content, with
the presentation-only fallback bucket handled entirely inside `group_skill_keys()`. A category-key
label mapping (`元素魔法`/`武技`/`強化`/`天賦`/`移動`/`神之秘法`/`特殊`/`性愛行為`, plus this fallback
bucket's `未知技能`) is built directly in `status_query.py`, independent of the identical mapping
`skill-category-combat-panel`'s `combat_view.py` task 1.3 builds — the same deliberate,
canonical-constants-anchored duplication D-1 already accepts for ordering, extended to label text.
This is a second, smaller instance of the same risk documented in the Open Questions cross-reference
with `skill-category-combat-panel`: if either file's label text is edited without the other, the two
panels' category headings can read differently for the same category. Accepted for the same reason as
D-1 — sourcing both from one shared constant would reintroduce the cross-proposal dependency this
design deliberately avoids.
```python
@dataclass(frozen=True)
class CharacterSkillRow:
    key: str
    label: str

@dataclass(frozen=True)
class CharacterSkillGroupView:
    group: str | None
    label: str | None
    skills: tuple[CharacterSkillRow, ...]

@dataclass(frozen=True)
class CharacterCategoryGroupView:
    category: str
    label: str
    groups: tuple[CharacterSkillGroupView, ...]
```
This mirrors `combat_view.py`'s `SkillGroupView`/`CategoryGroupView` shape one-for-one at the type
level (deliberately, so the two JSON payloads read as the same taxonomy to a client author) while
staying a structurally independent, simpler type — no accidental coupling through a shared class.

**D-3: `active_keys` and `passive_keys` are both derived from `owned_keys()`, split by
`SKILL_REGISTRY.get(key).kind` with an explicit, tested fallback for a key absent from the
registry — never a direct `SKILL_REGISTRY[key]` index.**
```python
def _split_active_passive_keys(entity) -> tuple[tuple[str, ...], tuple[str, ...]]:
    raw = entity.db.skills or {"active": [], "passive": []}
    raw_active_keys = set(raw.get("active", []))
    seen: set[str] = set()
    active: list[str] = []
    passive: list[str] = []
    for key in entity.skills.owned_keys():
        if key in seen:
            continue
        seen.add(key)
        skill = SKILL_REGISTRY.get(key)
        if skill is not None:
            (active if skill.kind is SkillKind.ACTIVE else passive).append(key)
        elif key in raw_active_keys:
            active.append(key)
        else:
            passive.append(key)
    return tuple(active), tuple(passive)
```
This replaces the existing `_read_passive_keys()` body entirely (adjusted to source from
`owned_keys()` rather than the raw `passive` list directly) and adds the new `active_keys` field via
the same helper. Two corrections made during review, both verified against real code before being
accepted:

1. **`owned_keys()` does not de-duplicate** — it is a plain `[*active, *passive, *INNATE_SKILL_ORDER]`
   concatenation (`world/skills/handler.py`), not a de-duplicating merge; the original draft's claim
   that it does was wrong. `combat_view.py`'s own `_build_skills()` already guards this with a
   `seen: set[str]`, and this helper does the same, for the same reason: an entity whose imported
   skill list accidentally repeats a key must not render (or count toward `MAX_ACTIVE_ROWS`/
   `MAX_PASSIVE_ROWS`) that skill twice.
2. **A registry lookup here must be `.get()`, never `[...]`.** `world/webclient/presentation/
   tests/test_character_panel.py::test_unknown_item_and_skill_degrade_to_their_keys` already
   constructs exactly this scenario — `entity.db.skills = {"active": [], "passive":
   ["no_such_skill"]}` — and asserts the panel degrades gracefully, rendering the raw key as both
   `key` and `label` rather than raising. The original draft's `SKILL_REGISTRY[k]` indexing would
   raise `KeyError` for that entity and crash panel construction entirely — the exact fail-open
   failure mode this project's read models are built to avoid. The fallback above preserves the
   existing test's semantics: an unknown key is *not* reclassified by kind (there is no kind to read),
   it stays in whichever raw bucket (`active`/`passive`) it was actually stored in, matching the v2
   behavior it must not regress. `group_skill_keys()` (D-2) applies the identical `.get()`-with-
   fallback pattern already established by `character.py`'s existing `_skill_label()` for the label
   text, and buckets an unregistered key into a synthetic, non-`SkillCategory` fallback group (see
   D-2) rather than raising.

**D-4: Grouping is applied at serialization time in `character.py`, not stored pre-grouped on
`CharacterReadModel`.** `CharacterReadModel` keeps `active_keys`/`passive_keys` as flat key tuples —
matching this project's existing pattern of "presenters shape frozen read models, read models stay
flat" (`CombatView.skills` similarly stays flat; `combat_view.py`'s presenters call
`group_skill_views()` themselves). `character.py`'s `_serialize()` calls
`status_query.group_skill_keys(model.active_keys)` and `group_skill_keys(model.passive_keys)`
separately, producing the `actives` and `passives` payload sections independently — an entity's
active and passive skills never need to be grouped together, so two independent calls is simpler than
threading a kind discriminator through one call.

**D-5: `web/static/webclient/js/elosern/character_menu.js`'s `buildMenu()` is updated in the same
commit as the schema bump, not left for later.** It currently reads `panel.passives` as a flat array
of `{label}` rows (`passives.forEach(function (row, index) { items.push(displayItem(..., row.label,
...)) })`) to build the "被動技能" menu section, and has no equivalent section for `actives` at all
(that field does not exist in schema version 2). Left unmodified, once `passives` nests, `row.label`
reads the *category's own* display label (`CharacterCategoryGroupView.label` is non-null) rather than
`undefined` — so the section silently shows category names (`元素魔法`, `武技`, ...) where skill names
belong, a wrong-content bug rather than a crash, and no less broken for being quieter. The new
`actives` skills would additionally be invisible in the WebClient menu even after the server starts
sending them, since no section exists for that field at all — silently defeating this change's own
stated purpose. `buildMenu()` is updated to flatten both `actives` and
`passives` into their respective menu sections, matching how it already flattens `traits` and
`equipment` today (both already flat arrays, unaffected by this change).
`web/static/webclient/js/plugins/character_dock.js` was checked and does not reference `passives` or
`actives` directly — it renders whatever `character_menu.js` hands it — so no change is needed there.

**D-6: `MAX_PASSIVE_ROWS`/`MAX_ACTIVE_ROWS` are re-asserted as explicit flattened-total checks, not
inherited implicitly from the v2 flat-array length check.** Applying `len(passives) >
MAX_PASSIVE_ROWS` unchanged to the new top-level `passives` array would bound the *category-group*
count instead (at most `len(SkillCategory)`), silently weakening the bound — the identical class of
gap `skill-category-combat-panel` identified and fixed for its own `MAX_SKILLS` check (that
proposal's design.md D-5). `validate_character()` computes the flattened row count across every
category and sub-group for each of `actives`/`passives` independently and rejects when either exceeds
its bound.

## Risks / Trade-offs

- **[Risk]** Duplicating the category/group ordering rule between `combat_view.py` and
  `status_query.py` risks the two drifting if `SkillCategory`'s declaration order or
  `ELEMENT_REGISTRY`'s order ever changes and only one call site is updated. → **Mitigation**: both
  read the same module-level constants directly (`for category in SkillCategory:`,
  `for element in ELEMENT_REGISTRY:`) rather than each hardcoding a literal order, so a change to
  either constant is picked up by both without any edit to either grouping function. What remains
  duplicated is the *iteration shape*, not the *order data* — the class of drift the enum/dict
  constants exist to prevent already does not apply here.
- **[Risk]** Schema version 3 is a breaking wire-format change. → **Mitigation**: no released users,
  per repository convention; same accepted trade-off as `skill-category-combat-panel`.
- **[Risk]** The client-side parity validator (`protocol.js`) and its dual-direction parity test are
  a second, JS-side source of truth for this schema and must be kept in lockstep. → **Mitigation**:
  pre-existing discipline (`character.py`'s own module docstring already documents this parity
  contract for schema version 2); this change updates both sides in the same commit, as version 2's
  authors already did.

## Migration Plan

Not applicable — no released users. Lands as a single atomic commit: `status_query.py`'s corrected
read and new field, `character.py`'s schema bump and grouped serialization, `protocol.js`'s parity
update, and all associated tests, together.

## Open Questions

- **Coupled with `skill-category-combat-panel`'s own Open Question**: this proposal's
  `group_skill_keys()` (D-1/D-2) implements the same first-seen-order rule for `sexual_act`
  sub-groups as `skill-category-combat-panel`'s `group_skill_views()`, by deliberate duplication
  rather than a shared dependency. `skill-category-combat-panel`'s design.md flags that a future
  canonical `sexual_act` line-ordering table (deferred to whichever change ships the sexual-act
  catalog) would need to update *both* helpers to stay in lockstep. Whoever resolves that Open
  Question must grep for `group_skill_keys` as well as `group_skill_views` before considering the
  change complete — recorded here so it is discoverable from either proposal, not only the one
  that happened to raise it first.
