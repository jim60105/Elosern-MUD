## MODIFIED Requirements

### Requirement: Keyboard input is dispatched through the WebClient plugin contract
Key input SHALL be dispatched through the KeyboardRouter handle path exposed by the
public keyboard bridge (the `window.Elosern.KeyboardRouter` claim contract), claimed
exactly when the router consumed the event or when the open command drawer owns the
key; unconsumed keys SHALL fall through to the text and command-history path, so
history recall keeps its turn. A modal capture that must pre-empt the keyboard
bridge — the exploration dock's bounded rest-duration entry, the services dock's
bounded quantity form, or the creation dock's text/numeric field — MAY use a
capture-phase listener and SHALL remove it when its form closes.

#### Scenario: No unclaimed-keydown noise remains
- **WHEN** the player navigates the action dock and types in the command drawer
- **THEN** the bridge claims exactly the events its router consumed and the keys its
  open drawer owns, so no unclaimed keydown noise remains

#### Scenario: Unclaimed keys still reach the text and history path
- **WHEN** the player uses the stock command-history recall keys in the command drawer
- **THEN** the bridge does not claim them and history recall works
