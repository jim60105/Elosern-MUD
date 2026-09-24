## MODIFIED Requirements

### Requirement: Keyboard input is dispatched through the WebClient plugin contract
Key input SHALL be dispatched through the KeyboardRouter handle path exposed by the
public keyboard bridge (the `window.Elosern.KeyboardRouter` claim contract), claimed
exactly when the router consumed the event or when the focused command field owns the
key; unconsumed keys SHALL fall through to the text and command-history path, so
history recall keeps its turn. Field ownership SHALL be determined by whether the field
holds focus, not by whether the command line is expanded: a collapsed command line's
hidden field cannot hold focus and owns no key, and an expanded line whose field has lost
focus owns none either. A modal capture that must pre-empt the keyboard
bridge — the exploration dock's bounded rest-duration entry or the creation dock's
text/numeric field — MAY use a
capture-phase listener and SHALL remove it when its form closes. A focus-trapped
surface laid over the stage — a reference drawer or a full-screen overlay — SHALL own
every key it receives while it holds trapped focus, and SHALL release that ownership
when it closes and returns focus to the control that opened it.

#### Scenario: No unclaimed-keydown noise remains
- **WHEN** the player navigates the action dock and types in the command field
- **THEN** the bridge claims exactly the events its router consumed and the keys its
  focused command field owns, so no unclaimed-keydown noise remains

#### Scenario: Unclaimed keys still reach the text and history path
- **WHEN** the player uses the stock command-history recall keys in the command field
- **THEN** the bridge does not claim them and history recall works

#### Scenario: A trapped surface owns its keys while it is open
- **WHEN** a full-screen overlay holds trapped focus and the player presses a navigation key
- **THEN** the overlay owns the key, the router consumes nothing behind it, and closing the
  overlay returns focus to its trigger and restores the router's ownership

#### Scenario: A collapsed command line owns no key
- **WHEN** the command line is collapsed and the action dock holds focus, and the player presses ArrowUp, then `/`, then ArrowUp
- **THEN** the first ArrowUp is claimed by the router for the dock, `/` expands the command line and moves focus into its field, and the second ArrowUp is owned by the focused field and walks the command history
