# Delta spec: webclient-character-roster (multichar-05-topbar-switcher-ui)

Chain note: applies after `multichar-02-roster-read-model` (the committed panel),
`multichar-03-character-switch-action`, and `multichar-04-character-create-action` (the two
actions). This delta adds the browser surface only.

## ADDED Requirements

### Requirement: The top band carries a character switcher rendered from the committed roster
The client SHALL render a character switcher in the stage's top band, beside the meta pill and
above the HUD island anchors, whenever the committed `roster` panel is available. Its collapsed
form SHALL present the current character's portrait thumbnail and name, both read from the roster
row marked as current — never from the status or character panel — so the collapsed form and the
expanded list can never name different characters. The collapsed form SHALL be width-bounded and
truncate a long name rather than growing with it. When the `roster` panel is unavailable the
switcher SHALL render nothing at all: neither an empty pill nor a placeholder character. The
switcher SHALL render in every committed mode, including creation, so a player who abandoned a
creation wizard can return to a finished character.

#### Scenario: The collapsed pill names the live character
- **WHEN** a snapshot commits a roster whose current row names 艾莉亞
- **THEN** the collapsed switcher renders 艾莉亞's name and portrait thumbnail

#### Scenario: The switcher is present during character creation
- **WHEN** the committed mode is `creation` and the roster panel is available
- **THEN** the switcher renders, and its collapsed form names the pending character being created

#### Scenario: An unavailable roster renders no switcher
- **WHEN** the committed `roster` panel reports the unavailable form
- **THEN** no switcher element is rendered anywhere in the top band

### Requirement: The expanded switcher lists every roster row with one shared lock note
Activating the switcher SHALL open a list rendering one row per committed roster character, in
payload order, each carrying that row's portrait thumbnail and name. A row whose committed pending
marker is set SHALL carry a stable in-creation marker; the client SHALL NOT synthesize a
disambiguating display name for it. The row marked as current SHALL be presented as selected and
SHALL NOT be activatable. When the committed roster reports switching as blocked, every
non-current row SHALL render disabled under exactly one shared inline note carrying the panel's
own committed reason string — never a per-row badge and never client-composed reason text. The
list SHALL be bounded in height with internal scrolling rather than growing the top band, SHALL
overlay the HUD islands transiently rather than displacing them, and SHALL close on Escape, on
outside pointer activation, and when a new presentation epoch is committed.

#### Scenario: Rows render in committed order with the current one selected
- **WHEN** a roster commits three characters and the switcher is expanded
- **THEN** three rows render in payload order, the current one is marked selected and is not
  activatable, and the other two are activatable

#### Scenario: A combat lock disables every other row under one note
- **WHEN** the committed roster reports switching as blocked with a reason
- **THEN** every non-current row renders disabled, exactly one inline note renders that committed
  reason, and no per-row badge is present

#### Scenario: A pending sibling is marked, not renamed
- **WHEN** a roster row carries the pending marker
- **THEN** the row renders the committed name plus a stable in-creation marker, and the name itself
  is unmodified

#### Scenario: Escape closes exactly one level
- **WHEN** the switcher list is open and Escape is pressed
- **THEN** the list closes, no action is dispatched, and no other open surface is affected

#### Scenario: The top band does not grow when the list opens
- **WHEN** the switcher list opens at the minimum supported viewport
- **THEN** the top band's own rendered box is unchanged and the list overlays the island anchors

### Requirement: Switching dispatches once and commits only on the server's snapshot
Activating an enabled, non-current row SHALL submit exactly one `account.character.switch`
carrying that row's committed identity, through the client's single dispatch entry and its
existing connected / locked / one-in-flight gates. Keyboard and pointer activation SHALL submit
the same action identifier and payload through the same entry. The surface SHALL NOT optimistically
mark the chosen row as current, SHALL NOT close on dispatch alone, and SHALL NOT add debouncing of
its own: the presented current character changes only when a snapshot naming the new puppet lands.
While the client is disconnected or its mutations are locked — including throughout the transition
between the two characters — every row and the create control SHALL render disabled and dispatch
nothing.

#### Scenario: Activating a row dispatches exactly one switch
- **WHEN** the player activates an enabled non-current row
- **THEN** exactly one `account.character.switch` request carrying that row's identity is
  submitted

#### Scenario: The selection does not move before the commit
- **WHEN** a switch has been dispatched but no new snapshot has been accepted
- **THEN** the collapsed pill and the selected row still name the previous character

#### Scenario: A disconnected switcher dispatches nothing
- **WHEN** the transport is lost or mutations are locked
- **THEN** every row and the create control render disabled and activating them submits nothing

#### Scenario: Keyboard activation matches pointer activation
- **WHEN** a row is activated from the keyboard
- **THEN** the same action identifier and payload are submitted through the same dispatch entry
  and the same gates apply

### Requirement: Creating a character is a confirmation-gated trailing control
The expanded list SHALL end with a create-character control. When the committed roster reports
that another character may not be created, that control SHALL render disabled with a stable
capacity reason, and the client SHALL take that fact from the committed field rather than
recomputing it from the row count. When creation is permitted, activating the control SHALL NOT
dispatch: it SHALL open an explicit confirmation stating that the current character will be left,
with a cancel control and a confirm control, and only the confirm control SHALL submit exactly one
`account.character.create` with an empty payload. Cancelling, or leaving the confirmation with
Escape, SHALL submit nothing and leave the current character untouched. Switching SHALL NOT be
confirmation-gated: it is reversible and is already refused server-side during combat.

#### Scenario: Opening the create control submits nothing
- **WHEN** the player activates the create-character control
- **THEN** a confirmation with a cancel control and a confirm control renders and no action is
  submitted

#### Scenario: Confirming dispatches exactly one creation
- **WHEN** the player activates the confirm control
- **THEN** exactly one `account.character.create` with an empty payload is submitted

#### Scenario: Cancelling leaves the current character
- **WHEN** the player cancels the confirmation or presses Escape on it
- **THEN** nothing is submitted, the session keeps its character, and the switcher returns to its
  list

#### Scenario: A full account cannot open the confirmation
- **WHEN** the committed roster reports that no further character may be created
- **THEN** the create control renders disabled with a stable capacity reason and activating it
  opens no confirmation
