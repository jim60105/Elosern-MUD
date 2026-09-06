# Design: defeat-aftermath-violation-sequence

Parent design: `docs/superpowers/specs/2026-09-06-defeat-aftermath-design.md`
§3.1 step 3, §4.1-4.2 (mechanics only; digest/narrative is
`defeat-aftermath-digest-narrative`, companion victims are
`defeat-aftermath-companion-victims`).

## Context

`defeat-aftermath-core` established the HP-1 floor, the guarded
`DEFEAT_ADULT_SCENES` hook inside `settle_session`'s single transaction,
the violator-departure phase, and the per-section rulebook loader. Monster
`SexualState` mounts from a baseline dict (`world/rules/sexual_state.py`
`_build_from_baseline`) — the archetype seam is a data source, not a schema
change. Arousal is a derived ordinal over the pleasure counter
(`_DerivedArousal`), so "raise arousal N steps" means raising pleasure
through the existing transition path. The resist contest already ships
extracted: `resist_verdict(actor, resister, *, rng)` in
`world/rules/sexual_resist.py` is pure and takes an injected roll source —
`_step4b_sexual_resist_gate` is its caller, not its owner.

## Goals / Non-Goals

**Goals:**

- Deterministic violation sequence: victory arousal → archetype threshold →
  attempts (state-derived dice, `resist_verdict` rolls) → declared deltas +
  symmetric counters + per-attempt clock advance → first-resistance stop →
  zero-landed PG variant.
- The §6.4 deferred per-archetype monster sexual baseline, owned here.
- The in-memory per-participant outcome object the digest phase consumes.

**Non-Goals:**

- No companion victims (player-pool only; companion breadth is
  `defeat-aftermath-companion-victims`). No affinity writes, no digest
  table, no wake dialogue (digest change). No NPC/humanoid violators
  (`engage()` still admits only `Monster`). No settings flag (core owns
  `DEFEAT_ADULT_SCENES`). No extraction refactor of `action.py`.

## Decisions

**D-V1: Sequence ordering inside the core's phase.**
The sequence registers as the body of the core's guarded hook and runs
between `defeat_settle` and `violator_depart`, so departure still follows
the last act. EventLog order becomes `defeat_settle, (violation_*)…,
violator_depart, weak_granted` — the core's pinned order plus spliced
violation entries; the core test updates to the extended order.

**D-V2: Arousal rides pleasure, shame stays pinned.**
The victory table declares pleasure-point deltas (arousal is derived);
archetype baselines may raise sensitivity/arousal-floor/pleasure-floor only
— a Monster's `shame` bounds are permanently pinned at the floor by
construction (shipped invariant, test-pinned), so no archetype row may set
shame. The section loader rejects a shame key with a rulebook validation
error.

**D-V3: `resist_verdict` is called, not extracted.**
The sequence calls the existing pure `resist_verdict(actor, resister, *,
rng)` with the monster as `actor`, the selected victim as `resister`, and
the state-derived roll via `rng`. There is no extraction task and no second
difficulty curve — the shipped curve IS the rail. (Verified:
`world/rules/sexual_resist.py:305`; the auto-comply branch keys on the
resister's affinity toward the actor, and a player holds no affinity
record toward a wilderness Monster actor, so a monster violator always
reaches the dice roll.)

**D-V4: Dice are state-derived pure values, not a seeded stream.**
`roll_d100()` (`world/rules/dice.py`) is a stateless Evennia dice wrapper
and `CombatSessionRecord` persists no seed or cursor — a "session seeded
stream" does not exist. Instead: `derived_roll(session_id, violator_key,
victim_key, attempt_index, purpose) -> int` is a deterministic hash-based
d100 derivation with no state at all. Rolled-back retries recompute identical
values because their inputs are durable record state; the recovery fallback
needs no replay bookkeeping. The derivation lives in one small pure helper
(`world/rules/state_derived_roll.py`) shared with the companion-victims
extension.

**D-V5: First successful resistance stops the violator (owner decision).**
One resisted attempt ⇒ that violator's remaining attempts cancel (prey that
fights back ends the pursuit). Fully-landed sequences run to the cap.
A sequence with zero landed attempts selects the PG wake template. The
digest's "full resistance" observation reads the same signal (the
zero-landed flag) — no second definition.
- Rejected alternatives: "truncation only when all attempts resisted"
  (self-contradictory once resisted attempts consume duration); early-stop
  at N consecutive resists (N is arbitrary).

**D-V6: The hook is registered, not branched.**
This change registers its body into the core's hook table; it never reads
the settings flag itself and never edits the guard. Off-state is therefore
structurally the core's shipped behavior.

**D-V7: The digest outcome object is in-memory and pure.**
`ViolationOutcome(participant, selected, landed, resisted, climax_delta,
zero_landed)` is returned to the settlement call graph, never persisted —
the digest runs inside the same settlement call, and a replay re-derives
the object from state-derived dice. Violation persists only its EventLog
entries and state/counter writes.

## Risks / Trade-offs

- [Farm route: deliberate goblin deaths grind `interspecies_act_count`
  unlocks] → Accepted by the owner; price is the core's loss menu (world
  time, weak debuff, degraded sexual state feeding `combat_modifiers.yaml`).
- [Pleasure-driven arousal can push the pleasure counter to its 100 cap] →
  Deltas clamp through the existing counter bounds; overflow is discarded,
  not wrapped — pinned by test.
- [A hash-derived d100 is not cryptographic randomness] → intended: the
  sequence must be replay-identical and offline-deterministic; fairness is
  uniformity across the key space, asserted distributionally in test.
- [Archetype baselines drift from lore registries] → Loader validates every
  archetype key against the monster lore data it is keyed on, same
  fail-closed idiom as other rulebooks.
- [Per-attempt clock advances interact with deadlines] → same clock path
  rest/skip use; the recovery change's side-effect battery covers the
  long-advance interaction once, and violation durations are small.
