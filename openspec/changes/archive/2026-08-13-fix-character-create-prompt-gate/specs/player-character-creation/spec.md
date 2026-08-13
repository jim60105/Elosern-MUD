## MODIFIED Requirements

### Requirement: Newly registered accounts have an inert pending player character
When Evennia creates the default `PlayerCharacter` for a newly registered account, the project account hook SHALL call its parent hook before marking that same account-owned character pending creation. While pending, command-set resolution SHALL derive a `mergetype="Replace"` creation-only gate with a priority above local exits and with `no_exits` and `no_objs` enabled. It SHALL expose only the character-creation command and harmless assistance or disconnect commands, rejecting every in-world command before it reaches a rules API or advances the world clock. While an interactive creation-wizard prompt that the creation surface itself started is open on the pending character, every unmatched or empty reply SHALL be delivered to that prompt so the wizard can resume, cancel, or reject it, and a completed, cancelled, or failed wizard SHALL tear down its prompt state so the gate never stays stuck; replies that match a command the gate exposes (for example `character`, `說明`, or `登出`) SHALL run that command instead. The pending marker SHALL persist across logout, login, and server reload; activation SHALL only change the marker, not perform an independently fallible command-set removal.

#### Scenario: A new account cannot rest before completing creation
- **WHEN** a newly registered account's auto-created character enters `rest 5s`
- **THEN** it receives a creation-required message, no magic-study code is called, and the world clock does not advance

#### Scenario: A pending character remains pending after reconnecting
- **WHEN** an account disconnects before completing character creation and later logs in again
- **THEN** its same account-owned character remains pending and gameplay commands remain unavailable until successful completion

#### Scenario: Pending state blocks traversal and object commands
- **WHEN** a pending character attempts a normal exit traversal or an object-targeting command
- **THEN** the creation-only gate rejects it before room, object, or rules state is changed

#### Scenario: The account hook retains Evennia ownership state
- **WHEN** a new account is created
- **THEN** its pending shell remains in `account.characters`, is the account's last puppet, and retains the parent hook's ownership locks

#### Scenario: A reply to an open creation wizard prompt reaches the wizard
- **WHEN** a pending character has an open `character create` wizard prompt and replies to it
- **THEN** the reply is delivered to the wizard and advances, cancels, or rejects the flow exactly as the wizard defines, instead of being rejected by the gate

#### Scenario: A cancelled wizard tears down its prompt state
- **WHEN** a pending character replies `cancel` to an open creation wizard prompt
- **THEN** the wizard exits with the cancellation message, the character remains pending, and no prompt state remains to swallow later input

#### Scenario: A failed wizard tears down its prompt state
- **WHEN** a pending character replies to an open creation wizard prompt with an invalid value, such as a non-integer age
- **THEN** the wizard reports the invalid input, the character remains pending, and no prompt state remains to swallow later input

#### Scenario: Empty input with no open prompt is rejected like any in-world input
- **WHEN** a pending character sends an empty line while no creation wizard prompt is open
- **THEN** it receives the creation-required message
