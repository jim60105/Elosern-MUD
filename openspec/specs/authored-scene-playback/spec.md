# authored-scene-playback Specification

## Purpose
Provide shared manual vue scene player and synchronized stage attribution through deterministic, independently testable behavior while preserving authoritative game ownership and offline play.

## Requirements

### Requirement: One player renders both static and generated scenes
Static and generated deliveries SHALL share manual page/line progression, speaker attribution, narration, replay and invalidation. Source type SHALL neither select a separate renderer nor reduce a generated formal scene to one response line.

#### Scenario: Generated attribution changes synchronously
- **WHEN** a generated scene moves from actor speech to host speech and narration
- **THEN** text, name and portrait emphasis change together under the same manual controls used for static scenes

### Requirement: Manual playback synchronizes every line boundary
Authored scenes SHALL advance only by explicit surface click or focused Space/Enter. Completing typing SHALL not advance a page. Text, displayed speaker and portrait emphasis SHALL change together at each line start; narration SHALL emphasize neither participant.

#### Scenario: Long line followed by narration
- **WHEN** a long host line spans two pages then narration begins
- **THEN** both host pages keep host attribution and narration clears speaker and emphasis together

#### Scenario: Final page requires acknowledgement
- **WHEN** the last page becomes fully visible
- **THEN** choices remain hidden until a further explicit activation finishes the scene

### Requirement: Playback recovery preserves presentation boundaries
A valid reconnected scene SHALL restart at line one without selecting again. Same-delivery availability updates SHALL preserve the current local cursor, while context invalidation SHALL retire playback and retain the attributed transcript.

#### Scenario: Preference and focus remain usable
- **WHEN** reduced motion and fast text are active while keyboard advances a scene
- **THEN** no auto-advance occurs and returning choices do not steal focus from an open drawer

#### Scenario: Combat invalidates midway
- **WHEN** combat begins before the formal scene finishes
- **THEN** obsolete playback/choices stop, no completion emits and historical transcript remains
