## MODIFIED Requirements

### Requirement: Combat browser acceptance is keyboard-only and desktop-bounded
The managed localhost Playwright suite SHALL exercise basic attack, active skill selection, NONE, SELF, SINGLE, AREA explicit and shorthand targeting, Flee, Forfeit confirmation, disabled reasons, stale and duplicate submission behavior, EventLog narrative delivery, and active-session reconnect. At 1451x790 and 2560x1440, narrative, true HP/MP/SP status, applied modifier text, and the active action controls SHALL remain visible and usable. Tests SHALL use deterministic fixtures and SHALL make no remote, LLM, or image-generation request.

#### Scenario: Complete target matrix passes in Chromium
- **WHEN** the required browser entry point runs against deterministic skills covering all four TargetSpec values
- **THEN** every flow completes using keyboard controls and each emitted action has its exact expected payload shape

#### Scenario: Minimum viewport retains combat essentials
- **WHEN** combat renders at the 1451x790 reference viewport with a disabled skill focused
- **THEN** the player can read narrative, numeric resources, applied modifiers, the disabled reason, and action controls without overlap preventing operation
