# Tasks: refactor-target-resolution-srp

Design decisions referenced below live in `design.md` (D1–D6).

## 1. Introduce the requirement value object

- [ ] 1.1 Add `TargetRequirement` to `world/rules/targeting.py`: a frozen dataclass with
  `spec: TargetSpec`, `faction: FactionConstraint = FactionConstraint.ANY`, and
  `forbid_self: bool = False` (D1). Verify by constructing all five item-relevant shapes
  (SELF/SELF_ONLY, SINGLE/ANY, AREA/ANY, plus a SINGLE/ANY with `forbid_self=True`) in a new
  `world/rules/tests/test_targeting.py` case asserting the defaults and frozen-ness.
- [ ] 1.2 Add `SkillDef.target_requirement` in `world/skills/registry.py` producing
  `TargetRequirement(self.target_spec, self.faction_constraint, forbid_self=self.category is
  SkillCategory.SEXUAL_ACT)`, computed once and not stored as a mutable attribute on the frozen
  dataclass (D2, and the frozen-dataclass risk in design.md). Verify with a registry test that every
  SINGLE-target `SEXUAL_ACT` skill reports `forbid_self=True` and every other shipped skill reports
  `False` — this is the `sexual-act-seeds` delta's third scenario.

## 2. Re-sign the resolver

- [ ] 2.1 Change the four validators in `world/rules/targeting.py` to
  `(actor, context, requirement, target)` (D5), and change `_validate_faction` to read
  `requirement.faction` instead of `skill.faction_constraint`. Verify the module no longer references
  `skill` in any validator body.
- [ ] 2.2 Change `resolve_targets` to `(actor, context, requirement, candidates)` and
  `candidate_rejection` to `(actor, context, requirement, target)`, reading shape from
  `requirement.spec`. Verify `world/rules/targeting.py` no longer imports `SkillDef`.
- [ ] 2.3 Replace the `SkillCategory.SEXUAL_ACT` branch in `resolve_targets`'s SINGLE arm with a
  `requirement.forbid_self` test, keeping the identical `RejectReason.TARGET_SPEC_MISMATCH` and detail
  string (D2). Verify `world/rules/targeting.py` no longer imports `SkillCategory`, and that a
  direct-constructed `forbid_self` requirement rejects the actor — the two new scenarios in the
  `targeting-validation` delta.
- [ ] 2.4 Drop the third parameter from `ActionContext.is_in_range`, `RoomActionContext.is_in_range`,
  `BattlefieldActionContext.is_in_range` (`world/rules/combat.py:123`), and the `_validate_range`
  call site (D3). Verify with a structural test asserting both shipped implementations expose exactly
  `(self, actor, target)`.

## 3. Move the damaging-action gate

- [ ] 3.1 Create `world/rules/action_gates.py` and move `damage_requires_battlefield()` into it with
  its body and docstring unedited (D4). Verify `test_action_pipeline_rejections.py`'s
  `inspect.getsource` sanctioned-gate assertion still passes after only its import path is updated.
- [ ] 3.2 Update the two callers (`world/rules/action.py:56`, `world/rules/action_preview.py:48`) to
  import from the new module and verify `world/rules/targeting.py` no longer imports `DamageEffect`.

## 4. Update call sites

- [ ] 4.1 Update `_step3_targeting` in `world/rules/action.py:394` to pass
  `(request.actor, request.context, skill.target_requirement, candidates)`. Verify the existing cast
  pipeline tests pass unchanged.
- [ ] 4.2 Update the three `candidate_rejection` call sites in `world/rules/action_preview.py`
  (`:215`, `:222`, `:327`). Verify the action-preview suite passes unchanged, confirming preview and
  execution still share one validator path.

## 5. Port the test suite

- [ ] 5.1 Port every `resolve_targets` / `candidate_rejection` call in
  `world/rules/tests/test_targeting.py` to the new signatures, changing signatures only (D6). Verify
  by reviewing the diff: any changed `assert*` argument in this file is a behavior regression, not a
  fix, and must be investigated before proceeding.
- [ ] 5.2 Update `world/rules/tests/test_battlefield_action_context.py:37` to the two-argument
  `is_in_range` and verify the suite passes.
- [ ] 5.3 Run the full deterministic test suite and verify zero behavioral diffs across the cast
  pipeline, combat, action-preview, and sexual-act suites — the whole point of this change is that
  nothing else moves.

## 6. Documentation and validation

- [ ] 6.1 Update the `world/rules/targeting.py` module docstring to state the new contract (the
  resolver consumes a `TargetRequirement` and knows nothing about what produced it), and note in
  `world/rules/action_gates.py`'s docstring why the gate lives outside targeting. Verify by reading
  both docstrings against the `targeting-validation` delta.
- [ ] 6.2 Run `openspec validate refactor-target-resolution-srp` and the repository's lint/observability
  gate; verify both pass.
