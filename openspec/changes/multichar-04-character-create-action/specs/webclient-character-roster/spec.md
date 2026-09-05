# Delta spec: webclient-character-roster (multichar-04-character-create-action)

Chain note: applies after `multichar-03-character-switch-action`, which introduces the
decide-then-schedule contract, the verified attach step, and the recovery ladder these requirements
reuse.

## ADDED Requirements

### Requirement: Creating a character is an allowlisted account-scoped action
The production action registry SHALL register the account-scoped action
`account.character.create`, accepting exactly an empty payload; any field at all SHALL be refused
through the dispatcher's existing malformed-payload rejection before the adapter runs. The adapter
SHALL obtain the account from the authenticated session's own puppet, SHALL follow the same
decide-synchronously / schedule-the-transition contract as switching, and SHALL declare no affected
panels and emit no completion presentation with its result. It SHALL reject with the stable code
`character_slots_full` when the account already holds the configured maximum number of characters,
and with `in_combat` when the session's current puppet is in an active combat session — because
creating a character leaves the current one — each with a safe Traditional Chinese message and no
state change. The combat condition SHALL be re-derived from the active-combat-session predicate,
never read from the roster panel's advisory field. The action SHALL NOT route an action identifier
or payload through the text command parser.

#### Scenario: A full account cannot create
- **WHEN** an account already holding the configured maximum submits `account.character.create`
- **THEN** the action is rejected with the `character_slots_full` code, no character object is
  created, no transition is scheduled, and the session keeps its current puppet

#### Scenario: Creating during combat is refused
- **WHEN** a player in an active combat session submits `account.character.create`
- **THEN** the action is rejected with the `in_combat` code and no character is created

#### Scenario: A rejection does not disturb an open creation form
- **WHEN** a player with unsaved creation-wizard form edits triggers a rejected
  `account.character.create`
- **THEN** the rejection result arrives with no panel update and no full snapshot, and the form
  edits are untouched

### Requirement: The new character shell is created before the current character is left
The scheduled creation transition SHALL create the new character shell **before** sending the
client's detach signal or changing the session's puppet, because the account's own
character-creation API performs the authoritative capacity check and reports a full account by
returning an error rather than raising. When shell creation reports an error or fails, the
transition SHALL stop with nothing about the session changed — no detach signal, no retired
sequence, no puppet change — SHALL log the failure, and SHALL deliver one Traditional Chinese line
telling the player the character was not created. Only once a shell exists SHALL the transition
attach it through the same verified attach and recovery ladder the switch action uses.

A shell that was created but could not be attached SHALL be left in place, not deleted: it is a
legitimate pending character the account owns, it appears in the roster with its pending marker,
and it can be entered later through the switch action. The creation path SHALL perform no
destructive write on its failure branch.

#### Scenario: A capacity failure at transition time costs the player nothing
- **WHEN** the account's character-creation API reports a full account at transition time
- **THEN** the session keeps its current puppet and its presentation epoch, no detach signal is
  sent, the player is told the character was not created, and the failure is logged

#### Scenario: A shell that cannot be attached is kept, not destroyed
- **WHEN** a shell is created but the puppet attach fails and the recovery ladder runs
- **THEN** the shell still exists, still belongs to the account, and appears as a pending roster
  row that the switch action can enter

#### Scenario: A successful creation attaches and synchronizes
- **WHEN** an account below its capacity accepts `account.character.create`
- **THEN** the new shell is created, verified as the session's puppet, recorded as the account's
  last puppet, and a fresh-epoch full snapshot is published for it

### Requirement: A newly created character enters the existing wizard and never resends the world introduction
The created shell SHALL receive the project's pending-creation marker through the account's own
post-creation hook, exactly as an account's first shell does, so the unchanged mode derivation
resolves the creation mode and the existing creation surface is presented with no client change.
The action SHALL NOT assign identity attributes, traits, or the pending marker directly, and SHALL
NOT name the shell: the creation wizard's activation remains the sole writer of a character's
display name. The reusable creation start presentation SHALL be delivered for the new shell. The
world introduction SHALL NOT be delivered for any character after the account's first, and this
SHALL hold structurally — the introduction is reachable only from the login hook, which a
mid-session puppet change does not run — rather than by an explicit suppression this action has to
remember.

#### Scenario: A second character enters the creation wizard
- **WHEN** an account below its capacity accepts `account.character.create`
- **THEN** the new pending shell is puppeted and the following snapshot resolves the creation mode
  with the creation surface available

#### Scenario: The world introduction is not resent
- **WHEN** a second or later character is created mid-session
- **THEN** the player receives the creation start presentation and does not receive the world
  introduction

#### Scenario: The action writes no canonical identity
- **WHEN** a new shell is created through the action
- **THEN** its key is the account's own default, no identity attribute or trait was assigned by the
  action, and only the wizard's activation later renames it

#### Scenario: An abandoned new character is reachable again
- **WHEN** a player creates a second character, leaves its wizard unfinished, and switches back to
  a finished character
- **THEN** the unfinished character remains a pending roster row, and switching to it presents the
  creation surface again with its saved draft
