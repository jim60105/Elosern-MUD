# defeat-aftermath-violation-sequence Specification

## Purpose

Define the deterministic adult violation sequence that rides the defeat
aftermath's guarded hook: archetype-keyed victory arousal and attempt caps,
state-derived sequence dice, the shipped resist contest with the victim
defending, per-attempt world-clock advances, the first-resistance violator
stop with its zero-landed PG variant, the full allied-participant victim
pool with per-victim writes and companion wake observations, and the
in-memory digest-ready outcome handoff.

## Requirements

### Requirement: Living defeat winners gain archetype victory arousal
On a hostile defeat with the adult path enabled, each living foe-team
monster SHALL gain the pleasure points its archetype's row in
`world/rules/rulebook/defeat_aftermath.yaml` declares, applied through the
existing pleasure-counter path (arousal is derived). Points accumulated
during the fight — including the player's own sexual-skill casts and the
monster's own catalog acts — SHALL count toward the violation threshold;
the victory delta is added on top, never replacing it. Clamping follows the
existing counter bounds (overflow discarded).

#### Scenario: Arousal carries over from the player's own mid-fight sexual casts
- **WHEN** the player raised a winning monster's pleasure mid-fight so its derived arousal ordinal sits one step below the archetype threshold, and the victory delta is two steps
- **THEN** the monster's post-victory arousal is at or above the threshold and the sequence begins

#### Scenario: Pleasure overflow clamps without wrapping
- **WHEN** a victory delta would push a monster's pleasure counter past its maximum
- **THEN** pleasure rests at the maximum and arousal reflects the clamped ordinal

### Requirement: Violation sequence runs per archetype threshold with an archetype attempt cap
For each living winner whose post-victory derived-arousal ordinal is ≥ its
archetype's declared threshold ordinal, the aftermath SHALL run at most the
archetype's declared attempt cap of violation attempts. Archetype rows SHALL
validate their keys against the monster lore registries at rulebook load
(fail closed), and a monster whose archetype has no row SHALL never start a
sequence.

#### Scenario: Below-threshold winner never violates
- **WHEN** a winning goblin's post-victory arousal ordinal is below the goblin threshold
- **THEN** zero violation EventLog entries are emitted for it and the core PG path proceeds

#### Scenario: Missing archetype row is inert
- **WHEN** a winner's archetype has no registry row
- **THEN** no sequence runs for it and one `log_warn` facade event records the miss

### Requirement: Sequence dice are state-derived pure values
Every d100 the sequence rolls SHALL be produced by a pure derivation keyed
on durable record state (session id, violator identity, victim identity,
attempt index) — the session persists no RNG cursor and the sequence
mutates no RNG state. A rolled-back settlement retried from the same
durable state SHALL therefore produce byte-identical rolls, with no replay
bookkeeping of its own.

#### Scenario: A rolled-back settlement re-derives the identical sequence
- **WHEN** a defeat settlement is injected to fail after the first attempt, rolls back, and is retried through the recovery fallback
- **THEN** the second run's full attempt sequence (rolls, targets, deltas) equals the first run's deterministically

### Requirement: Violation attempts select victims from the target pool
The violation target pool SHALL be every non-fled allied participant — the
defeated player plus each companion in the battlefield's knocked-out set.
Companions that fled the session SHALL be excluded; the player SHALL always
be in the pool. Each attempt's victim SHALL be selected deterministically
through the state-derived dice helper (session id + violator identity +
attempt index), and every write SHALL land on the selected victim's own
records: its `SexualState`, its credited counters, its EventLog entries —
never proxied through the player. A solo party (player only) SHALL behave
exactly as the pinned player-only baseline, and a party whose every other
allied member fled SHALL settle without error.

#### Scenario: Solo party matches the pinned baseline
- **WHEN** a solo player is defeated by a violator with cap 3 and every attempt lands
- **THEN** all three attempts target the player, identical to the player-only baseline the violation change pins

#### Scenario: Knocked-out companions enter the pool and take their own writes
- **WHEN** a party of the player plus one knocked-out (non-fled) companion is defeated by one violator with cap 2 and the state-derived selection picks the companion once
- **THEN** that attempt's deltas, counter credits, and `violation_act` entry land on the companion's own records and the violator's counters credit symmetrically per the shared crediting convention

#### Scenario: Fled companions are excluded
- **WHEN** the companion fled before the session settled defeat
- **THEN** no attempt targets the companion and its records are untouched

#### Scenario: The player's wake prose keys on her own landed attempts
- **WHEN** every landed attempt of the sequence targeted a companion victim
- **THEN** the player's `defeat_settle` wake prose stays the PG line and the companion victim's wake observation renders for the companion

### Requirement: Each attempt rolls the shipped resist contest with the victim defending
Each attempt SHALL roll exactly one resist contest by calling the existing
pure `resist_verdict(actor, resister, *, rng)`
(`world/rules/sexual_resist.py`) with the selected victim as `resister` and
the state-derived roll injected through its `rng` parameter — no formula is
extracted, copied, or re-tuned. A landed attempt applies the row's full
declared state deltas and credits the declared lifetime counters
symmetrically (victim and aggressor each credited per the shared
`participant` crediting convention). A resisted attempt applies only the
row's declared resisted-shrink deltas and its duration.

#### Scenario: A landed attempt writes deltas and credits both bodies
- **WHEN** a landed attempt declares pleasure/arousal deltas and `interspecies_act_count`
- **THEN** the victim's and the aggressor's sexual state reflect exactly the declared deltas and both counters increment by one

#### Scenario: A resisted attempt shrinks the deltas
- **WHEN** the victim wins the resist roll
- **THEN** only the resisted-shrink deltas apply and one `violation_resisted` EventLog entry records the contest outcome

### Requirement: First successful resistance cancels that violator's remaining attempts
When one of a violator's attempts is resisted, that violator SHALL stop:
the resisted attempt's shrunk deltas and declared duration are its last.
When every violator stops without any attempt landing, the settlement
continues on the core PG path with the PG wake template. No violation
mechanics beyond the declared deltas differ between the variants.

#### Scenario: A resisted violator stops at its first resistance
- **WHEN** an archetype row caps three attempts and the victim resists the first roll
- **THEN** exactly one violation EventLog group exists for that violator (the resisted attempt), no further attempts follow from it, and the wake lines use the PG template

#### Scenario: All-landed sequence runs to the cap
- **WHEN** every attempt of a capped violator lands
- **THEN** that violator executes exactly `attempt_cap` attempts

### Requirement: Each attempt advances the world clock by its declared duration
Each executed attempt SHALL advance the world clock with source
`defeat_aftermath` by exactly the attempt duration its archetype row
declares, before the next attempt begins.

#### Scenario: Three attempted acts spend three declared durations
- **WHEN** a sequence executes three attempts of declared duration D
- **THEN** the world clock advances by exactly 3×D from the sequence with source `defeat_aftermath`

### Requirement: The sequence registers into the core's guarded hook and emits declared EventLog kinds
The violation body SHALL register as the body of the
`DEFEAT_ADULT_SCENES`-guarded hook the core change declares — this change
adds no settings flag and no second guard — and SHALL be read once at hook
entry (no mid-sequence toggle semantics). It SHALL emit the new
open-vocabulary EventLog kinds `violation_attempt`, `violation_resisted`,
and `violation_act` between the core's `defeat_settle` and
`violator_depart` entries, authoring each kind's zh-tw offline template
line in this change. With the flag off, the settled state SHALL be exactly
the `defeat-aftermath-core` behavior.

#### Scenario: Switch off reproduces the core settlement exactly
- **WHEN** the same defeat settles with the switch true and with the switch false
- **THEN** the false-run state equals the core-only settlement (no violation EventLog entries, no act deltas) and the core's declared writes are otherwise identical

### Requirement: The sequence hands digest-ready outcomes to the same settlement call
At sequence end, the sequence engine SHALL return, in memory only (never
persisted), one immutable outcome per selected participant — selected
count, landed count, resisted count, climax delta, and a zero-landed
flag — to the settlement call graph for the digest phase's use. The
outcome is a pure derivation of the state-derived dice and declared rows,
so a settlement replay reproduces it without storage.
The climax delta counts climax onsets: one per `violation_act` entry
whose victim-side application pushed the victim's climax phase into
進行中, which keeps the outcome's counts equal to the EventLog's entry
counts by construction.

#### Scenario: The digest input object matches the emitted EventLog
- **WHEN** a sequence of mixed landed/resisted attempts completes
- **THEN** the returned per-participant outcome's landed/resisted/climax counts equal the violation EventLog entries' counts for that participant, and no new persisted record exists for the outcome

### Requirement: Knocked-out companions wake with their own digest observation
At sequence end each non-fled companion victim SHALL carry its own
per-participant digest observation (the same in-memory outcome shape as the
player's: selected/landed/resisted/climax/zero-landed), and settlement
SHALL emit its zh-tw wake observation line. No companion state kinds beyond
the existing `SexualState` fields are introduced.

#### Scenario: Companion wake observation is emitted
- **WHEN** a sequence ends with one knocked-out companion victim
- **THEN** the returned outcome set contains that companion's counts and one companion wake line is rendered for it
