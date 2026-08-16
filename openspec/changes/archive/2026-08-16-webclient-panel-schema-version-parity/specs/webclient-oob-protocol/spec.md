## MODIFIED Requirements

### Requirement: Every panel payload has an exact availability discriminator
Each registered panel schema SHALL define an available form and the common unavailable form. The unavailable form SHALL contain exactly `schema_version`, `available: false`, and `reason`; reason SHALL contain bounded `code` and safe Traditional Chinese `message`, plus a bounded `correlation_id` only for an internal presenter failure. The unavailable form's `schema_version` SHALL equal the panel's registered schema version — the same version the panel's available form carries — so the client's registered-version gate accepts it. Available payloads SHALL contain `available: true` and only fields defined by their panel schema.

#### Scenario: Missing canonical data uses a safe unavailable value
- **WHEN** a presenter cannot read required canonical data without mutation
- **THEN** its panel uses the common unavailable form with a stable non-internal reason and no correlation ID

#### Scenario: Presenter exception uses correlated unavailable value
- **WHEN** a presenter raises an unexpected exception
- **THEN** its unavailable reason uses a generic message and bounded correlation ID matching the server log without exposing exception details

#### Scenario: Unavailable character payload carries the registered version
- **WHEN** the character presenter reports the common unavailable form for a character panel registered at schema version 3
- **THEN** the unavailable payload carries `schema_version: 3` and the client accepts it, and a payload carrying any other version (`schema_version: 2`) is rejected without replacing or merging the stored panel

### Requirement: Presenter registration and execution are isolated and read-only
The presentation registry SHALL reject duplicate panel names and SHALL expose only registered stable panel names to the coordinator. Each presenter SHALL receive session-derived read context, SHALL return JSON-safe panel data without invoking mutation APIs, and SHALL execute independently so one presenter failure cannot suppress other panels or narrative output. The registry SHALL derive each panel's registered schema version from the panel schema's single server-side constant in its presenter module, and the client's panel allowlist and per-panel schema-version re-checks SHALL mirror the same value under a dual-direction parity contract so the two never diverge.

#### Scenario: Duplicate presenter registration fails
- **WHEN** two presenters attempt to register the same stable panel name
- **THEN** registry construction fails rather than selecting one by import order

#### Scenario: One presenter exception is isolated
- **WHEN** one registered presenter raises while a full snapshot is built
- **THEN** the server logs its panel name and correlation ID, emits the common schema-valid unavailable value through that panel's registered schema metadata, and continues building every other panel

#### Scenario: Presentation does not mutate canonical state
- **WHEN** a full snapshot and a panel update are built for an actor
- **THEN** the actor's traits, buffs, sexual state, combat record, location, wallet, quests, and world-clock tick remain unchanged

#### Scenario: Panel schema versions stay equal across server and client
- **WHEN** the parity contract compares, for every registered panel, the presenter module's schema-version constant, the registry's registered value, the client allowlist's mirrored value, and the client per-panel available-form re-check literal
- **THEN** all are numerically equal, and no registered panel stores a literal schema version that can drift from its module constant