# webclient-party-member-panel Specification

## Purpose
Publish the viewed party member's member-tab facts (bond, membership, intimate state, commander persona prose and the member action descriptors) as one exact read-only presentation panel.

## Requirements

### Requirement: The party_member panel is an exact read-only version-1 panel
The presentation registry SHALL register `party_member` at schema version 1. Its available form SHALL contain exactly `schema_version`, `available`, `kind: "party_member"`, `member_id`, `role`, `companion` and `commander`, where exactly one of `companion` and `commander` is non-null according to `role`. Server, protocol mirror and Vue store allowlists SHALL name it in lockstep.

#### Scenario: A companion payload carries only companion facts
- **WHEN** the viewed member is companion 艾拉
- **THEN** `role` is `companion`, `commander` is null, and `companion` carries exactly `bond`, `membership`, `intimate` and `actions`

#### Scenario: Shape drift is rejected identically
- **WHEN** a payload carries an unknown field, both sections non-null, or a raw affinity number
- **THEN** the server validator and the client mirror reject it identically

### Requirement: Companion facts are truthful and bounded
The companion section SHALL report the bond stage name with its stage index and stage count from the affinity rulebook (never the raw affinity value), the general flag and ordered temporary commissions, and the intimate level words, null when the companion has no sexual-state record.

#### Scenario: Bond pips come from the stage table
- **WHEN** 艾拉's bond resolves to the third of the rulebook's seven stages
- **THEN** `bond` is `{stage: "親睦", step: 3, steps: 7}` and no affinity number appears anywhere

### Requirement: Companion actions are server-authored descriptors
The companion section SHALL carry exactly three descriptors in the order possession, leave, persona: `explore.possess` or `explore.possess_release`, `explore.party_leave`, and `npc.persona.read`. Each SHALL carry its params, `enabled`, and the existing verdict's bounded reason. The client SHALL NOT infer availability.

#### Scenario: An escort-bound companion cannot be dismissed
- **WHEN** the viewed companion is a temporary-only escort member
- **THEN** the leave descriptor has `enabled: false` with the existing escort-bound reason text

#### Scenario: The possessed companion offers release
- **WHEN** the player is possessing the viewed companion
- **THEN** the possession descriptor is `explore.possess_release`, the companion's bond, membership and intimate facts equal the non-possessed payload for the same state, and the leave and persona descriptors carry their possession verdicts

### Requirement: The commander persona-edit descriptor is server-authored
The commander section SHALL carry exactly one `character.persona.update` descriptor, because the NPC editor cannot target a player character. It SHALL be disabled while the player possesses a companion, because that action edits the authenticated puppet rather than the commander whose prose the section displays.

#### Scenario: The commander editor is disabled while possessing
- **WHEN** the player possesses 艾拉 and the viewed member is the commander
- **THEN** the commander's persona-edit descriptor is disabled with the existing not-exploring reason

### Requirement: Commander facts carry persona prose
The commander section SHALL carry exactly `persona` (the four persona prose fields, each nullable and bounded by the persona-field cap) and `intimate`, built from the commander even while the player is possessing a companion.

#### Scenario: Possession shows the commander's own persona
- **WHEN** the player possesses 艾拉 and the viewed member is the commander
- **THEN** `commander.persona` holds the commander's four prose fields, not 艾拉's

### Requirement: The panel follows the viewed member
The `party_member` panel SHALL be built for the session's viewed member, falling back to the commander, and SHALL be republished by `party.view_member`.

#### Scenario: Selecting a member republishes the panel
- **WHEN** the player selects 卡恩 on the rail
- **THEN** the update carries `party_member.member_id` equal to 卡恩's identity
