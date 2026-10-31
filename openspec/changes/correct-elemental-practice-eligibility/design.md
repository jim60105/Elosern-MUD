# Design

## Context

`world/rules/progression/_practice.py::_is_elemental_magic` currently requires a matching magic-school `DamageEffect`. `_practice_growth_factors` uses it for affinity and `_owned_growth_factor` uses it for owned scoped growth. `grant_skill_practice_xp` and `grant_study_practice_xp` already consume these shared factors. Thus a single classifier correction fixes both paths without changing award storage.

Current observed examples supplied by the approved investigation show favored elemental damage learning faster, unfavored elemental damage slower, elemental healing/earth protection neutral, and elemental physical shadow martial practice neutral. Constants remain authored rulebook data.

## Goals / Non-Goals

Correct elemental learning eligibility. MUST NOT change race multipliers, affinity constants, skill rows, boon magnitude, practice caps, damage, healing output, MP cost, innate traits, freeform eligibility, mastery grants or divine cadence. This is an XP-only change.

## Decisions

### D1. Catalog semantics define learning eligibility

Retain the existing private signature verbatim:

```python
def _is_elemental_magic(skill: SkillDef) -> bool:
    ...
```

Return true exactly when `skill.kind is SkillKind.ACTIVE`, `skill.category is SkillCategory.ELEMENTAL_MAGIC`, and `skill.element` identifies an entry in `ELEMENT_REGISTRY`. Use the typed catalog identity; parsed effect prefixes do not classify a spell's learning domain. Ordinary healing, self-buff, party-buff, control, cleansing and mixed-effect elemental spells qualify regardless of whether damage appears. Element-tagged `MARTIAL_ARTS`, PASSIVE enhancements, elementless actions and `DIVINE_MYSTERY` remain neutral for these two elemental factors.

Use existing registry/vocabulary imports. Remove the now-unused `DamageEffect` import and damage-only explanation from `_practice.py`; do not add a public API or a second classifier. The category is already authoritative in registry rows and the resolver, so no per-skill exceptions or new school field is needed.

### D2. Both factors and award paths retain their contracts

`_owned_growth_factor(entity: Any, skill: SkillDef) -> float` and `_practice_growth_factors(entity: Any, skill: SkillDef) -> float` continue to call `_is_elemental_magic`. Keep matching owned scoped growth multiplicative with race and conferred growth; preserve restriction filtering and exclusion of conferred ownership from the owned factor. No changes to `practice_xp_amount`, the study formula or the sole XP writer beyond updated explanations.

### D3. Tests establish mechanism, with fixed synthetic outcomes

Extend `world/rules/tests/test_progression/test_element_affinity_and_practice_pipeline.py`. Install synthetic ACTIVE elemental damage, heal, self-buff, control and mixed-effect rows sharing a synthetic element; include an elemental-tagged PHYSICAL martial row and an elementless action. Give the synthetic actor independently chosen fixed multipliers. Assert known XP numbers, selected to avoid saturation, across favored/unfavored/undeclared affinity and scoped/unscoped growth controls. A different element and conferred-only growth owner detect wrong scope and wrong ownership.

Exercise `practice_xp_amount`, use awards and booked study rather than calling the predicate alone. Use independent expected numbers rather than asking the function under test for an expected multiplier. Compare matching practice-domain factors across use and study while retaining their distinct base amounts. Keep untouched recipient and before/after resource/stat controls; classification must not alter damage/heal magnitude, MP charge or innate values. Extend existing rollback tests only if a changed fixture requires it; do not create a new rollback subsystem.

All tests stay in existing modules, with synthetic fixture support in `_support.py` only when needed. No shard changes or browser work.

### D4. Delta and documentation

Modify the existing `skill-lineage` requirement `Successful ACTIVE resolution accruses lineage practice XP`, preserving unrelated scenarios. Replace its damage-only scenario with catalog-domain eligibility and add damage-free/use-study examples without copying production constants or skill keys. Its current canonical ID remains unchanged; retrieve it with `uv run --locked python -m tools.spec_traceability list` and use the existing discoverable behavior tests.

Amend §8 of `docs/superpowers/specs/2026-08-30-use-driven-progression-design.md`, the learning explanation in `docs/lore/skill-trees/index.md`, and `docs/lore/magic-system.md` only where needed to state elemental learning eligibility. Mastery changes own the separate mastery paragraphs in those documents.

## Risks / Trade-offs

- Category semantics must remain authoritative. A generic catalog relationship check may identify a malformed row; do not add a new per-key exception or rewrite the classifier from visual spell names.
- More skill shapes receive existing modifiers. Fixed synthetic favored/unfavored and owned-scope controls detect accidental flat bonuses or applying the bonus to martial skills.

## Human review document

This `design.md`, D1 and D4, is the review document for explanations. A person checks that prose describes learning-only affinity and keeps innate numbers fixed at birth. Automated tests establish XP eligibility and unchanged resolution outputs, without pinning prose.

## Migration Plan

Pre-release rule correction, applied atomically with tests and explanatory docs. No save migration, compensation award or retroactive XP recalculation. Existing stored XP remains unchanged; subsequent practice uses the corrected predicate.
