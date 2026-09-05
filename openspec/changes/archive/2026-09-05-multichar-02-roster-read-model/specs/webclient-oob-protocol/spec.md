# Delta spec: webclient-oob-protocol (multichar-02-roster-read-model)

The `roster` panel is the first registered panel whose subject is the account rather than the
session's puppet. The presenter contract is restated to admit that explicitly, so
"session-derived read context" is not read as "the puppet and nothing else".

## MODIFIED Requirements

### Requirement: Presenter registration and execution are isolated and read-only
The presentation registry SHALL reject duplicate panel names and SHALL expose only registered stable panel names to the coordinator. Each presenter SHALL receive session-derived read context, SHALL return JSON-safe panel data without invoking mutation APIs, and SHALL execute independently so one presenter failure cannot suppress other panels or narrative output. A presenter whose subject is the account owning the rendered puppet, rather than the puppet itself, SHALL derive that account from the rendered actor's own ownership link and SHALL be held to the identical read-only, isolation, and availability-discriminator contract as every puppet-subject presenter; it SHALL NOT widen the read context to the transport session and SHALL NOT read any account the rendered actor does not belong to. The registry SHALL derive each panel's registered schema version from the panel schema's single server-side constant in its presenter module, and the client's panel allowlist and per-panel schema-version re-checks SHALL mirror the same value under a dual-direction parity contract so the two never diverge.

#### Scenario: Duplicate presenter registration fails
- **WHEN** two presenters attempt to register the same stable panel name
- **THEN** registry construction fails rather than selecting one by import order

#### Scenario: One presenter exception is isolated
- **WHEN** one registered presenter raises while a full snapshot is built
- **THEN** the server logs its panel name and correlation ID, emits the common schema-valid unavailable value through that panel's registered schema metadata, and continues building every other panel

#### Scenario: Presentation does not mutate canonical state
- **WHEN** a full snapshot and a panel update are built for an actor
- **THEN** the actor's traits, buffs, sexual state, combat record, location, wallet, quests, and world-clock tick remain unchanged

#### Scenario: An account-subject presenter reads only the rendered actor's own account
- **WHEN** the account-subject panel is rendered for an actor while other accounts own characters in the same world
- **THEN** the payload names only characters belonging to the rendered actor's own account, and no other account's data is read or emitted

#### Scenario: Panel schema versions stay equal across server and client
- **WHEN** the parity contract compares, for every registered panel, the presenter module's schema-version constant, the registry's registered value, the client allowlist's mirrored value, and the client per-panel available-form re-check literal
- **THEN** all are numerically equal, and no registered panel stores a literal schema version that can drift from its module constant
