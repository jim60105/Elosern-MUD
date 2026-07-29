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

## What Changes

- Add `world/rules/rulebook/sexual.yaml`: ~24 declarative transition rules covering every
  behaviourally-meaningful (non-narrative, non-race-specific) line of `variable_rule.md`'s
  `性狀態.*` section — `arousal`, `wetness`, `shame`, `exposure`, `climax_phase`, `climax_today`,
  `virgin`, `experience_types`, and `sensitivity`. Every rule carries the unique `id` change 6's
  `load_rules()` already requires. Race-specific asides (elf rapid recovery, elf sensitivity floors,
  elf multi-orgasm 餘韻→接近 re-entry) and every narrative-only field (身體感受, 興奮要素,
  被注視感受, 最後性活動, 基本資訊.狀態) are excluded per D-7's carried-forward resolution — the
  former belongs to a future `buffs.yaml` entry, the latter to the Narrator/PersonaStore.
- Add `world/rules/sexual_transitions.py`: the module that owns `then`'s effect vocabulary for
  `sexual.yaml` — `FIELD_KINDS` (declares each targetable field's mutation shape: plain
  ordered-level, the cyclic `climax_phase`, the part-keyed `sensitivity` dict, the plain-int
  `climax_today` counter, the one-way `virgin` flag, the append-only `experience_types` set),
  `_parse_delta()` (parses `"+1"`, `"-1"`, and `"+1..+2"` random-range deltas), `_apply_then()` (the
  single dispatcher from a rule's opaque `then` dict to the correct `SexualState` mutation — routing
  every `climax_phase` write through change 7's `_apply_climax_phase_set()`, never writing the trait
  directly), `_build_context()` (assembles `evaluate_condition()`'s context from `entity.sexual`'s
  live properties plus the calling event's name and payload), and `apply_event(entity, event,
  **event_context)` — the public entry point, running change 6's `evaluate_condition()` against
  every loaded rule in a fixed-point loop so one rule's effect (e.g. arousal reaching `極限`) can
  correctly trigger a second rule (`climax_gate`) within the same call, without ever re-firing a
  rule for a change that already fully propagated.
- Add `world/rules/tests/test_sexual_transitions.py`: one `test_rule_<id>()` per rule ID (24
  functions), plus `test_every_rule_id_has_a_test()` — a structural check, mirroring change 6's own
  D-7 discipline, that walks `sexual.yaml`'s loaded rule IDs and asserts a matching `test_rule_<id>`
  exists via `inspect.getmembers`, so a rule literally cannot be added without a paired test existing
  — and `test_field_kinds_covers_every_targetable_field()`, asserting `FIELD_KINDS`' key set matches
  exactly the set of fields any rule in `sexual.yaml` targets, with no gap in either direction.
- Add targeted structural tests for the two irreversibility guarantees hard requirement 4 calls out
  by name: `test_virginity_once_is_irreversible()` (firing `first_vaginal_penetration` twice, or
  firing it and then attempting a direct reset, leaves `virgin` permanently `False`) and
  `test_experience_types_only_grows()` (firing two different experience-triggering events and
  re-firing one of them leaves the resulting set strictly growing, never shrinking or duplicating an
  error). Add `test_climax_phase_rules_route_through_guard()`, a source-inspection test confirming
  `sexual_transitions.py` contains no direct write to `climax_phase`'s trait value outside a call to
  `_apply_climax_phase_set()`.
- **Flags one integration gap for change 7's owner**, discovered while wiring `climax_today`'s
  per-climax increment (variable_rule.md's `每次達到高潮時+1`): change 7's documented public surface
  exposes `SexualState.climax_today` as a plain read-only `int` (unlike the ordered-level fields,
  whose properties return a live, mutable trait object), so no rule in this table can legally
  increment it without reaching into `SexualState`'s private `TraitHandler` — a boundary this
  proposal is explicitly instructed not to cross. See design.md's ambiguity section for the proposed
  minimal resolution (`SexualState.record_climax()`, mirroring `add_experience_type()`'s
  "sole mutator" shape) and the coordination this requires with change 7's owner. No change 7 file is
  edited by this proposal itself.

## Capabilities

### New Capabilities
- `sexual-transition-rulebook`: `rulebook/sexual.yaml`'s ~24 transition rules, the `then` effect
  vocabulary and its interpreter (`FIELD_KINDS`, `_parse_delta`, `_apply_then`, `_build_context`,
  `apply_event()` and its fixed-point loop), and the structural test-correspondence and
  field-coverage checks that make "every rule has a test" and "every field is reachable" CI-enforced
  properties rather than review-time conventions.

### Modified Capabilities
- None. `openspec/specs/` is still empty (changes 1–7 have not been archived yet).

## Impact

- **New files**: `world/rules/rulebook/sexual.yaml`, `world/rules/sexual_transitions.py`,
  `world/rules/tests/test_sexual_transitions.py`.
- **Modified files**: None planned. (See the flagged `climax_today` gap above — if change 7 is
  implemented before this change and its property surface indeed has no write path, a minimal,
  additive one-method patch to `world/rules/sexual_state.py`, coordinated with change 7's owner, is
  the expected — not built here — follow-up; nothing in this proposal edits change 7's artifacts.)
- **Depends on**: change 7 (`sexual-state`) for `SexualState`'s public property surface (`.arousal`,
  `.wetness`, `.shame`, `.exposure`, `.climax_phase`, `.climax_today`, `.virgin`,
  `.experience_types`, `.sensitivity`, `add_experience_type()`) and `_apply_climax_phase_set()`, and
  for design.md's D-7 `variable_rule.md` ambiguity analysis, inherited rather than re-derived. Change
  6 (`buffs-rulebook`) for `world/rules/rulebook/schema.py`'s `Rule`/`load_rules()`/
  `evaluate_condition()`, imported and reused, never reimplemented.
- **Consumers deferred to later changes**: change 8 (`action-resolver`) is expected to call
  `apply_event()` from its effect-resolution step, and to decide which player commands emit which
  event names (`stimulus_applied`, `climax_ends`, `first_vaginal_penetration`, etc.) — no event
  vocabulary member here is wired to any player-facing command. Change 8 is also expected to author
  any sexual-magic buff instances (rate/bounds/decay levers) targeting the field names this table
  and change 7 both use. Change 11 (`world-clock`) continues to own `decay_tick()`/
  `reset_daily_counters()`'s settlement-order position, untouched by this change.
