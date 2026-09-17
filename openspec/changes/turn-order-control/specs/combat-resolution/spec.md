## RENAMED Requirements

- FROM: `### Requirement: actions_per_turn: 0 skips a combatant's turn before ActionResolver is called`
- TO: `### Requirement: The turn loop consumes actions_per_turn as the round's action count, with zero skipping before ActionResolver is called`

## MODIFIED Requirements

### Requirement: The turn loop consumes actions_per_turn as the round's action count, with zero skipping before ActionResolver is called
`world/rules/combat.py`'s `run_round()` SHALL consult each acting combatant's combat-modifier
evaluation (the merged bundle and the matched rules' per-rule bundles) and consume the table's
`actions_per_turn` output as that combatant's action count for the round. The zero-lock decision
SHALL read the matched rules' per-rule zero-action results — an
entity matching any zero-action rule SHALL have its turn skipped entirely (producing an `EventLog`
with kind `"action_skipped"`) without calling `ActionResolver.resolve()` exactly as before this
widening, and a co-existing positive grant rule can never unlock that skip — while every entity not
locked SHALL provision its count from the merged bundle's positive `actions_per_turn` value. The
loop SHALL provision exactly that many action slots for the combatant at the combatant's single
sequence position, each slot
re-checking the round's liveness predicate (fled, knocked out, or depleted) before requesting an
action so a combatant defeated or knocked out by an earlier actor's settlement loses its remaining
slots without an event; the round's settlement stays one transaction per round either way. A
positive count beyond the loop's declared maximum provisions the maximum (a documented fuse, never
a silent unbounded loop). An absent key means one action, so every bundle shipped before this
widening — none of which co-matches a grant with a lock — resolves byte-identically. This check
SHALL read the combat-modifier rules' output keys only, with no branch distinguishing which
underlying rule (poison, paralysis, arousal, climax phase, or an extra-action grant) produced the
value.

#### Scenario: A climax-in-progress combatant's turn is skipped, not attempted
- **WHEN** `evaluate_combat_modifiers(entity)` returns `{"actions_per_turn": 0}` for the acting
  combatant
- **THEN** `ActionResolver.resolve()` is never called for that combatant this round, and the round's
  event list contains an `"action_skipped"` entry naming that combatant

#### Scenario: No source-level branch distinguishes the modifier's origin
- **WHEN** `world/rules/combat.py`'s source is inspected
- **THEN** it contains no conditional that special-cases a sexual-origin `actions_per_turn` modifier
  differently from a buff-origin one — both are read from the identical bundle key

#### Scenario: An absent or one-valued key resolves exactly one action
- **WHEN** a round runs with every combatant's bundle carrying no `actions_per_turn` key or the
  value `1`
- **THEN** each capable combatant receives exactly one provider interaction and the round's event
  sequence matches the pre-widening behaviour value-for-value

#### Scenario: A count of two grants a second slot at the same position and a mid-round defeat cuts it
- **WHEN** a synthetic bundle gives one combatant `actions_per_turn: 2`, the provider returns a
  resolvable request for both slots, and a separate fixture has an earlier actor's strike defeat or
  knock out that combatant after its first slot lands
- **THEN** the first fixture's combatant resolves two provider interactions inside the one round
  transaction with both events ordered after its original sequence position, and the second
  fixture's combatant resolves only its first slot with no event and no provider call for the
  cut slot

#### Scenario: A runaway bundle hits the fuse, not an unbounded loop
- **WHEN** a synthetic merge produces an `actions_per_turn` value above the loop's declared maximum
- **THEN** the combatant provisions exactly the declared maximum number of slots and round
  resolution completes without error

#### Scenario: An action lock dominates a co-existing grant
- **WHEN** a synthetic combatant simultaneously matches a shipped-shaped `actions_per_turn: 0`
  lock rule and a `+1` extra-action grant rule whose generic numeric merge alone would read as a
  positive count
- **THEN** the lock leg is evaluated first and skips the combatant's whole turn (chance rules
  resolving per the chance requirement) with no provider call, exactly as a lone lock does today

## ADDED Requirements

### Requirement: The round loop folds declarative in-round order operations into its sequence
`world/rules/combat.py`'s round loop SHALL treat the initiative sequence as a per-round snapshot
that declarative position markers may reshape before each remaining combatant's turn: a live buff
instance whose definition declares an in-round order operation relocates its holder's not-yet-acted
key within the snapshot — an advance operation moves the key ahead of the combatants still to act,
a retreat operation moves it behind them — with same-key operations collapsing last-declared-wins.
An operation naming a combatant that already acted this round, fled, or was never in the sequence
SHALL be a silent no-op. Effect resolution SHALL NEVER mutate the initiative sequence directly;
the marker instances are the single declarative source the loop reads, and the next round's
sequence SHALL be produced by the untouched round-start roll. The shipped opening-only first-actor
override and its move-to-head semantics SHALL stay exactly as written.

#### Scenario: An advance marker moves a not-yet-acted combatant ahead of the remaining tail
- **WHEN** a synthetic buff instance declaring an advance operation is live on a combatant that has
  not acted yet this round, applied before its original turn by an earlier actor's settlement
- **THEN** that combatant acts ahead of every other combatant still to act this round, every other
  key's relative order is unchanged, and the following round's order is again the rolled order

#### Scenario: A retreat marker pushes hit combatants to the tail and cannot reach an already-acted key
- **WHEN** a settlement applies a retreat-declaring marker instance to a struck combatant that has
  not acted yet this round, and an identical instance lands on a combatant that already acted
- **THEN** the first combatant moves behind every combatant still to act this round while the
  second keeps its completed turn with no further action, and no round's rolled sequence is mutated

#### Scenario: Actions stay one-per-slot through a relocation
- **WHEN** a combatant is relocated by an order operation and its action count for the round is
  taken from the modifier bundle
- **THEN** the relocation changes only WHEN the combatant acts, never HOW MANY times, and the
  combatant's action count is not altered by any order operation

### Requirement: A declared action-loss chance gates the round skip with one recorded roll
A combat-modifier rule's zero-action lock MAY declare a probability for the loss, validated fail
closed at rule load (the declaration is legal only alongside a zero action count, within the closed
percentage range). The decision SHALL read the matched rules' per-rule bundles: any matched
zero-action rule WITHOUT a declared chance SHALL force the certain skip regardless of co-existing
chances, and otherwise the maximum declared chance among matched zero-action rules SHALL decide.
`evaluate_combat_modifiers()` and its shipped generic merge SHALL stay pure reads that never roll,
and the round loop's skip leg SHALL be the sole consumer: for a chance-decided zero the loop rolls
exactly once per affected combatant per round using the shared dice seam — at or under the decided
chance the shipped skip event is produced with its roll and chance recorded in the event data;
above it the combatant acts normally. An undeclared-zero lock with no co-existing chance SHALL skip
with certainty exactly as shipped; a chance-decided winner SHALL provision its action slots from
the merged bundle's positive `actions_per_turn` value with a floor of one action exactly like an
entity whose turn was never locked (co-matching grant rules count toward that count), and the
side-effect-free action preview SHALL keep reporting the deterministic bundle state without ever
consuming the roll.

#### Scenario: A chance-bearing lock skips on a losing roll and acts on a winning one
- **WHEN** a synthetic lock rule declares a chance on its zero-action `then` and fixed dice make one
  gated combatant lose and another win the per-round contest
- **THEN** the loser produces the `action_skipped` event whose data records the declared chance and
  the consumed roll, the loser takes no action, and the winner resolves its normal action with no
  skip event

#### Scenario: A certainty co-existing with a chance still skips and the highest chance wins
- **WHEN** one gated combatant matches both a chance-bearing zero-action rule and a chance-free
  certain zero-action rule under fixed winning dice, and another combatant matches two
  chance-bearing zero-action rules of different declared values
- **THEN** the first combatant skips regardless of its dice — a declared chance can never
  probabilistically unlock a co-existing certainty — and the second combatant's contest is decided
  by the higher declared chance alone

#### Scenario: Modifier evaluation and preview never roll
- **WHEN** `evaluate_combat_modifiers()` and the side-effect-free action preview run against a
  chance-bearing lock's holder
- **THEN** both return their deterministic bundle/preview result, no dice value is consumed, and
  the resolution-time roll remains the single authoritative decision

#### Scenario: A malformed chance fails the rule load closed
- **WHEN** a rule declares a chance outside the closed range, on a non-zero `then` value, with a
  non-integer, or as a boolean
- **THEN** rule loading raises naming the offending rule id, and every previously valid rule file
  loads unchanged
