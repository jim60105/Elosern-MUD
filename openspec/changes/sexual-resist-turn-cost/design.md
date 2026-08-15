## Context

`docs/superpowers/specs/2026-08-15-sexual-act-resolution-design.md` §5 ("Turn Cost and Affinity
Consequence") is the source design for this proposal, `B6b` in the six-document
`2026-08-15-sexual-act-system-overview-design.md` set's §4.2 implementation sequence. Its outcome
table:

| Outcome | Actor's turn | Target's turn | Affinity |
|---|---|---|---|
| Comply (rolled or auto) | consumed | consumed | unchanged |
| Resist succeeds | wasted | proceeds normally | unchanged |
| Resist fails (forced) | consumed | consumed | **penalty applied** |

Three pieces of shipped state and one sibling proposal's shape are load-bearing here:

- `world/rules/combat_session.py::_scan_friendly_fire` — the exact pattern this proposal's own scan
  mirrors: scans a resolved round's `list[EventLog]` for qualifying entries, applies one affinity
  penalty per qualifying entry through `apply_affinity_change`, inside a nested `transaction.atomic()`
  covered by the caller's outer transaction, with an explicit rollback path restoring
  `relations_data` surfaces via `restore_relations_surfaces`. Called from `submit_player_action`
  inside the block the code's own comment names "Shared outer transaction
  (fix-combat-settlement-recovery D1): round effects, friendly-fire penalties, session metadata, and
  the terminal settlement commit (or roll back) as one unit."
- `world/rules/combat_session.py::_snapshot_party_surfaces` — snapshots `relations_data` only for
  `battlefield.roster` members whose `pk` is in `party_ids(actor)` (declared party companions). This
  is friendly-fire's own correct, narrower scope (friendly fire is defined as damaging a companion);
  it is *not* wide enough for this proposal (Decision 3).
- `world/rules/affinity.py::apply_affinity_change` — the sole affinity writer, gated on
  `isinstance(npc, NPC)`, requiring a value from the closed `AffinitySource` enum, flooring negative
  deltas at `0`, and always running `run_auto_leave_recheck`.
- `world/rules/event_log.py::EventEntry(kind, actor, target, data, text_template)` — the shape every
  effect handler's staged output already produces (e.g. the `damage` handler's `kind="damage"`
  entries, which `_scan_friendly_fire` itself already filters on).
- `sexual-resist-contest` (`B6a`, sibling proposal in this same session) — ships `ResistVerdict`
  (`resisted`, `auto_comply`, `roll`, plus the two score fields) as a pure function with **no
  production caller**. Its own proposal states explicitly: "No production call site is added in this
  proposal... `sexual-resist-turn-cost` (`B6b`) is the sibling proposal that calls it from a live
  action." This document's Decision 1 explains why that statement is honored in spirit but not in
  the most literal reading of "calls it".

`sexual-act-effects` (`B4`/`B5` in the overview's sequence) — the proposal that will define what an
act's effect handler actually does, including calling `resist_verdict()` per resistible participant
— has **not been implemented or written** as of this proposal. Its design is approved
(`sexual-act-resolution-design.md` §3) but no code exists.

## Goals / Non-Goals

**Goals:**
- A forced sexual act (resist attempted and failed) during active combat costs the target's affinity
  toward the actor, through the existing sole writer, with the existing daily-budget/cap/floor rules
  applying unchanged (negative deltas already bypass the daily budget entirely per
  `apply_affinity_change`'s own branching — see Decision 4).
- A complied-with act (whether rolled or `auto_comply`) and a successfully resisted act both apply no
  penalty, symmetric with the approved design's table.
- The mechanism is exercised and fully tested today even though its only caller
  (`sexual-act-effects`) does not exist yet, mirroring the precedent `climax-settlement` set for
  `stage_climax_extension()`.
- A rolled-back round leaves no `relations_data` inconsistency for *any* NPC a coercion penalty could
  have touched, not only party companions.

**Non-Goals:**
- **No new "skip this entity's turn" mechanic.** See Decision 2 — the "Actor's turn" / "Target's
  turn" column labels in the approved design's table are read here as *descriptive* of the resulting
  action economy (an actor who casts always spends their action; a target who is affected suffers the
  arousal-driven combat penalties on their own subsequent action, a target who resists does not), not
  as a literal instruction to build a new turn-consumption primitive. This proposal builds none.
- **No call to `resist_verdict()`.** This proposal never imports `world/rules/sexual_resist.py`. It
  reacts to an `EventEntry` a future proposal will emit, matching the field names `ResistVerdict`
  already defines, but does not invoke the function itself.
- **No change to `sexual-act-effects`' eventual implementation.** This proposal documents the
  contract that implementation must honor (Decision 1) but does not write it, exactly as
  `climax-settlement` documented `stage_climax_extension()`'s contract without writing its caller.
- **No out-of-combat wiring.** See Decision 5 — deferred to a follow-up proposal, named explicitly
  rather than silently dropped.
- **No change to `SexualState`, `sexual.yaml`, or any pleasure/counter mechanic.** Those belong to
  `sexual-act-effects`.

## Decisions

### Decision 1 — This proposal is the consumer of a contract, not the caller of `resist_verdict()`

`sexual-resist-contest`'s own proposal.md states this proposal "calls [`resist_verdict()`] from a
live action." A literal reading would require this proposal to own the effect-handler code that
decides whether an act's pleasure/counter effects apply — but that code lives in `action.py` and
`world/skills/sexual_acts/`, both exclusively owned by `sexual-act-effects` (`B4`/`B5`) per the
overview document's file-ownership table (`overview-design.md` §4.2), which this document set's
whole implementation strategy depends on staying disjoint per proposal.

Resolving this tension: the *decision* of whether an act's effect lands belongs to whichever
proposal owns the effect handler (`sexual-act-effects`), because only that code has the participant
list and the act definition to call `resist_verdict()` against. This proposal's actual, achievable
contribution — matching what it *can* own (`combat_session.py`, `affinity.py`) — is the
**consequence** of that decision: scanning the round's already-produced `EventLog` for a documented
record of the outcome, and applying the affinity penalty exactly where `_scan_friendly_fire` already
applies its own penalty for a structurally identical reason (a damage-effect handler decided a hit
landed on a companion; this proposal's sibling scan reacts to a resist-effect handler having decided
a forced act landed on a resister).

**The contract `sexual-act-effects` must honor**, for every resistible participant its effect handler
processes:

```python
EventEntry(
    kind="sexual_resist",
    actor=<caster's entity key>,
    target=<resisting participant's entity key>,
    data={"resisted": bool, "auto_comply": bool, "roll": int | None},
    text_template=<a narrative line appropriate to the outcome>,
)
```

emitted exactly once per resistible participant, regardless of outcome (so this proposal's scan can
distinguish "no entry because the target was never resistible" from "an entry recording compliance").
The three `data` fields' names and types match `ResistVerdict`'s own field names exactly, so a future
implementer writing the emitting code has no separate vocabulary to invent.

**This contract is not only recorded here.** A rubber-duck review of this proposal correctly flagged
that `sexual-act-effects` (`B5`) ships in the overview's batch 4, strictly before this proposal (`B6b`,
batch 5) — so a contract documented only in this design.md would be invisible to whoever implements
`B5`, since neither `B5`'s own row in `overview-design.md` §4.2 nor its real source design
(`sexual-act-resolution-design.md` §3) mentioned it. Fixed by adding this exact contract as
`sexual-act-resolution-design.md` §3.4 ("Resist outcome contract (for `B6b`)") — the shared source
design `B5`'s implementer actually reads — and cross-referencing it from `B5`'s own row in
`overview-design.md` §4.2, both edited in the same change as this proposal. The text above remains
here as this proposal's own record of what it consumes; §3.4 is now the authoritative statement of
what `B5` must emit, so the obligation holds regardless of which of `B5`/`B6b` lands first.

**Alternative considered:** have this proposal itself add a thin wrapper in `action.py` that calls
`resist_verdict()` and only stage the actual pleasure/counter effect via a callback `sexual-act-
effects` would later fill in. Rejected — this inverts the dependency the overview's sequencing
already established (`sexual-act-effects` is meant to be implementable independently of, and in
parallel with, `sexual-resist-contest`'s batch — see `overview-design.md` §4.3's batch 4:
`B5 ∥ B6a`), and would require this proposal to touch `action.py`, expanding its footprint into a
file a concurrently-running sibling proposal is actively editing.

### Decision 2 — "Target's turn consumed/wasted" is emergent, not a new mechanic

The approved design's outcome table labels the target's turn "consumed" (comply/forced) or
"proceeds normally" (resist succeeds), and states this "makes an act a genuine 1-for-1 action trade."

Read literally, this would require the target's own AI-driven or player-driven action for that same
round to be skipped or overridden whenever they comply or are forced — a change to `run_round`'s
per-combatant action loop, which is not in this proposal's ownership (`combat.py` is not listed in
`overview-design.md` §4.2 for `B6b`) and is architecturally invasive (it would need to reach into how
every combatant's `ActionProvider` is invoked, for every combatant shape — player, companion AI,
enemy AI).

This proposal reads the table's "1-for-1 action trade" claim as **already satisfied by mechanisms
this document set's own design already relies on elsewhere**, requiring no new code:
- The actor's action is spent on the cast regardless of outcome — true of any skill cast today,
  unconditionally, via `ActionResolver`'s existing cost/time charge, which occurs on any successful
  resolution and is untouched by whether a resistible sub-effect lands.
- If the act lands (comply or forced), the target's `pleasure`/`arousal` rises, and — per the already
  shipped `high_arousal_agility_accuracy_penalty` / `climax_in_progress_locks_actions` rows in
  `combat_modifiers.yaml` — the target's *own* subsequent action in the same or a later round may be
  degraded or locked outright, exactly the "emergent, not authored" pattern
  `sexual-resist-contest`'s own Decision 5 established for the resist score itself.
- If the act does not land (resist succeeds), none of that happens, so the target genuinely "proceeds
  normally" — no gauge changed, no modifier newly applies.

This is a strictly narrower, achievable reading that requires zero changes to the combat round loop,
and is consistent with this whole document set's recurring choice to let existing arousal-driven
modifiers carry combat consequences rather than authoring parallel bespoke ones (see also
`sexual-pleasure-model-design.md`'s repeated "requires no new rule" framing).

**Alternative considered:** implement a genuine turn-skip via a very-short-duration buff (mirroring
`paralysis_locks_actions`'s `actions_per_turn: 0` shape) applied to a complying/forced target.
Rejected for this proposal's scope — it would require this proposal (or its sibling) to decide the
buff's exact duration and interaction with the *existing* `climax_in_progress_locks_actions` lock
(double-applying a lock is meaningless; not applying it when climax hasn't triggered needs its own
rule), which is genuinely new balance surface this proposal's one-day sizing does not accommodate.
If a future playtest finds the emergent consequence insufficient, that is a follow-up proposal's
decision, not a silent addition here.

### Decision 3 — Broaden the relations snapshot from companions to every roster NPC

`_snapshot_party_surfaces` only captures `relations_data` for roster members whose `pk` is a
declared party companion (`party_ids(actor)`). Friendly fire is correctly scoped this way — it can
only ever target an ally-side companion by its own definition (`_scan_friendly_fire` filters on
`isinstance(target, NPC) and int(target.pk) in companion_pks`).

A sexual act's resister is not similarly restricted. The engine's own targeting rule ("Out of combat
there is no hostility model, so `SINGLE` may target anyone present" — `2026-07-29-ai-mud-engine-
design.md` §6.2) and nothing in `sexual-resist-contest`'s own scope restricts an in-combat resister to
declared companions either — an `NPC` present as any battlefield roster member (for example, a
`guild_exam` mode proctor, per `webclient-combat-menu`'s shipped `session.mode` values) is a
structurally valid resister.

If this proposal's scan penalizes a non-companion NPC's affinity and the round's outer transaction
later rolls back, `_restore_round_touched`'s existing `if party_before or members_before:` guard
would never restore that NPC's `relations_data` — the database write rolls back, but the idmapper's
in-process cache does not, leaving readers observing a value the transaction discarded. This is
exactly the class of bug `restore_relations_surfaces` exists to prevent for the companion case; this
proposal closes the same gap for the non-companion case by widening what gets snapshotted, not by
adding a second, parallel snapshot mechanism.

**Concretely:** the shipped `_snapshot_party_surfaces` has *two* levels of scoping, not one, and both
must be addressed — a gap this proposal's rubber-duck review caught in the original draft, which
described only the inner condition:

```python
companion_pks = set(party_ids(actor))
if companion_pks:                              # ← outer guard: skips the loop entirely
    for entity in battlefield.roster.values():  #   when the actor has zero companions
        pk = getattr(entity, "pk", None)
        if isinstance(pk, int) and pk in companion_pks:  # ← inner condition
            members_before[pk] = entity.db.party_member
            relations_before[pk] = entity.db.relations_data
```

Widening only the inner condition (`pk in companion_pks` → `isinstance(entity, NPC)`) is not enough:
the outer `if companion_pks:` early-return still skips the whole loop — leaving `relations_before`
empty — whenever the acting player has zero declared party companions, regardless of what the inner
condition would have matched. This is exactly the scenario this decision's own rationale uses to
motivate the change (a solo player with no companions coercing a present non-companion NPC, e.g. a
`guild_exam` proctor): under the original draft, `relations_before` would still end up empty for that
round, and the restore-guard widening below would have nothing to restore.

The fix removes the outer guard's gating effect on the `relations_before` population specifically, and
decouples the two dicts' population conditions, since only one of them is meaningfully
companion-scoped:

```python
companion_pks = set(party_ids(actor))
for entity in battlefield.roster.values():
    pk = getattr(entity, "pk", None)
    if not isinstance(pk, int):
        continue
    if isinstance(entity, NPC):
        relations_before[pk] = entity.db.relations_data   # every roster NPC, unconditionally
    if pk in companion_pks:
        members_before[pk] = entity.db.party_member        # only companions have party_member state
```

(This proposal renames/generalizes `_snapshot_party_surfaces` in place, or adds a sibling snapshot
merged into the same `relations_before` dict — an implementation choice for tasks.md, not a design
fork, since both produce the identical shape `_restore_round_touched` already consumes.) The restore
path (`_restore_round_touched`) needs no change beyond widening its own guard condition to also fire
when the (now-larger) `relations_before` mapping is non-empty even if `party_before`/`members_before`
are both empty (an all-companion-free battlefield with a non-companion NPC resister) — tasks.md 4.3
implements this guard change.

**Alternative considered:** add a second, independent snapshot dict scoped exactly to sexual-act
resisters, computed from the round's `EventLog` after the fact. Rejected — computing "which NPCs
might need a relations snapshot" from the very `EventLog` that is only produced *inside* the
transaction this snapshot must precede is circular; snapshotting must happen before the round runs,
which is why `_snapshot_party_surfaces` already takes this shape (pre-round, from the roster, not
post-round, from the log).

### Decision 4 — `sexual_forced_penalty` is a new, independently-tunable rulebook field

**This decision extends this proposal's file ownership beyond the overview document's original
table**, which listed only `world/rules/combat_session.py` and `world/rules/affinity.py`. Concrete
work during design revealed that a forced sexual act's penalty magnitude is a balance number, and
this codebase's own convention — demonstrated by every sibling proposal in this document set
(`sexual_pleasure.yaml`, `sexual_resist.yaml`, and the shipped `friendly_fire_penalty_per_hit` itself
in `affinity.yaml`) — is to keep balance numbers in a validated rulebook file, never hardcoded in
Python. `overview-design.md` §4.2's file-ownership table is updated in the same change as this
proposal to add `world/rules/affinity_config.py` and `world/rules/rulebook/affinity.yaml` to `B6b`'s
row, and this addition does not conflict with any other proposal in the full 22-proposal set — no
other proposal's file-ownership row lists either file.

`sexual_forced_penalty` is added to `affinity.yaml`'s top level, validated by
`affinity_config.py`'s loader with the same shape and the same non-negative-integer discipline
`friendly_fire_penalty_per_hit` already has, and `_TOP_LEVEL_FIELDS` gains the one new key.

**Why not reuse `friendly_fire_penalty_per_hit`'s existing value:** forcing a sexual act and
accidentally damaging a companion in melee are different categories of transgression with no reason
to share a magnitude forever. A future balance pass tuning one must not be forced to also retune the
other. A distinct field costs one YAML key and one validation line; conflating them would be a
modeling shortcut this codebase's existing granularity (`combat_modifiers.yaml`'s many distinct
per-source rows, `sexual_resist.yaml`'s own dedicated table) argues against.

**Alternative considered:** hardcode the penalty as a plain Python constant in `affinity.py`
(mirroring `NATURAL_CAP = 99`, which *is* a bare constant in that file). Rejected — `NATURAL_CAP` is
a structural invariant of the affinity system itself (the shape of the seven-stage ladder), not a
balance knob; `friendly_fire_penalty_per_hit`'s existing placement in `affinity.yaml` is the correct
precedent for a magnitude number, not `NATURAL_CAP`'s placement for a structural constant.

### Decision 5 — Out-of-combat symmetry is explicitly deferred, not silently dropped

The approved design states "Out of combat there is no turn economy. A successful resist simply fails
the act; the SP costs, state transitions, and affinity consequences are otherwise identical." Full
symmetry would require a scan equivalent to `_scan_sexual_coercion` at the out-of-combat cast path
(`world/rules/cast_settlement.py::settle_out_of_combat_cast`, or its caller
`commands/action.py::CmdCast._cast_out_of_combat`), neither of which is in this proposal's file
ownership, and neither of which appears in any other proposal's ownership row in the full 22-proposal
sequence either — a genuine gap in the original sequencing, discovered during this proposal's design.

This proposal does not expand to cover it, for two reasons: first, `cast_settlement.py`'s own
docstring describes carefully sequenced snapshot/transaction/clock-advance machinery this proposal
has not audited to the depth `sexual-resist-contest`'s and this proposal's own in-combat work
required, and doing so properly is realistically its own day of work; second, silently reaching into
an unowned, unaudited file to bolt on a small scan risks exactly the kind of under-verified change
this project's `AGENTS.md` warns against ("a deliberate skip is preferable to a fake implementation").

**Named as a follow-up:** a proposal (tentatively `sexual-resist-out-of-combat`) scoped to add the
symmetric scan at the out-of-combat cast path, once this proposal's `_scan_sexual_coercion` and its
`EventEntry` contract exist as a proven pattern to mirror. `overview-design.md` is updated to record
this as an addition to its implementation sequence in the same change as this proposal.

## Risks / Trade-offs

- **[Risk]** This proposal's scan has no production caller until `sexual-act-effects` lands and
  actually emits `"sexual_resist"`-kind entries, identical in shape to the risk `climax-settlement`
  accepted for `stage_climax_extension()`.
  → **Mitigation:** deliberate, matching this document set's parallelization strategy. This
  proposal's own tests construct synthetic `EventLog`s carrying the documented entry shape directly,
  so the scan is fully exercised without needing the sibling proposal's code to exist.
- **[Risk]** If `sexual-act-effects` ships an `EventEntry` whose `data` keys or types drift from this
  contract (e.g. a typo, or `"resisted"` as a string instead of a `bool`), `_scan_sexual_coercion`
  would silently treat it as "not forced" (via `.get(...) is False` returning `False` for a missing
  or mistyped key) rather than raising, since `_scan_friendly_fire`'s own precedent has no
  contract-violation error path either (it simply filters `entry.kind != "damage"`).
  → **Mitigation:** the contract is documented in this design, mirrored in the delta spec's own
  scenario text with exact field names, and — since this proposal's rubber-duck review found the
  original per-design.md-only documentation left `B5`'s batch-4 implementer with no obligation to
  discover it before `B6b` landed — now also fixed as `sexual-act-resolution-design.md` §3.4, the one
  shared source both `B5` and `B6b`'s implementers read regardless of batch order. A structural
  cross-proposal test is still out of scope for either proposal alone (neither can import the other's
  not-yet-existing module) but is recommended as part of whichever proposal lands second — this design
  doc records the recommendation rather than silently omitting it.
- **[Risk]** Broadening the relations snapshot (Decision 3) to every roster NPC, not only companions,
  adds a small per-round cost (one extra attribute read per non-companion NPC on the battlefield) to
  every round, including rounds with no sexual act at all.
  → **Mitigation:** bounded by the roster size already iterated for other per-round work
  (`_end_of_round_upkeep` already iterates every roster member); no new query is added, matching
  `climax-settlement`'s own accepted precedent for a comparable O(1)-per-entity addition to existing
  per-round iteration.
- **[Trade-off]** Decision 2 declines to build a literal turn-skip mechanic, which is a narrower
  reading of "consumes the target's turn" than the approved design's prose might suggest to a reader
  expecting an explicit skip. Accepted: the achievable, already-shipped-mechanism-reusing reading
  keeps this proposal to one day of work and avoids inventing new balance surface (buff duration,
  interaction with the existing climax lock) that the approved design does not itself specify with
  enough precision to implement safely today.
- **[Trade-off]** Decision 5 ships an intentionally asymmetric system (`B6b` lands, out-of-combat does
  not) until a follow-up proposal closes the gap. Accepted and explicitly named rather than hidden,
  consistent with this document set's established practice of recording every known gap plainly
  (`climax-settlement`'s own design.md did the same for the resist opening this proposal's sibling
  now fills).

## Migration Plan

None. The project has no released users (`AGENTS.md`); no backward-compatibility layer or data
migration is required. This proposal adds one enum member, one config field, one new function, and
widens one existing snapshot's scope — no existing call site's observable behavior changes for any
round that does not involve a forced sexual act.
