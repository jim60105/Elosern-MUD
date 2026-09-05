# Delta spec: webclient-character-roster (multichar-03-switch-create-actions)

Chain note: applies after `multichar-02-roster-read-model`, which introduces this capability's
read model. These requirements add the write path only.

## ADDED Requirements

### Requirement: Two allowlisted account-scoped actions switch and create characters
The production action registry SHALL register exactly two account-scoped actions,
`account.character.switch` and `account.character.create`, and no other account-scoped action.
`account.character.switch` SHALL accept exactly `character_id`, a positive integer excluding
booleans; `account.character.create` SHALL accept exactly an empty payload. Any other, missing,
or wrongly typed field SHALL be refused through the dispatcher's existing malformed-payload
rejection before the adapter runs. Both adapters SHALL obtain the account from the authenticated
session's own puppet and SHALL resolve `character_id` only against that account's character list —
never through a world-wide object search and never through a permission-based fallback — so no
character outside the acting account is reachable through this surface. Neither action SHALL route
an action identifier or payload through the text command parser.

#### Scenario: The registry holds exactly the two account actions
- **WHEN** the production action registry is built
- **THEN** it contains `account.character.switch` and `account.character.create` and no other
  `account.*` action

#### Scenario: A foreign character id is refused
- **WHEN** `account.character.switch` is submitted with the identity of a character owned by a
  different account
- **THEN** the action is rejected as an invalid character, no puppet change is scheduled, and no
  data about that character is returned

#### Scenario: A malformed payload never reaches the adapter
- **WHEN** `account.character.switch` is submitted with a missing, non-integer, boolean, negative,
  or extra field, or `account.character.create` is submitted with any field at all
- **THEN** the dispatcher returns the malformed-payload rejection and no adapter runs

### Requirement: A character-changing action reports its decision before its transition
Both account-scoped actions SHALL make every authorization decision — ownership, capacity, the
combat lock, and whether the requested character is already the live puppet — synchronously at
admission, and their action result SHALL report the outcome of that decision. An accepted action
SHALL NOT perform the puppet transition inside the adapter: the transition SHALL be scheduled to
run after the completion result has been sent and both the server in-flight marker and the
browser's mutation lock have been released, because the transition retires the very sequence the
result would be published into. The resulting message order on the wire SHALL be the action result
first, then the client's detach signal, then a fresh-epoch full snapshot for the new puppet. A
successful action SHALL NOT be marked as an uncertain outcome by the client.

Before acting, the scheduled transition SHALL re-validate the same conditions against committed
state. If re-validation or the puppet change fails, it SHALL leave the current puppet in place,
emit an operational error event, deliver a Traditional Chinese failure line to the player through
the ordinary message channel, and publish a fresh snapshot, so a failed transition is reported and
never leaves the client stranded on a retired sequence.

#### Scenario: A successful switch leaves no uncertain mutation
- **WHEN** a player switches to another owned character
- **THEN** the browser receives the success result and releases its mutation lock, then the detach
  signal, then the new puppet's fresh-epoch snapshot, and the mutation is not marked uncertain

#### Scenario: The result precedes the detach signal
- **WHEN** an accepted `account.character.switch` or `account.character.create` completes
- **THEN** the `ui_action_result` for that request identifier is delivered before any
  no-puppet protocol error, and no in-flight request is outstanding when the detach signal arrives

#### Scenario: A rejected action schedules nothing
- **WHEN** either action is rejected for any reason
- **THEN** the session keeps its current puppet, its presentation epoch is unchanged, and no
  transition is scheduled

#### Scenario: A failed transition is reported to the player
- **WHEN** a scheduled transition's re-validation or puppeting fails after a success result was
  sent
- **THEN** the session keeps its current puppet, the player receives a Traditional Chinese failure
  line, an operational error event is emitted, and a fresh snapshot is published

### Requirement: Neither account action publishes a completion snapshot
Both account-scoped actions SHALL declare no affected panels and SHALL emit no completion
presentation with their result. A successful action's canonical state reaches the client through
the transition's own fresh snapshot; a rejected action changes nothing and SHALL NOT trigger a
full snapshot, so a switch or creation refused while the character-creation surface is open cannot
re-render that surface and discard the player's unsaved draft edits.

#### Scenario: A rejection does not disturb an open creation form
- **WHEN** a player with unsaved creation-wizard form edits triggers a rejected
  `account.character.switch`
- **THEN** the rejection result arrives with no panel update and no full snapshot, and the form
  edits are untouched

#### Scenario: A success emits no completion presentation
- **WHEN** an accepted `account.character.switch` completes
- **THEN** exactly one presentation follows it — the transition's fresh-epoch full snapshot — and
  no update or snapshot is published at the retiring epoch

### Requirement: Switching is refused for a foreign, current, or combat-locked target
`account.character.switch` SHALL reject with the stable code `invalid_character` when
`character_id` does not resolve to a member of the acting account's character list, with
`in_combat` when the session's current puppet is in an active combat session, and with
`already_current` when `character_id` is already the session's live puppet. `already_current`
SHALL be a rejection rather than a success, because a success would tell the client a transition
is coming that will never arrive. Each rejection SHALL carry a stable code and a safe Traditional
Chinese message and SHALL change no state. The combat condition SHALL be evaluated from the same
active-combat-session predicate that blocks the character's movement; the roster panel's advisory
lock field SHALL never be the authorization.

#### Scenario: Combat blocks switching
- **WHEN** a player in an active combat session submits `account.character.switch` for another
  owned character
- **THEN** the action is rejected with the `in_combat` code, the puppet is unchanged, and the
  combat session is unaffected

#### Scenario: A stale click after the lock appears is still refused
- **WHEN** the client submits a switch based on a roster snapshot rendered before combat began
- **THEN** the server re-derives the combat predicate and rejects the request, rather than
  trusting the panel's advisory field

#### Scenario: Switching to the current character is refused
- **WHEN** `account.character.switch` names the session's live puppet
- **THEN** the action is rejected with the `already_current` code and the session is untouched

### Requirement: Creating a character reuses the existing creation wizard and never resends the world introduction
`account.character.create` SHALL reject with the stable code `character_slots_full` when the
account already holds the configured maximum number of characters, and with `in_combat` under the
same active-combat-session predicate as switching, because creating a character leaves the current
one. An accepted request's scheduled transition SHALL leave the current character, create one new
character shell through the account's own character-creation API — which applies the project's
pending-creation marker exactly as it does for an account's first shell — puppet that shell, record
it as the account's last puppet, and publish a full snapshot. Because the new shell is pending
creation, the snapshot's mode SHALL resolve to the creation mode through the unchanged mode
derivation and the existing creation surface SHALL be presented with no client change. The reusable
creation start presentation SHALL be delivered for the new shell; the world introduction SHALL NOT
be, for any character after the account's first — it is bound to the login hook, which a
mid-session puppet change does not run. The action SHALL NOT assign identity attributes, traits, or
the pending marker directly, and SHALL NOT rename the shell: the creation wizard's activation is
the sole writer of the character's display name.

#### Scenario: A second character enters the creation wizard
- **WHEN** an account below its capacity accepts `account.character.create`
- **THEN** a new pending shell is created and puppeted, and the following snapshot resolves the
  creation mode with the creation surface available

#### Scenario: The world introduction is not resent
- **WHEN** a second or later character is created mid-session
- **THEN** the player receives the creation start presentation and does not receive the world
  introduction

#### Scenario: A full account cannot create
- **WHEN** an account already holding the configured maximum submits `account.character.create`
- **THEN** the action is rejected with the `character_slots_full` code, no character object is
  created, and the session keeps its current puppet

#### Scenario: Creating during combat is refused
- **WHEN** a player in an active combat session submits `account.character.create`
- **THEN** the action is rejected with the `in_combat` code and no character is created

### Requirement: A puppet change through these actions carries no state across characters
A transition performed by either account-scoped action SHALL leave the retiring character's
session-scoped presentation state behind: the previous character's action-options state and
dismissal barriers, its transient creation concept proposal, and its completed-result cache and
in-flight marker SHALL NOT be visible to or reusable by the new puppet, and any generation still
in flight for the previous character SHALL publish nothing into the new sequence.

#### Scenario: The new puppet inherits no suggestion state
- **WHEN** a player with committed action-option cards switches to another character
- **THEN** the new puppet's first snapshot carries no card, fingerprint, or dismissal barrier from
  the previous character

#### Scenario: An in-flight generation cannot cross the switch
- **WHEN** an action-options generation started for the previous character settles after the
  switch completes
- **THEN** it publishes no panel state or result into the new character's sequence
