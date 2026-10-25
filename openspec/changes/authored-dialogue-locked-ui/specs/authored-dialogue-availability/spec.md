# Spec Delta

## ADDED Requirements

### Requirement: Locked topics remain readable refusals with accessible hints
Visibly locked topics SHALL remain selectable and SHALL show a lock plus the server requirement hint on hover and keyboard focus. Refusal playback SHALL return to choices without formal completion or predecessor advancement. Operationally disabled actions SHALL remain non-dispatchable.

#### Scenario: Keyboard refusal
- **WHEN** a player focuses and activates a locked topic
- **THEN** its canonical hint is accessible, its refusal plays and no protected formal completion is submitted

#### Scenario: Availability removes active row
- **WHEN** a committed refresh hides the focused topic
- **THEN** focus moves to a remaining choice without altering the playing scene or dispatching a replacement

