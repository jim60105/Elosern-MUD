# Spec Delta

## Purpose

Resolve the commander, authorize a named party member for one purpose, and define the ordered present party scope so every member-scoped rule re-derives identity on the server.

## ADDED Requirements

### Requirement: The commander is resolved from the authenticated acting character
The system SHALL resolve the commander as the acting character when it is a player character, and as the live player-character owner of a possessed, puppeted companion otherwise. Any other acting character SHALL be rejected with `not_party_member`.

#### Scenario: A player character is its own commander
- **WHEN** a player character with two companions requests a member-scoped operation
- **THEN** the resolved commander is that player character

#### Scenario: Possession keeps the commander
- **WHEN** the player is possessing companion 艾拉 and requests a member-scoped operation
- **THEN** the resolved commander is the player's own character, not 艾拉

### Requirement: A named member is re-derived and never substituted
Every member-scoped request SHALL name its member by identity, and the system SHALL accept it only when the identity resolves to the commander or an effective party member. A forged, stale, deleted, or non-member identity SHALL be rejected with `not_party_member` and SHALL NOT be replaced by the commander.

#### Scenario: A non-member identity is rejected
- **WHEN** a request names the dbid of an NPC that is in the room but not in the party
- **THEN** it is rejected with `not_party_member` and no rule runs

#### Scenario: A deleted member identity is rejected
- **WHEN** a request names the dbid of a companion that has since been deleted
- **THEN** it is rejected with `not_party_member` rather than acting as the commander

### Requirement: Member presence is checked against the commander's room
A member-scoped request SHALL require the named member to be located in the commander's room, and SHALL reject an absent member with `member_not_present`.

#### Scenario: A companion in another room is absent
- **WHEN** the commander names a companion that stayed behind in another room
- **THEN** the request is rejected with `member_not_present`

### Requirement: Acting purposes exclude knocked-out members
A request whose purpose is acting (item use, casting, practice booking) SHALL reject a companion whose stored HP is at or below the nonlethal floor with `member_cannot_act`. A request whose purpose is organizing (bag transfer, equipment toggle) SHALL admit that companion.

#### Scenario: A knocked-out companion cannot cast
- **WHEN** the commander names companion 卡恩 at stored HP 1 as a field caster
- **THEN** the request is rejected with `member_cannot_act`

#### Scenario: A knocked-out companion can still be organized
- **WHEN** the commander names companion 卡恩 at stored HP 1 as an item receiver
- **THEN** the member check passes

### Requirement: The present party scope is ordered and room-bound
The present party scope SHALL list the commander first, then effective companions in party order, each only when located in the commander's room; the acting character (the commander, or the possessed companion) is always part of it.

#### Scenario: A companion elsewhere is outside the scope
- **WHEN** the commander stands with 艾拉 while 卡恩 waits in another room
- **THEN** the present party scope is exactly the commander followed by 艾拉

#### Scenario: Possession does not change the scope
- **WHEN** the player possesses 艾拉 and the whole party shares her room
- **THEN** the scope is the commander, 艾拉, then 卡恩 — the same tuple as without possession

### Requirement: Text member tokens resolve only within the party
A text member token SHALL resolve by exact display name among the commander and effective party members only. A token matching zero or several members SHALL be rejected with `not_party_member` and SHALL NOT fall back to the caller.

#### Scenario: An ambiguous token is rejected
- **WHEN** two companions share the display name typed after `=`
- **THEN** the command is rejected with `not_party_member` and nothing changes

### Requirement: Combat activity is judged across the involved members
A member-scoped rule that is barred in combat SHALL treat the request as in combat when the acting character, the commander, or any named member is in an active combat session.

#### Scenario: A possessed figure in combat bars the request
- **WHEN** the player possesses 艾拉, 艾拉 is in an active combat session and the commander's body is not
- **THEN** a combat-barred request names 艾拉's session as active and is refused

### Requirement: A stale possession flag grants no authority
Commander resolution SHALL accept a possessed companion only while it is puppeted by a session of the owner's account; an NPC whose possession flag is set without such a session SHALL be rejected with `not_party_member`.

#### Scenario: A flagged but unpuppeted NPC is refused
- **WHEN** an NPC has `possessed_by` naming the player but no live session puppets it
- **THEN** commander resolution rejects it with `not_party_member`

### Requirement: Membership rejections are stable and write nothing
Each membership rejection SHALL carry its stable code and one fixed Traditional Chinese message, and SHALL leave every persistent attribute unchanged.

#### Scenario: A rejection writes nothing
- **WHEN** any member check rejects
- **THEN** the caller receives the code and its fixed message and no attribute of any entity has changed
