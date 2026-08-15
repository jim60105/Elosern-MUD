## Why

The sexual-state machine (`SexualState`, `sexual.yaml`, `climax-settlement`) and the skill category
taxonomy (`skill-category-registry`) are both live, but nothing yet lets a skill *be* a sex act.
There is no metadata shape for an act's body parts, participant-role pleasure split, or counter-based
unlock requirement, no query that turns an entity's lifetime counters into a set of available acts,
and no consumer that lets `SkillHandler.owned_keys()` — and therefore `ActionResolver` and the combat
panel — see an unlocked act at all. Until this lands, the eleven lifetime counters `sexual-counters`
shipped have nothing reading them, and `SexualMasteryEffect` (shipped since the skill-system
redesign) still has no consumer despite its own docstring promising one.

This change adds the registry, the metadata shape, and the unlock query. It does not add any act
content or any pleasure/counter-mutating effect — those are `sexual-act-effects` (this proposal's
direct dependent) and the six catalog proposals that follow it.

## What Changes

- Add `world/skills/sexual_acts/`, a new package: `_builder.py` (the `SexualActDef` dataclass and the
  `_act_family()` construction helper, mirroring `_elemental_spells()`'s shape) plus six line modules
  (`solo.py`, `shame.py`, `partner.py`, `combat.py`, `interspecies.py`, `divine.py`), each shipping
  empty in this change and assembled by `__init__.py` into `SEXUAL_ACT_REGISTRY: dict[str,
  SexualActDef]`. Six catalog proposals later fill exactly one module each with no other file touched
  — this change's only job is to make that possible.
- Every `SexualActDef` also registers an ordinary `SkillDef` in `SKILL_REGISTRY` under the same key,
  category `SkillCategory.SEXUAL_ACT`. This change adds no act rows itself; the seam is proven by one
  structural test using a synthetic act, not by shipping content.
- Add `SexualState.unlocked_act_keys() -> frozenset[str]` to `world/rules/sexual_state.py`: every act
  whose `SexualActDef.unlock` counter thresholds are all met, or the entire `SEXUAL_ACT_REGISTRY`
  keyset when the entity directly owns any skill carrying `SexualMasteryEffect` — the first consumer
  of that effect since it shipped. Conferred grants never satisfy the blanket unlock, matching
  `can_cast_spell_tier`'s existing mastery-override discipline.
- Add `SkillHandler.base_owned_keys()` to `world/skills/handler.py`, returning exactly what
  `owned_keys()` returns today (imported keys plus `INNATE_SKILL_ORDER`). `owned_keys()` becomes
  `base_owned_keys()` plus the entity's unlocked act keys, read by duck-typed attribute access
  (`getattr(entity, "sexual", None)`) so `world/skills/handler.py` gains no import from
  `world/rules/`. The split exists to break the recursion `unlocked_act_keys()`'s mastery check would
  otherwise cause.
- Add seven registry-load-time or test-time structural invariants (design doc §2.5): every act
  granting pleasure to a target grants non-zero pleasure to its own actor unless its `SkillDef`
  declares `requires_divine_arts`; no act declares `GENERIC_BODY_PART`; no act categorised outside
  this change's future 異種/神之秘法 lines declares a partless target; every part named is a
  `BODY_PARTS` member; every counter and event an act names actually exists; `SEXUAL_ACT_REGISTRY`'s
  keys and `SKILL_REGISTRY`'s `SEXUAL_ACT`-categorised keys agree exactly, modulo the three skills
  `skill-category-registry` already recategorised (`divine_sexual_arts`, `divine_sexual_mastery`,
  `reincarnation_boon_yuna`), which carry no `SexualActDef` and are excluded by name.

## Capabilities

### New Capabilities
- `sexual-act-registry`: `SexualActDef`, `SEXUAL_ACT_REGISTRY`, the six-module package with its
  pre-declared stubs, `_act_family()`, and the seven structural invariants.

### Modified Capabilities
- `sexual-state-handler`: adds the `unlocked_act_keys()` query, including the `SexualMasteryEffect`
  blanket-unlock rule and its conferred-grant exclusion.
- `skill-handler`: `owned_keys()` gains unlocked sexual acts; adds `base_owned_keys()` as the
  pre-extension set consulted by the mastery check to avoid recursion.

## Impact

- New: `world/skills/sexual_acts/__init__.py`, `_builder.py`, `solo.py`, `shame.py`, `partner.py`,
  `combat.py`, `interspecies.py`, `divine.py`.
- Modified: `world/rules/sexual_state.py` (new method only — no field or existing method changes),
  `world/skills/handler.py`.
- No change to `world/rules/action.py`, `world/skills/registry.py`, or any `rulebook/*.yaml` — those
  are `sexual-act-effects`'s territory (dependent proposal).
- No player-visible behaviour change: with zero acts registered, `unlocked_act_keys()` returns an
  empty set and `owned_keys()` is unchanged for every entity. `docs/game/commands.md` needs no update
  from this change alone.
