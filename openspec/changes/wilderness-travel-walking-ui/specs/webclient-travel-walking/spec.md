# Spec Delta

## Purpose

Provide persistent neighbour aim and commit-paced held walking through the existing guarded movement path. This capability defines observable browser travel behavior and its data boundaries.

## ADDED Requirements

### Requirement: Travel aim maps to guarded neighbour movement
Travel input SHALL retain released neighbour aim, combine arrows for diagonal aim and submit neighbour steps only through current committed exit descriptors with map-focused keyboard and pointer controls.

#### Scenario: Aim and release
- **WHEN** arrows aim a diagonal then release, Enter activates it and Escape clears it
- **THEN** the aim persists until cleared and exactly one current guarded move is submitted

#### Scenario: Non-targets and input owners
- **WHEN** party, unknown or blocked cells are clicked while a drawer, text entry or existing dialog owns focus
- **THEN** no inferred move or background travel action is dispatched

### Requirement: Held walking waits for committed steps and dwell
Held travel walking SHALL maintain a single store-owned pending step, advance only after its correlated committed movement and dwell, and stop without retry on release, refusal or lifecycle/input cancellation.

#### Scenario: Both completion orders
- **WHEN** a400ms hold starts and results/publications arrive in both orders or an unrelated revision arrives first
- **THEN** only the matching committed step increments progress and the next waits350ms or0 at off plus map/dispatch readiness

#### Scenario: Cancellation table
- **WHEN** release, any new key, Stop, refusal, disconnect, epoch change, blur, an unavailable/invalid/retired map or an opened card interrupts a held walk
- **THEN** no further step sends and a late result cannot restart it; originating arrow auto-repeat alone does not cancel

#### Scenario: Normal post-step refresh suspends rather than stops
- **WHEN** the first committed step starts an ordinary area refresh during a held walk
- **THEN** the walk survives refreshing, sends nothing until current map adoption and dwell complete, and can then send its second step

