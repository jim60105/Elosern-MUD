# portrait-source-attempts Specification

## Purpose
Provide read-only canonical portrait candidates and source-position fault facts while preserving existing selection, eligibility and generation ownership.

## Requirements

### Requirement: Portrait source order retains current policy
Portrait enumeration SHALL preserve matching equipment-bound selection, explicit official choice, gallery default and optional official default before the declared alpha terminal. Applicable faults SHALL stay at their source layer; unconfigured optional sources SHALL add none. No fixed-output source SHALL remain.

#### Scenario: Preferred selection is broken
- **WHEN** an explicit personal selection is missing and a default card is valid
- **THEN** its stored preference remains, its fault precedes the default candidate and the default can be selected without mutation

#### Scenario: Existing renderer contract remains usable
- **WHEN** the internal enumerator is integrated before the canonical portrait wire change
- **THEN** the current registered serializer still receives its existing single shape and scene resolution remains unchanged; no alternate accepted shape or duplicate selector appears
