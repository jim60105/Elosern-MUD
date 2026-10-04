## MODIFIED Requirements

### Requirement: Pointer parity is verified in the browser without weakening keyboard-only acceptance
The managed localhost Playwright suite SHALL exercise, with the pointer only at both acceptance viewports (the 1451x790 reference viewport and 2560x1440): an exploration root entry and one submenu submission, a service action submitted from its reference drawer's own control, a combat root action and one combat submenu selection, a disabled row that explains without submitting, and an activation attempt while the offline overlay is shown. Each SHALL assert the exact emitted `ui_action` count and payload. The keyboard-only acceptance requirements SHALL NOT be weakened to accommodate pointer parity and SHALL continue to pass, so keyboard-only play is still a verified guarantee rather than a side effect.

#### Scenario: A pointer-only journey completes in Chromium
- **WHEN** a seeded actor uses only the mouse to open an exploration submenu and submit an action
- **THEN** each step emits exactly one expected `ui_action` and the panels refresh, with no key press required

#### Scenario: Keyboard-only journeys still pass unchanged
- **WHEN** the existing keyboard-only exploration, service, creation, and combat journeys run
- **THEN** they pass with the keyboard steps and assertions their own acceptance requirements define, none of which is relaxed for pointer parity

#### Scenario: Offline pointer activation emits nothing
- **WHEN** the WebSocket is interrupted and the player clicks an enabled row under the offline overlay
- **THEN** no `ui_action` crosses the wire and the overlay remains until a valid new-epoch snapshot is adopted
