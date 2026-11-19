# item-effect-rulebook Specification

## Purpose
Defines the declarative vocabulary a usable item's effects are written in — the effect verbs, the
adjustable stats, the target scopes, the status selectors, the magnitude bounds — and the validated
rulebook that binds an ordered effect list to each usable item key at startup.

## Requirements

### Requirement: A usable item's effects are an ordered list bound by item key
A usable item SHALL author its non-empty effect list alongside its consumption and combat-use flags. The runtime mechanics flags SHALL remain separate from the effect profile, resolved by the item's own key. List order SHALL be application order and non-combat use time SHALL remain a shared setting.

#### Scenario: A registry definition carries no effect identity
- **WHEN** a usable authored row is loaded as a definition and an effect profile
- **THEN** the use-mechanics view contains its two flags with no separate effect ID or parameters; effect resolution finds the profile by the definition's item key

#### Scenario: One item declares several effects applied in order
- **WHEN** a row lists two order-sensitive effects and the item is used successfully
- **THEN** both apply in authored order for that item

#### Scenario: Item row edits do not select a different use duration
- **WHEN** two usable items declare different effects
- **THEN** a successful non-combat use of either charges the same separately configured time cost

### Requirement: Each effect declares exactly one verb
Every effect entry SHALL carry exactly one of three verbs: a stat adjustment (a stat name plus a
signed amount), a status application (one concrete status definition key), or a status removal (one
selector). An entry carrying two verbs, or none, SHALL fail validation. Every entry SHALL also carry a
target scope, defaulting to the acting entity when absent.

#### Scenario: A two-verb entry fails validation
- **WHEN** an effect entry declares both a stat adjustment and a status application
- **THEN** rulebook validation fails and the server does not start

#### Scenario: A verbless entry fails validation
- **WHEN** an effect entry declares a scope but no verb
- **THEN** rulebook validation fails and the server does not start

#### Scenario: An entry with no scope targets the acting entity
- **WHEN** an effect entry omits its scope
- **THEN** it resolves to the acting entity

### Requirement: Stat adjustments name a closed stat vocabulary and carry a signed bounded amount
A stat adjustment SHALL name one member of the closed vocabulary `hp`, `mp`, `sp`, `pleasure`, and
carry a non-zero integer amount whose absolute value does not exceed the configured maximum. A
positive amount restores or raises; a negative amount drains or lowers. A zero amount, a non-integer
amount, an out-of-bound amount, or an unknown stat SHALL fail validation.

#### Scenario: A negative amount is a valid declaration
- **WHEN** an effect declares a stat adjustment with a negative amount
- **THEN** validation accepts it and the effect lowers that stat when applied

#### Scenario: A zero amount fails validation
- **WHEN** an effect declares a stat adjustment with an amount of zero
- **THEN** rulebook validation fails, because an effect that can never change anything is a
  configuration error rather than a no-op

#### Scenario: An out-of-bound magnitude fails validation
- **WHEN** an effect declares a stat adjustment whose absolute amount exceeds the configured maximum
- **THEN** rulebook validation fails and the server does not start

#### Scenario: An unknown stat fails validation
- **WHEN** an effect names a stat outside the closed vocabulary
- **THEN** rulebook validation fails and the server does not start

### Requirement: Status application names a concrete definition; status removal accepts selectors
A status application SHALL name exactly one concrete status definition key known to the buff rulebook;
a selector SHALL be rejected there, because applying "every status" is not a meaningful operation. A
status removal SHALL accept either a concrete status definition key or one of the selectors
`negative` (every active debuff-polarity status), `positive` (every active buff-polarity status), or
`all` (both). An unknown status key SHALL fail validation in either position.

#### Scenario: A selector under the application verb fails validation
- **WHEN** an effect declares a status application whose value is `all`
- **THEN** rulebook validation fails and the server does not start

#### Scenario: Each removal selector is accepted
- **WHEN** effects declare status removals of `negative`, `positive`, and `all` respectively
- **THEN** all three validate

#### Scenario: A concrete removal key is accepted
- **WHEN** an effect declares a status removal naming one known status definition key
- **THEN** it validates and removes only that status when applied

#### Scenario: An unknown status key fails validation
- **WHEN** an effect names a status definition key the buff rulebook does not define
- **THEN** rulebook validation fails and the server does not start

### Requirement: The rulebook and the registry align exactly at startup
All and only usable item rows SHALL contribute a use profile at startup. A missing, empty, or invalid use-effect list on a usable item, or a use-effect list on any other item, SHALL reject the catalog before gameplay.

#### Scenario: An orphan rulebook entry fails startup
- **WHEN** an item that does not declare use mechanics supplies use effects
- **THEN** validation rejects the item before gameplay

#### Scenario: A usable item with no rulebook entry fails startup
- **WHEN** an item declares use mechanics but omits its effect list or sets it to null
- **THEN** validation rejects the item before gameplay

#### Scenario: An empty effect list fails startup
- **WHEN** a usable item declares an empty effect list
- **THEN** validation rejects the item before gameplay

### Requirement: An effect's scope is fixed by the rulebook and maps to one targeting requirement
Every effect SHALL declare one scope from the closed vocabulary: the acting entity, one other entity,
the actor's own side, the opposing side, or everyone present. Each scope SHALL map to exactly one
targeting requirement consumed by the shared target resolver, so item targets pass the identical
presence, alive, range, and faction validations a skill's targets pass.

#### Scenario: Every scope value loads
- **WHEN** a rulebook declares one effect at each of the five scopes
- **THEN** all five validate and the server starts

#### Scenario: Every shipped item is self-scoped
- **WHEN** the shipped rulebook is loaded
- **THEN** every declared effect targets the acting entity and the load succeeds

#### Scenario: A player cannot change an item's reach
- **WHEN** a caller supplies a group shorthand as an item-use target
- **THEN** it is rejected: the only caller-supplied target an item accepts is a single entity, and
  only for an effect the rulebook already scoped to a single entity

#### Scenario: Item and skill targets validate identically
- **WHEN** an item effect scoped to a single entity and a single-target skill are both resolved
  against the same dead candidate
- **THEN** both reject for the same reason through the same shared resolver

#### Scenario: An item's reach is fixed by the rulebook
- **WHEN** any caller attempts to change an item's reach
- **THEN** reach is a property of the item — the rulebook fixes it, and no player input, UI affordance, or command argument widens or narrows it

#### Scenario: Each scope binds its targets in one fixed way
- **WHEN** scopes resolve to targets
- **THEN** the acting-entity scope binds the actor with a self-only constraint, the single-entity scope consumes the one explicit target the caller supplied, and the three group scopes expand through the action context
