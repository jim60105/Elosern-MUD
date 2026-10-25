# authored-dialogue-availability Specification

## Purpose
Provide server-qualified topic disclosure and committed-state refresh through deterministic, independently testable behavior while preserving authoritative game ownership and offline play.

## Requirements

### Requirement: Generated disclosure uses the same protected qualification
Generated topics SHALL share hidden/locked/open qualification, safe hints/refusal, variants and predecessor gates. Only the currently permitted phase SHALL be projected. Protected bodies SHALL be absent before shared qualification and existing effect authority pass, including from freeform context.

#### Scenario: Generated locked sentinel is absent everywhere
- **WHEN** a generated topic is locked and another phase contains private text
- **THEN** neither formal body appears in panel, actions, affordances, public chains, hints or freeform input

### Requirement: Qualified topic disclosure is server-owned
Hidden topics SHALL be absent. Locked topics SHALL expose only permitted labels, lock state, canonical requirement hints and selectable refusal content. Qualified formal bodies SHALL be omitted until a currently authorized selection. Every selection SHALL recheck current canonical context before effects.

#### Scenario: No protected body in any projection
- **WHEN** a topic is hidden or locked and its formal scene contains a sentinel
- **THEN** no panel, exploration affordance, action descriptor or pure-chain bundle contains the sentinel

#### Scenario: Stale visible choice loses eligibility
- **WHEN** a listed open topic becomes ineligible before selection
- **THEN** the server gives its allowed refusal or rejection with no formal body and no formal effect

### Requirement: Physical refresh includes generated scene contexts
Committed physical-source changes SHALL refresh generated and static scene contexts through the same canonical hooks. Generated content SHALL require no static registry membership and immutable package payloads SHALL remain unchanged.

#### Scenario: Generated exposure qualification refreshes
- **WHEN** equipped exposure changes a generated topic's qualification
- **THEN** shared post-commit refresh updates its choices without another selection or package mutation

### Requirement: Physical condition mutations refresh live dialogue after commit
Canonical item, equipped or base exposure, social identity and skill changes SHALL refresh affected owner dialogue availability after commit, including text, other-connection and no-session origins. Rolled-back changes SHALL publish no false eligibility, and current playback SHALL retain its chosen scene.

#### Scenario: No-session equipped exposure
- **WHEN** a canonical equipment writer runs without WebClient action context and crosses a live topic boundary
- **THEN** all current authenticated owner watchers receive updated availability without another selection

#### Scenario: Outer rollback cancels physical refresh
- **WHEN** inventory or skill writes occur inside an owning transaction that later fails
- **THEN** neither false open state nor an unlock observation publishes

### Requirement: Locked presentation treats generated identities as opaque
Generated scene choices SHALL use the same selectable refusal, accessible hints and focus behavior as static choices. Full generated IDs SHALL survive UI admission and dispatch without static syntax restrictions or truncation.

#### Scenario: Generated locked choice uses ordinary refusal player
- **WHEN** a generated locked row with a valid long identity is activated
- **THEN** its shared refusal plays and no formal completion or protected successor is revealed

### Requirement: Locked topics remain readable refusals with accessible hints
Visibly locked topics SHALL remain selectable and SHALL show a lock plus the server requirement hint on hover and keyboard focus. Refusal playback SHALL return to choices without formal completion or predecessor advancement. Operationally disabled actions SHALL remain non-dispatchable.

#### Scenario: Keyboard refusal
- **WHEN** a player focuses and activates a locked topic
- **THEN** its canonical hint is accessible, its refusal plays and no protected formal completion is submitted

#### Scenario: Availability removes active row
- **WHEN** a committed refresh hides the focused topic
- **THEN** focus moves to a remaining choice without altering the playing scene or dispatching a replacement

### Requirement: Generated lifecycle retirement preserves deterministic phase authority
Generated phase, package cancellation or binding changes SHALL retire obsolete delivery/receipt/notification contexts through the shared lifecycle path. Existing committed-provenance phase authority SHALL remain unchanged and saved logical topic completion SHALL persist.

#### Scenario: Cancelled package cannot replay
- **WHEN** a live generated host's package is cancelled
- **THEN** its old scene, choice and completion capabilities reject without exposing private content or altering saved reading

### Requirement: Progression and world lifecycle refresh every relevant conversation
Owner guild, quest, claim and host-affinity changes, bound companion membership/presence changes and world-time commits SHALL refresh affected current dialogue contexts. Phase or control retirement SHALL clear obsolete delivery/receipts. No-session or another-connection origins SHALL preserve these semantics.

#### Scenario: Another companion departs
- **WHEN** a conversation host remains but a required bound companion leaves the actor room
- **THEN** the conversation topic relocks immediately after the move commit, without waiting for another topic selection

#### Scenario: Noncompletion quest transition
- **WHEN** a named quest is accepted, fails, invalidates or is abandoned by its owner through another connection
- **THEN** current topic eligibility is refreshed for that exact saved lifecycle state

#### Scenario: World time beyond action scope
- **WHEN** a clock commit crosses a daypart boundary and a different valid owner conversation depends on time
- **THEN** that conversation receives current availability without relying on WebClient command observation

### Requirement: Committed state changes refresh eligibility without rewriting playback
Relevant committed state changes SHALL refresh dialogue availability from canonical state. Failed or rolled-back changes SHALL publish no false opening. Ordinary eligibility refresh SHALL preserve a delivered scene variant, while host, phase or control invalidation SHALL retire it.

#### Scenario: Equipped exposure refreshes choices
- **WHEN** a lawful equipment commit crosses a topic exposure boundary during a scene
- **THEN** choices reflect new availability while playing wording remains fixed

#### Scenario: Every condition source refreshes
- **WHEN** item holdings, social identity, skills, owner rank/quest/claim/affinity, companion presence or world time commits a change
- **THEN** the next committed dialogue projection reflects that source without another topic selection
