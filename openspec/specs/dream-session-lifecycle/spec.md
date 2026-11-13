# dream-session-lifecycle Specification

## Purpose
Tracks bounded, resumable dream collaboration exchanges and explicit confirm-or-draft departure without dependence on additional generation.

## Requirements

### Requirement: Only completed exchanges consume the six-exchange budget

An exchange SHALL consist of one player message and one successfully delivered validated response. The session SHALL persist at most six completed exchanges and display remaining count. Opening text, confirmation actions, transport failures, validation retries and duplicate submission SHALL NOT consume exchanges. Rendered input SHALL have an independent hard bound.

#### Scenario: Retry and duplicate do not consume
- **WHEN** one message retries validation and is submitted twice
- **THEN** one successfully delivered response increments the persisted count once

#### Scenario: Reconnect after five
- **WHEN** a player reconnects with five completed exchanges
- **THEN** one remains and reconnect does not reset the count

#### Scenario: Oversized player message
- **WHEN** one message exceeds the rendered-input bound
- **THEN** it rejects without generation or budget consumption

### Requirement: Convergence and exit require explicit choices

Exchange five SHALL begin convergence. Exchange six SHALL summarize spoiler-free direction with no new question. At six, free text SHALL stop, the session SHALL become finalized and confirmation or draft preservation SHALL be offered. Early departure SHALL offer draft preservation and awakening, and confirmation after an explicit finalize. Only explicit valid-version confirmation SHALL submit; incomplete/unconfirmed content SHALL remain a draft.

#### Scenario: Sixth completes
- **WHEN** the sixth validated response is delivered
- **THEN** free-text input closes, the session is finalized and confirm/draft choices appear without a seventh exchange

#### Scenario: Exit before cap
- **WHEN** the player leaves after two exchanges
- **THEN** draft preservation and awakening are available, confirmation becomes available after an explicit finalize, and draft preservation schedules nothing

### Requirement: Failures preserve progress and permit offline awakening

Cancellation, disconnect and model failure SHALL preserve saved session progress and the independently committed sleep outcome. Ending/awakening SHALL require no further model call. Later entry SHALL resume saved discussion without duplicate request submission or repeated settlement of the original sleep.

#### Scenario: Failure after five
- **WHEN** generation fails while the player has five completed exchanges
- **THEN** the count stays five and draft/awakening remains possible offline

#### Scenario: Restart during delivery
- **WHEN** the same response-delivery identity is replayed after restart
- **THEN** presentation can recover it without a second completed exchange

### Requirement: Valid confirmation closes the session without awaiting dispatch
A valid explicit version confirmation SHALL atomically save the request, create/get unique dispatch work, preserve source linkage and close as confirmed. The pump SHALL be notified only after commit. Narrative confirmation SHALL await no model and write no clock; its outer rules consumer SHALL then continue only the linked sleep receipt's uncommitted interval or publish a real interruption. Rollback SHALL leave no confirmed session with missing request/work.

#### Scenario: Real confirmation with an unresolved model
- **WHEN** the real pre-recovery dream surface confirms while background generation remains unresolved
- **THEN** one immutable request/work and confirmed closure exist, exchange count is unchanged, and only the outer rules sleep continuation advances the remaining accepted owner sleep once or reports its genuine interruption before normal waking actions

#### Scenario: Work persistence fails
- **WHEN** work creation fails inside confirmation
- **THEN** request and confirmed closure roll back together and no pump notification or recovery continuation is committed

#### Scenario: Lost wake-up hint
- **WHEN** confirmation commits but its pump notification is lost
- **THEN** startup or a later notification finds queued work without re-confirming, scanning historical requests or re-settling sleep

#### Scenario: Narrative closure and physical continuation have distinct ownership
- **WHEN** narrative confirmation commits and a later rules continuation interval fails
- **THEN** request/work remain truthful, failed interval writes restore, durable same-receipt continuation intent remains retryable and reconnect never opens another sleep

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

### Requirement: A session is conversing until it is finalized

A session SHALL record one stage. While conversing, free text is allowed and the thread may still be chosen; supplied proposal content and confirmation SHALL be refused without a write. The finalize action or the sixth settled exchange SHALL finalize it: free text closes and the working proposal is saved as the session draft. Manual content and confirmation are accepted only when finalized, and a thread choice only while conversing.

#### Scenario: Supplied content while conversing
- **WHEN** a draft request carries proposal content while the session is conversing
- **THEN** it is refused with a reason and neither the working proposal nor any draft changes

#### Scenario: Confirm before finalize
- **WHEN** confirmation is requested while the session is conversing
- **THEN** it is refused with a reason, no request is created and the session stays open

#### Scenario: Draft while conversing saves the working proposal
- **WHEN** a draft request with no content arrives while conversing
- **THEN** the session draft holds the working proposal and the session stays conversing

#### Scenario: Finalize closes free text and saves the draft
- **WHEN** the owner finalizes with exchanges remaining and no response pending
- **THEN** the session is finalized, a further message is refused without consuming an exchange, and the session draft holds the working proposal

#### Scenario: Finalize while a response is pending
- **WHEN** finalize is requested while a response is pending
- **THEN** it is refused and the session stays conversing

#### Scenario: Sixth exchange finalizes
- **WHEN** the sixth exchange settles
- **THEN** the session is finalized and the session draft holds the proposal that exchange produced

#### Scenario: A submitted form replaces the proposal once finalized
- **WHEN** a finalized session receives a draft request carrying a changed summary, lists and requirement rows
- **THEN** the working proposal and the session draft equal the submitted form and the last change report is cleared

#### Scenario: The thread stays locked in the form
- **WHEN** a finalized form omits the thread, names a different thread than the locked choice, and releases a locked thread that is no longer offered to a new story
- **THEN** the omitted thread keeps the locked choice, the different one is refused without a write, and the release is accepted

#### Scenario: Thread choice closes with the stage
- **WHEN** thread choice is requested for a finalized session, including one finalized before any message was sent
- **THEN** it is refused with a reason and the stored choice is unchanged

#### Scenario: The same dream stays finalized
- **WHEN** a finalized session is read again or re-entered during the same sleep
- **THEN** it is still finalized and a message is refused

#### Scenario: Awakening keeps the right version
- **WHEN** the owner awakens while conversing with a non-empty working proposal, and when the owner awakens while finalized
- **THEN** the first saves the working proposal as the session draft and the second leaves the last saved draft unchanged

### Requirement: A later sleep reopens an unfinalized conversation

A finalized, unconfirmed session that still has exchanges SHALL return to conversing when it is resumed on a later sleep, keeping its saved proposal as the starting proposal. One with no exchange remaining SHALL stay finalized.

#### Scenario: A later sleep returns to conversing
- **WHEN** a finalized, unconfirmed session with exchanges remaining is resumed on a later sleep, and when one with no exchange remaining is resumed
- **THEN** the first is conversing with its saved proposal as the starting proposal and accepts a message, and the second stays finalized
