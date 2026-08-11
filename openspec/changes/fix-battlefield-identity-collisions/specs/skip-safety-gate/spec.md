## ADDED Requirements

### Requirement: Skip-safety registers battlefields by participant dbref

The skip-safety registry SHALL index active battlefields by each participant's immutable dbref, never by its mutable display key, and SHALL unregister by dbref on settlement.

#### Scenario: Same-name entities do not cross-evict registrations

- **WHEN** two different entities share a display key and each is in its own active battlefield
- **THEN** registering or settling one entity's battlefield never removes or corrupts the other's registration

#### Scenario: IN_COMBAT lookup uses the actor's dbref

- **WHEN** `evaluate_skip_safety(actor)` consults the battlefield registry
- **THEN** it resolves the actor's battlefield by `str(actor.pk)` and returns `IN_COMBAT` only when the actor is a living, non-fled member of that battlefield
