## MODIFIED Requirements

### Requirement: The quest drawer is a two-level icon-tabbed surface

The quest drawer (the handbook window) SHALL present a first-level icon tablist in its header: the quest book, guild counter and titles tabs outside combat, and the titles tab alone in combat. A tab with sub-views SHALL add a vertical second-level tablist on its left edge. Every tab SHALL carry a text accessible name shown as a tooltip and SHALL be keyboard operable. The guild counter tab SHALL be disabled, yet focusable with its reason, while no usable guild section exists.

#### Scenario: The quest book is the first landing tab
- **WHEN** the player opens the quest drawer outside combat for the first time in a session
- **THEN** the quest book tab is selected

#### Scenario: The first-level tabs follow the mode
- **WHEN** the drawer renders outside combat, and separately in combat
- **THEN** outside combat the first-level tablist carries exactly the book, counter and titles tabs in that order, and in combat it carries exactly the titles tab

#### Scenario: A remembered book or counter tab yields in combat
- **WHEN** the remembered first-level tab is the quest book or the guild counter and the drawer opens in combat
- **THEN** the titles tab is selected and the remembered key is not overwritten

#### Scenario: The drawer remembers the last first-level tab
- **WHEN** the player selects the guild counter tab, closes the drawer, and reopens it in front of the same clerk
- **THEN** the guild counter tab is selected

#### Scenario: A remembered counter tab falls back when the counter is gone
- **WHEN** the remembered tab is the guild counter and the drawer reopens with no usable guild section
- **THEN** the quest book tab is selected and the guild counter tab is disabled

#### Scenario: The disabled counter tab explains itself
- **WHEN** the guild counter tab is disabled because the services panel is unavailable
- **THEN** keyboard focus can reach it, its tooltip and accessible description carry the panel's reason message, and activating it changes nothing

#### Scenario: The disabled counter tab names the missing clerk
- **WHEN** the guild counter tab is disabled because no guild section resolves while the services panel is available
- **THEN** its reason states that the counter needs a guild clerk

#### Scenario: Icon tabs are operable by keyboard
- **WHEN** focus is on a tab and the player presses an arrow key along the tablist's orientation, then Enter
- **THEN** focus moves to the adjacent tab and Enter selects it, and moving focus alone does not change the selection

#### Scenario: Opening in combat reads no counter services
- **WHEN** the drawer opens while the committed mode is combat
- **THEN** no guild counter services read is dispatched

## ADDED Requirements

### Requirement: A handbook route request opens the drawer on the named tab

The store SHALL offer one handbook route entry that publishes a sequenced route request naming a first-level tab and opens the quest drawer. The drawer SHALL switch to that tab once per new request, including while already open, and SHALL never re-apply a consumed request. A tab outside the mode's tab set SHALL be refused without opening anything. The request SHALL carry no provider and SHALL cause no read beyond the drawer's ordinary opening read.

#### Scenario: A titles request opens the titles tab
- **WHEN** the handbook route entry is called with the titles tab while the drawer is closed
- **THEN** the quest drawer opens with the titles tab selected

#### Scenario: A request switches an open drawer
- **WHEN** the drawer is open on the quest book and a titles request arrives
- **THEN** the titles tab becomes selected without closing the drawer

#### Scenario: An unknown tab is refused
- **WHEN** the handbook route entry is called with a tab key outside the current tab set
- **THEN** it returns false, no drawer opens and no request is published

#### Scenario: A handbook request reads no provider
- **WHEN** a handbook route request is published while the drawer is already open
- **THEN** no shop or counter services read is dispatched, and opening a closed drawer this way dispatches exactly the reads a plain opening dispatches

#### Scenario: A consumed request is not re-applied
- **WHEN** a titles request opened the drawer, the player switched to the quest book and closed the drawer, and the drawer is reopened without a new request
- **THEN** the quest book tab is selected

### Requirement: The titles tab organizes the committed title codex by rail

The titles tab SHALL render only the committed `title_codex` panel. Its rail SHALL list the six fixed-title categories in the server's closed category order, then the epithet entry, then a ballot entry only while the panel carries a pending ballot. A category entry SHALL show the count of its unlocked rows. Fixed titles SHALL render as a medal wall and epithets and nominees as list rows.

#### Scenario: The rail follows the payload's ballot
- **WHEN** the panel carries a pending ballot, and separately an empty one
- **THEN** the first rail ends with the ballot entry carrying the ballot's length as a hot count, and the second has no ballot entry

#### Scenario: A remembered ballot entry falls back when the ballot clears
- **WHEN** the ballot entry is selected and a commit empties the pending ballot
- **THEN** the rail selects the epithet entry and no ballot rows render

#### Scenario: A category counts unlocked rows
- **WHEN** a category holds three rows of which one is unlocked
- **THEN** its rail entry's count is 1

#### Scenario: A locked medal keeps its name and hint
- **WHEN** a locked fixed row is selected
- **THEN** its medal is marked locked, and the detail shows the row's display and its hint verbatim

#### Scenario: Medals walk by keyboard
- **WHEN** focus is on a medal and the player presses an arrow key, Home or End, then Enter
- **THEN** focus moves in reading order without changing the selection, and Enter selects the focused medal

### Requirement: The titles tab equips through the detail footer

The titles detail footer SHALL offer equip for the selected unlocked fixed row or epithet. Equip SHALL emit exactly one `title.equip` intent with `kind` `fixed` and the row key, or `kind` `epithet` and the row display. Equip SHALL be disabled and emit nothing for the equipped entry and for a locked row. The full title SHALL render verbatim from `full_title` in the header only while the titles tab is selected.

#### Scenario: Equipping an unlocked fixed title
- **WHEN** an unlocked, unequipped fixed row is selected and equip is activated
- **THEN** exactly one `title.equip` intent with `{kind: "fixed", identifier: <row key>}` is emitted

#### Scenario: Equipping an epithet
- **WHEN** an unequipped epithet row is selected and equip is activated
- **THEN** exactly one `title.equip` intent with `{kind: "epithet", identifier: <row display>}` is emitted

#### Scenario: Locked and equipped entries cannot equip
- **WHEN** a locked fixed row, or the equipped fixed row or epithet, is selected and equip is activated
- **THEN** the control is disabled with a reason and no intent is emitted

#### Scenario: The full title belongs to the titles tab
- **WHEN** the titles tab is selected, and separately the quest book tab
- **THEN** the header shows `full_title` verbatim on the first and no full title on the second

### Requirement: Epithet removal takes two steps and any close attempt cancels it

A remove control SHALL render only for an epithet row whose `can_remove` is true. Activating it SHALL arm a confirmation and move focus to its cancel control. Confirming SHALL emit exactly one `title.remove` intent with the row display. Cancelling, changing the selection or the rail, or any drawer close attempt (Escape, close control, scrim) while armed SHALL disarm it without emitting, and the close attempt SHALL NOT close the drawer.

#### Scenario: The remove control follows the flag
- **WHEN** an epithet row with `can_remove` false is selected
- **THEN** no remove control renders

#### Scenario: Confirming removes
- **WHEN** the player arms removal and confirms
- **THEN** exactly one `title.remove` intent with `{display: <row display>}` is emitted

#### Scenario: Arming moves focus to cancel
- **WHEN** the player activates the remove control
- **THEN** focus is on the confirmation's cancel control

#### Scenario: A close attempt cancels instead of closing
- **WHEN** removal is armed and the player presses Escape, activates the close control, or clicks the scrim
- **THEN** the confirmation disarms, no intent is emitted, and the drawer stays open; a second close attempt closes it

#### Scenario: A selection change disarms
- **WHEN** removal is armed and another row or rail entry is selected
- **THEN** the confirmation disarms without emitting

### Requirement: The titles tab answers a pending ballot

Selecting a nominee SHALL show its display and basis in the detail. The footer SHALL offer accept, emitting exactly one `title.accept` intent whose `index` is the nominee's one-based ballot position, and decline, emitting exactly one `title.decline` intent with an empty payload.

#### Scenario: Accepting a nominee
- **WHEN** the second nominee is selected and accept is activated
- **THEN** exactly one `title.accept` intent with `{index: 2}` is emitted

#### Scenario: Declining the ballot
- **WHEN** any nominee is selected and decline is activated
- **THEN** exactly one `title.decline` intent with `{}` is emitted

### Requirement: The titles tab degrades honestly

Before the first `title_codex` commit the titles tab SHALL be enabled and show the shared empty state. While the committed panel is unavailable the titles tab SHALL be disabled, yet focusable, with the panel's reason. No form SHALL list invented rows.

#### Scenario: Before the first commit
- **WHEN** the titles tab is selected before any `title_codex` panel was committed
- **THEN** it shows the shared empty state and no medal or row

#### Scenario: An unavailable codex disables the tab
- **WHEN** the committed `title_codex` panel is the common unavailable form
- **THEN** the titles tab is disabled, keyboard focus can reach it, and its tooltip and accessible description carry the panel's reason message

#### Scenario: A vanished selection falls back
- **WHEN** the selected epithet is gone after a commit
- **THEN** the first row of the same rail entry is selected, or the empty detail shows when the entry has no rows

### Requirement: The handbook titles tab fits the reference viewports

On the live client at 1451x790 and at 2560x1440 the titles tab SHALL lay out its rail, list and detail columns side by side without overflowing the drawer body. The medal wall and the row list SHALL NOT scroll horizontally. No rendered text in the tab SHALL be smaller than the `--text-xs` token's computed size.

#### Scenario: Three columns fit at both viewports
- **WHEN** the live client opens the titles tab at 1451x790 and at 2560x1440
- **THEN** the rail, list and detail columns do not overlap, each lies inside the drawer body, and neither the medal wall nor the row list has a horizontal scroll overflow

#### Scenario: No text below the floor
- **WHEN** the titles tab renders at either viewport
- **THEN** every visible text node's computed font size is at least the computed size of `--text-xs`
