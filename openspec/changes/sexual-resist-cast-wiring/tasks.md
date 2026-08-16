## 1. Confirm the dependency surface this change reads

- [ ] 1.1 Confirm `world/rules/sexual_resist.py`'s `resist_verdict(actor, resister, *, rng=roll_d100) ->
  ResistVerdict` signature and `ResistVerdict(resisted, auto_comply, roll, actor_score, resister_score)`
  shape are unchanged from design.md's Context excerpt.
- [ ] 1.2 Confirm `world/rules/combat_session.py`'s `_scan_sexual_coercion` still reads
  `entry.kind == "sexual_resist"`, `entry.data.get("resisted")`, `entry.data.get("auto_comply")`, and
  `entry.target` exactly as documented in its own docstring — this proposal's emitted `EventEntry` must
  match that contract verbatim, with zero change to `combat_session.py` itself.
- [ ] 1.3 Confirm `world/skills/sexual_acts/_builder.py`'s `SexualActDef.resistible: bool` field and
  `world/skills/sexual_acts/__init__.py`'s `SEXUAL_ACT_REGISTRY` (keyed identically to `SKILL_REGISTRY`)
  are unchanged.
- [ ] 1.4 Confirm `world/rules/action.py`'s `_step3_targeting`, `_handle_pleasure_effect`,
  `_handle_sexual_counter_effect`, `_entries_from_effect`, `_ENTRY_TEMPLATES`, and
  `ActionResolver.resolve()` match design.md's Context/D-1 excerpts. If any have changed shape since this
  proposal was written, re-open the affected Decision before writing code.
- [ ] 1.5 Confirm `world/rules/combat.py`'s existing `from world.rules.dice import roll_d100` /
  `test_combat_party.py`'s `patch("world.rules.combat.roll_d100", ...)` pattern (design.md D-6) is still
  the live convention for mocking dice rolls in this codebase.

## 2. Wire the resist gate into `world/rules/action.py`

- [ ] 2.1 Add `from world.rules.dice import roll_d100` and `from world.rules.sexual_resist import
  resist_verdict` to `action.py`'s top-level imports (design.md D-6).
- [ ] 2.2 Add `_resist_pending_effect(target, verdict) -> PendingEffect` per design.md D-3: description
  `f"sexual_resist|{_entity_key(target)}|{int(verdict.resisted)}|{int(verdict.auto_comply)}|{roll_field}"`
  with `roll_field = "none" if verdict.roll is None else str(verdict.roll)`, `surfaces=frozenset()`,
  `apply=lambda: None`.
- [ ] 2.3 Add `_step4b_sexual_resist_gate(request, skill, targets) -> tuple[list[Any], list[PendingEffect]]`
  per design.md D-1's quoted implementation: look up `SEXUAL_ACT_REGISTRY.get(skill.key)`; return
  `(targets, [])` unchanged when absent or `resistible` is falsy; otherwise loop `targets`, skip the actor
  (design.md D-2), call `resist_verdict(request.actor, target, rng=roll_d100)` for every other entry,
  stage one `_resist_pending_effect` per call, and keep only non-resisted targets in the returned list.
- [ ] 2.4 In `ActionResolver.resolve()`, call `targets, resist_pending = _step4b_sexual_resist_gate(request,
  skill, targets)` immediately after `_step4_capability(request.actor)`, **rebinding** `targets` itself
  rather than introducing a second `filtered_targets` name (design.md D-1) — every later use of `targets`
  in `resolve()`, including `_step5_effect_resolution` and `_step6_combat_kill_xp`, then unambiguously
  sees the post-resist list with no risk of a future edit picking the wrong variable. Prepend or append
  `resist_pending` into the `pending` list alongside the handler output before `_step7_build_event_log`
  runs, so the resist entries appear in the built `EventLog`.
- [ ] 2.5 Add `"sexual_resist"` to `_ENTRY_TEMPLATES` with narrative Traditional Chinese text handling
  both outcomes without leaking raw data keys and without interpolating `{data[roll]}` directly (`roll`
  is `None` for an auto-complied verdict, and `str.format` would render the literal text `"None"`) — e.g.
  `"{target} 面對 {actor} 的意圖，做出了自己的選擇。"`. **This step must land before 2.6**:
  `_entries_from_effect`'s first line rejects any `kind` absent from `_ENTRY_TEMPLATES` before any `elif`
  branch runs (design.md D-3), so skipping this step makes every resistible-act cast reject outright.
- [ ] 2.6 Add an `elif kind == "sexual_resist":` branch to `_entries_from_effect` parsing the three
  trailing `|`-delimited values (after `kind`/`target`) into `data={"resisted": bool(int(values[0])),
  "auto_comply": bool(int(values[1])), "roll": None if values[2] == "none" else int(values[2])}`, raising
  `ValueError` on a malformed description exactly as the `pleasure_gain`/`sexual_counter` branches already
  do for their own arity.

## 3. Behaviour tests for the delta spec

- [ ] 3.1 Run `uv run --locked python -m tools.spec_traceability list` and note the canonical requirement
  IDs for `sexual-resist-cast-wiring::*` from this change's delta spec.
- [ ] 3.2 Add `world/rules/tests/test_sexual_resist_cast_wiring.py` (new `EvenniaTest`-based module)
  covering, with `patch("world.rules.action.roll_d100", return_value=<n>)` for determinism:
  - Casting `combat_tease` (the one shipped `resistible=True` `SINGLE` act) against an NPC target forced
    into a losing contest (mock the roll and/or affinity stage so `resisted=True`) leaves the target's
    `pleasure` and counters unchanged, and the cast still returns `outcome == "success"`.
  - The same cast forced into a winning contest (`resisted=False`) applies the target's pleasure/counter
    effects exactly as an equivalent `resistible=False` act would.
  - The actor's own `hostile_act_count` and pleasure share are credited identically in both branches
    (design.md D-5).
  - Exactly one `sexual_resist`-kind `EventEntry` appears in the result's `event_log.entries` per cast,
    with `target` equal to the target's `str(target.key)` and `data` containing exactly `resisted`,
    `auto_comply`, `roll`.
  - An `auto_comply=True` verdict (mock `resist_verdict` directly, or drive an NPC affinity stage into an
    auto-comply stage) logs `data["roll"] is None`.
  - A non-resistible sexual act (e.g. `solo_self_touch`, `resistible=False`) and a non-sexual-act skill
    never call `resist_verdict` (patch it and assert `assert_not_called()`), proving the gate's
    early-return path. Do not use `partner_caress`/`partner_hand_hold`/`combat_tease` for this case — all
    three are `resistible=True` (design.md D-3a).
  - A synthetic two-target `AREA` `resistible=True` act (build one inline via `_act_family()` the way
    `test_acceptance.py`'s existing synthetic-act pattern does, not by editing any shipped catalog module)
    resolves one independent contest per target, and a target-specific losing roll excludes only that
    target from the act's effects while the other target and the actor are unaffected.
- [ ] 3.3 Apply `covers_requirement("sexual-resist-cast-wiring::<id>")` (using the IDs from 3.1) to each
  test function whose assertions establish that requirement.
- [ ] 3.4 Run `uv run --locked python -m tools.spec_traceability check` and confirm every
  `sexual-resist-cast-wiring` requirement is covered.

## 4. Regression verification against already-shipped resist-adjacent code

- [ ] 4.1 Update `world/skills/sexual_acts/tests/test_seed_acts.py::
  test_partner_seed_increments_duo_act_count_on_both_participants` to wrap its `partner_caress` cast in
  `with patch("world.rules.action.roll_d100", return_value=<a value forcing resisted=False>):` (design.md
  D-3a) — this is a genuine, required fix, not an optional hardening; without it this test becomes flaky
  the moment task 2 lands. Confirm the mocked value actually forces compliance against this test's
  fixture's default agility/affinity scores rather than assuming any particular roll works.
- [ ] 4.2 Re-run `world/skills/sexual_acts/tests/test_seed_acts.py` in full (including the fix from 4.1)
  and confirm every assertion passes deterministically — `test_combat_tease_increments_hostile_act_count_
  on_actor_only` and `test_self_cast_rejection_credits_no_counters_on_either_seed` need no code change
  (design.md's Risks section explains why) but re-run them at least twice each to catch any reliance on a
  lucky roll this proposal's static analysis missed.
- [ ] 4.3 Re-run `world/rules/tests/test_combat_session_sexual_coercion.py` (B6b's suite) unmodified and
  confirm it still passes — this proposal must not require any change to that file.
- [ ] 4.4 Re-run `world/rules/tests/test_sexual_resist.py` (`B6a`'s own `resist_verdict()` tests) unmodified
  and confirm they still pass — this proposal must not require any change to `sexual_resist.py`.

## 5. Full verification

- [ ] 5.1 Run `uv run --locked evennia test --settings test_settings.py --keepdb world.rules.tests
  world.skills.tests` and confirm the whole combined suite passes.
- [ ] 5.2 Run `uv run --locked python -m compileall -q world`.
- [ ] 5.3 Run `openspec validate sexual-resist-cast-wiring --strict` and resolve any reported issue.
- [ ] 5.4 Confirm no file outside `world/rules/action.py`, the new
  `world/rules/tests/test_sexual_resist_cast_wiring.py`, and the one-test edit to
  `world/skills/sexual_acts/tests/test_seed_acts.py` (task 4.1) was touched, matching the proposal's
  Impact list exactly — in particular, confirm `world/rules/sexual_resist.py`,
  `world/rules/combat_session.py`, `world/skills/sexual_acts/_builder.py`, and every
  `world/skills/sexual_acts/*.py` catalog module (not its `tests/` subpackage) have zero diff from this
  change.

## 6. Update the overview design document

- [x] 6.1 Add a new row to `docs/superpowers/specs/2026-08-15-sexual-act-system-overview-design.md` §4.2's
  Proposals table for `sexual-resist-cast-wiring`, following this proposal's final Impact section for the
  "Files owned exclusively" column and `B5, B6a, B6b` for "Depends on". Done at proposal-writing time,
  ahead of implementation — verify it is still accurate against this proposal's final state before
  archiving.
- [x] 6.2 Add a short prose note (near the existing `sexual-resist-out-of-combat` entry, matching that
  passage's terse, evidence-dense style) explaining that `B5`'s row's emission obligation was not actually
  fulfilled and that this proposal picks it up, citing the exact `B5` Non-Goals quote and the `B6b`
  design.md quote this proposal's own Why section cites — without rewriting `B5`'s row's original
  historical claim. Done at proposal-writing time; also added a `9 (unscheduled)` row to §4.3's batch
  table and updated the intro paragraph's follow-up count from one to two.
