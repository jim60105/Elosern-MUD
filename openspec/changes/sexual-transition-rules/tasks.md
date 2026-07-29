## 1. Dependency verification

- [ ] 1.1 Confirm `world.rules.rulebook.schema.Rule`/`load_rules`/`evaluate_condition` (change 6),
      `world.rules.sexual_state.SexualState`/`OrderedLevelTrait`/`_apply_climax_phase_set`/
      `SexualState.record_climax()` (change 7), and `entity.traits.sp` (change 3) are importable
      before writing any rule or interpreter code. `record_climax()` is already part of change 7's
      landed public surface — no coordination or additive patch to `sexual_state.py` is needed.
- [ ] 1.2 Create `world/rules/rulebook/sexual.yaml` and `world/rules/sexual_transitions.py` as empty
      scaffolds with module docstrings referencing design doc §6.4, this change, and change 7's D-7
      (inherited ambiguity analysis).

## 2. `then` effect vocabulary (`world/rules/sexual_transitions.py`)

- [ ] 2.1 Define `FIELD_KINDS` per design.md D-1: `arousal`/`wetness`/`shame`/`exposure` →
      `"ordered_level"`; `climax_phase` → `"ordered_level_cyclic"`; `sensitivity` →
      `"ordered_level_dict"`; `climax_today` → `"counter"`; `virgin` → `"flag_one_way"`;
      `experience_types` → `"append_only_set"`; `sp` → `"vital_gauge"` (D-8 — the one field this
      table targets outside `SexualState`).
- [ ] 2.2 Implement `_parse_delta(spec: str) -> int | tuple[int, int]` per design.md D-2: `"+N"`/
      `"-N"` → `int`; `"+N..+M"` → `(N, M)`; `"-M..-N"` (both negative, ascending, e.g. `"-30..-20"`
      for `sp_cost_on_climax`) → `(-M, -N)`; requires `lo <= hi` for any range form (raises
      otherwise); any other shape raises `ValueError` at rule-table load time, not at apply time.
- [ ] 2.3 Implement `_apply_then(entity, then: dict, context: dict, rng) -> tuple[str | None, str | None]`
      per design.md D-1, dispatching on `FIELD_KINDS[then["field"]]`:
      - `ordered_level`: resolve `delta` (via `_parse_delta`, drawing from `rng` for a range) or
        `set` (via `trait.levels.index(...)`, raising on an unrecognized level), write through
        `entity.sexual.<field>.value`.
      - `ordered_level_cyclic`: call `world.rules.sexual_state._apply_climax_phase_set(entity,
        then["set"])` — the only call site in this module referencing `climax_phase`'s value.
      - `ordered_level_dict`: read `context["part"]`, raising if absent; write through
        `entity.sexual.sensitivity[part].value`.
      - `counter`: call `entity.sexual.record_climax()` — never `entity.sexual._traits.climax_today`.
      - `flag_one_way`: `entity.sexual.virgin = then["set"]` (the setter's own irreversibility guard,
        change 7's D-2, does the rest).
      - `append_only_set`: `entity.sexual.add_experience_type(then["add"])`.
      - `vital_gauge`: resolve `delta` (via `_parse_delta`, drawing from `rng` for a range) and apply
        it to `entity.traits.<field>.value` — change 3's `TraitHandler`, never `entity.sexual`
        (design.md D-8). Relies on the trait's own configured floor to prevent a negative value; this
        branch adds no clamp of its own.
      Return `(field, direction)` for the caller's `_changed` bookkeeping, or `(None, None)` if the
      call was a guarded no-op (e.g. an invalid `climax_phase` transition).
- [ ] 2.4 Implement `_build_context(entity, event: str | None, changed: dict, event_context: dict) ->
      dict` per design.md D-3: live `arousal`/`wetness`/`shame`/`exposure`/`climax_phase` trait
      objects, plain `climax_today`/`virgin`/`experience_types` values, `_changed`, `event`, and
      `**event_context` merged in. (`sp` is not added to the context — no rule in this table
      conditions on it, only `sp_cost_on_climax`'s `then` writes it.)
- [ ] 2.5 Implement `apply_event(entity, event: str, *, rng=None, max_passes: int = 50,
      **event_context) -> dict` per design.md D-3: the fixed-point loop, clearing `event` after pass
      1, resetting `_changed` to only the immediately-preceding pass's deltas each iteration, and
      terminating when a pass produces zero changes. `rng` defaults to the `random` module and is
      injectable for deterministic tests.

## 3. `sexual.yaml` — the 25 rules (design.md D-4's catalog)

- [ ] 3.1 `arousal_up_on_stimulus` — `event: stimulus_applied` → `field: arousal, delta: "+1..+2"`
      (design doc §6.4's own worked example, transcribed verbatim).
- [ ] 3.2 `arousal_up_on_sustained_stimulus` — `event: sustained_stimulus_applied` →
      `field: arousal, delta: "+1"`.
- [ ] 3.3 `arousal_extreme_stimulus_to_max` — `event: extreme_stimulus_applied` →
      `field: arousal, set: 極限`.
- [ ] 3.4 `arousal_reset_after_climax` — `event: climax_ends` → `field: arousal, set: 微興奮`.
- [ ] 3.5 `wetness_follows_arousal` — `field_changed: arousal, direction: up` →
      `field: wetness, delta: "+1"` (design doc §6.4's own worked example, transcribed verbatim).
- [ ] 3.6 `wetness_up_on_direct_stimulus` — `event: direct_stimulus_applied` →
      `field: wetness, delta: "+1..+2"`.
- [ ] 3.7 `wetness_max_on_climax` — `event: climax_ends` → `field: wetness, set: 泛濫`.
- [ ] 3.8 `sensitivity_up_on_frequent_stimulation` — `event: frequent_stimulation` →
      `field: sensitivity, delta: "+1"` (part supplied by the event's own context, per design.md
      D-1's `ordered_level_dict` kind).
- [ ] 3.9 `climax_gate` — `field: arousal, equals: 極限` → `field: climax_phase, set: 接近` (design
      doc §6.4's own worked example, transcribed verbatim including its `id`).
- [ ] 3.10 `climax_phase_critical_point_to_in_progress` — `field: climax_phase, equals: 接近, event:
      stimulus_applied` → `field: climax_phase, set: 進行中` (change 7's D-7 exact carried-forward
      resolution for「達臨界點」).
- [ ] 3.11 `climax_phase_ends_to_afterglow` — `event: climax_ends` → `field: climax_phase, set: 餘韻`.
- [ ] 3.12 `climax_today_increment_on_climax` — `event: climax_ends` →
      `field: climax_today, delta: "+1"` (via change 7's `record_climax()`, task 1.1).
- [ ] 3.13 `virginity_once` — `event: first_vaginal_penetration` → `field: virgin, set: false` (change
      7's D-7 resolved, unqualified event; design doc §6.4's own worked example, transcribed
      verbatim).
- [ ] 3.14 `experience_vaginal_added` — `event: first_vaginal_penetration` →
      `field: experience_types, add: 陰道性交` (shares `virginity_once`'s exact event, per D-7).
- [ ] 3.15 `experience_masturbation_added` — `event: masturbation_climax` →
      `field: experience_types, add: 自慰`.
- [ ] 3.16 `experience_lesbian_added` — `event: penetrative_sex_with_female` →
      `field: experience_types, add: 女女性愛`.
- [ ] 3.17 `experience_titfuck_added` — `event: breast_sex_performed` →
      `field: experience_types, add: 乳交`.
- [ ] 3.18 `experience_watched_added` — `event: watched_during_activity` →
      `field: experience_types, add: 被觀看`.
- [ ] 3.19 `experience_exposure_added` — `event: public_exposure` →
      `field: experience_types, add: 露出`.
- [ ] 3.20 `experience_interspecies_added` — `event: sexual_activity_with_nonhuman` →
      `field: experience_types, add: 異種性愛`.
- [ ] 3.21 `shame_up_on_exposure_increase` — `field_changed: exposure, direction: up` →
      `field: shame, delta: "+1"`.
- [ ] 3.22 `shame_up_on_public_sexual_activity` — `event: public_sexual_activity` →
      `field: shame, delta: "+1"`.
- [ ] 3.23 `shame_up_on_watched` — `event: watched_during_activity` → `field: shame, delta: "+1"`
      (shares `experience_watched_added`'s event name, per design.md D-6.2).
- [ ] 3.24 `exposure_up_on_clothing_damaged` — `event: clothing_damaged_in_combat` →
      `field: exposure, delta: "+1"`.
- [ ] 3.25 `sp_cost_on_climax` — `event: climax_ends` → `field: sp, delta: "-30..-20"` (design.md
      D-8 — `當前狀態.體力值`'s 「高潮消耗20~30點」; the one rule targeting `entity.traits.sp` rather
      than a `SexualState` field).
- [ ] 3.26 Confirm every entry has a unique `id` and that `load_rules()` loads all 25 without error.

## 4. Tests — one per rule ID (`world/rules/tests/test_sexual_transitions.py`)

- [ ] 4.1 `test_rule_arousal_up_on_stimulus` — asserts `arousal`'s ordinal rises by the injected RNG's
      resolved value within `[1, 2]`.
- [ ] 4.2 `test_rule_arousal_up_on_sustained_stimulus` — asserts a fixed `+1`.
- [ ] 4.3 `test_rule_arousal_extreme_stimulus_to_max` — asserts `arousal.level == "極限"` regardless
      of starting level.
- [ ] 4.4 `test_rule_arousal_reset_after_climax` — asserts `arousal.level == "微興奮"` after
      `climax_ends`, starting from a higher level.
- [ ] 4.5 `test_rule_wetness_follows_arousal` — asserts `wetness` rises by `1` when an `arousal`-
      raising event fires, via the cascade, not a direct call.
- [ ] 4.6 `test_rule_wetness_up_on_direct_stimulus` — asserts `wetness` rises by the injected RNG's
      resolved value within `[1, 2]`.
- [ ] 4.7 `test_rule_wetness_max_on_climax` — asserts `wetness.level == "泛濫"` after `climax_ends`.
- [ ] 4.8 `test_rule_sensitivity_up_on_frequent_stimulation` — asserts the named part's sensitivity
      rises by `1`, and repeats the assertion for a second, differently-named part using the same
      rule, proving genericity (per the `sexual-transition-rulebook` capability's part-agnostic
      scenario).
- [ ] 4.9 `test_rule_climax_gate` — asserts `climax_phase.level == "接近"` when `arousal` reaches
      `極限`, and that firing again while already at `接近` (or from an invalid source phase) no-ops
      rather than erroring.
- [ ] 4.10 `test_rule_climax_phase_critical_point_to_in_progress` — asserts `進行中` is reached only
      when `climax_phase` is already `接近` and `stimulus_applied` fires; asserts no transition when
      `climax_phase` is at a different phase.
- [ ] 4.11 `test_rule_climax_phase_ends_to_afterglow` — asserts `餘韻` is reached from `進行中` on
      `climax_ends`.
- [ ] 4.12 `test_rule_climax_today_increment_on_climax` — asserts `climax_today` increases by exactly
      `1` per `climax_ends` call.
- [ ] 4.13 `test_rule_virginity_once` — asserts `virgin` becomes `False` on
      `first_vaginal_penetration`.
- [ ] 4.14 `test_rule_experience_vaginal_added` — asserts `"陰道性交"` is added to `experience_types`
      on the same event as task 4.13, in the same call.
- [ ] 4.15 `test_rule_experience_masturbation_added` — asserts `"自慰"` is added on
      `masturbation_climax`.
- [ ] 4.16 `test_rule_experience_lesbian_added` — asserts `"女女性愛"` is added on
      `penetrative_sex_with_female`.
- [ ] 4.17 `test_rule_experience_titfuck_added` — asserts `"乳交"` is added on
      `breast_sex_performed`.
- [ ] 4.18 `test_rule_experience_watched_added` — asserts `"被觀看"` is added on
      `watched_during_activity`.
- [ ] 4.19 `test_rule_experience_exposure_added` — asserts `"露出"` is added on `public_exposure`.
- [ ] 4.20 `test_rule_experience_interspecies_added` — asserts `"異種性愛"` is added on
      `sexual_activity_with_nonhuman`.
- [ ] 4.21 `test_rule_shame_up_on_exposure_increase` — asserts `shame` rises by `1` when an
      `exposure`-raising event fires, via the cascade.
- [ ] 4.22 `test_rule_shame_up_on_public_sexual_activity` — asserts `shame` rises by `1` on
      `public_sexual_activity`.
- [ ] 4.23 `test_rule_shame_up_on_watched` — asserts `shame` rises by `1` on
      `watched_during_activity`, independent of task 4.18's assertion on the same event.
- [ ] 4.24 `test_rule_exposure_up_on_clothing_damaged` — asserts `exposure` rises by `1` on
      `clothing_damaged_in_combat`.
- [ ] 4.25 `test_rule_sp_cost_on_climax` — asserts `entity.traits.sp.value` decreases by the injected
      RNG's resolved value within `[20, 30]` on `climax_ends`, and asserts a second case where `sp`
      starts below the resolved cost stops at the gauge's own floor rather than going negative.

## 5. Structural and cross-cutting tests

- [ ] 5.1 `test_every_rule_id_has_a_test()` — per design.md D-7: walks `sexual.yaml`'s loaded rule
      IDs, asserts a `test_rule_<id>` function exists via `inspect.getmembers`, and asserts no
      `test_rule_<id>` function exists for an `id` not present in `sexual.yaml`.
- [ ] 5.2 `test_field_kinds_covers_every_targetable_field()` — per design.md D-7: asserts
      `FIELD_KINDS`'s key set equals exactly the set of `then.field` values used anywhere in
      `sexual.yaml` — now including `sp` (D-8), the one field outside `SexualState`.
- [ ] 5.3 `test_virginity_once_is_irreversible()` — per hard requirement 4: fires
      `first_vaginal_penetration` via `apply_event()` twice in sequence, and separately attempts a
      direct `entity.sexual.virgin = True` afterward; asserts `virgin` is `False` after every
      attempt.
- [ ] 5.4 `test_experience_types_only_grows()` — per hard requirement 4: fires two distinct
      experience-triggering events, then re-fires one of them; asserts the resulting set strictly
      grows across the sequence and never loses or duplicates an entry.
- [ ] 5.5 `test_climax_phase_rules_route_through_guard()` — a source-inspection test (mirroring
      change 7's own task 8.2 discipline) asserting `sexual_transitions.py` contains no reference to
      `.climax_phase.value =` or `._traits.climax_phase` outside the one call site invoking
      `_apply_climax_phase_set()`.
- [ ] 5.6 `test_climax_today_never_touches_private_traits()` — a source-inspection test asserting
      `sexual_transitions.py` contains no reference to `entity.sexual._traits` at all (broader than
      5.5 — covers every field, not only `climax_phase`).
- [ ] 5.7 `test_fixed_point_loop_terminates_on_a_synthetic_oscillation()` — per design.md's Risks
      section: constructs two throwaway, mutually-triggering rules against a private rule list (not
      `sexual.yaml` itself) and asserts `apply_event()`'s loop terminates at `max_passes` rather than
      hanging.
- [ ] 5.8 Confirm no rule in `sexual.yaml` references a race/species condition or targets a
      narrative-only field (身體感受, 興奮要素, 被注視感受, 最後性活動, 基本資訊.狀態) — a plain
      read-through of the loaded rule table, per the `sexual-transition-rulebook` capability's
      exclusion requirement.
- [ ] 5.9 `test_sp_cost_never_reaches_through_entity_sexual()` — a source-inspection test asserting
      the `vital_gauge`-kind branch of `_apply_then()` references `entity.traits.<field>.value` only,
      with no reference to `entity.sexual` anywhere in that branch (design.md D-8).
- [ ] 5.10 Confirm no rule in `sexual.yaml` models `疲勞狀態`'s action-efficiency threshold (`≤30點時
      所有行動效率降低`) — a plain read-through of the loaded rule table, per design.md D-9 and the
      `sexual-transition-rulebook` capability's exclusion requirement naming change 6 as the owner of
      that future `combat_modifiers.yaml` row.

## 6. Final verification

- [ ] 6.1 Run the full `world/rules/tests/` suite added by this change and confirm every test
      passes.
- [ ] 6.2 Confirm no edit was made to any file owned by change 3, change 6, or change 7
      (`entity_traits.py` or equivalent, `schema.py`, `combat_modifiers.yaml`/`.py`,
      `buffs.yaml`/`.py`, `sexual_state.py`) — this change reads `entity.traits.sp`,
      `SexualState`'s public surface (including `record_climax()`), and change 6's rule-loading
      machinery only, without modifying any of them.
- [ ] 6.3 Confirm `world/rules/sexual_transitions.py` contains no `ActionResolver`, targeting,
      combat-resolution, or `WorldClock` reference — those remain changes 8, 9, and 11's scope. Also
      confirm it contains no `combat_modifiers.yaml`-shaped threshold-and-modifier-bundle rule — that
      remains change 6's scope (design.md D-9).
- [ ] 6.4 Run `openspec validate sexual-transition-rules --strict` and confirm it passes.
