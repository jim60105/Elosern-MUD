# Spec Delta

## ADDED Requirements

### Requirement: Locked presentation treats generated identities as opaque
Generated scene choices SHALL use the same selectable refusal, accessible hints and focus behavior as static choices. Full generated IDs SHALL survive UI admission and dispatch without static syntax restrictions or truncation.

#### Scenario: Generated locked choice uses ordinary refusal player
- **WHEN** a generated locked row with a valid long identity is activated
- **THEN** its shared refusal plays and no formal completion or protected successor is revealed

### Requirement: Locked topics remain readable refusals with accessible hints
Visibly locked topics SHALL remain selectable and SHALL show a lock plus the server requirement hint on hover and keyboard focus. Refusal playback SHALL return to choices without formal completion or predecessor advancement. Operationally disabled actions SHALL remain non-dispatchable.

#### Scenario: Keyboard refusal
- **WHEN** a player focuses and activates a locked topic
- **THEN** its canonical hint is accessible, its refusal plays and no protected formal completion is submitted

#### Scenario: Availability removes active row
- **WHEN** a committed refresh hides the focused topic
- **THEN** focus moves to a remaining choice without altering the playing scene or dispatching a replacement

