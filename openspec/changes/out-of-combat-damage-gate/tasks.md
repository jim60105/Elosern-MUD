## 1. Reject reason and player-facing line

- [x] 1.1 Add `DAMAGE_REQUIRES_MONSTER_TARGET = "damage_requires_monster_target"` to `RejectReason` in `world/rules/action.py`
- [x] 1.2 Add its Traditional Chinese line to `world/rules/player_messages.py::rejection_message`, stating that a damaging skill must be aimed at a co-located monster
- [x] 1.3 Verify the existing rejection-message coverage test (every `RejectReason` member has a message) still passes

## 2. The shared predicate

- [x] 2.1 Add one side-effect-free predicate over `(skill, context)` that is true when the skill's parsed `effects` contain a `world.skills.effects.DamageEffect` instance and `context.battlefield is None`
- [x] 2.2 Place it where both `world/rules/action.py` and `world/rules/action_preview.py` can consume it without either importing the other, following how the two files already share the `usable_out_of_combat` condition's shape
- [x] 2.3 Document at the predicate that indirect hp movement (`SexualDrainEffect`) is deliberately excluded, matching `overwhelm-threshold`'s `commanded_damage_reaches_enemy()`

## 3. Resolver gate

- [x] 3.1 In `world/rules/action.py`'s capability step, evaluate the new gate immediately after the existing `usable_out_of_combat` check at line 310, marking it as the second sanctioned combat-state gate
- [x] 3.2 Reject with `RejectReason.DAMAGE_REQUIRES_MONSTER_TARGET` before any resource deduction, `roll_d100()` call, `PendingEffect` staging, or world-clock access
- [x] 3.3 Confirm the gate reads `context.battlefield` only and introduces none of the tokens `in_combat`, `is_combat`, `combat_state`, or `isinstance(context, Battlefield`
- [x] 3.4 Add the site comment explaining that the reason names the player-facing rule while the condition tests for the battlefield's absence

## 4. Preview mirror

- [x] 4.1 Apply the same predicate in `world/rules/action_preview.py` beside the existing `usable_out_of_combat` condition at line 141, in the same order
- [x] 4.2 Report disabled with the new reason so the shared preview and the combat-session submission revalidation agree with `ActionResolver.preflight()`

## 5. Tests

- [x] 5.1 Build a synthetic `SkillDef` carrying `damage:<element>:<school>` with `usable_out_of_combat=True`; assert `ActionResolver.resolve()` with a `RoomActionContext` rejects with the new reason and deducts no resource, rolls nothing, stages nothing, and reads no clock
- [x] 5.2 Assert the identical request with a `BattlefieldActionContext` is not gated and proceeds through the ordinary pipeline
- [x] 5.3 Assert a non-damaging `usable_out_of_combat=True` skill with a `RoomActionContext` is unaffected
- [x] 5.4 Assert a drain-only skill (pleasure into caster hp/mp/sp, no `DamageEffect`) with a `RoomActionContext` is not gated
- [x] 5.5 Assert gate order: a `DamageEffect` skill with `usable_out_of_combat=False` still reports `SKILL_NOT_USABLE_OUT_OF_COMBAT`
- [x] 5.6 Assert preview and `preflight()` report the same one of the two reasons for both the unflagged and the flagged synthetic skill
- [x] 5.7 Assert the gate is computed per request from the resolved `SkillDef`'s own effects and the request's own context — no registry-key enumeration, no dependence on how many skills currently declare `usable_out_of_combat=True`, so `skill-field-availability` cannot invalidate this test
- [x] 5.8 As a change-local verification only (not a test): confirm by inspection that no skill shipping at this commit both declares `usable_out_of_combat=True` and carries a `DamageEffect`, so this change is inert on landing. Record the finding in the commit message rather than pinning it in an assertion that a later change must delete
- [x] 5.9 Update `world/rules/tests/test_no_combat_branching.py` — the existing structural tripwire that currently encodes the one-gate contract and WILL fail on this change until updated: assert the only `context.battlefield` conditionals in `action.py` and `targeting.py` that distinguish combat from non-combat are the two named gates, and that the forbidden-token scan still finds nothing. Repoint its `covers_requirement` annotation at the modified requirement
- [x] 5.10 Annotate every new test with `covers_requirement` from `uv run --locked python -m tools.spec_traceability list`
- [x] 5.11 Prefer extending existing `world/rules/tests/` modules so `.github/evennia-shards.json` stays untouched; if a new module is unavoidable, register it in exactly one shard in this change

## 6. Verification

- [x] 6.1 `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb world.rules world.skills`
- [x] 6.2 `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb commands`
- [x] 6.3 `uv run --locked python -m tools.observability_lint check`
- [x] 6.4 `uv run --locked python -m tools.spec_traceability check`
- [x] 6.5 `uv run --locked python -m compileall -q world commands`
- [x] 6.6 `openspec validate out-of-combat-damage-gate --strict`
