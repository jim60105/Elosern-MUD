# Spec Delta

## ADDED Requirements

### Requirement: The session keeps a working proposal that only settled exchanges change

Each dream session SHALL hold one structured working proposal and the change report of its last settled exchange. A new session SHALL start with an empty proposal. A player message SHALL never become proposal content by itself. Each exchange SHALL give the collaborator the current working proposal, and a settled exchange SHALL replace it with the edited result and its report. A failed, abandoned or stale response SHALL leave both unchanged. Reconnect and a later resume SHALL restore both.

#### Scenario: A message is not the proposal
- **WHEN** an exchange settles whose response carries no edits
- **THEN** the working proposal is still empty and the player's message appears in no proposal field

#### Scenario: Edits accumulate across exchanges
- **WHEN** a first exchange writes a summary and a second exchange is requested
- **THEN** the second request carries that summary as the current proposal, and after it settles the proposal holds the second response's edits applied on top of the first

#### Scenario: Change report follows the last settled exchange
- **WHEN** an exchange that adds one list item settles, then an exchange with no edits settles
- **THEN** the report first names that item as added and afterwards shows no change

#### Scenario: Failed generation changes nothing
- **WHEN** generation fails or its retries are exhausted
- **THEN** no exchange is consumed and the working proposal and its report are unchanged

#### Scenario: Stale response applies no edits
- **WHEN** a response carrying edits arrives after the player awakened or the turn was abandoned
- **THEN** the working proposal is unchanged and no exchange is consumed

#### Scenario: Draft and awakening keep the working proposal
- **WHEN** a draft is saved with no supplied direction, or the player awakens with a non-empty working proposal and no saved draft
- **THEN** the saved draft carries the working proposal's fields and chosen thread

#### Scenario: Resume restores the proposal
- **WHEN** a saved session is resumed on a later sleep
- **THEN** its working proposal, last report and chosen thread are the ones it held before

#### Scenario: Resume seeds from the saved draft
- **WHEN** a saved session with a saved draft is resumed and the retained association holds no working proposal
- **THEN** the working proposal and chosen thread are taken from the saved draft's direction, and a session that already accepted an exchange reports its thread as locked

### Requirement: Thread choice precedes the first message and then locks

Before the first message of a session is accepted, the owner SHALL be able to choose a new story or one currently offered thread for the proposal; the default SHALL be a new story. Accepting the first message SHALL lock the choice for the session, including later resumes. The chosen thread's player-visible label SHALL be given to the collaborator. A choice after the lock, or of a thread that is not offered, SHALL be refused without a write.

#### Scenario: Choose before speaking
- **WHEN** the owner chooses an offered thread before any message
- **THEN** the choice is stored, the surface revision advances and the next exchange's request carries that thread's label

#### Scenario: Default is a new story
- **WHEN** the first message is sent without any choice
- **THEN** the proposal belongs to a new story and the request carries no thread label

#### Scenario: Locked after the first message
- **WHEN** the owner tries to choose after a message was accepted, including after that message's generation failed
- **THEN** the request is refused with a reason and the stored choice is unchanged

#### Scenario: Unoffered thread
- **WHEN** the owner names a thread that is ended, inaccessible or unknown
- **THEN** the request is refused with a reason and the stored choice is unchanged

#### Scenario: Lock survives resume
- **WHEN** a session with a locked choice is resumed on a later sleep
- **THEN** the choice is the same and choosing is still refused
