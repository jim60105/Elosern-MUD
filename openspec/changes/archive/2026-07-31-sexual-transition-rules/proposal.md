## Why

This is roadmap item #7b (design doc §11), depending on change 7 (`sexual-state`, which built
`OrderedLevelTrait`, the `SexualState` handler, and `_apply_climax_phase_set()` but authored no
transition rule) and change 6 (`buffs-rulebook`, which built the shared declarative condition
grammar in `world/rules/rulebook/schema.py` — `Rule`, `load_rules()`, `evaluate_condition()` — and
left an explicit handoff for this table to import rather than reinvent). Change 7 exists but is
inert: `entity.sexual` decays and clamps on its own, but nothing a player or the generative layer
does can move it, because no `rulebook/sexual.yaml` exists and no interpreter reads one. This change
transcribes `tmp/story_settings/variable_rule.md`'s `性狀態.*` behavioural spec into that missing
table, giving `entity.sexual` its only way to actually change in response to play.

**This change was split from change 7's original, larger scope during review** specifically because
the rule-plus-test surface (~25 rules, one test each, plus the structural correspondence and
coverage checks) was judged to fill a full working day on its own. Change 7's design doc D-7
preserves the `variable_rule.md` ambiguity/self-contradiction analysis already done during that
first pass, explicitly as this change's starting point; this proposal inherits those resolutions
rather than re-deriving them, and documents only the handful of additional ambiguities D-7 did not
already cover.

**Post-review addendum.** A coordinator review of the initial 24-rule draft found one genuine
coverage gap: `variable_rule.md`'s `當前狀態.體力值` section couples a sexual event (climax) to a
non-`SexualState` field (`sp`, change 3's stamina gauge) — the only line in the source spec where a
*sexual* event drives a *non-sexual* field, which is exactly why `FIELD_KINDS`' own coverage check
(scoped to the fields the draft's rules already targeted) could not catch it. This is now rule 25,
`sp_cost_on_climax` (design.md D-8), and a companion exclusion — the source's adjacent
`疲勞狀態` action-efficiency threshold — is recorded with change 6 named as its correct owner
(design.md D-9) rather than left to fall between this change and change 7's scope unnamed.

## What Changes

- Add `world/rules/rulebook/sexual.yaml`: 25 declarative transition rules covering every
  behaviourally-meaningful (non-narrative, non-race-specific) line of `variable_rule.md`'s
  `性狀態.*` section — `arousal`, `wetness`, `shame`, `exposure`, `climax_phase`, `climax_today`,
  `virgin`, `experience_types`, `sensitivity` — plus one line of `當前狀態.體力值` whose trigger is a
  sexual event (`sp_cost_on_climax`, design.md D-8). Every rule carries the unique `id` change 6's
  `load_rules()` already requires. Race-specific asides (elf rapid recovery, elf sensitivity floors,
  elf multi-orgasm 餘韻→接近 re-entry), every narrative-only field (身體感受, 興奮要素, 被注視感受,
  最後性活動, 基本資訊.狀態), and `體力值`'s own action-efficiency threshold (疲勞狀態) are excluded —
  the first two per D-7's carried-forward resolution (a future `buffs.yaml` entry and the
  Narrator/PersonaStore, respectively), the third named explicitly for change 6's `combat_modifiers.
  yaml` (design.md D-9), since it is a standing-condition modifier, not an event-triggered transition.
- Add `world/rules/sexual_transitions.py`: the module that owns `then`'s effect vocabulary for
  `sexual.yaml` — `FIELD_KINDS` (declares each targetable field's mutation shape: plain
  ordered-level, the cyclic `climax_phase`, the part-keyed `sensitivity` dict, the plain-int
  `climax_today` counter, the one-way `virgin` flag, the append-only `experience_types` set, and —
  for the one field outside `SexualState`, `sp` — a `vital_gauge` kind writing through change 3's
  `entity.traits.sp.current`, the gauge's public writable property), `_parse_delta()` (parses
  `"+1"`, `"-1"`, `"+1..+2"`, and `"-30..-20"`
  same-sign range deltas), `_apply_then()` (the single dispatcher from a rule's opaque `then` dict to
  the correct mutation — routing every `climax_phase` write through change 7's
  `_apply_climax_phase_set()`, never writing the trait directly, and routing `climax_today` through
  change 7's `record_climax()`, never through `SexualState`'s private `TraitHandler`), `_build_
  context()` (snapshots `entity.sexual` at the start of each pass and rejects payload collisions
  with authoritative state keys), and `apply_event(entity, event, **event_context)` — the
  public entry point, running change 6's `evaluate_condition()` against every loaded rule in a
  fixed-point loop so one rule's effect (e.g. arousal reaching `極限`) can correctly trigger a second
  rule (`climax_gate`) within the same call, without ever re-firing a rule for a change that already
  fully propagated. Exhausting the defensive pass limit raises rather than returning partially
  settled state as success.
- Add `world/rules/tests/test_sexual_transitions.py`: one `test_rule_<id>()` per rule ID (25
  functions), plus `test_every_rule_id_has_a_test()` — a structural check, mirroring change 6's own
  D-7 discipline, that walks `sexual.yaml`'s loaded rule IDs and asserts a matching `test_rule_<id>`
  exists via `inspect.getmembers`, so a rule literally cannot be added without a paired test existing
  — and `test_field_kinds_covers_every_targetable_field()`, asserting `FIELD_KINDS`' key set matches
  exactly the set of fields any rule in `sexual.yaml` targets, with no gap in either direction (this
  is exactly the check whose scope excluded `sp` in the initial draft, and why the coordinator's
  review — not this test — is what caught the gap; the check now covers `sp` alongside every other
  targeted field).
- Add targeted structural tests for the two irreversibility guarantees hard requirement 4 calls out
  by name: `test_virginity_once_is_irreversible()` (firing `first_vaginal_penetration` twice, or
  firing it and then attempting a direct reset, leaves `virgin` permanently `False`) and
  `test_experience_types_only_grows()` (firing two different experience-triggering events and
  re-firing one of them leaves the resulting set strictly growing, never shrinking or duplicating an
  error). Add `test_climax_phase_rules_route_through_guard()`, a source-inspection test confirming
  `sexual_transitions.py` contains no direct write to `climax_phase`'s trait value outside a call to
  `_apply_climax_phase_set()`.
- `climax_today_increment_on_climax` uses `SexualState.record_climax()` — change 7's own addition to
  its public surface, closing the write-path gap this proposal originally flagged for coordination.
  No further change to `sexual_state.py` is needed or expected from this proposal.

## Capabilities

### New Capabilities
- `sexual-transition-rulebook`: `rulebook/sexual.yaml`'s 25 transition rules, the `then` effect
  vocabulary and its interpreter (`FIELD_KINDS`, `_parse_delta`, `_apply_then`, `_build_context`,
  `apply_event()` and its fixed-point loop), and the structural test-correspondence and
  field-coverage checks that make "every rule has a test" and "every field is reachable" CI-enforced
  properties rather than review-time conventions.

### Modified Capabilities
- None. `openspec/specs/` is still empty (changes 1–7 have not been archived yet).

## Impact

- **New files**: `world/rules/rulebook/sexual.yaml`, `world/rules/sexual_transitions.py`,
  `world/rules/tests/test_sexual_transitions.py`.
- **Modified files**: None. `SexualState.record_climax()` is change 7's own file and already landed
  there; this proposal only calls it.
- **Depends on**: change 7 (`sexual-state`) for `SexualState`'s public property surface (`.arousal`,
  `.wetness`, `.shame`, `.exposure`, `.climax_phase`, `.climax_today`, `.virgin`,
  `.experience_types`, `.sensitivity`, `add_experience_type()`, `record_climax()`) and
  `_apply_climax_phase_set()`, and for design.md's D-7 `variable_rule.md` ambiguity analysis,
  inherited rather than re-derived. Change 6 (`buffs-rulebook`) for `world/rules/rulebook/schema.py`'s
  `Rule`/`load_rules()`/`evaluate_condition()`, imported and reused, never reimplemented. Change 3
  (`entity-traits`) for `entity.traits.sp` — read/written directly by `sp_cost_on_climax` (design.md
  D-8), the one rule targeting a field outside `SexualState`.
- **Consumers deferred to later changes**: change 8 (`action-resolver`) is expected to call
  `apply_event()` from its effect-resolution step, and to decide which player commands emit which
  event names (`stimulus_applied`, `climax_ends`, `first_vaginal_penetration`, etc.) — no event
  vocabulary member here is wired to any player-facing command. Change 8 is also expected to author
  any sexual-magic buff instances (rate/bounds/decay levers) targeting the field names this table
  and change 7 both use. Change 11 (`world-clock`) continues to own `decay_tick()`/
  `reset_daily_counters()`'s settlement-order position, untouched by this change. **Change 6
  (`buffs-rulebook`) is the named owner** of a future `fatigue_action_penalty`-shaped row in
  `combat_modifiers.yaml` for `variable_rule.md`'s `疲勞狀態` threshold (design.md D-9) — explicitly
  excluded from this table as a standing-condition modifier, not an event-triggered transition, and
  not built here.
