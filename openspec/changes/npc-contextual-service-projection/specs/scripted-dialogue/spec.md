# Spec Delta

## MODIFIED Requirements

### Requirement: Dialogue tables are immutable, keyed, and registry-backed
Static/generated dialogue SHALL use immutable stable topic identities and complete linear scenes with greetings. Source-aware resolution SHALL read scanner-published static YAML or permitted immutable DB phases without global registry mutation. Every permitted topic up to sixteen SHALL be reachable, preserving guild, greeting, fallback and command-discovery semantics.

#### Scenario: Authored table behavior remains unchanged
- **WHEN** an authored guild host is queried through the resolver
- **THEN** its ordered authored greeting and topics remain available and the table is unchanged

#### Scenario: Generated topics use the existing conversation vocabulary
- **WHEN** a generated conversable host's current phase is queried by text, presentation, and action-validation consumers
- **THEN** they resolve the same permitted greeting, ordered stable topic IDs and complete generated scenes without a model call, static profile requirement or global registry mutation

#### Scenario: guild_staff definition registers and answers command guidance
- **WHEN** the `guild_staff` dialogue definition is registered and queried
- **THEN** its greeting and topic scenes describe registering, taking a
  commission from the board and reporting it back at the counter, and none of
  them contains a backticked token or a `guild` command name

#### Scenario: guild_staff definition carries the 回報 keyword for chip rendering
- **WHEN** the `guild_staff` dialogue table is inspected for keyword chips
- **THEN** it exposes the `回報` keyword alongside the authored service
  keywords, bounded by the existing keyword limit

#### Scenario: A missing table yields the no-understanding line
- **WHEN** a dialogue lookup references a `dialogue_key` absent from the registry
- **THEN** the no-understanding line is returned for keywords and no greeting is
  resolved, and nothing is written

#### Scenario: The registry is read-only at runtime
- **WHEN** the dialogue-table registry is consulted during gameplay
- **THEN** it is read-only at runtime

#### Scenario: guild_staff prose is in-world only
- **WHEN** the `guild_staff` greeting and topic scenes are authored
- **THEN** they are spoken in character, telling in the host's own in-world voice what the guild
  counter is for; registering as an adventurer, taking commissions from the board, reporting
  finished work back at the counter with the commission's number, giving up a commission, and
  asking where one stands in rank; and never name a command, a game mechanic, or an interface
  element

#### Scenario: Command discoverability lives outside the dialogue table
- **WHEN** players need to discover guild commands
- **THEN** command discoverability belongs to help, documentation and the interface, not to the
  dialogue table's prose

#### Scenario: Explicit supported service associations
- **WHEN** immutable source dialogue declares services metadata
- **THEN** each association names an existing same-source supported deterministic entry and validation rejects unknown, duplicate, dangling or cross-phase references; ordinary topics remain ordinary dialogue
