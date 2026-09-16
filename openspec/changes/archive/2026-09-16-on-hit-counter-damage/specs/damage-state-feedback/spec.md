## ADDED Requirements

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
