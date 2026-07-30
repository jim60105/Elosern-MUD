## 1. Package layout

- [ ] 1.1 Confirm `world/rules/` exists with change 3's `traits.py` only; create
      `world/rules/rulebook/__init__.py` and `world/rules/tests/__init__.py` if either is missing.
- [ ] 1.2 Create `world/rules/rulebook/schema.py`, `world/rules/buffs.py`,
      `world/rules/combat_modifiers.py` as empty modules with module docstrings referencing design doc
      §3.2/§5.2/§6.4 and this change. `schema.py`'s docstring additionally states, per design.md D-2,
      that a future sexual-state rule table is expected to import this module's condition grammar and
      loader rather than reimplementing condition matching.
- [ ] 1.3 Confirm the `evennia.contrib.rpg.buffs` import path (`BuffHandler`, `BaseBuff`) against the
      installed Evennia 6.1.0, matching this project's established verify-before-trusting discipline
      (changes 1–5) — no code in this change should assume an unverified method name before this step.

## 2. Shared rule schema (`world/rules/rulebook/schema.py`)

- [ ] 2.1 Define the frozen `Rule` dataclass (`id: str`, `when: dict`, `then: dict`) per design.md D-2.
- [ ] 2.2 Implement `load_rules(path: Path) -> list[Rule]` per design.md D-2: parses a YAML list of
      `{id, when, then}` mappings; raises `MissingRuleIdError` if any entry lacks `id`; raises
      `DuplicateRuleIdError` if any two entries share an `id` within the same file.
- [ ] 2.3 Implement `evaluate_condition(when: dict, context: Mapping[str, Any]) -> bool` per design.md
      D-2, recognizing exactly: `event` (equality against `context["event"]`), `field` + `equals` /
      `field` + `gte` (comparison against `context[field]`, tolerating a missing key as
      "not satisfied," not `KeyError`), `field_changed` + `direction` (membership against
      `context["_changed"]`), `buff_active` (membership against `context["active_buffs"]`). Multiple
      condition keys in one `when` block combine with implicit AND. An unrecognized condition key
      raises, naming the key.
- [ ] 2.4 Confirm `evaluate_condition()` never inspects `then` and no function in this module branches
      on `then`'s contents — `then` stays a plain, opaque `dict` (design.md D-1's "shared `when`,
      table-owns-`then`" split).

## 3. Combat modifier table (`world/rules/rulebook/combat_modifiers.yaml`,
`world/rules/combat_modifiers.py`)

- [ ] 3.1 Author `world/rules/rulebook/combat_modifiers.yaml` per design.md D-3: `poison_agility_penalty`
      (`buff_active: poisoned` → `agility: "-10%"`), `paralysis_locks_actions` (`buff_active: paralysis`
      → `actions_per_turn: 0`), `fear_agility_and_accuracy_penalty` (`buff_active: fear` →
      `agility: "-15%", accuracy: -10`), `high_arousal_agility_accuracy_penalty` (`field: arousal, gte:
      高度` → `agility: "-20%", accuracy: -15`, transcribed verbatim from design doc §6.4),
      `climax_in_progress_locks_actions` (`field: climax_phase, equals: 進行中` → `actions_per_turn: 0`,
      also verbatim from §6.4). Every entry has a unique `id`.
- [ ] 3.2 Implement `_build_context(entity) -> dict` in `combat_modifiers.py` per design.md D-3: always
      sets `active_buffs` from `entity_active_buffs(entity)` (task 4.4); sets `arousal`/`climax_phase`
      only when `getattr(entity, "sexual", None)` is not `None`, tolerating change 3's current
      placeholder without raising.
- [ ] 3.3 Implement `evaluate_combat_modifiers(entity) -> dict` per design.md D-3: loads
      `combat_modifiers.yaml` once at module import via task 2.2's `load_rules()`; evaluates every rule
      against `_build_context(entity)` using task 2.3's `evaluate_condition()`; merges every matching
      rule's `then` into one bundle (later-evaluated matching rules combine with earlier ones rather
      than overwriting — define and document the merge rule for overlapping keys, e.g. percentage
      adjustments to the same field combine additively on the percentage, flat adjustments sum). This
      function MUST NOT assign to `entity.traits`, `entity.buffs`, `entity.db.*`, or any other
      attribute.
- [ ] 3.4 Confirm no conditional in `combat_modifiers.py` distinguishes a buff-origin rule from a
      sexual-field-origin rule when evaluating (design.md D-1/D-3's "no special-case branch"
      requirement) — a plain grep/read-through check, mirroring change 3's D-9 tripwire style.

## 4. Buff definitions and BuffHandler glue (`world/rules/rulebook/buffs.yaml`, `world/rules/buffs.py`)

- [ ] 4.1 Author `world/rules/rulebook/buffs.yaml` per design.md D-4: `poisoned` (duration 300, tick
      interval 10, stacking `refresh`, `modifiers.rate = {target: hp, delta: -5}`); `paralysis`
      (duration 30, stacking `refresh`, empty `modifiers`); `fear` (duration 60, stacking `refresh`,
      empty `modifiers`); `conferred_growth_rate` (duration `null`/permanent, stacking
      `unique_per_source`, `modifiers.rate = {target: magic_level_growth, scale_from_source: true}`).
- [ ] 4.2 Define `RulebookBuff(BaseBuff)` in `world/rules/buffs.py` per design.md D-4: one generic
      subclass parameterized by its own `key` looked up in the loaded `buffs.yaml` definitions at
      apply/tick time — no per-buff Python subclass. Confirm the exact `BaseBuff` hook names
      (`at_apply`/`at_tick`/`at_remove` or the installed contrib's actual equivalents) against Evennia
      6.1.0 before wiring (task 1.3).
- [ ] 4.3 Implement `_apply_rate_modifier(entity, rate_mod: dict) -> None` per design.md D-4
      (**fixed after review — was `NotImplementedError` for every non-trait target; now an explicit
      no-op for `magic_level_growth` specifically**): when `rate_mod["target"]` is one of
      `entity.traits`' gauge keys (`hp`/`mp`/`sp`), applies the delta via `TraitHandler`'s own Mod API
      (additive only, per change 3 D-7's `mod`-component boundary — confirm the exact API against the
      installed contrib); when `rate_mod["target"]` is in `_NO_OP_RATE_TARGETS` (currently exactly
      `{"magic_level_growth"}`), returns immediately without applying anything — its value is consumed
      by pull, through `growth_rate_multiplier()`/change 11b's `effective_magic_growth_multiplier()`,
      never by push on tick; applying it here too would double-apply the conferred scale. Document this
      directly in the function's docstring, naming `growth_rate_multiplier()`/change 11b as the actual
      reader, so a future edit does not "fix" this back into an active modifier. When the target is
      neither a known trait key nor in `_NO_OP_RATE_TARGETS` (e.g. a future `SexualState` field — no
      buff targets one yet, per change 7/8's own artifacts), still raises `NotImplementedError` naming
      the owning change, rather than silently no-op'ing an target this module has no documented reason
      to ignore.
- [ ] 4.4 Implement `entity_active_buffs(entity) -> set[str]` per design.md D-4: thin wrapper over
      `entity.buffs`'s own active-key accessor (confirm exact method name, e.g. `.all()`, against the
      installed contrib).
- [ ] 4.5 Implement `blocks_action(entity) -> bool` per design.md D-4: returns whether
      `entity_active_buffs(entity)` intersects a small, explicit `BLOCKING_BUFF_KEYS` set (`{"paralysis"}`
      at minimum for this change's seed set). No side effects.
- [ ] 4.6 Implement `grant_conferred_growth_rate(entity, source_key: str, scale: float) -> None` per
      design.md D-5: calls `entity.buffs.add("conferred_growth_rate", source_key=source_key,
      scale=scale)` (confirm `BuffHandler.add()`'s exact keyword-argument passthrough against the
      installed contrib). Performs no ownership or resource check, mirroring change 5's
      `grant_conferred()`.
- [ ] 4.7 Implement `growth_rate_multiplier(entity) -> float` per design.md D-5: iterates
      `entity.buffs`'s active buff instances, multiplies together the `scale` of every instance whose
      key is `conferred_growth_rate`, returns `1.0` if none are active. Pure query — no attribute writes.
- [ ] 4.8 Implement a plain buff-tick callable (e.g. `tick_buffs(entity)`) per design.md's Non-Goals:
      applies exactly one tick's worth of each active buff's `rate` modifier via task 4.3, invokable
      directly in a test with no `WorldClock`/scheduler present. Confirm neither this function nor any
      other in `buffs.py`/`combat_modifiers.py` references trait-regen scheduling or sexual-state decay
      scheduling, or imports a not-yet-existing `world/rules/sexual_state.py` or `WorldClock` class.
- [ ] 4.9 In `typeclasses/entities.py`, **replace** change 3's `buffs = AttributeProperty(default=None)`
      declaration with a real handler mount per design.md D-4:
      ```python
      @lazy_property
      def buffs(self):
          return BuffHandler(self)
      ```
      (confirm `evennia.utils.lazy_property` against however change 5 mounted `entity.skills`/
      `entity.equipment`, for consistency). `entity.buffs` is now read-only — no bare-assignment form,
      matching `entity.traits`/`entity.skills`/`entity.equipment`. Confirm the diff touches only the
      `buffs` declaration and no other attribute, method, or base class earlier changes authored.

## 5. Tests

- [ ] 5.1 `world/rules/tests/test_rulebook_schema.py` — per the `rulebook-schema` capability:
      `load_rules()` raises on a missing `id`, raises on a duplicated `id`, and loads successfully for a
      well-formed file; `evaluate_condition()` covers each condition kind (`event`, `field`+`equals`,
      `field`+`gte` against an orderable stand-in, `field_changed`+`direction`, `buff_active`), the
      implicit-AND combination of two condition keys in one `when` block, a missing context key
      returning `False` rather than raising, and an unrecognized condition key raising; a positive test
      confirms `load_rules()` accepts two rules with structurally different `then` shapes (a
      field-delta shape and a multi-key adjustment-bundle shape) without inspecting either.
- [ ] 5.2 `world/rules/tests/test_schema_docstring.py` (or folded into 5.1) — asserts
      `world/rules/rulebook/schema.py`'s module docstring names a future sexual-state rule table as an
      expected importer of its condition grammar and loader.
- [ ] 5.3 `world/rules/tests/test_combat_modifiers.py` — per the `combat-modifier-table` capability: one
      test function per buff-presence rule ID (`test_rule_poison_agility_penalty`,
      `test_rule_paralysis_locks_actions`, `test_rule_fear_agility_and_accuracy_penalty`), each
      constructing the minimal buff state that satisfies that one rule and asserting its exact `then`
      bundle appears in `evaluate_combat_modifiers()`'s output; a test asserting multiple simultaneously
      active rules merge into one bundle; a test asserting the function never mutates
      `entity.traits`/`entity.buffs` state across repeated calls; a test asserting an entity with
      nothing active returns an empty bundle.
- [ ] 5.3a `world/rules/tests/test_combat_modifiers.py` — **the unit-test half for the two sexual-field
      rules, which runs today and must not be confused with 5.3b's integration test.** Implement
      `test_rule_high_arousal_agility_accuracy_penalty` and
      `test_rule_climax_in_progress_locks_actions` by feeding `_build_context()` (or
      `evaluate_combat_modifiers()` directly, via a small test seam) a duck-typed stub object exposing
      `.arousal`/`.climax_phase` attributes — a plain fake, explicitly NOT a real `entity.sexual`,
      since `SexualState` does not exist yet — and assert the rule evaluates against the stub and
      produces the documented `then` bundle (`agility: "-20%", accuracy: -15` /
      `actions_per_turn: 0` respectively). This proves the condition grammar and the effect vocabulary
      for these two rules work now, independent of change 7. Also implement
      `test_high_arousal_rule_is_inert_without_sexual_state`, asserting neither of these two rules ever
      fires when `entity.sexual is None` (every entity's real state today, per change 3's placeholder).
- [ ] 5.3b `world/rules/tests/test_combat_modifiers_self_arming.py` — **the integration-test half,
      kept in its own module so neither half of this pair can be dropped without the omission being
      conspicuous.** Implement `test_high_arousal_rule_fires_once_sexual_state_exists`, guarded by
      `pytest.importorskip("world.rules.sexual_state")`: constructs a real entity with a real
      `entity.sexual` (once change 7 exists) whose `arousal` is at or above `高度`, and asserts
      `evaluate_combat_modifiers()` returns `high_arousal_agility_accuracy_penalty`'s bundle against the
      live object, not a stub. This test is expected to report **skipped** — not passed, not failed —
      for the entire lifetime of this change and until change 7 lands; see task 6.6 for the verification
      step confirming that.
- [ ] 5.4 `world/rules/tests/test_rule_id_test_correspondence.py` — the mechanical check per design.md
      D-7: walks `combat_modifiers.yaml`'s loaded rule IDs and asserts a `test_rule_<id>` function exists
      in `test_combat_modifiers.py` via `inspect.getmembers`; walks `buffs.yaml`'s buff keys and asserts a
      `test_buff_<key>` function exists in `test_buffs.py`. Fails naming any rule ID or buff key missing
      its corresponding test function.
- [ ] 5.5 `world/rules/tests/test_buffs.py` — per the `buff-handler-integration` capability: one test
      function per buff key (`test_buff_poisoned`, `test_buff_paralysis`, `test_buff_fear`,
      `test_buff_conferred_growth_rate`) exercising each buff's documented modifier behavior (`poisoned`:
      one tick reduces `hp` by its configured delta; `paralysis`/`fear`: applying and then querying
      `entity_active_buffs()`/`blocks_action()` reflects presence with no rate/bounds/decay side effect;
      `conferred_growth_rate`: applying via `grant_conferred_growth_rate()` and reading back via
      `growth_rate_multiplier()`, **and** ticking it via `tick_buffs()` per task 5.6a below);
      `entity.buffs` returns a `BuffHandler` instance and has no bare-assignment form; a grep-based
      assertion that neither `buffs.py` nor `combat_modifiers.py` assigns directly to `entity.buffs` or
      `entity.db.buffs`; a test asserting no buff definition in `buffs.yaml` configures a
      combat-stat-multiplier-shaped key.
- [ ] 5.6a `world/rules/tests/test_buffs.py::test_conferred_growth_rate_tick_is_a_no_op` — **the
      regression test for the reachability defect this review round fixed; kept as its own named test so
      it cannot be quietly dropped or folded away.** Constructs an entity, applies
      `grant_conferred_growth_rate(entity, source_key="elosia", scale=0.5)`, then calls `tick_buffs(entity)`
      and asserts (a) it completes without raising `NotImplementedError` or any other exception, and (b)
      `entity.traits.magic_level.value` is exactly unchanged before and after the call. This is the
      concrete regression change 11's `buff_ticks` settlement stage and change 11b's
      `effective_magic_growth_multiplier()` together made reachable — see design.md's Risks entry for
      this defect.
- [ ] 5.6 `world/rules/tests/test_conferred_growth_rate.py` (or folded into 5.5) — per design.md D-5/D-6:
      `grant_conferred_growth_rate(entity, source_key="elosia", scale=0.5)` followed by
      `growth_rate_multiplier(entity)` returns exactly `0.5`; an entity with no such buff returns `1.0`;
      `grant_conferred_growth_rate()` does not raise for an unknown `source_key`; a grep-based assertion
      that `world/rules/buffs.py` contains no dataclass resembling `ConferredRateGrant` — the mechanism
      is buff-instance-only.
- [ ] 5.7 `world/rules/tests/test_blocks_action.py` (or folded into 5.5) — `blocks_action()` returns
      `True` with `paralysis` active, `False` with only `fear` active, and has no observable side
      effect.
- [ ] 5.8 `world/rules/tests/test_buff_tick_seam.py` — invokes the buff-tick callable (task 4.8) directly
      with no clock/scheduler present and confirms it applies exactly one tick of `poisoned`'s rate
      modifier; a source-scan assertion (mirroring change 3's D-9 tripwire style) that neither
      `buffs.py` nor `combat_modifiers.py` references a settlement order, trait-regen scheduling, or
      imports `world.rules.sexual_state`/a `WorldClock` class.
- [ ] 5.9 `world/rules/tests/test_entity_mount.py` — confirms `typeclasses/entities.py`'s diff for this
      change touches only the `buffs` declaration (task 4.9), and that a freshly constructed
      `LivingEntity`'s `entity.buffs` is a working `BuffHandler` immediately, with no other attribute or
      base class altered.

## 6. Verification

- [ ] 6.1 Run the full `world/rules/tests/` suite added or extended by this change and confirm every
      test passes, except `test_high_arousal_rule_fires_once_sexual_state_exists` (task 5.3b), which is
      expected to report skipped rather than passed until change 7 lands — see task 6.5.
- [ ] 6.2 Confirm no function in `world/rules/buffs.py` or `world/rules/combat_modifiers.py` assigns to
      `entity.traits.<anything>.value`/`.base`/`.mod` except through `_apply_rate_modifier()`'s
      documented, additive-only Mod path (grep by hand, mirroring change 3's task 7.5 and change 5's
      task 8.2 discipline).
- [ ] 6.3 Confirm `world/rules/rulebook/combat_modifiers.yaml` and `world/rules/rulebook/buffs.yaml` each
      parse via `load_rules()`/the buff-definition loader with no `id`/`key` missing or duplicated.
- [ ] 6.4 Confirm every rule ID in `combat_modifiers.yaml` and every buff key in `buffs.yaml` has exactly
      one corresponding test function (task 5.4's mechanical check, run explicitly as part of this
      verification pass).
- [ ] 6.5 Run `world/rules/tests/test_combat_modifiers_self_arming.py` (task 5.3b) in isolation and
      confirm pytest reports `test_high_arousal_rule_fires_once_sexual_state_exists` as **skipped**,
      not passed and not failed, at this point in the roadmap (before change 7 exists). A pass here
      would mean the test is silently exercising something other than a real `SexualState` — the same
      failure mode change 4's D-5 self-arming pattern (the skill-registry pluggable check) explicitly
      guards against — and would indicate the test's `importorskip` guard is broken, not that the
      feature is somehow already done. This check is distinct from and does not replace 5.3a's
      always-runs unit test against the duck-typed stub.
- [ ] 6.6 Run `openspec validate buffs-rulebook --strict` and confirm it passes.
