## 1. Fields and construction

- [ ] 1.1 In `_build_from_baseline()`, unconditionally add all eleven counter traits (design.md D-1
      table) via `self._traits.add(<key>, trait_type="counter", base=0, min=0)` — no `max`, no
      baseline lookup; every entity starts every counter at `0`.

## 2. Properties and mutators

- [ ] 2.1 Add eleven read-only properties (`masturbation_count`, `toy_use_count`,
      `exposure_act_count`, `watched_count`, `duo_act_count`, `group_act_count`,
      `hostile_act_count`, `restraint_count`, `interspecies_act_count`, `climax_count`,
      `climax_extension_count`), each `return int(self._traits.<key>.value)`, matching
      `climax_today`'s existing property shape.
- [ ] 2.2 Add eleven mutators (`record_masturbation()`, `record_toy_use()`, `record_exposure_act()`,
      `record_watched()`, `record_duo_act()`, `record_group_act()`, `record_hostile_act()`,
      `record_restraint()`, `record_interspecies_act()`, `record_climax_count()`,
      `record_climax_extension()`), each `self._traits.<key>.base += 1`, matching `record_climax()`'s
      existing shape. Do **not** modify `record_climax()` or `climax_today` — they stay exactly as
      shipped.
- [ ] 2.3 Update `__all__` in `sexual_state.py` only if any new name needs to be importable elsewhere
      (none of the eleven mutators/properties are expected to need direct import by another module in
      this proposal's scope — confirm during implementation).

## 3. Tests

- [ ] 3.1 One test per the delta spec's six scenarios: zero-start for all eleven; a mutator affects
      only its own counter; repeated calls accumulate linearly; `reset_daily_counters()` leaves all
      eleven untouched; `climax_count`/`record_climax_count()` is independent of the existing
      `climax_today`/`record_climax()`; a structural test grepping (or AST-inspecting) every
      non-`sexual_state.py` module under `world/` and `commands/` for `._traits` access naming any of
      the eleven keys, following the existing `sexual_transitions.py`-inspection precedent
      (`sexual-transition-rulebook`'s "climax_today increments through record_climax(), never through
      SexualState's private handler" requirement's own test).
- [ ] 3.2 A single table-driven test iterating all eleven `(field, mutator)` pairs, calling each
      mutator once and asserting only its own field moved — this is the practical way to cover
      "affects only its own counter" for all eleven without eleven near-identical test functions,
      matching design.md D-3's stated preference for table-driven coverage over repetition.

## 4. Verification

- [ ] 4.1 Run `uv run --locked python -m tools.spec_traceability list` and confirm the requirement id
      for the new `sexual-state-handler` requirement; annotate the tests from section 3 with
      `@covers_requirement(...)` using the literal id.
- [ ] 4.2 Run the focused test module:
      `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb
      world.rules.tests.test_sexual_state`.
- [ ] 4.3 Run `uv run --locked python -m tools.spec_traceability check`.
- [ ] 4.4 Run `openspec validate sexual-counters --strict`.
- [ ] 4.5 Confirm `pleasure-gauge` (this proposal's dependency) is applied first, or that this
      proposal's diff applies cleanly on top of it — both edit `world/rules/sexual_state.py` and are
      sequenced, not concurrent.
