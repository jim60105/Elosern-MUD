## ADDED Requirements

### Requirement: Combat boundaries emit observability events

`submit_player_action` SHALL emit one `combat_round_settled` info event
through the `world.observability` facade whenever an ordinary round commits,
with `char`, `opponent`, `tick`, `hp_before`, and `hp_after` context, and one
`settlement_done` info event when a terminal settlement commits, with `char`,
`ms`, and notification-count context. Events MUST be emitted after the
round's durable commit and MUST NOT alter the atomic round/settlement unit.

#### Scenario: A committed round leaves one boundary event

- **WHEN** an ordinary combat round commits durably
- **THEN** exactly one `combat_round_settled` event is logged with the
  combatant identities and HP delta in context

#### Scenario: A rolled-back round emits no settlement event

- **WHEN** a round's settlement fails and the whole unit rolls back
- **THEN** no `settlement_done` event is logged for that attempt
