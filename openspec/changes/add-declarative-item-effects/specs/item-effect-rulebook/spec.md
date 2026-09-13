## Purpose

Defines the declarative vocabulary a usable item's effects are written in — the effect verbs, the
adjustable stats, the target scopes, the status selectors, the magnitude bounds — and the validated
rulebook that binds an ordered effect list to each usable item key at startup.

## ADDED Requirements

### Requirement: A usable item's effects are an ordered list bound by item key
The item-effect rulebook SHALL bind an ordered list of one or more effects to each usable item, keyed
by the item's own registry key. The item registry SHALL declare only whether an item is usable and how
it behaves when used (consumable, combat permission); it SHALL NOT carry any effect identity,
magnitude, stat, scope, or status name. List order SHALL be application order.

#### Scenario: A registry definition carries no effect identity
- **WHEN** a usable item's registry definition is inspected
- **THEN** it carries a consumable flag and a combat-use permission and nothing that names an effect,
  a magnitude, a stat, or a status

#### Scenario: One item declares several effects applied in order
- **WHEN** an item whose rulebook entry lists two effects is used successfully
- **THEN** both are applied, in the order the list declares

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
The set of item keys the effect rulebook declares SHALL equal exactly the set of registry keys whose
definition is usable. An entry for an item that is not usable, or a usable item with no entry, SHALL
fail validation at startup rather than at first use. Every entry SHALL declare at least one effect.

#### Scenario: An orphan rulebook entry fails startup
- **WHEN** the rulebook declares effects for an item key whose registry definition is not usable
- **THEN** validation fails and the server does not start

#### Scenario: A usable item with no rulebook entry fails startup
- **WHEN** a registry definition is usable but the rulebook declares no entry for its key
- **THEN** validation fails and the server does not start

#### Scenario: An empty effect list fails startup
- **WHEN** a rulebook entry declares an empty effect list
- **THEN** validation fails and the server does not start

### Requirement: Only the acting entity is an accepted scope until item targeting ships
The scope vocabulary SHALL be defined as the acting entity, a single other entity, and the three
battlefield-relative groups (own side, opposing side, everyone). Until the change that resolves item
targets ships, the loader SHALL accept only the acting-entity scope and SHALL reject every other value
with a message naming the change that will enable it, so no half-wired scope can reach settlement.

#### Scenario: A non-self scope is refused with a message naming its owner
- **WHEN** a rulebook entry declares a scope other than the acting entity
- **THEN** validation fails with a message naming the change that will enable that scope

#### Scenario: Every shipped item is self-scoped
- **WHEN** the shipped rulebook is loaded
- **THEN** every declared effect targets the acting entity and the load succeeds
