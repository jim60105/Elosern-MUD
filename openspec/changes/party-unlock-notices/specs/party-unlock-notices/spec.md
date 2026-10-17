# Spec Delta

## Purpose

Track which party members unlocked skills during the current session so the party window can mark them, without persisting any unread state.

## ADDED Requirements

### Requirement: Unlocks mark the learner as unread for the session
After any committed practice grant unlocks a skill for a party member, the system SHALL mark that member as having an unread unlock and add the skill to that member's recent-unlock set in session-scoped, non-persistent state of every session of the commander's account.

#### Scenario: A companion unlock sets the unread mark
- **WHEN** 艾拉 unlocks 群體治癒 while the player is connected
- **THEN** the session state reports 艾拉 unread with 群體治癒 in her recent set, and no persistent attribute changed

#### Scenario: A rolled-back grant marks nothing
- **WHEN** the action that would have unlocked the skill rolls back
- **THEN** no unread mark or recent skill is recorded

### Requirement: Opening a member's skills clears only the unread mark
Clearing a member's unread mark SHALL remove only that member's unread flag in the requesting session; the member's recent-unlock set SHALL remain for the rest of the session.

#### Scenario: Clearing keeps the recent set
- **WHEN** the unread mark for 艾拉 is cleared
- **THEN** 艾拉 is no longer unread and 群體治癒 is still in her recent set

### Requirement: Unread state never outlives the session
Unread marks and recent-unlock sets SHALL be dropped when the session disconnects and SHALL never be written to persistent storage; possession and release SHALL NOT clear them.

#### Scenario: Reconnect drops the marks
- **WHEN** the player reconnects after 艾拉 was marked unread
- **THEN** no member is unread and every recent set is empty

#### Scenario: Possession keeps the marks
- **WHEN** the player possesses 艾拉 while 卡恩 is marked unread
- **THEN** 卡恩 is still marked unread
