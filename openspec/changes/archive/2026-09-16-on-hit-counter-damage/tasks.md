## Batch order (earth wave — integration contract in ../terrain-marker/design.md D4/D5)

0. Predecessors: none in content — this change owns the `physical_hit` event and the
   source-targeted then-actions. SEQUENCING: merge AFTER `terrain-marker` — the two are
   file-disjoint except the shared `world/rules/combat.py` `_handle_damage` (this change's
   `physical_hit` dispatch leg in the staged `apply()`; that change's `unconditional_defense_bypass`
   read at the policy-decision hunk — disjoint hunks, same function). `earth-spell-catalog`
   is strictly after BOTH merge and authors data only (fire's future `scorching_armor` is later
   data over this same vocabulary — zero new trigger events).

## 1. Event vocabulary and load validation

- [x] 1.1 Inspect current source/exported references (codegraph/LSP) for `validate_state_reaction_rules`, `dispatch_outcome_reaction` and all its callers, `_handle_damage`'s staged `apply()` (school parse, `actual_loss` gate, nonlethal threading), `evaluate_combat_modifiers`/`_adjusted_defense`, and the public `apply_buff` attribution contract before editing.
- [x] 1.2 INTRODUCTIONALLY CLOSE the `when.event` value vocabulary — today only `when` keys are validated and unknown event values load silently as never-firing rules: add the closed enum {`hp_loss`, `mp_zero`, `negative_buff_added`, `physical_hit`} to `validate_state_reaction_rules`, rejecting any other value naming the rule id (the three shipped values keep loading unchanged); grow the `then` vocabulary to exactly one-of {`apply_buff`, `remove_buff`, `pleasure_gain`, `counter_damage`, `apply_buff_to_source`} with fail-closed validation: `counter_damage` finite positive number (bool rejected), `apply_buff_to_source` must name a `BUFF_DEFINITIONS` key; update the `state_reactions.yaml` header comment's vocabulary doc. This change ships ZERO live rules (catalog owns data).

## 2. Dispatch site

- [x] 2.1 In `_handle_damage`'s staged `apply()`, after the existing `actual_loss > 0` → `hp_loss` dispatch, additionally dispatch `dispatch_outcome_reaction(target, "physical_hit", source=actor, source_tier=…, source_skill=…)` ONLY for a physical-school landing strike with positive actual loss — one dispatch per landing strike, `hp_loss` first and byte-identical, magic/miss/zero-loss/rate-tick paths dispatch nothing new. Thread the initiating event context's nonlethal facts (session flag, protected key set, battlefield handle) into the dispatch context.

## 3. Source-targeted executors

- [x] 3.1 `counter_damage`: settle `max(0, round(holder effective atk_phys × coefficient) − adjusted defense(source))` onto the event source inside the same commit pass — no hit roll/crit/accuracy; dispatch the source's ordinary `hp_loss` exactly once for its actual loss; NEVER dispatch `physical_hit` from the counter leg (plus a settled-counter guard flag in the dispatch context as belt); dead/unresolvable source → silent no-write; protected source floors at 1 with the existing knockout mark path; never revives.
- [x] 3.2 `apply_buff_to_source`: apply the named definition to the source through the shipped public `apply_buff` entry with event-source-derived grant attribution and the event's tier; immunity no-write and refresh stacking ride the shipped entry unchanged; the new-instance `negative_buff_added` dispatch fires once and cannot recurse into `physical_hit`.

## 4. Behavioral evidence and integration

- [x] 4.1 Synthetic behavior module (suggested `world/rules/tests/test_on_hit_counter_damage.py`): landed physical strike fires the rule once with the source attached; magic/miss/zero-loss/rate-tick silence; per-strike dispatch on a double-strike policy; thorn-shaped counter priced at effective-attack × coefficient minus defense floored at the damage floor exactly once with the attacker's `hp_loss` reactions firing once; mutual thorn-holders settle one counter per initiating strike (no chain); late commit failure rolls the counter HP back with the initiating loss; ignite-shaped `apply_buff_to_source` live instance + attribution vs immune attacker vs sourceless write; dead-source silence; protected-source counter floors with one terminal settlement; the full malformed-load matrix (unknown `when.event` value, `counter_damage: -1`/`abc`/boolean, unknown buff key, two actions in one `then`, mixed legacy+source action) each naming the rule id.
- [x] 4.2 Existing-reaction regression kept honest: `hp_loss`/`mp_zero`/`negative_buff_added` dispatch order and payloads unchanged (existing suites green without edits unless one pins something the widened enum legitimately changes — behavior-first rule applies). No data-echo, key-set or row-mirror assertions anywhere (ratified NON-GOAL).
- [x] 4.3 Register each new non-browser test module in exactly one shard in `.github/evennia-shards.json`; verify the ownership optimization contract test.
- [x] 4.4 Run the focused labels below after editing stops; `tools.observability_lint check` in the same batch; `tools.test_data_lint check`; `tools.spec_traceability check`; `openspec validate on-hit-counter-damage --strict`. Canonical IDs via `uv run --locked python -m tools.spec_traceability list` at the separately authorized main-sync; annotate exactly the tests establishing `damage-state-feedback::a-qualifying-physical-strike-dispatches-one-source-attributed-on-hit-event` and `damage-state-feedback::source-targeted-reaction-actions-settle-once-in-transaction-without-recursion`.

### Focused invocation

```sh
uv run --locked evennia test --settings test_settings.py --keepdb world.rules.tests.test_on_hit_counter_damage world.rules.tests.test_damage_state_feedback world.rules.tests.test_phase_spell_reactions world.rules.tests.test_mp_flow world.rules.tests.test_rulebook_schema
uv run --locked python -m tools.observability_lint check
uv run --locked python -m tools.test_data_lint check
uv run --locked python -m tools.spec_traceability check
uv run --locked openspec validate on-hit-counter-damage --strict
```

Pass `MUD_TEST_SETTINGS=1` through the tool environment, never a shell prefix. `world.rules.tests.test_on_hit_counter_damage` is the intended synthetic module owned by this change, not an existing-test claim (tasks 1.1 confirms the shipped reaction-test module names; adjust the label list to the actual modules, never claiming an edit to a non-existent file). No full local suite/browser/aggregate-coverage run; no command above ten minutes. No apply, archive, main-spec sync or merge in the proposal turn.
