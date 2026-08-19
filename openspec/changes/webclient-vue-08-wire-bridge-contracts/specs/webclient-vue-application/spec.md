## ADDED Requirements

### Requirement: The app preserves the client DOM contract hooks and exposes stable test hooks
The Vue application SHALL preserve the DOM contract identifiers that the OOB and browser contract depend
on: the focusable action-dock target that the keyboard router dispatches into, the `action-` and `target-`
item keys selected by pointer or keyboard, and the identity of the required panel surfaces. The application
SHALL expose a stable `data-testid` hook on every remaining interactive surface so behavioral browser
acceptance targets deterministic hooks rather than styling selectors. The application SHALL also preserve
the stable public façades that existing OOB and browser contracts reference — the narrative input/append
path (`window.Elosern.narrativeInput`), the action submission entry point (`window.Elosern.actions.submit`),
and the keyboard-router consumption contract — implemented as browser-bridge shims over the store and the
imported logic, so existing behavioral tests and the choice-point/narrative append path keep their single,
non-duplicated entry points while the DOM is implemented in Vue.

#### Scenario: Keyboard router reaches the same dock
- **WHEN** the application renders the active menu frame and the player focuses the preserved action-dock target
- **THEN** a key press dispatches through the keyboard router to the focused item

#### Scenario: Pointer chooses by the stored key with keyboard parity
- **WHEN** the player clicks an action or target row
- **THEN** the `action-` or `target-` item key is used and the chosen item equals the item a keyboard journey would reach

#### Scenario: Interactive surfaces carry stable hooks
- **WHEN** any required interactive surface renders
- **THEN** it exposes a stable, unique `data-testid` identifier usable by automation

#### Scenario: Existing façade contracts hold
- **WHEN** an existing browser test or spec references the `window.Elosern.narrativeInput` narrative append path or the `window.Elosern.actions.submit` action entry point
- **THEN** those contracts resolve and route through the store and the single bridge dispatch path (the live transport round-trip is proven by a later change) with no duplicated append or action path
