## Why

`docs/superpowers/specs/2026-08-15-sexual-act-system-overview-design.md` §4.2 assigned the resist-emission
obligation explicitly to `sexual-act-effects` (`B5`): "emits the `EventEntry(kind="sexual_resist", ...)`
contract `B6b`'s scan consumes, per source design §3.4 — fixed in the shared source design so this
obligation applies regardless of `B5`/`B6b` batch order." `B5`'s actual archived proposal declined it
instead (`openspec/changes/archive/2026-08-16-sexual-act-effects/design.md`, Non-Goals: "No resist
contest — this proposal's handlers assume the act's cast already succeeded; whether it should have been
resistible is `sexual-resist-contest`'s and `sexual-resist-turn-cost`'s territory"), and
`sexual-resist-turn-cost` (`B6b`) built only the consequence side (`_scan_sexual_coercion` in
`world/rules/combat_session.py`), documenting as a known risk that it has "no production caller until
`sexual-act-effects` lands and actually emits `sexual_resist`-kind entries" — while relying on the
overview doc's `B5` assignment as the reason it does not need to build the emission itself.

The result, verified directly against the current merged code: `SexualActDef.resistible` is declared and
validated (`world/skills/sexual_acts/_builder.py`) but consumed nowhere in the live cast-resolution path.
`resist_verdict()` (`world/rules/sexual_resist.py`, shipped by `sexual-resist-contest`/`B6a`, a pure
function) has no caller outside its own tests. `world/rules/action.py`'s `_resolve_act()` never calls it
and never emits `EventEntry(kind="sexual_resist", ...)`. Every currently-shipped `resistible=True` act
(all three of `sexual-act-seeds`/`B8`'s `SINGLE`-target seeds: `combat_tease`, `partner_caress`, and
`partner_hand_hold`) always executes unconditionally: a target can never actually resist, and
`sexual-resist-turn-cost`'s affinity penalty can never fire — despite three already-merged
proposals (`B5`, `B6a`, `B6b`) each having done their own part on the assumption that another proposal
would close the loop. This is distinct from the separately-tracked, explicitly-deferred
`sexual-resist-out-of-combat` follow-up, which is scoped to the out-of-combat cast path
(`cast_settlement.py`/`commands/action.py`); this proposal is scoped to the in-combat path only —
`world/rules/action.py`, the same file `sexual-act-effects` already owned and where the emission was
always meant to live.

## What Changes

- Add a new resist-gating step to `world/rules/action.py`'s `ActionResolver.resolve()`, run after target
  resolution and before effect resolution, that fires only when the cast skill's key is present in
  `SEXUAL_ACT_REGISTRY` and that act declares `resistible=True`.
- For every resolved target other than the actor, call `resist_verdict(actor, target, rng=roll_d100)`
  (`world/rules/sexual_resist.py`, unmodified) and stage one `EventEntry(kind="sexual_resist",
  data={"resisted": bool, "auto_comply": bool, "roll": int | None})` per target into the action's
  `EventLog` — exactly the contract `sexual-resist-turn-cost`'s `_scan_sexual_coercion` already documents
  and expects, so `world/rules/combat_session.py` needs no change.
- Exclude every target whose verdict resolves `resisted=True` from the target list handed to the
  pleasure/counter/event effect handlers, so a successfully-resisted target receives none of the act's
  effects while every other target (complied, auto-complied, or forced) is affected exactly as today.
- Leave the actor's own pleasure/counter effects (`act.actor_counters`, the actor's own
  `pleasure:`/`sexual_counter:` share) unconditional, regardless of any target's resist outcome —
  consistent with D-4's existing self-limiting invariant ("every act applies pleasure to the actor"),
  which this proposal does not touch or reinterpret.
- Leave resource cost, time cost, and skill-practice XP unconditional on resist outcome — the cast still
  happened and still cost the actor a turn's worth of resources even when a target refuses it; only the
  refusing target's own participation in the act's effects is withheld. See design.md D-4 for why this
  reading is the correct one for the current, already-shipped multi-target architecture, not the
  single-target model the original source design was written against.
- Add a new capability `sexual-resist-cast-wiring` documenting the emission contract and the
  exclusion-from-effects behavior as first-class, testable requirements — no existing capability's spec
  (`sexual-act-effects`, `sexual-resist-contest`, `sexual-resist-turn-cost`) currently claims this
  behavior, and none of their Non-Goals sections need editing (they already correctly describe what those
  proposals did and did not do).

## Capabilities

### New Capabilities
- `sexual-resist-cast-wiring`: the in-combat wiring that turns a `resistible=True` act's cast into an
  actual resist contest — calling `resist_verdict()`, emitting the `sexual_resist` EventLog contract, and
  excluding a successfully-resisting target from the act's pleasure/counter/event effects.

### Modified Capabilities
- none — this proposal is additive only. `sexual-act-effects`, `sexual-resist-contest`, and
  `sexual-resist-turn-cost`'s existing requirements are exercised (the first two are called into for the
  first time in production; the third finally gets a production caller for the contract it already
  documents), not changed.

## Impact

- Code: `world/rules/action.py` only, plus a new test module,
  `world/rules/tests/test_sexual_resist_cast_wiring.py`.
- Existing test touch: `world/skills/sexual_acts/tests/test_seed_acts.py` casts all three shipped
  `resistible=True` acts. Its `combat_tease` assertions are verified (not modified) to stay deterministic
  under resist-gating, since they read only `act.actor_counters`, which this proposal never gates — but
  `test_partner_seed_increments_duo_act_count_on_both_participants` asserts `partner_caress`'s target's
  `duo_act_count` (a `participant_counters` credit, which resist-gating **does** withhold from a
  resisting target) with no `roll_d100` mock, and **must** be updated to force a compliant roll (design.md
  D-3a) or it becomes flaky the moment this change lands.
- No change to `world/rules/sexual_resist.py` (`B6a`'s pure function), `world/rules/combat_session.py`
  (`B6b`'s consumer, already correct and already expecting exactly this contract), `world/skills/
  sexual_acts/_builder.py` (the `resistible` field is already validated; this proposal only reads it),
  or any `sexual_acts/*.py` catalog module (no new act content).
- Unblocks `sexual-catalog-shame`'s (`C3`, proposed, not yet implemented) three `resistible=True` `AREA`
  acts (`shame_provocative_gaze`, `shame_public_performance`, `shame_devoted_pose`) and any future
  catalog proposal's resistible acts: once this change lands, casting them will actually run a resist
  contest per target instead of silently always succeeding.
