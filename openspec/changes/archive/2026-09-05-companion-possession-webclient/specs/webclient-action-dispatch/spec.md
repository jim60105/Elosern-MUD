# Delta spec: webclient-action-dispatch (companion-possession-webclient)

The registry enumeration is exact, so the enumeration requirement is MODIFIED (full
reproduction): two more exploration adapters, each with its exact validator and deterministic
adapter. Requirement reproduced in full.

## MODIFIED Requirements

### Requirement: Action registries are allowlisted and duplicate-safe
The action registry SHALL bind each stable action ID to one exact payload validator and one adapter, SHALL reject duplicate registration, and SHALL reject unknown action IDs. The production registry SHALL contain exactly the three combat adapters `combat.cast`, `combat.flee`, and `combat.forfeit`, the seven service adapters `guild.register`, `guild.quest_accept`, `guild.quest_abandon`, `guild.quest_turnin`, `guild.exam_start`, `shop.buy`, and `shop.sell`, the two inventory adapters `inventory.use` and `inventory.toggle_equip`, the five creation adapters `creation.preset`, `creation.custom`, `creation.concept`, `creation.activate`, and `creation.reset`, the ten exploration adapters `explore.move`, `explore.look`, `explore.talk_scripted`, `explore.talk_freeform`, `explore.party_invite`, `explore.party_leave`, `explore.engage`, `explore.wait`, `explore.possess`, and `explore.possess_release`, the `options.dismiss` action, the four title adapters `title.accept`, `title.decline`, `title.equip`, and `title.remove`, and the persona-editing adapter `character.persona.update`, each with its own exact validator and deterministic adapter, until another owning change adds an explicitly specified action. Tests MAY use an isolated proof adapter that cannot be reached in production configuration. No action SHALL route an action ID or payload string through the text command parser.

#### Scenario: Unknown action cannot become a command
- **WHEN** a client submits an unregistered action ID or a string resembling an Evennia command
- **THEN** the dispatcher rejects it with a schema-valid `ui_action_result` (outcome `rejected`, stable code `unknown_action`) carrying the request ID, and it is not routed through the text command parser

#### Scenario: Malformed action payload rejects without a protocol error
- **WHEN** a client submits a globally valid `ui_action` envelope whose registered action payload fails its exact schema
- **THEN** the dispatcher sends a schema-valid `ui_action_result` (outcome `rejected`, stable code `malformed_payload`) without invoking the adapter and without emitting a `ui_protocol_error`

#### Scenario: Duplicate action registration fails
- **WHEN** two adapters attempt to register the same action ID
- **THEN** registry construction fails rather than selecting one by registration order

#### Scenario: Production registry exposes only specified combat, service, inventory, creation, exploration, dismiss, title, and persona mutations
- **WHEN** the production registry is loaded after the possession-webclient change
- **THEN** its action IDs are exactly `combat.cast`, `combat.flee`, `combat.forfeit`, `guild.register`, `guild.quest_accept`, `guild.quest_abandon`, `guild.quest_turnin`, `guild.exam_start`, `shop.buy`, `shop.sell`, `inventory.use`, `inventory.toggle_equip`, `creation.preset`, `creation.custom`, `creation.concept`, `creation.activate`, `creation.reset`, `explore.move`, `explore.look`, `explore.talk_scripted`, `explore.talk_freeform`, `explore.party_invite`, `explore.party_leave`, `explore.engage`, `explore.wait`, `explore.possess`, `explore.possess_release`, `options.dismiss`, `title.accept`, `title.decline`, `title.equip`, `title.remove`, and `character.persona.update`, each with its own exact validator and deterministic adapter
