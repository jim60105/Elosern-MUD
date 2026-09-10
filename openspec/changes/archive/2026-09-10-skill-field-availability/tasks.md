## 1. Enumerate the current state

- [x] 1.1 Produce a one-off listing of every `SKILL_REGISTRY` entry with its key, kind, target spec, category, effect type names, and current `usable_out_of_combat` value, covering the hand-written definitions, every generated family, the sexual-act catalog, and `flee`
- [x] 1.2 Record which entries carry a `DamageEffect`, as the set that must end up `True`
- [x] 1.3 Keep the listing out of the repository — it is an audit aid, not an artifact

## 2. Apply the policy

- [x] 2.1 Judge every `ACTIVE` skill by the policy: `True` unless casting it with no fight in progress is meaningless or would bypass a subsystem that owns the outcome
- [x] 2.2 Set `usable_out_of_combat=True` on `basic_attack` in `world/skills/registry.py`
- [x] 2.3 Set `usable_out_of_combat=True` on every damage-carrying definition, editing the elemental-spell families at their shared builder where the judgement is uniform rather than row by row
- [x] 2.4 Give every `PASSIVE` entry a deliberate value at its construction site, including the generated `_body_multiplier` tiers
- [x] 2.5 Review `world/skills/sexual_acts/_builder.py`; keep `True` unless the audit finds a reason otherwise, and record the reason if it does
- [x] 2.6 Leave `flee` at `False` in `world/rules/disengage.py`, with a comment naming why (nothing to disengage from outside combat)
- [x] 2.7 Confirm no module mutates `usable_out_of_combat` on an already-constructed `SkillDef`

## 3. Frozen inventory test

- [x] 3.1 Add the frozen-inventory assertion in `world/skills/tests/`: the set of keys declaring `usable_out_of_combat=False` equals an explicit literal set enumerated in the test
- [x] 3.2 Make the failure message name every key that is in one set and not the other, so an undecided new skill is identified by key
- [x] 3.3 Add the companion assertion that every `DamageEffect`-carrying entry declares `True`
- [x] 3.4 Add a short comment in the test stating the policy the enumerated set encodes, so a future author applies the same judgement

## 4. Cross-capability assertions

- [x] 4.1 Assert `basic_attack` passes the `usable_out_of_combat` gate with a `RoomActionContext` and then rejects with `RejectReason.DAMAGE_REQUIRES_MONSTER_TARGET`, dealing no damage and spending no resource
- [x] 4.2 Assert one newly permitted elemental damage spell behaves the same way, demonstrating that the flag governs selection while the gate governs resolution
- [x] 4.3 Assert `flee` still reports `SKILL_NOT_USABLE_OUT_OF_COMBAT` outside combat
- [x] 4.4 Re-run `out-of-combat-damage-gate`'s test module unchanged: its assertions are per-request and registry-independent by construction, so this change must not require editing any of them — if one needs editing, that is a defect in the earlier change to fix there, not here
- [x] 4.5 Annotate every new test with `covers_requirement` from `uv run --locked python -m tools.spec_traceability list`
- [x] 4.6 Prefer extending existing `world/skills/tests/` modules so `.github/evennia-shards.json` stays untouched; if a new module is unavoidable, register it in exactly one shard in this change

## 5. Verification

- [x] 5.1 `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb world.skills`
- [x] 5.2 `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb world.rules commands`
- [x] 5.3 `uv run --locked python -m tools.spec_traceability check`
- [x] 5.4 `uv run --locked python -m compileall -q world`
- [x] 5.5 `openspec validate skill-field-availability --strict`
