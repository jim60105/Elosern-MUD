## Context

`world/rules/sexual_state.py` owns `SexualState`, `DECAY_CONFIG`, `decay_tick()`, and
`_apply_climax_phase_set()` — the sole guarded write path for `climax_phase`, valid over the cycle
`未達 → 接近 → 進行中 → 餘韻 → 未達` (plus `餘韻 → 接近`). `world/rules/rulebook/sexual.yaml` declares
the event-driven transition table `world/rules/sexual_transitions.py::apply_event()` evaluates.

Two call sites already invoke `decay_tick()` once per settlement point:

- `world/rules/combat.py::_end_of_round_upkeep`, once per living, non-fled roster member, per combat
  round (`COMBAT_YAML["round"]["seconds"]`, currently 6s). Governed by the `combat-resolution` spec's
  "Per-round upkeep ticks buffs and advances sexual decay by the round duration" requirement.
- `world/rules/clock.py::_settle_buffs_and_decay`, once per settlement quantum in its main loop and
  once more for any leftover remainder, out of combat. Governed by the `settlement-stage-order` spec's
  "Long jumps settle in quanta... with an early exit once nothing remains to settle" requirement.

Neither call site currently does anything beyond decay. `climax_phase` reaching `進行中` is therefore
a dead end: the only rule leaving it (`climax_phase_ends_to_afterglow`) fires on the `climax_ends`
event, which nothing emits, and `DECAY_CONFIG["climax_phase"]`'s `only_from: 餘韻` means passive decay
never reaches `進行中` either. Combined with the shipped `climax_in_progress_locks_actions` combat
modifier (`actions_per_turn: 0`), this is a permanent action lock once triggered — currently
unreachable, about to become reachable once the broader sexual-act-system design set lands acts that
raise pleasure to `極限`.

This proposal (`docs/superpowers/specs/2026-08-15-sexual-pleasure-model-design.md` §3, proposal `B3`
in that document set's implementation sequence) closes the loop and adds the climax-extension
mechanic the design calls for. It intentionally does **not** implement the acts that stage an
extension, nor the resist contest that later bounds indefinite suppression — both are later,
independently-scoped proposals (`sexual-act-effects`, `sexual-resist-contest`) in the same design set.
This proposal's new surface (`stage_climax_extension()`) is the seam they will call into.

This proposal depends on two proposals from the same document set that are expected to land first:
`pleasure-gauge` (the `pleasure` field, with `arousal` becoming a derived, still-comparable view) and
`sexual-counters` (eleven lifetime counters on `SexualState`, including `高潮次數` and `連續高潮次數`,
each with one sanctioned mutator per the `record_climax()` precedent). This proposal reads neither
`pleasure` nor the counter mutators' exact names directly in its own spec text; it calls whatever
`sexual-counters` ships for the two climax-related counters, resolved by inspecting
`world/rules/sexual_state.py` at implementation time (see tasks.md) rather than guessing a name here
that risks drifting from what that sibling proposal actually ships.

## Goals / Non-Goals

**Goals:**
- An entity whose `climax_phase` reaches `進行中` always returns to `未達` (via `餘韻`) within finite
  settlement time, with no external caller required to know that emission is necessary.
- A staged extension keeps an entity in `進行中` for one more settlement point at half the ordinary SP
  cost, and the mechanism composes with an unbounded number of stages.
- The two lifetime climax counters (`高潮次數`, `連續高潮次數`) increment exactly once per
  `climax_ends`/`climax_extended` respectively, with no other trigger.
- `sexual.yaml`'s male-male experience path is symmetric with its existing female-female path, and
  neither touches `virgin`.
- Every random SP-cost delta stays deterministic under an injected RNG, matching the existing
  `apply_event(rng=...)` seam.

**Non-Goals:**
- No act, effect handler, or player-facing command calls `stage_climax_extension()`. That is
  `sexual-act-effects`' job (a sibling proposal), which computes whether a cast act's pleasure gain
  meets `climax_extension_threshold` before clamping — a computation this proposal does not perform or
  gate on.
- No resist contest, no affinity interaction, no cap on the number of extensions, and no "turn 6+
  rolls again" opening. `climax_turns` is tracked here specifically so a later proposal can read it,
  but this proposal enforces no behavior conditioned on its value beyond exposing it.
- No change to `_VALID_CLIMAX_TRANSITIONS` or `_apply_climax_phase_set()`'s guard rules. The cycle
  itself is correct and unchanged; only the missing emitter is added.
- No change to `pleasure`/`arousal` band tables, sensitivity, or shame multipliers (owned by
  `pleasure-gauge`).
- No RNG threading through `combat.py`/`clock.py`'s public function signatures (`run_round`,
  `advance`, etc.). See Decision 5.

## Decisions

### D1 — The settlement decision is a pure function in `sexual_state.py`; the `apply_event()` call stays at the two call sites

`sexual_transitions.py` already imports `_apply_climax_phase_set` from `sexual_state.py` (line 14).
If `sexual_state.py` imported `apply_event` back from `sexual_transitions.py`, that would cycle.

The design in `2026-08-15-sexual-pleasure-model-design.md` §3.3 anticipates exactly this: "the
emission lives at the call sites, which already own ordering, not inside the state module." This
proposal therefore adds one new function to `sexual_state.py`:

```python
def climax_settlement_action(entity) -> str | None:
    """Advance climax-turn bookkeeping and report which settlement action to take.

    Returns "extend" when a staged extension is consumed, "end" when the
    entity must resolve its climax normally, or None when climax_phase is not
    進行中 (climax_turns is reset to 0 in this case, if it was nonzero).

    This performs every mutation that does not require the sexual.yaml rule
    cascade: climax_turns and pending_climax_extension bookkeeping, and the
    two lifetime counter increments. It does NOT call apply_event() — the
    caller (combat.py or clock.py) does that, using the returned action to
    choose between "climax_extended" and "climax_ends".
    """
```

Both call sites gain the same three-line shape after their existing `decay_tick(entity, seconds)`
call:

```python
action = climax_settlement_action(entity)
if action == "extend":
    apply_event(entity, "climax_extended")
elif action == "end":
    apply_event(entity, "climax_ends")
```

`combat.py` and `clock.py` already import from `sexual_state.py` (`decay_tick`) and will additionally
import `apply_event` from `sexual_transitions.py` directly — both modules sit downstream of both, so
no cycle is introduced. This also means the counter-increment side effects (see D3) happen inside
`climax_settlement_action()`, in the same module the counters' mutators live in, rather than requiring
`combat.py`/`clock.py` to know the counters' names.

**Alternative considered:** put the whole decision-plus-emission sequence in one function inside
`sexual_transitions.py` (which already imports from `sexual_state.py`, so no cycle there). Rejected
because `sexual_transitions.py`'s existing structural tests
(`test_field_kinds_covers_every_targetable_field`, `test_every_rule_id_has_a_test`) enumerate exactly
the fields and rule ids `sexual.yaml` declares; adding non-rule-table logic to that module blurs the
line the `sexual-transition-rulebook` spec draws around it ("no rule-loading or condition-matching
logic duplicated"). Keeping the decision in `sexual_state.py` and the emission at the call sites
matches the design document's explicit instruction and keeps `sexual_transitions.py` a pure rule
evaluator.

### D2 — Transient state uses the existing `entity.attributes`/`_STATE_CATEGORY` pattern, not a new `TraitHandler` counter

`climax_turns` and `pending_climax_extension` are stored via `entity.attributes.add(key, value,
category=_STATE_CATEGORY)`, the same mechanism `virgin` and `experience_types` already use — not as
`TraitHandler` counters like `climax_today`.

**Rationale:** a `TraitHandler` counter (`trait_type="counter"`) is built for `base`/`min`-clamped
monotonic accumulation reset on a schedule (`climax_today`'s daily reset). `climax_turns` needs
reset-to-zero on an arbitrary condition (leaving `進行中`) mid-settlement, and `pending_climax_extension`
needs additive staging from an as-yet-unbuilt external caller followed by a decrement-by-one at
consumption — both are better expressed as plain integers under direct control than as a trait with
its own bound-clamping semantics that would need reconfiguring for behavior neither field actually
wants (no `min`/`max` clamp is desired beyond `>= 0`, which the code enforces directly).

Both fields use the same rollback *mechanism* `virgin`/`experience_types` already rely on
(`_STATE_CATEGORY` attributes are ordinary Evennia attributes), but rollback coverage in this codebase
is by explicit enumeration, not by attribute category: `clock.py::_ADVANCE_ENTITY_SURFACES` and
`action.py::_snapshot_entity_state`/`_restore_entity_state` list every covered attribute by
`(key, category)`. `climax_turns` and `pending_climax_extension` MUST be added to both enumerations
in this same change, or a failed-and-rolled-back `advance()`/action commit/combat-session round would
leave stale bookkeeping persisted. See D6.

Public surface:

```python
@property
def climax_turns(self) -> int: ...          # read-only

@property
def pending_climax_extension(self) -> int: ...  # read-only

def stage_climax_extension(self, count: int = 1) -> None:
    """Add `count` to the pending extension stage. The sole write path."""
```

`stage_climax_extension` validates `count` as a positive `int` (`>= 1`), raising `ValueError`
otherwise, so a future effect caller cannot stage a negative or non-integral value that the settlement
decision would later silently treat as "no extension staged".

`stage_climax_extension` is additive (not a setter) specifically so a future divine-arts proposal
(時姦, per `docs/superpowers/specs/2026-08-15-divine-sexual-arts-design.md` §2) can stage several
rounds of extension from one action by calling it with `count > 1`, without needing its own field.

### D3 — The two lifetime counters increment inside `climax_settlement_action()`, bound to whatever `sexual-counters` shipped

`高潮次數` increments exactly once when `climax_settlement_action()` returns `"end"`; `連續高潮次數`
increments exactly once when it returns `"extend"`. Both calls happen inside
`climax_settlement_action()` itself, immediately before it returns, using `sexual-counters`' shipped
mutator methods on `SexualState` — which live in the same file this proposal edits.

This proposal does not invent names for those mutators. `tasks.md` instructs the implementer to open
the already-landed `world/rules/sexual_state.py` (as shipped by `sexual-counters`) and call whatever
public methods that proposal exposes for these two specific counters, rather than this design
document guessing a name that could drift from what actually shipped. This is a deliberate
inter-proposal binding done at implementation time, not proposal-writing time — by the time this
change is applied, `sexual-counters` is real, inspectable code.

### D4 — `_has_settlement_work` gains one more disjunct: `climax_phase == 進行中`

`clock.py::_has_settlement_work` currently returns `True` when any buff needs ticking, or when any
`DECAY_CONFIG`-tracked field is off its configured floor (respecting each field's `only_from` gate).
`climax_phase`'s own `DECAY_CONFIG` entry only counts while the phase is `餘韻` (`only_from: 餘韻`).

An entity stuck in `進行中` could, in principle, have every other `DECAY_CONFIG` field already at
floor (arousal/pleasure decays independently and unconditionally, unlike `climax_phase`). If that
happens, `_has_settlement_work` would return `False`, and `_settle_buffs_and_decay`'s quanta loop
would `break` **before** reaching the quantum that would have called `climax_settlement_action()` —
stranding the entity in `進行中` for the remainder of a long time-skip, reintroducing a version of the
exact bug this proposal fixes, just gated behind a specific field-decay ordering instead of behind
"nothing ever emits `climax_ends`."

The fix is one additional `or` clause:

```python
sexual = getattr(entity, "sexual", None)
if sexual is None:
    return False
if sexual.climax_phase.level == "進行中":
    return True
return any(...)  # unchanged DECAY_CONFIG loop
```

This is the `settlement-stage-order` spec delta (see specs/). `combat.py::_end_of_round_upkeep` has
no analogous early-exit gate — it unconditionally processes every living, non-fled roster member every
round — so it needs no equivalent fix.

### D5 — No RNG threading through `combat.py`/`clock.py` public signatures

`apply_event()` already accepts an optional `rng` for deterministic testing, defaulting to the global
`random` module. Threading an `rng` parameter through `_end_of_round_upkeep` → `run_round` →
`combat_session.py` call sites, and through `_settle_buffs_and_decay` → `_run_stages` → `advance()`,
would touch call sites well outside this proposal's owned files and outside a one-day scope.

Both new `apply_event(entity, "climax_ends")`/`apply_event(entity, "climax_extended")` calls at the
settlement call sites use the default global RNG, exactly like the pre-existing (if previously
unreachable) `sp_cost_on_climax` rule would have. Determinism for the SP-cost **rules themselves** is
tested by calling `apply_event()` directly with an injected `rng` stub in unit tests (the existing
pattern in `world/rules/tests/test_sexual_transitions.py`); the two settlement call sites are covered
by qualitative integration tests (SP decreases by an amount inside the documented range; exact value
is not asserted there). See tasks.md and Risks below.

### D6 — The new attributes join the explicit snapshot enumerations; the decision function is defensively guarded

`advance()` is wrapped by outer transactions (movement and cast settlement) that snapshot only
`clock.py::_ADVANCE_ENTITY_SURFACES` and restore exactly those attributes; `action.py`'s
transactional resolver snapshots/restores the keys enumerated in `_snapshot_entity_state()` /
`_restore_entity_state()` (the `sexual_event` effect handler declares the `{"sexual", "traits"}`
surfaces). Membership is by explicit `(key, category)` enumeration, never by attribute category —
`virgin`/`experience_types` are covered because they are listed, not because they live in
`_STATE_CATEGORY`. This change therefore adds `climax_turns` and `pending_climax_extension` to both
enumerations, and task 1.2 additionally confirms where the two lifetime counters are persisted
(`sexual_traits` internals are covered for free by both enumerations; a `sexual_state`-category
attribute would need the same listing) so rollback coverage is complete whether or not the sibling
proposal's storage shape requires it. Rollback regression tests (tasks.md §6) cover a failed
`advance()`, a failed action commit, and a failed combat-session round.

`climax_settlement_action()` guards on the absence of a sexual handler
(`getattr(entity, "sexual", None) is None` → return `None` with no writes), mirroring
`_has_settlement_work`'s existing `sexual is None` contract. The guard is vacuous in production —
every settlement caller already assumes a sexual handler (`decay_tick` dereferences it unguarded) —
but it keeps the new per-entity settlement call harmless for the pure combat/clock test fakes that
patch `decay_tick` yet provide no sexual handler (`tests/combat_fixtures.py::FakeEntity`,
`tests/test_clock.py`'s `sexual = None` entities), and it lets the existing mocked settlement tests
stay green without a cascade of new patches. tasks.md 5b.4 still audits every existing patch site
that exercises `run_round`/`advance` end to end, so any fixture that has real sexual state at
`進行中` is patched explicitly rather than left to emit a real `climax_ends` unnoticed.

## Risks / Trade-offs

- **[Risk]** A future proposal could call `stage_climax_extension()` unconditionally without checking
  `climax_phase`, staging an extension that is silently discarded (since `climax_settlement_action`
  only ever consumes a stage while `climax_phase == 進行中`, and resets `pending_climax_extension` to
  0 — not merely leaves it — whenever the entity is not in `進行中`, so a stage made while `接近` and
  never reaching `進行中` this settlement point does not carry over indefinitely).
  → **Mitigation:** `climax_settlement_action()` resets `pending_climax_extension` to 0 alongside
  `climax_turns` whenever `climax_phase != 進行中`, so a stray stage cannot accumulate silently across
  phases; this is asserted by a dedicated test (tasks.md).
- **[Risk]** Existing settlement-path tests that patch `tick_buffs`/`decay_tick` but let the real
  `climax_settlement_action()` run would newly crash or emit real climax events on fixtures that
  carry sexual state at `進行中`.
  → **Mitigation:** the D6 guard (`sexual is None` → no-op) keeps fake and sexual-less fixtures
  green; tasks.md 5b.4 audits every patch site that drives `run_round`/`advance` end to end and adds
  explicit `climax_settlement_action` mocks wherever a fixture would otherwise produce a real event;
  the full-suite run in task 7.7 is the final gate.
- **[Risk]** Calling `climax_settlement_action()` unconditionally for every roster member every round
  adds a fixed small overhead (a few attribute reads) to `_end_of_round_upkeep`, which already runs
  per-entity per-round.
  → **Mitigation:** the added work is O(1) attribute reads with no new query, consistent with
  `decay_tick`'s existing per-field cost; not measured separately given the existing budget documented
  in `AGENTS.md`'s test-runtime section is dominated by browser tests, not this loop.
- **[Trade-off]** Extension is genuinely unbounded by this proposal, matching the approved design's
  explicit choice (`sexual-pleasure-model-design.md` §3.5: "Indefinite suppression is a designed
  threat, not an oversight"). This proposal ships that half of the mechanic without its counterplay
  (the resist opening at the sixth climax turn), which is intentionally deferred to
  `sexual-resist-contest`. Until that proposal lands, nothing in the shipped codebase can actually
  stage an extension (Non-Goals), so this gap has no production exposure — it exists only as tested,
  inert capability.
- **[Trade-off]** SP-cost determinism at the two settlement call sites is verified qualitatively
  (range-bound), not via exact injected-RNG assertions, per D5. This is a narrower guarantee than the
  rest of the sexual-transition rule surface enjoys at its own call site, accepted to avoid an
  unrelated, cross-cutting signature change.

## Migration Plan

None. The project has no released users (`AGENTS.md`); no backward-compatibility layer or data
migration is required. Any entity already persisted with `climax_phase == 進行中` from a prior test
fixture or manual state (there is no such path in production data since the bug was previously
unreachable) will simply resolve on its next settlement point once this change lands.

## Open Questions

None. The counter-mutator binding (D3) is deliberately resolved at implementation time rather than
here; it is not an open design question, it is a stated inter-proposal contract.
