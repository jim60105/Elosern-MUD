## ADDED Requirements

### Requirement: A session admits at most one scheduled puppet transition at a time
A session that already has a puppet transition scheduled from an accepted
`account.character.switch` or `account.character.create` SHALL refuse any further
`account.character.switch` or `account.character.create` submitted before that transition
finishes, with the stable code `transition_pending` and a safe Traditional Chinese message,
scheduling no further transition. This holds regardless of which of the two actions scheduled the
pending transition and regardless of which of the two actions is being refused: a scheduled switch
blocks a subsequent create and a scheduled create blocks a subsequent switch, because either one
changes the same session's puppet. The refusal SHALL be decided at admission, before any account,
character, or combat-session lookup, so it costs nothing beyond a session-scoped flag check. Once
the pending transition finishes — whether by success or by any step of the recovery ladder — the
session SHALL no longer refuse a further character-changing action as `transition_pending`. When
the session holds a puppet — because the transition succeeded or a recovery/cancellation step
retained or restored one — a further `account.character.switch` or `account.character.create`
SHALL be admitted and evaluated normally. The recovery rung that leaves the session holding no
character clears the marker as well; a request from such a puppet-less session is answered by the
ordinary no-character entry gate, never by the pending refusal.

#### Scenario: A second switch while one is pending is refused
- **WHEN** `account.character.switch` is submitted for a session that already has a puppet
  transition scheduled from an earlier accepted `account.character.switch`
- **THEN** the second request is rejected with the `transition_pending` code, no further
  transition is scheduled, and the first transition's own outcome is unaffected

#### Scenario: A create while a switch is pending is refused
- **WHEN** `account.character.create` is submitted for a session that already has a puppet
  transition scheduled from an earlier accepted `account.character.switch`
- **THEN** the create request is rejected with the `transition_pending` code and no character is
  created

#### Scenario: A switch while a create is pending is refused
- **WHEN** `account.character.switch` is submitted for a session that already has a puppet
  transition scheduled from an earlier accepted `account.character.create`
- **THEN** the switch request is rejected with the `transition_pending` code and no puppet change
  is scheduled

#### Scenario: The next request is admitted once the pending transition completes
- **WHEN** a session's pending transition finishes by success, or by a recovery/cancellation step
  that retained or restored a puppet, and the session submits a further
  `account.character.switch` or `account.character.create`
- **THEN** the request is admitted and evaluated normally, not refused as pending

#### Scenario: The pending refusal never shadows a puppet-less session
- **WHEN** the recovery rung that leaves the session holding no character has finished and a
  further character-changing action is submitted from that session
- **THEN** the request is answered by the ordinary no-character entry gate rather than the
  `transition_pending` refusal

#### Scenario: A rapid double submission never reports a false success
- **WHEN** two `account.character.switch` requests naming different owned characters are submitted
  from the same session before the first's transition has run
- **THEN** exactly one request is accepted and schedules a transition, and the other is rejected
  with the `transition_pending` code rather than being accepted and later silently dropped

#### Scenario: The pending refusal takes precedence over every other rejection reason
- **WHEN** a session with a puppet transition already pending submits a further
  `account.character.switch` that would also independently fail — for a character id not owned by
  the account, for a session whose current puppet is in an active combat session, or for the
  session's already-current puppet
- **THEN** the request is rejected with the `transition_pending` code, never with
  `invalid_character`, `in_combat`, or `already_current`
