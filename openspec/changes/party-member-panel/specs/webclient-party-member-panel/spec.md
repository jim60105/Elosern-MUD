# Spec Delta

## Purpose

Publish the viewed party member's member-tab facts (bond, membership, intimate state, commander persona prose and the member action descriptors) as one exact read-only presentation panel.

## ADDED Requirements

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
- **WHEN** 艾拉's bond is the third of five stages
- **THEN** `bond` is `{stage: "信賴", step: 3, steps: 5}` and no affinity number appears anywhere

### Requirement: Member actions are server-authored descriptors
The companion section SHALL carry descriptors for possess or release (`explore.possess` / `explore.possess_release`), leave (`explore.party_leave`) and the persona editor (`npc.persona.read`), each with its params, `enabled` and the existing verdict's bounded reason. The commander section SHALL carry the persona-edit descriptor. The client SHALL NOT infer availability.

#### Scenario: An escort-bound companion cannot be dismissed
- **WHEN** the viewed companion is a temporary-only escort member
- **THEN** the leave descriptor has `enabled: false` with the existing escort-bound reason text

#### Scenario: The possessed companion offers release
- **WHEN** the player is possessing the viewed companion
- **THEN** the possession descriptor is `explore.possess_release` and every other field equals the non-possessed payload for the same state

### Requirement: Commander facts carry persona prose
The commander section SHALL carry exactly the four persona prose fields (each nullable and bounded by the persona-field cap), the intimate state, and the persona-edit descriptor, built from the commander even while the player is possessing a companion.

#### Scenario: Possession shows the commander's own persona
- **WHEN** the player possesses 艾拉 and the viewed member is the commander
- **THEN** `commander.persona` holds the commander's four prose fields, not 艾拉's

### Requirement: The panel follows the viewed member
The `party_member` panel SHALL be built for the session's viewed member, falling back to the commander, and SHALL be republished by `party.view_member`.

#### Scenario: Selecting a member republishes the panel
- **WHEN** the player selects 卡恩 on the rail
- **THEN** the update carries `party_member.member_id` equal to 卡恩's identity
