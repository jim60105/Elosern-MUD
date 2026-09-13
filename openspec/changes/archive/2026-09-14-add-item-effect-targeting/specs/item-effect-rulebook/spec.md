## REMOVED Requirements

### Requirement: Only the acting entity is an accepted scope until item targeting ships
**Reason**: the self-only acceptance seam was a forward-declared transitional guard that exists only
until the change resolving item targets ships; this change is that change. Its refusal scenario —
"A non-self scope is refused with a message naming its owner" — is retired with the seam it
enforces, so the replacement is declared as an ADDED requirement rather than a MODIFIED block that
would have to keep a scenario the implementation removes (precedent: REMOVED-with-reason in
`2026-08-13-overwhelm-log-attribution`).

## ADDED Requirements

### Requirement: An effect's scope is fixed by the rulebook and maps to one targeting requirement
Every effect SHALL declare one scope from the closed vocabulary: the acting entity, one other entity,
the actor's own side, the opposing side, or everyone present. Each scope SHALL map to exactly one
targeting requirement consumed by the shared target resolver, so item targets pass the identical
presence, alive, range, and faction validations a skill's targets pass. An item's reach SHALL be a
property of the item: the rulebook fixes it, and no player input, UI affordance, or command argument
SHALL widen or narrow it. The acting-entity scope SHALL bind the actor with a self-only constraint;
the single-entity scope SHALL consume the one explicit target the caller supplied; the three group
scopes SHALL expand through the action context.

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
