# Delta spec: webclient-gallery-panel (webclient-oob-protocol)

## MODIFIED Requirements

### Requirement: Presenter registration and execution are isolated and read-only

The presentation registry SHALL reject duplicate panel names and SHALL expose
only registered stable panel names to the coordinator. The registered production
set SHALL include the `gallery` panel alongside the existing registered panels;
adding a registered panel SHALL remain a registry-registration act and SHALL NOT
change any envelope schema. Each presenter SHALL receive session-derived read
context, SHALL return JSON-safe panel data without invoking mutation APIs, and
SHALL execute independently so one presenter failure cannot suppress other
panels or narrative output. A presenter whose subject is the account owning the
rendered puppet, rather than the puppet itself, SHALL derive that account from
the rendered puppet's own account only.

#### Scenario: Duplicate presenter registration fails

- **WHEN** a second `PresenterSpec` is registered under an existing panel name
- **THEN** registration raises rather than replacing the first spec

#### Scenario: The gallery panel joins the registered set additively

- **WHEN** the production registry is built after this change
- **THEN** `panel_names` includes `gallery` together with every previously registered panel name, and the snapshot/update/result/error envelope schemas are unchanged

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
