## 1. First-actor override in the round loop

- [ ] 1.1 Add keyword-only `first_actor: str | None = None` to `world/rules/combat.py::run_round()`, documenting in the docstring that it reorders `roll_initiative()`'s returned sequence only — no re-roll, no extra action, no skipped combatant
- [ ] 1.2 Apply the override as a list reordering of `roll_initiative(battlefield)`'s result: move the named key to index 0 and keep every other key's relative order; a key absent from that sequence is a silent no-op
- [ ] 1.3 Confirm no new `roll_d100()` call and no alternative scoring path is introduced, and that `first_actor=None` leaves the `roll_initiative()` call site unchanged

## 2. Round-one forwarding in overwhelm resolution

- [ ] 2.1 Add keyword-only `first_actor: str | None = None` to `world/rules/overwhelm.py::resolve_overwhelm()` and `_resolve_overwhelm_raw()`
- [ ] 2.2 Forward it into `combat.run_round()` for the `rounds == 0` iteration only — reusing the existing round-one condition that captures the commanded-action marker window — and pass `None` for every later round
- [ ] 2.3 Preserve the existing default-forwarding discipline (`fix-dot-kill-credit` D4): with `first_actor=None` and every other policy flag defaulted, the call into `run_round()` must be exactly the pre-change call
- [ ] 2.4 Update `resolve_overwhelm()`'s docstring to state that the override affects turn order alone and never damage, verdicts, `rounds_elapsed`, or `total_seconds`

## 3. The commanded-damage pure query

- [ ] 3.1 Add `commanded_damage_reaches_enemy(battlefield, actor_key, skill_key, target_keys) -> bool` to `world/rules/overwhelm.py`, importing `DamageEffect` from `world.skills.effects`
- [ ] 3.2 Return `False` for a `skill_key` absent from `SKILL_REGISTRY`, without raising
- [ ] 3.3 Require both conditions: at least one `DamageEffect` instance among the skill definition's parsed `effects`, and at least one member of `target_keys` on the team opposing `battlefield.team_of(actor_key)`
- [ ] 3.4 Document that `target_keys` holds concrete roster keys only, that AREA-shorthand resolution belongs to the caller, and that a non-roster value fails closed to `False`
- [ ] 3.5 Confirm `classify_overwhelm()` does not call the new query and its verdict logic is untouched

## 4. Tests

- [ ] 4.1 Extend `world/rules/tests/test_initiative_and_turn_loop.py` (already registered in `.github/evennia-shards.json`): under a fixed seed, `run_round(first_actor=key)` resolves `key` first while the remaining combatants keep the relative order they hold under `first_actor=None`
- [ ] 4.2 Assert the override is order-only: the same seed with and without the override resolves exactly one action per capable combatant and the same multiset of acting keys
- [ ] 4.3 Assert `first_actor=None` is byte-identical to the omitted parameter — same final hp, same `EventLog` sequence including every `"roll"`-kind value, same acting order
- [ ] 4.4 Assert a dead, fled, knocked-out, and non-roster `first_actor` each leave the rolled order untouched and raise nothing
- [ ] 4.5 Assert `resolve_overwhelm()` forwards the override to round one and `None` to every later round (a recording `run_round` double or a captured call log), and that a default-mode call's forwarded arguments are unchanged
- [ ] 4.6 Assert `total_seconds == rounds_elapsed * 6` and every other `OverwhelmResult` field is unchanged for a stale override key versus `first_actor=None` under the same seed
- [ ] 4.7 Extend `world/rules/tests/test_overwhelm_threshold.py` with the `commanded_damage_reaches_enemy()` truth table: damage-at-enemy `True`; buff / heal / self-heal / cleanse / debuff-only / disguise / movement `False`; composite damage-plus-buff `True`; damage aimed at self, allies, or nothing `False`; `SexualDrainEffect`-without-`DamageEffect` `False`; unknown key `False`
- [ ] 4.8 Assert the query's purity by inspection and by repeated identical calls on unmutated state
- [ ] 4.9 Annotate every new test with `covers_requirement` from `uv run --locked python -m tools.spec_traceability list`
- [ ] 4.10 Prefer extending existing test modules so `.github/evennia-shards.json` stays untouched; if a new module is unavoidable, register it in exactly one shard in this change

## 5. Verification

- [ ] 5.1 `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb world.rules`
- [ ] 5.2 `uv run --locked python -m tools.observability_lint check`
- [ ] 5.3 `uv run --locked python -m tools.spec_traceability check`
- [ ] 5.4 `uv run --locked python -m compileall -q world`
- [ ] 5.5 `openspec validate combat-opening-seams --strict`
