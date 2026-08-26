## MODIFIED Requirements

### Requirement: Keyboard input is dispatched through the WebClient plugin contract
Key input SHALL be dispatched through the KeyboardRouter handle path exposed by the
public keyboard bridge (the `window.Elosern.KeyboardRouter` claim contract), claimed
exactly when the router consumed the event or when the focused command field owns the
key; unconsumed keys SHALL fall through to the text and command-history path, so
history recall keeps its turn. Because the command field is permanently present rather
than opened, field ownership SHALL be determined by whether the field holds focus, not
by an open state. A modal capture that must pre-empt the keyboard
bridge — the exploration dock's bounded rest-duration entry, the services dock's
bounded quantity form, or the creation dock's text/numeric field — MAY use a
capture-phase listener and SHALL remove it when its form closes. A focus-trapped
surface laid over the stage — a reference drawer or a full-screen overlay — SHALL own
every key it receives while it holds trapped focus, and SHALL release that ownership
when it closes and returns focus to the control that opened it.

#### Scenario: No unclaimed-keydown noise remains
- **WHEN** the player navigates the action dock and types in the command field
- **THEN** the bridge claims exactly the events its router consumed and the keys its
  focused command field owns, so no unclaimed keydown noise remains

#### Scenario: Unclaimed keys still reach the text and history path
- **WHEN** the player uses the stock command-history recall keys in the command field
- **THEN** the bridge does not claim them and history recall works

#### Scenario: A trapped surface owns its keys while it is open
- **WHEN** a full-screen overlay holds trapped focus and the player presses a navigation key
- **THEN** the overlay owns the key, the router consumes nothing behind it, and closing the
  overlay returns focus to its trigger and restores the router's ownership
