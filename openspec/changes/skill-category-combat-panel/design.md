## Context

Full rationale lives in `docs/superpowers/specs/2026-08-15-skill-category-system-design.md` §5.1–5.2;
this document covers only the implementation-level decisions needed to build this specific change.

`world/rules/combat_view.py` builds a frozen `CombatView` (session, participants, skills) strictly
from canonical state, consumed identically by two presenters: `web/webclient/presentation/
combat_panel.py` (JSON `context_actions` schema version 2, validated by `validate_context_actions()`)
and `commands/combat.py`'s `CmdCombatActions` (Telnet text). `CombatView.skills` is currently a flat
`tuple[SkillDescriptorView, ...]` built by `_build_skills()`, iterating `actor.skills.owned_keys()`
in order and filtering to owned active, enabled-or-disabled-with-reason skills, bounded by
`MAX_SKILLS = 32`. Both presenters iterate that same flat tuple today. This change depends on
`skill-category-registry` having already landed `SkillCategory` and `SkillDef.category`/`.group`.

## Goals / Non-Goals

**Goals:**
- One shared grouping implementation, consumed by both presenters, so WebClient and Telnet can never
  disagree about grouping or ordering.
- The individual skill descriptor's own fields are byte-identical to schema version 2 — only the
  envelope nests.
- Deterministic category and group ordering, independent of what the entity happens to own.
- Empty categories/groups are omitted, not emitted empty — consistent with this project's "hide, do
  not disable" convention for unavailable content.

**Non-Goals:**
- No change to skill availability, targeting, cost, or any other combat-resolution behavior. This is
  presentation-only.
- No canonical ordering for `sexual_act` line groups beyond first-seen-among-owned-skills order (see
  Decision D-4) — a catalog-wide line order is deferred to whichever future change actually ships the
  sexual-act catalog content, since only 3 `sexual_act` skills exist in the registry today and none
  of them share a `group` collision that would make ordering observable.
- No player-configurable ordering, filtering, or search.

## Decisions

**D-1: Grouping is computed by one shared pure function in `world/rules/combat_view.py`, not
duplicated in each presenter.** Both `combat_panel.py` and `commands/combat.py` already import
directly from `combat_view.py` (`build_combat_view`, `CombatViewError`), so adding
`group_skill_views()` beside them introduces no new dependency edge. The alternative — grouping
inside each presenter separately — was rejected because it is exactly the kind of duplicated
condition-matching logic this project's specs repeatedly forbid (see `sexual-transition-rulebook`'s
"no rule-loading or condition-matching logic duplicated" precedent); two independent groupings could
silently drift.

**D-2: Two new frozen dataclasses, `SkillGroupView` and `CategoryGroupView`, added to
`combat_view.py` beside `SkillDescriptorView`.**
```python
@dataclass(frozen=True)
class SkillGroupView:
    group: str | None       # element key, sexual-act line name, or None
    label: str | None       # None exactly when group is None
    skills: tuple[SkillDescriptorView, ...]

@dataclass(frozen=True)
class CategoryGroupView:
    category: str            # SkillCategory value
    label: str                # display label
    groups: tuple[SkillGroupView, ...]
```
`CombatView.skills` stays the flat tuple (nothing currently reading it directly needs to change,
and it remains the input to `group_skill_views()`); a **new** `CombatView` field is not introduced.
Both presenters call `group_skill_views(view.skills)` themselves rather than `CombatView` doing it
eagerly, keeping `CombatView`'s existing "frozen read-only view model, strictly built once" contract
intact — grouping is a presentation-time transform of already-frozen data, not new state.

**D-3: Category ordering is `SkillCategory`'s Python enum declaration order; `elemental_magic`
sub-group ordering is `ELEMENT_REGISTRY`'s dict declaration order.** Both are already fixed,
deterministic sequences with no runtime dependency on what the entity owns — `group_skill_views()`
iterates them directly (`for category in SkillCategory: ...`, `for element in ELEMENT_REGISTRY: ...`)
rather than sorting observed groups, which is what guarantees the ordering never depends on
`owned_keys()`'s incidental order.

**D-4: `sexual_act` sub-group ordering is first-seen-among-owned-skills order, not a canonical line
table.** Alternatives considered: hardcode the seven line names (`獨處`, `羞恥`, `關係`, `戰鬥`,
`異種`, `神之秘法`, `精通`) from the sexual-act design document now. Rejected for this change
specifically: only three `sexual_act` skills exist in the shipped registry (`divine_sexual_arts` /
`神之秘法`, `divine_sexual_mastery` and `reincarnation_boon_yuna` / `精通`), so a canonical seven-line
order is unobservable and untestable today, and hardcoding it here would let this presentation-only
change silently assert a catalog-content decision that belongs to the sexual-act-catalog change. When
that change lands, it either supplies the canonical order or this decision is revisited — noted as an
Open Question below.

**D-5: `validate_context_actions()`'s existing whole-payload invariants are preserved by validating
after flattening, and one of them — the `MAX_SKILLS` bound — must be re-asserted explicitly, not
inherited implicitly.** The two existing payload-wide checks — every skill's `targets` reference a
presented participant, and skill keys are unique across the whole payload — are still checked against
the flattened set of all skill descriptors across every group, so a duplicate key between two
different categories is still caught. The v2 validator's third whole-payload check,
`len(skills) > MAX_SKILLS` (`combat_panel.py` line 385), does **not** carry over unchanged: naively
applying the same check to the new top-level `skills` array would instead bound the number of
*category groups* (at most 8, `len(SkillCategory)`) — a materially weaker check that stops enforcing
the actual total-skill-count bound the OOB protocol limit depends on. `_validate_category_group()`
therefore computes `sum(len(sub_group["skills"]) for category in skills for sub_group in
category["groups"])` and rejects when that flattened total exceeds `MAX_SKILLS`, and separately
asserts the top-level `skills` array itself has at most `len(SkillCategory)` entries (a cheap,
explicit bound rather than an implicit one). This is the corrected version of a design gap identified
during review: the original draft's claim that "the nested structure adds no new whole-payload
invariant beyond category/group internal shape" was wrong about `MAX_SKILLS` specifically — that
invariant is not new, but it does need a new, explicit implementation to survive the shape change,
and proposal.md's "every existing validation ... unchanged" claim is read as *behaviorally* unchanged
(the same entities are still rejected for the same reason), not *implementation*-unchanged.

**D-6: The `_validate_skill()` per-descriptor validator is unchanged.** Because the individual skill
descriptor object is byte-identical to schema version 2 (proposal), the existing validator is reused
inside a new `_validate_skill_group()` / `_validate_category_group()` wrapper, not rewritten.

**D-7: The three production WebClient JS files that read `context_actions.skills` are updated in the
same commit as the server-side schema bump, not left for a later change.**
`web/static/webclient/js/elosern/protocol.js`'s `validateContextActionsPanel()`,
`web/static/webclient/js/elosern/combat_menu.js`'s `panelSkills()`/`skillItems()`, and
`web/static/webclient/js/plugins/combat_dock.js`'s `panelSignature()` all currently treat
`payload.skills` as a flat array and read `.key`/`.label`/`.enabled`/`.targets` directly off each
entry. This was an oversight in the original draft of this design (caught during review, not an
intentional deferral) — a v3 server payload against unmodified client JS makes `protocol.js` throw
`"unsupported context_actions panel schema_version"` on every combat snapshot, so the WebClient never
renders a combat panel at all once the server ships. This is the identical class of obligation the
sibling `skill-category-status-listing` proposal already scopes correctly for its own schema bump
(its design.md calls updating `protocol.js` "pre-existing discipline," citing `character.py`'s own
module docstring documenting the same client/server parity contract). `protocol.js`'s update mirrors
`_validate_category_group()`/`_validate_skill_group()` structurally; `combat_menu.js` and
`combat_dock.js` flatten the nested structure (iterate categories, then sub-groups, then skills) to
rebuild the flat lists their existing menu-construction and change-detection logic already expects,
rather than rewriting that downstream logic to be nesting-aware — the nesting is a presentation
concern for headings/sub-headings, not a reason to restructure how menu items or signatures are
built from the underlying skill set.

## Risks / Trade-offs

- **[Risk]** Schema version 3 is a breaking wire-format change; any client still speaking version 2
  cannot parse the new envelope. → **Mitigation**: this project has no released users; there is no
  version-2 client to protect, per repository convention (proposal.md's BREAKING note).
- **[Risk]** Browser acceptance tests for this change are the most expensive tests in the repository
  (each combat browser test boots its own Evennia server, ~35–70s). → **Mitigation**: accepted cost,
  called out explicitly in the shared implementation-sequence document
  (`2026-08-15-sexual-act-system-overview-design.md` §4.3) which schedules this proposal as a full
  day with no parallel track for the same implementer.
- **[Risk]** A future change adds a `sexual_act` skill whose line was already observed for that entity
  in a different order on a previous request, producing a flicker in sub-group order across requests
  for the same entity. → **Mitigation**: acceptable for this change's scope (only 3 sexual_act skills
  exist today, all with stable, non-overlapping groups); flagged as an Open Question for whoever ships
  the catalog content.

## Migration Plan

Not applicable — no released users. Lands as a single atomic commit: `combat_view.py`'s new views and
grouping helper, `combat_panel.py`'s schema bump and validator changes, `commands/combat.py`'s Telnet
grouping, and all associated tests, together.

## Open Questions

- Should a canonical `sexual_act` line-ordering table exist, and if so, does it belong in this
  change, in `world/lore/`, or in the future sexual-act-catalog change itself? Deferred per D-4;
  revisit when that change is proposed. **This decision has a coupled sibling**: the
  `skill-category-status-listing` proposal's `group_skill_keys()` independently implements the same
  first-seen-order rule for `sexual_act` (by design — see that proposal's D-1 — to avoid a hard
  dependency between the two panel proposals). If this Open Question is later resolved by introducing
  a canonical order, `group_skill_keys()` must be updated in lockstep or the two panels will silently
  disagree on `sexual_act` sub-group order. Neither proposal's code enforces this in lockstep
  automatically; whoever resolves this Open Question must grep for `group_skill_keys` as well as
  `group_skill_views` before considering the change complete.
