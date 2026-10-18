# Spec Delta

## Purpose

Give the text client read-only views of any party member's status and skills, matching the party window's 狀態 and 技能 tabs.

## ADDED Requirements

### Requirement: 狀態 shows a member's true status
`狀態 [<成員>]` (alias `status`) SHALL print the named member's (default: the commander) HP, MP and SP, every trait with base, effective value and its breakdown layers, the active conditions with remaining time, modifiers and source, the guild rank and merit when present, and the active disguise's displayed values labelled as displayed; it SHALL write nothing and SHALL be available in and out of combat.

#### Scenario: A disguised companion shows true values
- **WHEN** the player types `狀態 艾拉` while 艾拉 is disguised
- **THEN** every trait line shows 艾拉's true base and effective values and the disguise appears only as a separately labelled section

#### Scenario: A non-member is refused
- **WHEN** the player types `狀態 不存在的人`
- **THEN** the command prints the `not_party_member` message and nothing else

### Requirement: 技能 shows a member's skills and growth
`技能 [<成員>]` (alias `skills`) SHALL print the named member's active and passive skills grouped by category, each active skill with level, XP band or capped mark, the booked mark, the new mark for this session's unlocks, its prerequisite and next unlock, and the freeform ladder when the member owns the element's mastery; it SHALL write nothing.

#### Scenario: Skill growth matches the panel
- **WHEN** the player types `技能 艾拉`
- **THEN** each printed level, booked mark and ladder rung equals the version-9 `character` panel built for 艾拉

### Requirement: Member views are documented and possession-identical
Both commands SHALL be documented in both player command documents, and SHALL print identical output for the same member whether or not the player is possessing a companion.

#### Scenario: Possession does not change the view
- **WHEN** the player types `狀態` while possessing 艾拉
- **THEN** the output describes the commander, exactly as without possession
