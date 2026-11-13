# Spec Delta

## MODIFIED Requirements

### Requirement: Convergence and exit require explicit choices

Exchange five SHALL begin convergence. Exchange six SHALL summarize spoiler-free direction with no new question. At six, free text SHALL stop, the session SHALL become finalized and confirmation or draft preservation SHALL be offered. Early departure SHALL offer draft preservation and awakening, and confirmation after an explicit finalize. Only explicit valid-version confirmation SHALL submit; incomplete/unconfirmed content SHALL remain a draft.

#### Scenario: Sixth completes
- **WHEN** the sixth validated response is delivered
- **THEN** free-text input closes, the session is finalized and confirm/draft choices appear without a seventh exchange

#### Scenario: Exit before cap
- **WHEN** the player leaves after two exchanges
- **THEN** draft preservation and awakening are available, confirmation becomes available after an explicit finalize, and draft preservation schedules nothing

## ADDED Requirements

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

