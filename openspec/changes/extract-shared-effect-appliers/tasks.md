# Tasks: extract-shared-effect-appliers

Design decisions referenced below live in `design.md` (D1–D5).

## 1. Extract the pleasure entry points

- [ ] 1.1 Create `world/rules/pleasure.py` and move `_apply_pleasure_gain` into it as
  `apply_pleasure_gain` (D1, D2). Do **not** move `_apply_climax_phase_set`: it lives in
  `world/rules/sexual_state.py:853` and is already imported by `action.py:48` and
  `sexual_transitions.py:14`; `pleasure.py` imports it the same way. Verify the new module imports
  cleanly and pulls in nothing from `world/rules/action.py`.
- [ ] 1.2 Move the body **unedited** — no reordering, no extraction, no signature change (D2). Verify
  the `sexual-act-effects` source-inspection scenario still passes after being pointed at the new
  location: the arousal-ordinal and climax-phase captures are still the first two statements.
- [ ] 1.3 Move `_zero_pleasure` (`world/rules/action.py:1380`) into the same module as
  `zero_pleasure`, unedited and unmerged with the gain entry (D2b). Verify `_handle_sexual_drain`
  still zeroes a target sitting at 接近 **without** advancing their climax phase to 進行中 — the
  behavior that folding it into `apply_pleasure_gain` would have broken.
- [ ] 1.4 Update all six production call sites to the imported names: `action.py:962`, `:1101`,
  `:1102`, and `world/rules/defeat_aftermath.py:926`, `:928`, `:1499` — the last three currently
  import the private name across a module boundary (`defeat_aftermath.py:47`). Update the nine call
  sites in `world/rules/tests/test_sexual_act_effects.py`. Verify
  `grep -rn "_apply_pleasure_gain\|_zero_pleasure"` returns zero hits repository-wide.
- [ ] 1.5 Add the no-bypass structural test: every assignment to `entity.sexual.pleasure.base` or
  `.value` in the deterministic core lives in `world/rules/pleasure.py` — module-scoped, not
  function-scoped, because two writers legitimately exist (D2b). Verify it passes — this is the
  `sexual-act-effects` delta's first ADDED scenario.
- [ ] 1.6 Add the non-cast-caller test: importing `world/rules/pleasure.py` does not pull in the cast
  pipeline, and an applied gain produces the identical cascade a cast produces for the same magnitude.

## 2. Publish the buff-application entry point

- [ ] 2.1 Rename `buffs._add_buff` to `buffs.apply_buff` and update its in-module callers. Verify both
  grant-time guards are untouched: the equipment-immunity early return and the `unique_per_source`
  source-key raise (D-note in design; the guards are the reason the function is published at all).
- [ ] 2.2 Add tests for both guards reached through the public name: an immunized debuff writes
  nothing and leaves the active set unchanged; a `unique_per_source` definition with no `source_key`
  raises. These are the `buff-handler-integration` delta's first two scenarios.
- [ ] 2.3 Add the structural test that no module outside `world/rules/buffs.py` calls
  `entity.buffs.add(...)` directly. Verify it passes against the current tree.

## 3. Add selector-driven status removal

- [ ] 3.1 Implement `buffs.remove_by_selector(entity, selector) -> int` accepting a concrete
  definition key or `all` / `positive` / `negative`, resolving against live buff **instances**
  (`buff.buffkey`) exactly as `cleanse_debuffs` does today, removing through the existing
  `dispel=True` path, and returning the count (D3). Verify it fails closed on an unrecognized
  selector.
- [ ] 3.2 Re-express `cleanse_debuffs()` as `remove_by_selector(entity, "negative")` (D3). Verify
  `world/rules/tests/test_holy_water_cleanse.py` and the cleanse-handler tests pass unchanged — the
  shipped call sites are not edited.
- [ ] 3.3 Add tests for all five scenarios in the `cleanse-effect-handler` delta's ADDED requirement:
  `negative`, `positive`, `all`, a concrete key with two live instances of one definition, and an
  empty match returning `0`.
- [ ] 3.4 Add a startup assertion that no `buffs.yaml` definition key collides with a selector word
  (`all`, `positive`, `negative`), so the ambiguity can never be introduced later (design Risks).
  Verify by temporarily adding such a key and confirming the load fails.

## 4. Verification

- [ ] 4.1 Run the deterministic suite — `test_effect_handlers.py`, `test_sexual_act_effects.py`,
  `test_climax_settlement.py`, `test_sexual_transitions.py`, `test_buffs.py`,
  `test_holy_water_cleanse.py`, `test_divine_mystery_gate.py`, and the defeat-aftermath suites — and
  verify every assertion passes with no assertion text changed. An assertion that needed editing means behavior moved.
- [ ] 4.2 Run `openspec validate extract-shared-effect-appliers` and the repository's
  lint/observability gate; verify both pass.
