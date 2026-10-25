# Spec Delta

## MODIFIED Requirements

### Requirement: The dispatcher preserves talk and engage refusals during possession
Lawful possessed authored talk open, selection and leave SHALL use the acting-body/owning-player context. Freeform talk and combat engage SHALL retain stable possession refusals and epoch guards. Shop buy/sell SHALL retain ordinary commander-purse/member-bag rules without a new prohibition.

#### Scenario: Freeform and engage attempts move nothing
- **WHEN** a possessing client dispatches freeform talk or combat engage against a normally eligible local target
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

#### Scenario: Authored talk is enabled
- **WHEN** a lawful controlled companion selects a present authored host
- **THEN** the actor speaks through a complete scene, with host-to-owning-player affinity and owner reading identity

### Requirement: Shop access does not delegate other NPC services during possession
While possessing a companion, guild register/board/quests/turnin/merit, guild exam, church join/pray/offer/redeem/merit, freeform talk, combat engage, and generated quest-issuer commissions SHALL retain their existing unavailable or refused behavior. Guild and church commands SHALL remain absent from the possessed cmdset. Their actions SHALL NOT gain commander delegation or new possession-specific handling.

#### Scenario: Guild and church stay outside the possessed command surface
- **WHEN** the active command set is built for a possessed companion
- **THEN** guild and church commands remain absent, including the guild examination command, while shop commands remain available

#### Scenario: Hidden services cannot act as the commander
- **WHEN** a possessing client attempts an existing guild or church action, or a quest-issuer commission interaction
- **THEN** existing admission or domain authorization prevents the service and changes no registration, guild/church merit, wallet, offering, quest, reward, or exam state; the companion is never substituted with the commander to enable it

#### Scenario: Authored conversation opening is enabled
- **WHEN** a possessing client attempts `explore.talk_open` against a normally eligible host
- **THEN** lawful authored conversation opens with actor/owner separation, while a generated quest-issuer commission remains unavailable through possession

#### Scenario: Authored service prose grants no delegation
- **WHEN** a possessed actor selects the guild reporting topic or addresses a generated issuer
- **THEN** existing domain-local authority still refuses unsupported service mutation; no registration, reward, quest or wallet authority is invented by the dialogue engine
