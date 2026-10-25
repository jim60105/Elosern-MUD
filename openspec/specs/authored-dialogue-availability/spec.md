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
