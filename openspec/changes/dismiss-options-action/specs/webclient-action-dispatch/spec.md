## MODIFIED Requirements

### Requirement: Action registries are allowlisted and duplicate-safe
The action registry SHALL bind each stable action ID to one exact payload validator and one adapter, SHALL reject duplicate registration, and SHALL reject unknown action IDs. The production registry SHALL contain exactly the three combat adapters `combat.cast`, `combat.flee`, and `combat.forfeit`, the seven service adapters `guild.register`, `guild.quest_accept`, `guild.quest_abandon`, `guild.quest_turnin`, `guild.exam_start`, `shop.buy`, and `shop.sell`, the five creation adapters `creation.preset`, `creation.custom`, `creation.concept`, `creation.activate`, and `creation.reset`, the eight exploration adapters `explore.move`, `explore.look`, `explore.talk_scripted`, `explore.talk_freeform`, `explore.party_invite`, `explore.party_leave`, `explore.engage`, and `explore.wait`, and the `options.dismiss` action, each with its own exact validator and deterministic adapter, until another owning change adds an explicitly specified action. Tests MAY use an isolated proof adapter that cannot be reached in production configuration. No action SHALL route an action ID or payload string through the text command parser.

#### Scenario: Unknown action cannot become a command
- **WHEN** a client submits an unregistered action ID or a string resembling an Evennia command
- **THEN** the dispatcher rejects it with a schema-valid `ui_action_result` (outcome `rejected`, stable code `unknown_action`) carrying the request ID, and it is not routed through the text command parser

#### Scenario: Malformed action payload rejects without a protocol error
- **WHEN** a client submits a globally valid `ui_action` envelope whose registered action payload fails its exact schema
- **THEN** the dispatcher sends a schema-valid `ui_action_result` (outcome `rejected`, stable code `malformed_payload`) without invoking the adapter and without emitting a `ui_protocol_error`

#### Scenario: Duplicate action registration fails
- **WHEN** two adapters attempt to register the same action ID
- **THEN** registry construction fails rather than selecting one by registration order

#### Scenario: Production registry exposes only specified combat, service, creation, exploration, and dismiss mutations
- **WHEN** the production registry is loaded after the dismiss-options-action change
- **THEN** its action IDs are exactly `combat.cast`, `combat.flee`, `combat.forfeit`, `guild.register`, `guild.quest_accept`, `guild.quest_abandon`, `guild.quest_turnin`, `guild.exam_start`, `shop.buy`, `shop.sell`, `creation.preset`, `creation.custom`, `creation.concept`, `creation.activate`, `creation.reset`, `explore.move`, `explore.look`, `explore.talk_scripted`, `explore.talk_freeform`, `explore.party_invite`, `explore.party_leave`, `explore.engage`, `explore.wait`, and `options.dismiss`, each with its own exact validator and deterministic adapter

#### Scenario: Test proof action remains isolated
- **WHEN** a dispatcher test installs a synthetic proof adapter
- **THEN** that adapter exists only in the test-owned registry and does not appear in the production registry

## ADDED Requirements

### Requirement: Adapters may receive the authenticated session through a fixed optional third parameter

Every registered adapter SHALL declare the callable signature `adapter(actor, payload, session=None)`. The dispatcher SHALL invoke every adapter with the authenticated session as the third positional argument and SHALL never use runtime signature introspection to decide what to pass. A direct two-argument invocation of an adapter (for example in a unit test) SHALL behave exactly as before through the default. The session SHALL be used only for per-session presentation targeting (for example dismiss eviction); adapters SHALL NOT read or write character state through it, and the actor identity rule (session.puppet only) is unchanged.

#### Scenario: A dispatched adapter receives the session

- **WHEN** the dispatcher admits an action whose adapter declares the three-parameter ABI
- **THEN** the adapter is invoked exactly once with the authenticated session as the third positional argument

#### Scenario: A two-argument direct invocation remains valid

- **WHEN** an existing test calls a production adapter as `adapter(actor, payload)`
- **THEN** the call succeeds through the default with `session=None` and produces the same behavior as before this change

#### Scenario: No signature introspection at the call site

- **WHEN** the dispatcher invokes an adapter
- **THEN** it passes `(actor, payload, session)` positionally unconditionally, without inspecting the callable signature