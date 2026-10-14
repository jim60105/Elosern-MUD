# Spec Delta

## MODIFIED Requirements

### Requirement: Gallery URLs are built only from validated card identities
The presenter SHALL build a gallery media URL only from a card's stored identity that it has
validated against the subject's own `gallery/<kind>/<subject-key>/` prefix, the closed set of store
extensions, and the store-root confinement check (rejecting symlinks and out-of-root resolutions).
The presenter SHALL never expose an absolute path or the store root.

#### Scenario: A card whose file vanished is skipped, not emitted
- **WHEN** the resolved card's file has been deleted from the store
- **THEN** the chain continues to the next step and the payload never carries that card's URL

#### Scenario: A cross-subject or out-of-root identity is never served
- **WHEN** a card carries an identity whose path segments address a different subject, or that resolves outside the store root or through a symlink
- **THEN** the card is skipped and no URL is produced from it

#### Scenario: An invalid card never yields a broken URL
- **WHEN** a card's file no longer exists or its identity fails validation
- **THEN** the card SHALL be skipped, with resolution continuing at the next remaining candidate of
  the current step or the next step, rather than the chain emitting a broken URL

#### Scenario: Exact requested card remains attributable after loss
- **WHEN** a readable gallery card record has missing or rejected output
- **THEN** its exact requested descriptor contains a bounded source fault and no broken original URL; previews may use alpha but cannot change the original image id

