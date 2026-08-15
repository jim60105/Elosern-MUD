## 1. Package scaffold

- [ ] 1.1 Create `world/skills/sexual_acts/__init__.py`, `_builder.py`, `solo.py`, `shame.py`,
      `partner.py`, `combat.py`, `interspecies.py`, `divine.py`, and `tests/__init__.py`.
- [ ] 1.2 Each of the six line modules exports its one tuple constant (`SOLO_ACTS`, `SHAME_ACTS`,
      `PARTNER_ACTS`, `COMBAT_ACTS`, `INTERSPECIES_ACTS`, `DIVINE_ACTS`) equal to `()`.

## 2. SexualActDef and _act_family()

- [ ] 2.1 Define `SexualActDef` in `_builder.py` with exactly the fields in design.md D-1 (no `line`
      field).
- [ ] 2.2 Implement `_act_family()` per design.md D-2: builds paired `SkillDef`/`SexualActDef` rows,
      sets `SkillDef.category=SkillCategory.SEXUAL_ACT` and `group=line`, `cost={}`,
      `usable_out_of_combat=True`, `effects=[]`.
- [ ] 2.3 Implement the five per-row structural checks inside `_act_family()` (design.md D-6, items
      1-5): non-zero `actor_pleasure_ratio` unless `requires_divine_arts`; no `GENERIC_BODY_PART`; no
      `target_part` for `異種`/`神之秘法` lines; every part in `BODY_PARTS`; `base_pleasure > 0` and
      `resistible` is a bare `bool`.

## 3. Registry assembly

- [ ] 3.1 `__init__.py` imports all six line modules, merges their rows into
      `SEXUAL_ACT_REGISTRY: dict[str, SexualActDef]`, and registers every produced `SkillDef` into
      `world.skills.registry.SKILL_REGISTRY`.
- [ ] 3.2 Confirm import order: `world/skills/sexual_acts/__init__.py` must import after
      `world/skills/registry.py`'s module body has finished constructing `SKILL_REGISTRY`, so
      registration is an update, not a race. Add a regression test asserting
      `SKILL_REGISTRY is world.skills.registry.SKILL_REGISTRY` (the same object, not a copy) after
      `world.skills.sexual_acts` is imported.

## 4. SexualState.unlocked_act_keys()

- [ ] 4.1 Add `unlocked_act_keys()` to `world/rules/sexual_state.py` per design.md D-4, with the
      deferred `SEXUAL_ACT_REGISTRY`/`SexualMasteryEffect`/`SKILL_REGISTRY` imports inside the method
      body.
- [ ] 4.2 Add the private `_has_sexual_mastery()` helper reading `entity.skills.base_owned_keys()`,
      with the membership guard (`if key in SKILL_REGISTRY`) placed immediately after the first `for`
      clause, before the second `for` dereferences `SKILL_REGISTRY[key]` — placing it last raises
      `KeyError` (design.md D-4).
- [ ] 4.3 Add a regression test calling `_has_sexual_mastery()` (or `unlocked_act_keys()`) for an
      entity whose `base_owned_keys()` includes `"flee"` **without** first importing
      `world.rules.disengage` in that test module, asserting no `KeyError` is raised. This is the
      exact failure mode design.md D-4 documents: `"flee"` is registered into `SKILL_REGISTRY` only
      as `world/rules/disengage.py`'s import side effect, and `INNATE_SKILL_ORDER` always names it.

## 5. SkillHandler extension

- [ ] 5.1 Add `base_owned_keys()` to `world/skills/handler.py`, moving `owned_keys()`'s current body
      into it verbatim.
- [ ] 5.2 Reimplement `owned_keys()` to return `base_owned_keys()` plus
      `sorted(entity.sexual.unlocked_act_keys())` via `getattr(self.entity, "sexual", None)`, with no
      new import from `world.rules`.

## 6. Acceptance proof (test-local, never committed to a line module)

- [ ] 6.1 In `tests/test_acceptance.py`, build one `SexualActDef`/`SkillDef` pair via `_act_family()`
      with `effects=[]` and a nonzero `unlock` threshold on an otherwise-unused counter; install it
      into `SEXUAL_ACT_REGISTRY`/`SKILL_REGISTRY` for the test only
      (`unittest.mock.patch.dict`), removed on teardown. `solo.py` and the other five line modules
      are never edited by this task — they ship `= ()` from the first commit.
- [ ] 6.2 Assert the full round trip: the act is absent from `owned_keys()` and `_step1_ownership`
      rejects casting it with `UNKNOWN_SKILL` while the entity's counter is below threshold; once the
      counter clears the threshold, the act is present in `owned_keys()` and a cast through
      `ActionResolver` resolves as a successful no-op (zero pending effects, since `effects=[]`).

## 7. Structural tests

- [ ] 7.1 `tests/test_registry_structure.py`: assert every counter/event name referenced by any act
      resolves against `SexualState`'s eleven counter attributes and `sexual.yaml`'s `when["event"]`
      values (design.md D-6, items 6-7).
- [ ] 7.2 Assert `set(SEXUAL_ACT_REGISTRY)` equals `SKILL_REGISTRY`'s `SEXUAL_ACT`-categorised keys
      minus the three named exclusions (design.md D-6, item 8).
- [ ] 7.3 Assert `owned_keys()` equals `base_owned_keys()` for an entity with zero unlocked acts (the
      design.md Risks section's drift guard).
- [ ] 7.4 Assert `world/skills/handler.py`'s import statements contain no `world.rules.*` reference.

## 8. Traceability and verification

- [ ] 8.1 Run `uv run --locked python -m tools.spec_traceability list` to obtain canonical requirement
      IDs for the three new/modified capabilities and annotate each requirement's covering test with
      `covers_requirement`.
- [ ] 8.2 Run `uv run --locked python -m tools.spec_traceability check`.
- [ ] 8.3 Run the focused package tests:
      `uv run --locked evennia test --settings test_settings.py world.skills world.rules.tests.test_sexual_state`
      (adjust dotted path to the actual new test module locations).
- [ ] 8.4 Run `uv run --locked python -m compileall -q world`.
- [ ] 8.5 Run `openspec validate sexual-act-registry --strict`.
