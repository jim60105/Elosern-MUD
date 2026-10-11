# Spec Delta

## MODIFIED Requirements

### Requirement: The quest book shows one quest state at a time
The existing quest drawer SHALL offer four second-level state tabs for in-progress, completed, failed and invalidated, preserving keyboard/accessibility, per-tab selection and one-state-at-a-time layout. Counts SHALL reflect stored rows. Completed-count emphasis SHALL remain restricted to enabled eligible counter claims; invalidated SHALL never indicate payout.

#### Scenario: The book opens on quests in progress
- **WHEN** the quest book tab is selected for the first time in a session
- **THEN** the in-progress state tab is selected and only in-progress rows are listed

#### Scenario: Switching state replaces the list
- **WHEN** the player selects the failed state tab
- **THEN** only failed rows are listed, with no other state's rows on screen

#### Scenario: Counts describe the stored rows
- **WHEN** the book holds three active, two completed, one failed and one invalidated record
- **THEN** the four existing-layout state tabs report 3, 2, 1 and 1 in accessible names

#### Scenario: A turn-in waiting at the counter emphasizes the completed count
- **WHEN** a completed row has an enabled turn-in descriptor in the matching counter row
- **THEN** the completed tab's count is emphasized, and it is not emphasized when no completed row can be turned in

#### Scenario: An empty state tab says so
- **WHEN** the selected state has no rows
- **THEN** the list shows the shared empty guidance (a decorative glyph, a headline, and one guidance line) and no rows, and the detail area is empty

#### Scenario: Invalidated history remains visible
- **WHEN** an accepted alternative is invalidated while the book is open
- **THEN** it moves to the invalidated state tab in stored order, preserving selection fallback and displaying its deterministic reason without reward entitlement

### Requirement: Selecting a quest shows its full detail beside the list
The existing single-selection listbox and beside-list detail SHALL retain category/name/tracking/grade/progress, canonical objective/deadline/rationale/issuer/reward fields, one-based stage and truthful null handling. Detail SHALL support completed, failed and invalidated stamps with nullable terminal_reason from the row. Invalidated detail SHALL state the obsolete-result reason and no payout, preserving existing keyboard/session selection behavior.

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

#### Scenario: Invalidated detail has its own stamp and reason
- **WHEN** an invalidated private escort is selected
- **THEN** detail shows invalidated and the bounded server-authored obsolete-result reason, with no successful completion, failure penalty or payout claim

### Requirement: The detail action bar mirrors server descriptors
Tracking SHALL render for active rows only. Ordinary guild abandon/turn-in SHALL mirror matching services descriptors by quest_id. Active private escort abandonment SHALL mirror its host-independent quest_log abandon descriptor with the same two-step confirmation. Terminal states SHALL offer no tracking/abandonment; invalidated SHALL explain no payout. Existing labels, disabled reasons, stale confirmation reset and dispatch ownership SHALL remain.

#### Scenario: Tracking dispatches once and follows the commit
- **WHEN** the player activates the tracking toggle on an untracked in-progress row
- **THEN** exactly one `guild.quest_track` request with `{quest_id, tracked: true}` is submitted and the toggle's pressed state changes only when the commit lands

#### Scenario: Tracking works away from any clerk
- **WHEN** the player toggles tracking with no guild staff present
- **THEN** exactly one `guild.quest_track` request is submitted, because tracking is host-independent

#### Scenario: Completed and failed rows offer no tracking
- **WHEN** completed, failed or invalidated detail is shown
- **THEN** no tracking control renders

#### Scenario: Abandon needs two steps
- **WHEN** an enabled counter or private escort abandonment is activated
- **THEN** a confirmation names the exact quest and irreversible failure, cancel changes nothing, and confirm submits that descriptor action with its exact quest_id

#### Scenario: An armed abandon disarms on change
- **WHEN** an abandon confirmation is open and the selection changes or the row leaves the list
- **THEN** the confirmation closes without dispatching

#### Scenario: Away from a clerk no counter action renders
- **WHEN** the book renders without a usable guild section
- **THEN** no guild counter action renders; active private escort abandonment remains available from its own host-independent quest_log descriptor

#### Scenario: A disabled counter action stays disabled
- **WHEN** the matched counter turn-in descriptor is disabled with an already-claimed reason
- **THEN** the action bar shows that reason and no enabled turn-in control

#### Scenario: A private commission offers no counter actions
- **WHEN** an active private escort is selected with or without guild staff
- **THEN** tracking and its host-independent abandonment descriptor render, no unrelated counter turn-in renders, and only confirming the named quest dispatches abandonment

#### Scenario: A claimed reward is stated away from the counter
- **WHEN** a completed row with `reward_claimed` true is selected with no guild section available
- **THEN** the action bar reads 報酬已領取

#### Scenario: A pending counter reward points back to the counter
- **WHEN** a completed counter-settled row with `reward_claimed` false is selected away from any clerk
- **THEN** the action bar states that the reward is claimed by returning to the guild counter

#### Scenario: Multiple escort sources select the affected mission
- **WHEN** party dismissal identifies two active escort reasons for one NPC
- **THEN** the current mission choices name both records and confirm only the selected record's descriptor; the other reason and any general identity persist
