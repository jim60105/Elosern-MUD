# Spec Delta

## REMOVED Requirements

### Requirement: 穗鳴雀 construction persists both approved contact kits
**Reason**: Content identity belongs to authored data; general behavior is retained.
**Migration**: Use Shipped variants construct their declared configuration through the common boundary. Retarget substantive tests in this change.

### Requirement: 潮燈蟹 construction persists both approved contact kits
**Reason**: Content identity belongs to authored data; general behavior is retained.
**Migration**: Use Shipped variants construct their declared configuration through the common boundary. Retarget substantive tests in this change.

## ADDED Requirements

### Requirement: Shipped variants construct their declared configuration through the common boundary
Every shipped variant SHALL construct through the common deterministic entry point using its current authored complete profile when required, valid grade, ordered active/passive kit and optional behavior binding. Construction SHALL be atomic. Reload SHALL preserve committed identity, ownership, binding and depleted pools; registry edits SHALL NOT reset live individuals. Missing special kits SHALL retain innate actions and tier defaults.

#### Scenario: All variants
- **WHEN** every registry variant is constructed
- **THEN** profile source, literal stored bases, grade and ownership/binding match the selected declaration without baked multipliers; references validate before persistence

#### Scenario: Failure and reload
- **WHEN** assignment fails after a write, or a successful individual spends resources and reloads
- **THEN** failure leaves no partial individual; reload retains committed state; independent synthetic fault tests establish rollback

#### Scenario: Selectors remain identity-based
- **WHEN** a display name changes while stable keys stay fixed
- **THEN** existing hunt selectors still resolve and no profile or skill is inferred from prose
