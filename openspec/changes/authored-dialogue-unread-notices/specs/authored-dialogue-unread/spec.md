# Spec Delta

## Purpose

Provide persistent unread markers and deferred deduplicated unlock batches through deterministic, independently testable behavior while preserving authoritative game ownership and offline play.

## ADDED Requirements

### Requirement: Generated phase observation preserves unread privacy and history
Unread observation SHALL apply to both sources by stable host/topic identity. First-seen topics in a newly permitted phase SHALL initialize without unlock popups. Previously observed locked topics later opening SHALL follow shared notice rules. Only current permitted-phase IDs SHALL enter live batches.

#### Scenario: Returning to a read phase creates no duplicate notice
- **WHEN** a generated role changes phases and later returns to a previously read phase
- **THEN** completion remains saved and neither obsolete-phase IDs nor repeated unlock notifications appear

### Requirement: Unread markers follow formal topic history
Initially open uncompleted formal topics SHALL show unread markers. Locked topics SHALL show locks instead. A first later opening SHALL become unread regardless of refusal playback. Completion SHALL persist through variant changes and relock/reopen, and repeated opening SHALL not reset it.

#### Scenario: Refusal then first unlock
- **WHEN** a locked topic refusal was read and its qualification later commits true
- **THEN** the newly open formal topic is unread and eligible for one unlock batch

#### Scenario: Read and unread reopen
- **WHEN** one completed and one uncompleted ever-open topic relock then reopen
- **THEN** the completed one stays read, the other stays unread and neither creates another unlock popup

### Requirement: Unlock notifications are deferred and deduplicated per batch
Newly opened formal topics SHALL produce one non-focus-stealing live notification per unlock batch after the current scene returns to choices. Announcement delivery SHALL be tracked separately from reading. Reconnect SHALL restore unread markers without replaying popup notifications.

#### Scenario: Several topics unlock while reading
- **WHEN** one committed refresh opens three never-open topics during scene playback
- **THEN** one notification waits until choices return and focus stays in its existing region

#### Scenario: Reload after announcement delivery
- **WHEN** a live batch was claimed and the client reloads before reading its topics
- **THEN** persistent unread markers remain and no popup batch is replayed

#### Scenario: Initial open is not a later unlock
- **WHEN** a host is observed for the first time with already open formal topics
- **THEN** unread markers appear without a newly-unlocked popup

