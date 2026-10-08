## Purpose

Present the NPC author editor in the browser: opened from a selected NPC's 編輯人物設定 entry, bound to that target and session, showing and editing the complete compact card with visible budgets, and saving or cancelling back to the original interaction context with accessible, correlation-safe behavior.

## Requirements

### Requirement: The author editor opens from the selected target and binds to it
Activating a target's 編輯人物設定 navigation SHALL open one editor window bound to that target identity and the presentation epoch current at opening, SHALL immediately request `npc.persona.read` for that identity, and SHALL never rebind to a target selected afterwards. Only one editor SHALL be open at a time, and opening it SHALL not dispatch any other action.

#### Scenario: The entry opens a bound editor and reads once
- **WHEN** the player selects a present NPC, opens its verb menu, and activates 編輯人物設定
- **THEN** one editor opens in the loading state, exactly one `npc.persona.read` naming that NPC is dispatched, and selecting a different target afterwards does not change the editor's bound NPC

#### Scenario: A disabled entry explains itself
- **WHEN** the target's 編輯人物設定 entry is disabled by the server
- **THEN** activating it opens nothing and the server-authored reason is shown

#### Scenario: The editor reuses existing shell primitives
- **WHEN** the editor is built
- **THEN** it reuses the client's existing drawer frame, header, overlay, typography, spacing, and focus primitives
- **AND** no full-screen NPC catalogue or new layout system is added

### Requirement: The editor presents the full card and the offline greeting with notices and budgets
In its ready states the editor SHALL present the complete labeled card — the seven card sections as labeled text controls in the card's render order, with public and hidden identity as separate controls inside the identity section — followed by one optional offline-greeting control (離線問候語) with its own 300-code-point budget that does not count toward the card total.

#### Scenario: The greeting control previews the default and keeps its own budget
- **WHEN** the editor is ready for a table-backed host whose greeting field is empty and the player types a greeting beyond 300 code points
- **THEN** the control shows its own overflow without touching the card total, the preview shows the table greeting as the current default, and save is disabled until the draft is valid

#### Scenario: Budgets update as the player types
- **WHEN** the player types into the speech-style control until the card's rendered total exceeds its bound
- **THEN** the total capacity shows the overflow, the control's text is not truncated, an accessible error names the total budget, and save is disabled

#### Scenario: Notices are always visible
- **WHEN** the editor is ready for any NPC
- **THEN** the author-mode/spoiler notice and the no-regeneration notice are visible without scrolling the notices out of their region

#### Scenario: The heading names the bound NPC
- **WHEN** the editor is in its ready states
- **THEN** the bound NPC's name and title appear in its heading

#### Scenario: Controls are marked and carry budgets
- **WHEN** the card controls render
- **THEN** each control is marked required or optional
- **AND** each control shows its remaining code points and the remaining capacity of the complete labeled card, computed by the browser card-contract mirror

#### Scenario: The greeting control previews the default and states its scope
- **WHEN** the greeting control renders
- **THEN** it previews the currently-effective authored default greeting (the read's `default_greeting` — the table or profile line — or 無 when it is empty)
- **AND** helper text states the field replaces that default as the NPC's offline/keywordless first line, never affects keyword answers, and never affects LLM dialogue, which always follows the card

#### Scenario: Invalid drafts are reported before submission
- **WHEN** a control holds over-budget or empty-required input
- **THEN** it is reported before submission without truncating the text, and save is disabled while the local draft is invalid

#### Scenario: Narrow viewports keep the controls reachable
- **WHEN** the editor renders on a narrow viewport
- **THEN** it is a single scrollable column whose save and cancel controls stay reachable

### Requirement: Editor state transitions are correlated and never fabricate outcomes
The editor SHALL move only through loading, ready-clean, ready-dirty, saving, conflict, and rejected/unavailable states. Every read and save result SHALL be correlated to its request and to the bound target. Only a confirmed server save SHALL replace the committed baseline and report success; a rejected save SHALL keep the draft intact with an announced, field-specific message.

#### Scenario: A late read for a closed editor is ignored
- **WHEN** the player opens the editor for one NPC, closes it before the read settles, and opens it for another NPC
- **THEN** the first read's late result does not populate or close the second editor

#### Scenario: Late or superseded results never seed or close the editor
- **WHEN** a read or save result arrives late for a closed editor, another target, or a superseded request
- **THEN** it neither seeds nor closes the current editor

#### Scenario: A rejected save keeps the draft
- **WHEN** a save is rejected with a field-specific code
- **THEN** the draft text is unchanged, the message names the field, focus moves to that field, and the baseline is unchanged

#### Scenario: Saving cannot be submitted twice
- **WHEN** the player activates save twice quickly
- **THEN** exactly one `npc.persona.update` is dispatched

#### Scenario: Submission is locked while saving
- **WHEN** the editor is in the saving state
- **THEN** duplicate submission is impossible

#### Scenario: A reconnect keeps the draft and re-reads
- **WHEN** the transport drops while the editor holds a dirty draft and the same character reconnects
- **THEN** no success or failure is claimed while disconnected, the editor re-reads once on the new epoch, keeps the draft, and enters the conflict state only if the version moved

#### Scenario: Transport loss leaves the editor open with save disabled
- **WHEN** the transport is lost while the editor is open
- **THEN** the editor stays open without a success or failure claim and save is disabled
- **AND** after reconnection of the same character the editor rebinds to the new presentation epoch and re-reads before allowing another save, keeping the draft
- **AND** when the re-read version differs from the draft's base version the editor enters the conflict state

#### Scenario: A background refresh never replaces a draft
- **WHEN** a background panel refresh arrives while the editor holds a draft
- **THEN** the refresh never replaces the draft

### Requirement: Conflicts, departures, and session changes protect the draft
A version conflict SHALL preserve the draft and offer an explicit reload, which issues a fresh `npc.persona.read` that replaces the baseline and version while keeping the draft, and an explicit discard, which replaces the draft with the latest saved card; there SHALL be no automatic merge or silent overwrite, and saving after a reload is a deliberate submission against the reloaded version.

#### Scenario: Another tab saved first
- **WHEN** two browser tabs open the same NPC, the first saves, and the second then saves
- **THEN** the second tab shows the conflict with its draft intact, choosing reload re-reads the card at the new version while keeping the draft, and choosing discard then shows the first tab's saved card at the new version

#### Scenario: The NPC walks away
- **WHEN** the bound NPC leaves the room while the editor holds a dirty draft
- **THEN** the draft stays visible, an unavailable notice appears, and save is disabled

#### Scenario: A puppet change clears the editor
- **WHEN** the player switches to another character while the editor is open
- **THEN** the editor closes and no card text remains in the client store or any persistent browser storage

#### Scenario: Departure or access change yields an unavailable state
- **WHEN** the bound NPC leaves the actor's location, is deleted, or the actor's mode or access changes
- **THEN** the editor keeps the draft visible with a clear unavailable state and disables save, with server revalidation remaining authoritative

#### Scenario: Session replacement closes the editor and clears state
- **WHEN** logout (the puppet detaching), a puppet change, or a session replacement (a new presentation epoch within the same transport, or a reconnect that lands on a different character) occurs
- **THEN** the editor closes and all private editor state is cleared

#### Scenario: Editor data never leaks to logs or storage
- **WHEN** the editor operates
- **THEN** editor data is never written to persistent browser storage, the narrative log, or an action echo

### Requirement: Editor closing and accessibility follow the shell's dialog rules
Cancel SHALL close a clean editor immediately; closing a dirty editor by cancel, Escape, or backdrop SHALL require an explicit confirmation to discard. The editor SHALL be a named modal dialog with focus contained while open, visible focus, labeled controls, keyboard-operable buttons, and announced errors and save results.

#### Scenario: Escape on a dirty draft asks first
- **WHEN** the player edits a field and presses Escape
- **THEN** a discard confirmation appears, declining it keeps the editor and draft, and accepting it closes the editor and returns focus to the verb-menu entry or the interaction surface

#### Scenario: Typing does not move the character
- **WHEN** the player types movement or dock shortcut keys into an editor field
- **THEN** the characters enter the field and no movement or dock action is dispatched

#### Scenario: A keyboard-only save round trip persists
- **WHEN** a keyboard-only player opens the editor for a real NPC, changes a field, saves, closes, and reopens the editor
- **THEN** the reopened editor shows the saved text at the advanced version

#### Scenario: Closing returns focus to the opening context
- **WHEN** the editor closes
- **THEN** focus returns to the opening control when it still exists and otherwise to the interaction surface, returning the player to the original interaction context

#### Scenario: Editor typing never triggers game shortcuts
- **WHEN** the player types in editor controls
- **THEN** typing never triggers movement or dock shortcuts

#### Scenario: No new gamepad support is added
- **WHEN** a player navigates with a gamepad
- **THEN** only the client's existing navigation applies; no gamepad support beyond it is added

### Requirement: NPC editor dirty and reconnect comparisons use canonical normalization
NPC editor comparisons SHALL apply the same complete card-and-greeting normalized equality as the server, including the explicit boundary-whitespace set and exact CRLF conversion. Boundary-only changes SHALL remain clean; preserved interior or excluded-character changes SHALL be dirty.

#### Scenario: Boundary-only typing stays clean
- **WHEN** the user adds only enumerated outer whitespace to a card leaf or greeting
- **THEN** the editor remains normalized-clean and does not request dirty-close discard confirmation

#### Scenario: Interior whitespace is a real edit
- **WHEN** the user adds interior U+0085 or boundary U+200B to a previously clean draft
- **THEN** the editor reports dirty state and the normalized save is a real server change

#### Scenario: Reconnect after uncertain boundary-only save
- **WHEN** transport is lost during a boundary-only submission and later reconnects
- **THEN** the editor re-reads authoritative data/version before another save, reconciles normalized equality without claiming unobserved success, and does not create spurious dirty state or duplicate version advances

#### Scenario: Comparison never rewrites inputs or discards drafts
- **WHEN** normalization runs for comparison, including after rejected or uncertain saves
- **THEN** it never destructively rewrites local inputs and never discards drafts

#### Scenario: Prior correlation and conflict rules remain in force
- **WHEN** the editor compares state after reconnects or conflicts
- **THEN** the existing session correlation, expected-version and explicit conflict reload rules remain in force, and the editor never infers a successful prior save merely from local equality
