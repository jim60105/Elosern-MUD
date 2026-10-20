# Spec Delta

## REMOVED Requirements

### Requirement: The dispatcher refuses possession-incompatible actions with fixed zero-write results
**Reason**: Shop refusal and guild-opener refusal are superseded. The CLI forbids retiring scenario names within a MODIFIED block, so the requirement is replaced while preserving actual talk/engage refusal and result guards.
**Migration**: Use the replacement dispatcher requirement below and update active traceability references at spec synchronization. No runtime compatibility path or saved-data migration is needed.

## ADDED Requirements

### Requirement: The dispatcher preserves talk and engage refusals during possession
While the session actor is a possessed NPC, dispatches of `explore.talk_scripted`, `explore.talk_freeform`, and `explore.engage` SHALL be rejected by the adapters with outcome `rejected`, the corresponding stable `possessed_talk` or `possessed_engage` code and fixed Traditional Chinese message, before any service-scoped state read or dialogue/combat mutation. `shop.buy` and `shop.sell` SHALL instead follow normal party-scoped trade rules.

#### Scenario: Talk and engage attempts move nothing
- **WHEN** a possessing client dispatches scripted talk, freeform talk, or combat engage against a normally eligible local target
- **THEN** the result is rejected with the corresponding `possessed_talk` or `possessed_engage` code and fixed line, and dialogue sessions, combat sessions, affinity and all other canonical state remain unchanged

#### Scenario: The refusal still respects the epoch guard
- **WHEN** a possession-refused result races an epoch bump
- **THEN** the stale refused result is suppressed exactly like any other completion

#### Scenario: Action result contract unchanged
- **WHEN** a possession refusal is returned
- **THEN** the `ui_action_result` contract (request id, epoch guard) is unchanged

#### Scenario: Guild navigation and service content are absent
- **WHEN** a possessing client renders a room containing a guild host
- **THEN** no guild navigation opener or guild service section is rendered, no guild action is dispatched, and no synthetic possession-refusal message is displayed for the omitted surface

### Requirement: Shop access does not delegate other NPC services during possession
While possessing a companion, guild register/board/quests/turnin/merit, guild exam, church join/pray/offer/redeem/merit, talk and freeform talk, combat engage, and quest-issuer commissions SHALL retain their existing unavailable or refused behavior. Guild and church commands SHALL remain absent from the possessed cmdset. Their actions SHALL NOT gain commander delegation or new possession-specific handling.

#### Scenario: Guild and church stay outside the possessed command surface
- **WHEN** the active command set is built for a possessed companion
- **THEN** guild and church commands remain absent, including the guild examination command, while shop commands remain available

#### Scenario: Hidden services cannot act as the commander
- **WHEN** a possessing client attempts an existing guild or church action, or a quest-issuer commission interaction
- **THEN** existing admission or domain authorization prevents the service and changes no registration, guild/church merit, wallet, offering, quest, reward, or exam state; the companion is never substituted with the commander to enable it

#### Scenario: Conversation opening stays refused
- **WHEN** a possessing client attempts `explore.talk_open` against a normally eligible host
- **THEN** the existing `possessed_talk` refusal remains, no dialogue opens, and no quest-issuer commission is made available through it
