# altoria-hospitality Specification

## Purpose
Give the capital a tavern, an inn and a public bathhouse — permanent
hospitality interiors whose hosts teach, by conversation alone, what their
rooms exist for. The rooms land as narrative homes for commands the world
already has (rest, sleep, practice, talk, invite): no lodging fee, drink
effect or bathing mechanic is invented, because the source document leaves all
three unproposed.

## Requirements

### Requirement: The capital has a tavern, an inn and a bathhouse
The capital SHALL carry three hospitality locations — a tavern, an inn and a public bathhouse —
each a permanent interior with an authored host who converses. The inn and the tavern SHALL
share one exterior, because an inn lane with both on it is one street.

#### Scenario: All three exist and are enterable
- **WHEN** synchronization completes
- **THEN** each of the three interiors exists once, is reachable from and back to its exterior,
  and holds one host carrying a dialogue capability

### Requirement: A hospitality location adds no mechanism it does not have
None of the three SHALL introduce a command, a cost, a state effect or a persisted field.
Resting, sleeping, practising, conversation and party invitation SHALL behave inside them
exactly as they behave anywhere else, and SHALL NOT require being inside them. Lodging charges,
drinking or gambling effects and bathing effects are unproposed in the source document; landing
the room SHALL NOT be treated as licence to invent them.

#### Scenario: Resting in the inn is resting anywhere
- **WHEN** a player rests, sleeps or practises inside the inn and outside it
- **THEN** the outcome and the clock cost are identical, and no charge is taken

#### Scenario: No new command or persisted state arrives with the rooms
- **WHEN** the command set and the persisted attribute set are compared before and after
- **THEN** they are unchanged

### Requirement: Each host's dialogue teaches what its location is for
A hospitality host's dialogue SHALL name the commands its location exists to host, so the
affordance is discoverable by talking to the person standing in it rather than only by reading
external documentation.

#### Scenario: Talking to a hospitality host surfaces its affordances
- **WHEN** a player talks to each of the three hosts
- **THEN** the innkeeper's lines name resting and practising, and the tavern keeper's name
  conversation and party invitation
