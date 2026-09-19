# damage-state-feedback Specification

## Purpose
Define reusable passive reactions to actual damage and new negative buffs, and state-dependent recovery benefits independent of equipment or profession names.

## Requirements

### Requirement: Damage feedback follows actual loss and newly accepted negative instances
A qualified passive SHALL react once to each positive actual HP loss and each newly accepted negative buff instance, using an authored gain proportional to the harm actually suffered, applied through the canonical state writer. For an HP-loss event the gain SHALL be derived from the ratio of that event's actual loss to the recipient's maximum HP, scaled by the table's authored coefficient and floored to a whole number. For a newly accepted negative buff instance, which carries no HP loss, the gain SHALL be the same derivation applied to an authored flat fraction of maximum HP. Spell, item, rulebook and periodic-damage sources SHALL share this behavior and SHALL be priced identically for an identical loss: the source's tier, school and spell-or-not nature SHALL NOT affect the gain. A recipient whose maximum HP is unreadable or not positive SHALL produce no gain rather than a guessed one. Misses, zero loss, healing, resource costs, immunity and instance refresh SHALL not trigger.

The retired source-tier gain mapping SHALL NOT be loadable: a `pleasure_gain` authored as a tier-keyed mapping SHALL fail closed at rule load naming the rule id. Source tier SHALL retain every other role it has, including capture at application for periodic effects and grant-time attribution for source-targeted actions.

#### Scenario: Different damage sources share the reaction
- **WHEN** a synthetic passive owner suffers direct spell, item and periodic damage of equal actual loss
- **THEN** each actual loss causes the configured gain exactly once, and all three gains are equal because the gain reads the loss rather than the source

#### Scenario: A larger loss is worth proportionally more
- **WHEN** a synthetic passive owner suffers one loss of a tenth of maximum HP and, separately, one loss of half of maximum HP
- **THEN** the second gain is five times the first

#### Scenario: A full journey costs half of maximum HP
- **WHEN** a synthetic passive owner at the post-climax baseline suffers cumulative losses totalling half of maximum HP
- **THEN** the accumulated gain reaches the threshold band that opens the climax gate

#### Scenario: A no-loss negative instance uses the flat fraction
- **WHEN** a synthetic passive owner newly accepts a negative buff instance that inflicts no HP loss
- **THEN** the gain equals the authored flat fraction of maximum HP, and is smaller than the gain from a loss of a tenth of maximum HP

#### Scenario: An unreadable maximum produces no gain
- **WHEN** a synthetic passive owner whose maximum HP is unreadable or not positive suffers an actual loss
- **THEN** no gain is applied and no state write occurs

#### Scenario: A tier-keyed gain mapping fails at load
- **WHEN** a rule authors `pleasure_gain` as a source-tier-keyed mapping
- **THEN** rule loading raises naming that rule id

#### Scenario: Immune and refresh outcomes do not count
- **WHEN** a negative buff is refused by immunity or only refreshes an existing instance
- **THEN** there is no new-instance feedback

#### Scenario: New debuff and its ticks are distinct
- **WHEN** a new damaging debuff is accepted and later ticks twice
- **THEN** the new-instance event and each positive-loss tick independently trigger once

### Requirement: Feedback cascades remain within the initiating transaction
Feedback that changes arousal or phase SHALL use canonical transitions and phase reactions without recursive damage-event loops. The initiating action, item or world-clock transaction SHALL capture and restore every transitive state surface. A failed settlement SHALL leave neither the triggering loss/buff nor resulting pleasure/phase/marker changes.

#### Scenario: Feedback can enter the normal lock phase
- **WHEN** a configured damage gain crosses the recipient into in-progress
- **THEN** normal phase reactions and action locking occur without inventing a second state system

#### Scenario: Late failure restores the complete cascade
- **WHEN** an item or clock settlement fails after feedback activates a phase marker
- **THEN** HP, negative buff state, pleasure, phase, counters and marker all restore

### Requirement: Recovery-only passive adjustment composes once and is snapshotted
A configured passive SHALL provide a state-derived recovery-only modifier independent of equipment. Recovery profiles SHALL capture it on application, while ordinary direct heals and already state-scaled sacramental effects SHALL not receive it again. Existing equipment healing modifiers SHALL compose once through their own stage. Numeric conferred adjustments SHALL retain existing fractional semantics without granting binary event reactions.

#### Scenario: Equipment-independent recovery
- **WHEN** a synthetic passive owner with no equipment applies a recovery profile at a nonzero state ordinal
- **THEN** ticks include the configured captured benefit even after source state changes

#### Scenario: No duplicate sacramental multiplier
- **WHEN** the same owner uses a direct state-scaled heal and a periodic recovery profile
- **THEN** only the configured recovery profile receives the extra recovery-only modifier

### Requirement: A qualifying physical strike dispatches one source-attributed on-hit event
The damage settlement SHALL dispatch exactly one `physical_hit` outcome reaction to the struck target when a physical-school strike lands positive actual HP loss, carrying the attack's source entity and the strike's captured source tier through the existing outcome-reaction dispatch path. A magic-school strike, a miss, a zero-actual-loss write, a buff rate tick, a divert leg and an already-dead target SHALL dispatch nothing new. Every existing outcome event (`hp_loss`, `mp_zero`, `negative_buff_added`) SHALL keep its dispatch points, payloads and exactly-once crossings byte-identically. Rule loading SHALL recognize `physical_hit` within a CLOSED `when.event` vocabulary (`hp_loss`, `mp_zero`, `negative_buff_added`, `physical_hit`) and reject any other event value fail-closed at load naming the rule — closing the enum that today loads unknown event values silently as never-firing rules.

#### Scenario: A landed physical hit fires the event once with its source
- **WHEN** a synthetic physical strike from caster A lands positive HP loss on a target while a synthetic `physical_hit`-keyed reaction rule is loaded
- **THEN** the rule executes exactly once for that strike against the target, and its action sees A as the event source with the strike's captured tier

#### Scenario: Non-qualifying writes stay silent
- **WHEN** a magic strike, a missed physical swing, a zero-loss physical write and a damaging rate tick all settle against the same reactor
- **THEN** the `physical_hit` rule executes zero times while each source's existing `hp_loss` behavior is unchanged

#### Scenario: An unknown event value fails the load closed
- **WHEN** a synthetic rule file declares `when.event: turned_to_stone`
- **THEN** rule loading raises naming the rule id, and the shipped rule file loads unchanged

#### Scenario: Multi-strike policies fire per qualifying strike
- **WHEN** a policy-declared double-strike lands both strikes physically on the reactor
- **THEN** the event dispatches once per landing strike, each carrying the same source, and a first miss dispatches nothing for the missed strike

### Requirement: Source-targeted reaction actions settle once, in-transaction, without recursion
The reaction `then` vocabulary SHALL grow exactly two source-targeted actions, both validated fail-closed at rule load (every existing `apply_buff`/`remove_buff`/`pleasure_gain` shape preserved verbatim): `counter_damage: <coefficient>` settling one immediate counter strike onto the event's source — physical magnitude from the holder's effective attack times the declared finite positive coefficient, defense subtracted ordinarily, no hit roll — and `apply_buff_to_source: <definition-key>` applying the named loaded definition to the source through the shipped public buff-application entry point with grant-time attribution from the event source. Both SHALL settle inside the initiating damage's commit transaction so a later settlement failure rolls the counter HP, the applied instance and the initiating loss back together. The counter strike SHALL dispatch the source's ordinary `hp_loss` outcome exactly once for its actual loss and SHALL NEVER dispatch `physical_hit`; the buff-application leg SHALL dispatch the shipped new-negative-instance reaction only. A source that is dead or unresolvable contributes no counter damage and no buff write; a source wearing debuff immunity receives no applied debuff; a protected (nonlethal) source floors through the existing knockout policy with at most one terminal settlement. Reaction dispatch for one `physical_hit` SHALL complete without re-entering `physical_hit` dispatch on any entity.

#### Scenario: A thorn-shaped counter returns coefficient-priced damage to the attacker
- **WHEN** a synthetic reactor with a `physical_hit` + `counter_damage: 1.0` rule is hit for positive physical loss by a living attacker
- **THEN** the attacker loses the holder's effective-attack × 1.0 amount minus its ordinary defense exactly once, the initiating strike's damage and practice settlement are unchanged, and the attacker's own `hp_loss` reactions fire once for the counter's loss

#### Scenario: Counters cannot chain
- **WHEN** the attacker also holds a `physical_hit` + `counter_damage` rule of its own
- **THEN** only the struck reactor's counter settles for the initiating strike, the attacker's rule does not execute on the counter's loss, and HP movement terminates after one counter per strike

#### Scenario: The counter settles and rolls back with its round
- **WHEN** a synthetic settlement fails at a commit step after the counter already moved HP
- **THEN** the initiating loss, the counter HP and every staged surface restore together, leaving neither party changed

#### Scenario: An ignite-shaped source buff rides the same event as data
- **WHEN** a synthetic reactor with a `physical_hit` + `apply_buff_to_source` rule is hit physically by a living attacker not immune to the named debuff, and separately by an immune attacker and a sourceless write
- **THEN** the first attacker holds the live instance with grant-time attribution to the reactor, the immune attacker holds nothing, the sourceless write applies nothing, and no counter vocabulary is involved

#### Scenario: Malformed source actions fail the rule load closed
- **WHEN** rules declare `counter_damage: -1`, `counter_damage: abc`, a boolean coefficient, `apply_buff_to_source` naming an unknown definition, both source actions in one `then`, or a source action alongside a legacy action
- **THEN** each raises at load time naming the offending rule id, and every previously valid rule file loads unchanged

### Requirement: The outcome-reaction vocabulary grows one declarative order-marker action
The reaction `then` vocabulary SHALL grow exactly one order-operation action, `mark_order_op`,
naming a buff definition that itself declares an in-round order operation — validated fail closed
at rule load (an unknown definition, or a definition without the order clause, names the offending
rule id; every existing `apply_buff`/`remove_buff`/`pleasure_gain`/`counter_damage`/
`apply_buff_to_source` shape is preserved verbatim). At dispatch the action applies the named
definition as a live instance onto the outcome event's source with the same grant-time attribution,
in-transaction settlement, rollback coverage, sourceless-write no-op, and once-per-event semantics
as the shipped source-targeted actions, and SHALL itself perform no initiative-sequence mutation —
the round loop's declarative fold is the sole consumer of the mounted marker. The action SHALL NOT
combine with the two shipped source-targeted actions in one `then`.

#### Scenario: A ward-shaped rule marks the strike's source
- **WHEN** a synthetic reactor holding the gating buff is struck physically by a living attacker
  while a `physical_hit` rule declaring `mark_order_op` on a retreat-declaring definition is loaded
- **THEN** the attacker holds the live marker instance attributed to the reactor at grant time, the
  initiating strike's damage and practice settlement are unchanged, and no initiative sequence is
  mutated by the dispatch itself

#### Scenario: Sourceless and gated writes apply nothing
- **WHEN** a sourceless write and a strike by an attacker whose mount the rule no longer matches
  settle against the same reactor
- **THEN** no marker instance is applied in either case and every other shipped reaction behavior
  on the reactor is unchanged

#### Scenario: A malformed order-marker rule fails the rule load closed
- **WHEN** rules declare `mark_order_op` naming an unknown definition, a definition without the
  order clause, a bare non-key value, or `mark_order_op` alongside `counter_damage` or
  `apply_buff_to_source`
- **THEN** each raises at load time naming the offending rule id, and every previously valid rule
  file loads unchanged

### Requirement: A qualified passive self-recovers once on canonical climax entry

A qualified passive SHALL restore its holder's HP when that holder canonically enters the in-progress climax phase. The restored amount SHALL be an authored fraction of the holder's maximum HP, floored to a whole number, and SHALL cost no resource of any kind — no MP, no SP, no action, no cast.

The restoration SHALL occur exactly once per canonical entry into that phase: it SHALL be driven by the phase *transition*, never by the phase state, so a climax extension or any other event occurring while the holder is already in that phase SHALL restore nothing further. A holder who does not qualify for the passive SHALL receive nothing.

The trigger SHALL be the phase entry alone. The restoration SHALL NOT depend on how the holder's arousal was accrued: a climax reached entirely outside combat, through stimulus carrying no HP loss, SHALL pay out exactly as one reached through damage. The passive is therefore both the damage loop's third leg and a deliberate out-of-combat recovery option, priced by the climax's own existing costs rather than by a provenance check.

The restoration SHALL be clamped to the holder's missing HP, SHALL never raise HP above maximum, and SHALL never apply to a holder at or below zero HP — it restores, it does not revive. A holder whose maximum HP is unreadable or not positive SHALL receive nothing rather than a guessed amount.

The restoration SHALL settle inside the transaction that performed the phase transition, so a later failure in that settlement restores the HP, the phase and the pleasure gauge together.

#### Scenario: Entering climax restores the authored fraction

- **WHEN** a synthetic qualified holder missing more than the authored fraction of its maximum HP canonically enters the in-progress climax phase
- **THEN** its HP increases by the floored authored fraction of maximum HP, and no MP, SP or action is consumed

#### Scenario: A second stimulus during climax restores nothing further

- **WHEN** a synthetic qualified holder that already entered the in-progress climax phase receives a further qualifying stimulus without leaving that phase
- **THEN** its HP is unchanged by the passive

#### Scenario: A climax reached without any damage pays out identically

- **WHEN** a synthetic qualified holder missing more than the authored fraction of its maximum HP reaches the in-progress climax phase entirely through stimulus that inflicted no HP loss
- **THEN** its HP increases by the same floored authored fraction as a damage-driven climax would have restored

#### Scenario: A holder without the passive receives nothing

- **WHEN** a synthetic holder that does not qualify for the passive canonically enters the in-progress climax phase
- **THEN** its HP is unchanged

#### Scenario: The restoration cannot overheal

- **WHEN** a synthetic qualified holder missing less than the authored fraction of its maximum HP enters the in-progress climax phase
- **THEN** its HP rises to exactly its maximum and no surplus is carried anywhere

#### Scenario: The restoration never revives

- **WHEN** a synthetic qualified holder at or below zero HP would enter the in-progress climax phase
- **THEN** no HP is restored

#### Scenario: An unreadable maximum restores nothing

- **WHEN** a synthetic qualified holder whose maximum HP is unreadable or not positive enters the in-progress climax phase
- **THEN** no HP is restored and no write occurs

#### Scenario: A failed settlement restores the whole cascade

- **WHEN** the transaction that performed the phase transition fails after the passive restored HP
- **THEN** HP, climax phase and the pleasure gauge are all restored to their pre-transaction values

#### Scenario: A malformed self-recovery fraction fails at load

- **WHEN** a rule authors the self-recovery action with a fraction that is not a finite number in the open-closed range from zero to one
- **THEN** rule loading raises naming that rule id
