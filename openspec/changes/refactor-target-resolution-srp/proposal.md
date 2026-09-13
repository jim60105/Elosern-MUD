# Proposal: refactor-target-resolution-srp

## Why

`world/rules/targeting.py` calls itself "combat-agnostic target validation for
deterministic actions", but every entry point takes a `SkillDef` and the
resolver body special-cases one skill category. That coupling is the single
blocker for the approved item-effect model
(`docs/superpowers/specs/2026-09-14-item-effect-model-design.md` §4): a usable
item declaring `scope: single` or `scope: all-allies` has no skill, so today it
would need a second, parallel target resolver — exactly the duplication the
module was created to prevent.

Five concrete couplings exist today:

1. All four validators take `skill: SkillDef`; `_validate_presence` and
   `_validate_alive` never read it (`targeting.py:131-137`).
2. `resolve_targets` hard-codes "a `SkillCategory.SEXUAL_ACT` skill may not
   target the actor" inside the general resolver (`targeting.py:222-236`).
3. `ActionContext.is_in_range(actor, target, skill)` carries a parameter
   **neither implementation reads** — `RoomActionContext` returns `True`
   unconditionally, `BattlefieldActionContext` reads only `battlefield.fled`
   (`targeting.py:78`, `combat.py:123`).
4. `damage_requires_battlefield()` — a skill-effect combat-state gate, not
   target validation — lives in this module (`targeting.py:99`).
5. `resolve_targets(request: Any, ...)` reaches into `request.actor` and
   `request.context` with no declared contract.

Doing this first, as a separately reviewable behavior-preserving refactor,
keeps the item work from carrying an unrelated skill-pipeline diff.

## What Changes

- Add `TargetRequirement` (frozen dataclass: `spec`, `faction`, `forbid_self`)
  as the resolver's single input contract. Any caller that can describe its
  targeting rule can now use the resolver; nothing needs to own a `SkillDef`.
- Add `SkillDef.target_requirement` producing one, with
  `forbid_self = (self.category is SkillCategory.SEXUAL_ACT)`. **The sexual-act
  self-cast prohibition is now stated by the skill that owns it**, and the
  resolver stops importing `SkillCategory` entirely.
- **BREAKING (internal API)**: `resolve_targets(actor, context, requirement,
  candidates)` and `candidate_rejection(actor, context, requirement, target)`
  replace their `(request, target, skill)` shapes. All four validators take
  `(actor, context, requirement, target)`.
- **BREAKING (internal API)**: `ActionContext.is_in_range(actor, target)` drops
  its third parameter. Behavior-preserving: neither shipped implementation
  reads it.
- Move `damage_requires_battlefield()` out of `targeting.py` into a new
  `world/rules/action_gates.py`. Its body, its two callers' behavior, and the
  `inspect.getsource` sanctioned-gate assertion in
  `test_action_pipeline_rejections.py` are unchanged — only its home.

No player-visible behavior changes. No rulebook, registry, or persisted data
changes. Every rejection reason, ordering guarantee, and AREA filtering rule is
preserved exactly.

## Capabilities

### New Capabilities

None. The refactor restates existing requirements against a new input contract.

### Modified Capabilities

- `targeting-validation`: the requirement "FactionConstraint is read from
  SkillDef, not declared by the caller" is RENAMED and restated — the constraint
  now reaches the resolver through a `TargetRequirement` that the definition
  produces, preserving the actual invariant (the *definition* owns the
  constraint, never the calling request) while removing `SkillDef` from the
  resolver's signature. The four-ordered-validations requirement gains the
  `forbid_self` rule as an explicit, definition-supplied input rather than a
  category test inside the resolver. The `ActionContext` protocol requirement
  updates `is_in_range()` to its two-argument form.
- `battlefield-action-context`: the `is_in_range` requirement and its three
  scenarios update to the two-argument signature; the "regardless of the skill's
  own identity" guarantee becomes structural (the signature can no longer see a
  skill) instead of a documented promise.
- `sexual-act-seeds`: "A SINGLE-target sexual act cannot be self-cast" currently
  attributes the prohibition to a category test inside the targeting pipeline.
  The rejection and both its scenarios are unchanged, but the requirement is
  restated so the skill definition declares the prohibition and the pipeline
  merely enforces what it is given.

## Impact

- **Code**: `world/rules/targeting.py` (the refactor), `world/rules/combat.py`
  (`BattlefieldActionContext.is_in_range` signature), `world/skills/registry.py`
  (`SkillDef.target_requirement` property), `world/rules/action.py`
  (`_step3_targeting` call site, `damage_requires_battlefield` import),
  `world/rules/action_preview.py` (three `candidate_rejection` call sites plus
  the gate import), new `world/rules/action_gates.py`.
- **Non-test call sites**: exactly four — `action.py:394`,
  `action_preview.py:215`, `:222`, `:327`.
- **Tests**: `world/rules/tests/test_targeting.py` (18 `resolve_targets` call sites change signature —
  the bulk of the work; `candidate_rejection` has no test call sites, only the three in
  `action_preview.py`), `test_battlefield_action_context.py:37`, `test_action_pipeline_rejections.py`
  (import path only).
- **Downstream**: unblocks `add-item-effect-targeting`, which resolves item
  scopes through this resolver. No other in-flight change touches these files.
- **Data**: none. No migration (unreleased project, zero users).
