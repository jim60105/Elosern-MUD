# webclient-quest-drawer Specification

## Purpose
The quest drawer surface: a two-level icon-tabbed master/detail drawer that presents the player's quest book by state and hosts the guild counter, rendering only committed `quest_log` and `services` data and mirroring server action descriptors exactly.

## Requirements

### Requirement: The quest drawer is a two-level icon-tabbed surface

The quest drawer SHALL present an icon-only first-level tablist (quest book, guild counter) in its header and,
for a tab with sub-views, a vertical icon-only second-level tablist on its left edge. Every icon-only tab SHALL
carry a text accessible name shown as a tooltip on hover and keyboard focus, and SHALL be keyboard operable. The
guild counter tab SHALL be disabled, yet focusable with its reason exposed, while no usable guild section exists.

#### Scenario: The quest book is the first landing tab
- **WHEN** the player opens the quest drawer for the first time in a session
- **THEN** the quest book tab is selected

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

### Requirement: The quest book shows one quest state at a time

The quest book tab SHALL offer exactly three second-level tabs, in progress, completed, and failed, each listing
only the `quest_log` rows in that state in panel order. The book SHALL NOT render all states at once and SHALL
NOT use expand or collapse controls. Each state tab SHALL show its row count when non-zero, as part of its
accessible name. The completed tab's count SHALL be emphasized only while at least one completed row has an
enabled counter turn-in descriptor.

#### Scenario: The book opens on quests in progress
- **WHEN** the quest book tab is selected for the first time in a session
- **THEN** the in-progress state tab is selected and only in-progress rows are listed

#### Scenario: Switching state replaces the list
- **WHEN** the player selects the failed state tab
- **THEN** only failed rows are listed, with no other state's rows on screen

#### Scenario: Counts describe the stored rows
- **WHEN** the book holds three in-progress, two completed, and one failed record
- **THEN** the three state tabs report 3, 2, and 1 in their accessible names

#### Scenario: A turn-in waiting at the counter emphasizes the completed count
- **WHEN** a completed row has an enabled turn-in descriptor in the matching counter row
- **THEN** the completed tab's count is emphasized, and it is not emphasized when no completed row can be turned in

#### Scenario: An empty state tab says so
- **WHEN** the selected state has no rows
- **THEN** the list shows the shared empty guidance (a decorative glyph, a headline, and one guidance line) and no rows, and the detail area is empty

### Requirement: Selecting a quest shows its full detail beside the list

The list SHALL be a single-selection listbox whose rows show the category, name, tracked marker, grade, and
in-progress progress. The detail beside it SHALL show the category and commission kind, name, objective line and
note, grade, a completed or failed stamp, one-based stage progress, rationale, deadline, issuer with flavor, and
reward with settlement. A section whose source is null SHALL be omitted or show a fixed fallback, never invented
text.

#### Scenario: The first row is selected by default
- **WHEN** a state tab with rows is shown and no row was selected in it before
- **THEN** its first row is selected and its detail is shown

#### Scenario: Session memory ends with the presentation
- **WHEN** the transport generation or the presentation epoch changes and the drawer is opened again
- **THEN** the quest book tab, the in-progress state, and each state's first row are selected, as on a first open

#### Scenario: Selection is remembered per tab
- **WHEN** the player selects the second in-progress row, switches to completed, and switches back
- **THEN** the second in-progress row is still selected

#### Scenario: A vanished selection falls back
- **WHEN** the selected row leaves its state after a committed update
- **THEN** the first remaining row of that state is selected, or the detail empties when none remain

#### Scenario: Stage numbering is one-based
- **WHEN** an in-progress row with `stage_index` 0 and `stage_total` 1 is shown
- **THEN** the detail reads stage 1 of 1

#### Scenario: Null prose sections stay honest
- **WHEN** a row's `rationale` is null and its `flavor` is null
- **THEN** the rationale section is omitted and the issuer section shows the fixed no-message fallback

#### Scenario: A null reward omits the reward section
- **WHEN** a row's `reward` is null
- **THEN** no reward section and no settlement note render

#### Scenario: The list is keyboard operable
- **WHEN** focus is in the list and the player presses the down arrow, then Enter
- **THEN** the next row is selected and its detail is shown

### Requirement: The detail action bar mirrors server descriptors

The action bar SHALL render tracking only for in-progress rows, from the row's own `track` descriptor. Abandon
and turn-in SHALL render only from the `services` guild quest row with the same `quest_id`, mirroring its
enabled state, label, and reason; `quest_id` SHALL be the only join between the panels. Abandon SHALL need a
second confirmation. Rows without an enabled action SHALL state why: the counter reason, the claimed reward, the
counter-return hint, or the failed no-reward line.

#### Scenario: Tracking dispatches once and follows the commit
- **WHEN** the player activates the tracking toggle on an untracked in-progress row
- **THEN** exactly one `guild.quest_track` request with `{quest_id, tracked: true}` is submitted and the toggle's pressed state changes only when the commit lands

#### Scenario: Tracking works away from any clerk
- **WHEN** the player toggles tracking with no guild staff present
- **THEN** exactly one `guild.quest_track` request is submitted, because tracking is host-independent

#### Scenario: Completed and failed rows offer no tracking
- **WHEN** a completed or failed row's detail is shown
- **THEN** no tracking control renders

#### Scenario: Abandon needs two steps
- **WHEN** the player activates abandon on an in-progress row whose counter descriptor is enabled
- **THEN** a confirmation naming the quest and stating that abandoning fails it irreversibly appears with cancel and confirm, and only confirm submits the counter descriptor's exact action and payload

#### Scenario: An armed abandon disarms on change
- **WHEN** an abandon confirmation is open and the selection changes or the row leaves the list
- **THEN** the confirmation closes without dispatching

#### Scenario: Away from a clerk no counter action renders
- **WHEN** the book renders with no guild section available
- **THEN** no abandon or turn-in control renders on any row

#### Scenario: A disabled counter action stays disabled
- **WHEN** the matched counter turn-in descriptor is disabled with an already-claimed reason
- **THEN** the action bar shows that reason and no enabled turn-in control

#### Scenario: A private commission offers no counter actions
- **WHEN** an in-progress private commission is selected in front of a clerk
- **THEN** only the tracking toggle renders, because no counter row matches its quest ID

#### Scenario: A claimed reward is stated away from the counter
- **WHEN** a completed row with `reward_claimed` true is selected with no guild section available
- **THEN** the action bar reads 報酬已領取

#### Scenario: A pending counter reward points back to the counter
- **WHEN** a completed counter-settled row with `reward_claimed` false is selected away from any clerk
- **THEN** the action bar states that the reward is claimed by returning to the guild counter

### Requirement: The quest drawer degrades honestly

The drawer SHALL render a fixed absent line while `quest_log` has not been committed, the panel's own reason
message (carrying its reason code) when `quest_log` is unavailable, and an empty-state line for an available,
empty book. None of these forms SHALL list invented rows.

#### Scenario: The book before its first commit
- **WHEN** the drawer opens before any `quest_log` panel has been committed
- **THEN** the list area shows the fixed absent line and no rows

#### Scenario: An unavailable book shows its reason
- **WHEN** the committed `quest_log` panel is unavailable
- **THEN** the list area shows its reason message with its reason code and no rows

### Requirement: The guild counter tab presents counter business only

The guild counter tab SHALL render only from the `services` panel's guild section: registration for an
unregistered holder, and for a registered holder the quest board for accepting new quests and guild rank with
the promotion examination. It SHALL NOT re-list the holder's accepted quest records, so no quest appears in both
tabs as a held quest.

#### Scenario: The counter tab carries counter business
- **WHEN** the guild counter tab is selected in front of a clerk by a registered holder
- **THEN** it shows the board and the rank block, and lists no accepted quest

#### Scenario: Neither tab invents the other's data
- **WHEN** `quest_log` is available and `services` is unavailable
- **THEN** the quest book renders normally and the guild counter tab is disabled with the services reason

### Requirement: The guild board is organized by difficulty grade tabs

For a registered holder, the guild counter tab SHALL offer one vertical icon tab per key of the guild section's
`rank_ladder`, in ladder order, each showing that grade's seal, listing only that grade's board offers, and
showing its offer count. Grades above the holder's rank SHALL be marked locked, grades with no offers SHALL be
dimmed, and the holder's own grade SHALL be marked. The client SHALL derive no grade order or rank rule of its
own.

#### Scenario: Every grade has a fixed tab
- **WHEN** the counter tab renders for a registered E-rank holder with a seven-key ladder
- **THEN** seven grade tabs render in ladder order, and their positions never depend on which grades currently have offers

#### Scenario: A grade tab lists only its offers
- **WHEN** the player selects the F tab while the board holds two F and two E offers
- **THEN** only the two F offers are listed

#### Scenario: The default grade has work
- **WHEN** the counter tab is first shown for an E-rank holder whose board has F offers but no E offers
- **THEN** the F tab is selected, and when no grade at or below E has offers, the E tab is selected

#### Scenario: Grades above the holder's rank are locked
- **WHEN** an E-rank holder views the D tab
- **THEN** the D tab carries the locked mark and its list states that this grade opens after a promotion, with no rows

#### Scenario: A locked grade never implies hidden offers
- **WHEN** a locked grade tab is selected
- **THEN** no offer row, offer detail, or accept action renders, and the tab shows no offer count

#### Scenario: An eligible empty grade says so
- **WHEN** an E-rank holder views an E tab with no offers
- **THEN** the tab is dimmed and its list states that no offers of that grade are posted

#### Scenario: The holder's own grade is marked and named
- **WHEN** the grade tabs render
- **THEN** the holder's own grade carries the own-grade mark, and its tooltip names it as the holder's rank

### Requirement: The counter tab shows the rank card above the board

For a registered holder, the guild counter tab SHALL render the guild rank card, unchanged in content and
behavior, at the top of the board list column whenever the guild section carries a `rank` object, and the promotion examination request
SHALL keep dispatching exactly as before.

#### Scenario: Rank above the board
- **WHEN** a registered holder opens the counter tab in front of an examination counter
- **THEN** the rank card renders above the grade's offer list with its merit meter and examination request

#### Scenario: The examination request is unchanged
- **WHEN** the player activates an enabled examination request in the counter tab
- **THEN** exactly one `guild.exam_request` with the next-rank payload is submitted

### Requirement: Selecting a board offer shows its detail and the accept action

Selecting an offer SHALL show the same detail layout as a quest: the category, name, objective line and note,
grade, an acceptance condition naming the grade, the deadline or 無期限, `branch_label` as the commissioner with
the flavor prose, and the reward with counter settlement. The action bar SHALL render the offer's `accept`
descriptor as the primary action, and when it is disabled SHALL show its reason instead of an enabled control.

#### Scenario: An offer shows what accepting commits to
- **WHEN** the player selects an F offer with a 72-hour deadline and an item reward
- **THEN** the detail shows its objective and note, 接取後 3 日, the branch label, its flavor, and the item with quantity

#### Scenario: Accepting dispatches the descriptor once
- **WHEN** the player activates the enabled accept action on a selected offer
- **THEN** exactly one request with the descriptor's action and `{definition_key}` payload is submitted

#### Scenario: A disabled accept shows its reason
- **WHEN** the selected offer's accept descriptor is disabled because the quest is already active
- **THEN** the action bar shows the descriptor's reason and no enabled accept control

#### Scenario: An accepted offer appears in the book once
- **WHEN** an acceptance commits
- **THEN** the new quest appears in the quest book's in-progress tab and is not listed anywhere in the counter tab as a held quest

### Requirement: An unregistered holder sees registration instead of the board

When the guild section reports the holder as unregistered, the guild counter tab SHALL render no grade tabs
and no board. It SHALL instead render a registration card carrying the `registration.register` descriptor as its
primary action, or that descriptor's disabled reason.

#### Scenario: Registration replaces the board
- **WHEN** an unregistered holder opens the counter tab in front of a clerk
- **THEN** a registration card with the register action renders, and no grade tab, board row, or rank card renders

#### Scenario: Registering dispatches once
- **WHEN** the player activates the enabled register action
- **THEN** exactly one `guild.register` request is submitted, and the board with grade tabs appears only after the commit
