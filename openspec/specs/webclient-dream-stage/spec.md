# webclient-dream-stage Specification

## Purpose
Defines how the browser presents and operates the collaborative dream of the cloud throne. The dream is staged as an AVG scene over its official artwork, with visible exchange and excitement tracks, paced reveals, a legible story-direction (念頭) keepsake, and exits that never lose the player's words by accident. All of it runs on the unchanged server-authored `dream` panel.

## Requirements

### Requirement: The dream is a full-stage AVG scene over its official artwork

While the committed `dream` panel state is open, the browser SHALL present the dream as one modal dialog covering the stage. The dialog SHALL be named by its visible title 雲上王座之夢 and SHALL contain these regions:
- the server-resolved scene artwork;
- a keepsake card showing the current wish and the stage's rows;
- a reply bar for free text;
- a message band that presents the narration and the goddess's lines under her name plate.

#### Scenario: Open dream renders the stage regions
- **WHEN** an open dream state with artwork is committed
- **THEN** a modal dialog shows the artwork, the keepsake card with four rows, the reply bar and the message band, and contains no `<details>` element

#### Scenario: Artwork fails to load
- **WHEN** the preferred exact dream official image fails
- **THEN** the bundled dream image then distinct town terminal are resolved through the shared scene lifecycle and reached failures remain local, without broken images

#### Scenario: An empty artwork URL is removed
- **WHEN** the optional exact official dream source is undeclared
- **THEN** the required bundled dream image displays without error styling and there is no inherited physical-location background

#### Scenario: A changed artwork URL is attempted afresh
- **WHEN** a relevant dream descriptor revision changes
- **THEN** the shared lifecycle recomputes its ordered attempts and ignores stale callbacks

#### Scenario: The surface stays flat and standard-styled
- **WHEN** the stage is rendered
- **THEN** it uses no nested disclosure widgets and surfaces no command syntax or JSON, and every button outside the edit sheet's and thread choice's inline controls shares the client's standard button styling

#### Scenario: Dream wire ships atomically
- **WHEN** the dream panel is emitted
- **THEN** the server presenter and the client validator declare the same schema version and the same exact state fields, state.scene_art is the canonical descriptor, and a payload that lacks a current field, carries an unknown one or carries a raw URL-only scene_art is rejected

#### Scenario: Stage fields are validated together
- **WHEN** a dream state carries a stage, proposal, change report, thread choice and stage flags
- **THEN** the client validator accepts a consistent state and rejects an unknown stage, a proposal or change report outside its exact bounded shape, free text offered outside the conversing stage, and editing or confirmation offered outside the finalized stage

#### Scenario: The largest legal stage state fits
- **WHEN** a dream state carries a proposal and a change report at their aggregate bounds, 32 thread labels and the prose keys at their own bounds
- **THEN** the published payload stays inside the protocol envelope and the client validator accepts it

#### Scenario: Dream art leaves lifecycle unchanged
- **WHEN** the dream descriptor resolves repeatedly
- **THEN** no physical-room/archetype generation is enqueued and sleep/session/dialogue/authoring state is unchanged

### Requirement: Exchange budget and goddess excitement have visual, non-colour-only forms

The reply bar SHALL show the six-exchange budget as six pips, with spent exchanges hollow, plus a remaining-count label. The goddess's name plate SHALL show a five-segment excitement gauge lit up to the server-supplied track ordinal, plus the server-supplied level label. Both SHALL be exposed as meters whose value text states, for the budget, the remaining and total counts and, for the gauge, the level label.

#### Scenario: Fresh dream
- **WHEN** a dream with zero completed exchanges is shown
- **THEN** six live pips with a remaining-count label of six, five gauge segments with one lit, a budget value text containing 6 twice and a gauge value text containing the server's level label are present

#### Scenario: Composing marks the next pip
- **WHEN** the player types into the reply bar with no exchange completed
- **THEN** the first pip is marked as the one the send would spend

#### Scenario: An exchange completes
- **WHEN** the completed count rises to one
- **THEN** exactly one pip is hollow

#### Scenario: A pending response keeps the next pip marked
- **WHEN** a response is pending
- **THEN** the pip that the next send would spend remains marked, as it is while the player is composing

### Requirement: Narration and dialogue are paced by beats that only animate on a live exchange

On a first entry (no completed exchange and no scene or dialogue), the message band SHALL type the opening as narration. Whenever the committed completed count increases while the surface is mounted (including an increase that arrives with a reconnect), the band SHALL type the new scene narration, then the goddess's line as a second beat. Mounting the surface SHALL show the latest beat in full without typing.

#### Scenario: Arrival types the opening
- **WHEN** a dream opens with no exchange yet
- **THEN** the band presents the opening prose as narration

#### Scenario: Live reveal then advance
- **WHEN** the completed count rises with a new scene and line
- **THEN** the band shows the scene first, shows the line after one activation, and the live region announces `王座上的女神說：` followed by the line

#### Scenario: Full-motion typing completes then advances
- **WHEN** a live reveal starts at full motion and the player activates the band twice
- **THEN** the scene is partly shown at first, the first activation shows it in full, and the second presents the goddess's line

#### Scenario: Reconnect does not replay
- **WHEN** a state with the same completed count is republished at a newer revision
- **THEN** the presented beat is unchanged

#### Scenario: Activating the band completes then advances
- **WHEN** the player activates the band (click, Enter or Space) while a beat is still typing
- **THEN** the beat completes and the next activation advances to the next beat

#### Scenario: The re-read control steps back
- **WHEN** the player uses the re-read control
- **THEN** the band steps back to the previous beat in full

#### Scenario: Typing is time-paced only at full motion
- **WHEN** typing runs at the full motion level
- **THEN** it progresses over time at the player's text speed

#### Scenario: Reduced and off motion show text at once
- **WHEN** the motion level is reduced or off
- **THEN** text appears at once and no animation outlasts its motion level's duration

#### Scenario: Each new response is announced in full
- **WHEN** a new response arrives
- **THEN** an assistive-technology announcement reports it with the scene, the goddess's line, the excitement level and the remaining count

#### Scenario: Pending and failure announce once
- **WHEN** a pending state or a failure occurs
- **THEN** each is announced once when it occurs

### Requirement: The reply bar sends bounded free text and hands it back on failure

The reply bar SHALL accept free text only while the server allows input and the transport is unlocked. Enter SHALL send `dream.say` with the current session id and revision and the message split at 2000 code points into two parts. Shift+Enter SHALL insert a newline, and Enter during an IME composition SHALL NOT send. A successful dispatch SHALL clear the field. Once the session is finalized the free-text form SHALL be replaced by an end bar.

#### Scenario: Bounded send on Enter
- **WHEN** the player types 4000 characters and presses Enter
- **THEN** `dream.say` is dispatched with two 2000-code-point parts and the field clears

#### Scenario: Shift+Enter and IME do not send
- **WHEN** the player presses Shift+Enter, or Enter while composing
- **THEN** nothing is dispatched

#### Scenario: Failed generation is retryable
- **WHEN** a sent message's generation fails
- **THEN** the field holds the sent words, the send control changes to its retry label and no pip is hollow

#### Scenario: Budget exhausted
- **WHEN** all six exchanges are spent
- **THEN** no free-text form is present and the end bar is shown

#### Scenario: Converging captions
- **WHEN** a conversing session's track is converging with two, then one, exchange remaining
- **THEN** a converging caption is shown and it is extended for the last exchange

#### Scenario: Transport locked
- **WHEN** the client is disconnected, mutations are locked, the session is inactive, or a dispatch is in flight
- **THEN** the reply field, the thread choice and all four keepsake rows are disabled, and while disconnected the reconnect caption is shown

#### Scenario: The transport lock conditions are enumerated
- **WHEN** deciding whether the transport is locked
- **THEN** it is locked while the client is disconnected, mutations are locked, the session is not active, a dispatch is in flight, or combat playback holds the command panel

#### Scenario: Converging caption needs at most two exchanges left
- **WHEN** deciding whether to show the converging caption
- **THEN** it appears only while conversing, when at most two exchanges remain and the server reports the track is converging, and never once finalized

#### Scenario: Disconnected reply bar explains itself
- **WHEN** the client is disconnected
- **THEN** the reply bar says that the link to the dream is being restored and that typed words are kept

#### Scenario: Pending response state is shown
- **WHEN** a response is pending
- **THEN** the field is disabled, the band echoes the player's sent words prefixed `你：`, and the name plate shows that the goddess is responding

#### Scenario: Refill respects newly typed text
- **WHEN** the server reports a failed generation
- **THEN** the field is refilled with the words just sent, unless the player has typed new text

#### Scenario: The end bar names the waiting goddess
- **WHEN** the session is finalized, at the cap or before it
- **THEN** the reply form is replaced by an end bar whose text differs between the two cases

### Requirement: Direction confirmation is validated locally without discarding words

Confirming with an empty summary SHALL NOT dispatch. It SHALL open (or keep) the edit sheet with an alert and focus the summary. The confirm row SHALL be marked unavailable with a visible reason while the summary is empty, but SHALL stay focusable. A summary longer than 2000 code points SHALL refuse draft and confirm with an alert until shortened.

#### Scenario: Empty confirm
- **WHEN** the player activates the confirm row of a finalized session with no summary
- **THEN** nothing is dispatched, the edit sheet shows an alert and focus is on the summary field

#### Scenario: Over-length direction
- **WHEN** the finalized form's summary is 2001 code points and the player confirms
- **THEN** the field holds all 2001 code points, nothing is dispatched, and an alert is shown

#### Scenario: Overflow is marked, never truncated
- **WHEN** the finalized form's summary is longer than 2000 code points
- **THEN** it is shown in full, the counter marks the overflow, the text is never truncated silently, and draft and confirm are refused with an alert until the player shortens it

### Requirement: Escape never awakens and awakening protects unsaved local words

Escape SHALL NOT dispatch any dream action. It SHALL do the first of these that applies:
1. close the open layer (artwork view, thread list, finalize confirmation, whole-wish view, awaken check or edit sheet);
2. move focus out of a text field to the message band;
3. otherwise, move focus to the awaken row.

Activating the awaken row SHALL dispatch at once only when nothing local would be lost.

#### Scenario: Escape focuses the awaken row
- **WHEN** the player presses Escape with no layer open and focus outside a text field
- **THEN** focus moves to the awaken row and nothing is dispatched

#### Scenario: Escape closes a layer and keeps edits
- **WHEN** the player presses Escape with the edit sheet open after changing a field
- **THEN** the sheet closes, the change is kept and nothing is dispatched

#### Scenario: Unsent words are protected
- **WHEN** the reply field holds text and the player activates the awaken row
- **THEN** an alert dialog opens with focus on the stay control, and only its awaken control dispatches `dream.awaken`

#### Scenario: A clean awaken dispatches at once
- **WHEN** the awaken row is activated with no unsent reply and no unsaved finalized edit
- **THEN** `dream.awaken` is dispatched at once, with no dialog

#### Scenario: The awaken guard names what would be lost
- **WHEN** the awaken row is activated while an unsent reply exists, or while a finalized form differs from the server proposal
- **THEN** an alert dialog opens with one statement for unsent words and one for unsaved manual edits, each shown only when it applies; while conversing an unedited form never triggers the dialog

#### Scenario: The awaken guard dialog behaves predictably
- **WHEN** the awaken dialog is open
- **THEN** initial focus rests on the stay control, Escape or the stay control returns to the dream without dispatching, and the awaken control dispatches `dream.awaken`

#### Scenario: The awaken check says the wish is kept
- **WHEN** the dialog opens while the server proposal has a summary and no draft is saved
- **THEN** it states that the current wish will be kept

### Requirement: Republished drafts rehydrate without overwriting the player's own edits

On mount the local form SHALL load the server proposal and thread. When the server republishes the proposal or thread for the same session, each local field the player has not edited SHALL adopt the server value, and a field the player has edited SHALL keep the player's value. Unsent reply text SHALL never be cleared by a republish. Clearing an edited summary SHALL restore following the server.

#### Scenario: External draft change
- **WHEN** a changed proposal and thread are republished while the reply field holds unsent text
- **THEN** the unsent text remains, the card names the thread and shows the republished summary, and the whole-wish view shows the republished fields

#### Scenario: Saved preferences load on mount
- **WHEN** the surface mounts on a finalized state whose proposal carries a summary and list items
- **THEN** the form holds them as unedited values, the awaken row dispatches at once, and confirm sends them

#### Scenario: Edited summary is kept
- **WHEN** the player has edited the summary of a finalized form and a republish carries a different summary
- **THEN** the player's summary remains, and after clearing it the next republish is adopted

#### Scenario: Unedited lists follow
- **WHEN** a finalized form's lists are unedited and a republish changes one
- **THEN** the form shows the republished list

### Requirement: Dream confirmation displays the frozen experience requirements

The whole-wish view and the edit sheet SHALL show the proposal's bounded experience requirements with a readable label for each kind. A draft or confirmation dispatched from the finalized form SHALL carry exactly the requirement rows the form shows. Existing exit, local-word preservation and accessibility behavior SHALL remain intact, without JSON or a new story panel.

#### Scenario: Player sees the intended executable experience
- **WHEN** the proposal carries one requirement of each kind
- **THEN** the whole-wish view while conversing and the edit sheet when finalized each list three rows with their kind labels and texts, and `dream.confirm` carries `kind`, `thread_id`, `summary`, exactly those rows and only the non-empty lists at the latest committed revision, with no version identity

#### Scenario: Reconnect and local edit
- **WHEN** the proposal republishes with different requirement rows while the reply field holds unsent text
- **THEN** the unsent words survive and the shown rows are the republished ones

#### Scenario: Confirmation closes without preparation lock
- **WHEN** valid confirmation commits with generation still pending
- **THEN** the dream stage closes and waking controls remain usable; preparation/waiting messages appear through ordinary output rather than keeping the dream modal locked

### Requirement: The keepsake card shows the current wish and stage-specific rows

The keepsake card SHALL show the current wish summary or an empty-state invitation, a two-step stage indicator and the thread line. It SHALL offer four rows in fixed positions: row 1 opens the whole-wish view while conversing and the edit sheet when finalized; row 2 requests finalize while conversing and confirms when finalized; row 3 saves a draft; the last row awakens. Digits 1 to 3 SHALL activate rows 1 to 3 outside text fields and without modifiers.

#### Scenario: Rows while conversing
- **WHEN** a conversing state is shown and the player activates rows 1, 2 and 3 in turn
- **THEN** row 1 opens the read-only view, row 2 opens the finalize confirmation without dispatching, and row 3 dispatches `dream.draft` with no direction content

#### Scenario: Rows when finalized
- **WHEN** a finalized state with a summary is shown and the player activates rows 1, 3 and 2 in turn
- **THEN** row 1 opens the edit sheet, row 3 dispatches `dream.draft` with the form, and row 2 dispatches `dream.confirm` with the form

#### Scenario: One primary control per stage
- **WHEN** the session is conversing with input allowed, and when it is finalized
- **THEN** the only primary control is the send control in the first case and the confirm row in the second

#### Scenario: Finalize row waits for the response
- **WHEN** a response is pending while conversing
- **THEN** the finalize row is disabled and the draft and awaken rows stay enabled

#### Scenario: Digit shortcuts
- **WHEN** the player presses 1 outside a text field, then Ctrl+1, then 1 inside a text field
- **THEN** only the first press activates row 1

#### Scenario: Sixth exchange moves focus
- **WHEN** a live exchange reaches six
- **THEN** focus rests on the confirm row when a summary exists and on row 1 when it does not

#### Scenario: Thread line shows the lock
- **WHEN** the thread can no longer be chosen
- **THEN** the thread line carries a lock marker and names the new story, the chosen thread's label, or a previously chosen thread that is no longer offered

#### Scenario: Draft confirmation waits for the committed state
- **WHEN** a draft is dispatched
- **THEN** a toast is shown and announced only once a newer committed state reports a saved draft, and a refused draft shows none

### Requirement: The whole wish is read-only while conversing

While conversing, row 1 SHALL open a modal view that traps focus, renders the rest of the stage inert and shows every proposal field, the requirement rows and the thread as plain text with a placeholder for an empty field. The view SHALL contain no form field. It SHALL offer the finalize request and a close control.

#### Scenario: Plain text, no inputs
- **WHEN** the view opens on a proposal with a summary, list items and requirement rows
- **THEN** each value is rendered as text, empty fields show a placeholder, and the view contains no input, textarea or select element

#### Scenario: Finalize from the view
- **WHEN** the player activates the view's finalize control
- **THEN** the view closes and the finalize confirmation opens without dispatching

#### Scenario: View follows a republish
- **WHEN** the proposal is republished while the view is open
- **THEN** the view shows the republished values

### Requirement: Finalize asks before giving up remaining exchanges

Requesting finalize SHALL open an alert dialog that states how many exchanges would be given up, with default focus on the control that keeps conversing. Only its explicit finalize control SHALL dispatch `dream.finalize` with the current session id and revision. When a live state change makes the session finalized before the cap, the edit sheet SHALL open.

#### Scenario: Default focus stays
- **WHEN** the finalize confirmation opens with three exchanges remaining
- **THEN** it names the count three, focus is on the stay control, and activating that control or pressing Escape closes it without dispatching

#### Scenario: Repeated key cannot finalize and submit
- **WHEN** the player presses 2, then presses 2 again and activates the focused control
- **THEN** the second key press does nothing, the focused control is the stay control, the confirmation closes and nothing is dispatched

#### Scenario: Explicit finalize dispatches once
- **WHEN** the player activates the finalize control
- **THEN** exactly one `dream.finalize` is dispatched and the dialog closes

#### Scenario: Becoming finalized opens the edit sheet
- **WHEN** the committed state changes from conversing to finalized with exchanges remaining, and when it changes at the sixth exchange
- **THEN** the edit sheet opens in the first case and does not open by itself in the second

### Requirement: The thread choice sits above the reply bar before the first message

While the server allows choosing a thread and offers at least one, a choice control SHALL sit above the reply bar with the new story preselected and a note that the choice locks at the first message. Selecting a different option SHALL dispatch `dream.choose_thread` with that thread id, or null for the new story. With no thread offered, or once choosing is not allowed, the control SHALL be absent.

#### Scenario: Choose a thread
- **WHEN** the player opens the choice and selects an offered thread
- **THEN** `dream.choose_thread` is dispatched with that thread's id and focus returns to the reply field

#### Scenario: Reselecting dispatches nothing
- **WHEN** the player selects the option that is already chosen
- **THEN** nothing is dispatched

#### Scenario: Speaking without choosing
- **WHEN** the player types and sends without touching the choice
- **THEN** only `dream.say` is dispatched

#### Scenario: Nothing to offer or locked
- **WHEN** no thread is offered, or the state no longer allows choosing
- **THEN** the choice control is not rendered

### Requirement: The edit sheet edits the wish only when finalized

When finalized, row 1 SHALL open a modal sheet that traps focus and renders the rest of the stage inert. It SHALL contain, without nested disclosure: the summary field with a code-point counter out of 2000 and a revert control when it differs from the server; five chip lists; the requirement rows; and the thread shown as fixed. Its draft and confirm controls SHALL dispatch the same form payload. The sheet SHALL NOT be reachable while conversing.

#### Scenario: Chips and draft
- **WHEN** the player adds the same list item twice and saves a draft
- **THEN** one chip exists, `dream.draft` carries that list with one item, the sheet closes and the dream stays open

#### Scenario: Chip editing rules
- **WHEN** the player presses Enter in a chip input, or Backspace on an empty chip input
- **THEN** Enter adds a trimmed, de-duplicated chip and Backspace removes the last chip

#### Scenario: Both controls send the same payload shape
- **WHEN** the sheet's draft or confirm control dispatches
- **THEN** both send `kind`, `thread_id`, `summary`, `requirements` and only the non-empty lists at the latest committed revision

#### Scenario: The thread is fixed
- **WHEN** the sheet is open with a chosen thread that is still offered
- **THEN** the thread is shown as text and the sheet offers no control that changes it

#### Scenario: An ended thread can be released
- **WHEN** the chosen thread is no longer offered and the player activates the release control
- **THEN** the form's thread becomes the new story and the next payload carries a null thread id and the new-story kind

#### Scenario: Not reachable while conversing
- **WHEN** the session is conversing
- **THEN** no control opens the edit sheet and Ctrl+Enter does not confirm

### Requirement: The keepsake card reports what the last exchange changed

While conversing, the keepsake card SHALL show a change line built from the server's change report: each changed field named in words with a glyph, list fields with their counts of added and removed items, or a statement that nothing changed. With no report the line SHALL be absent. After a live exchange the card's wish and change line SHALL update only once the goddess's line has finished revealing, SHALL stay until the next exchange settles, and SHALL be announced once through the live region.

#### Scenario: Changed fields are named
- **WHEN** the report says the summary changed, one list gained an item and lost another, and the other fields are untouched
- **THEN** the line names the summary and that list, shows the list's added and removed counts as text, and names no other field

#### Scenario: Nothing changed
- **WHEN** the report shows no change in any field
- **THEN** the line states that nothing changed, in different text from a changed turn

#### Scenario: No report yet
- **WHEN** the state carries no change report
- **THEN** no change line is rendered

#### Scenario: The line waits for the reveal
- **WHEN** a live exchange arrives with a new proposal and report while its scene and line are still being presented
- **THEN** the card still shows the previous wish and line, and shows the new ones only after the last beat has been shown in full

#### Scenario: Announced once
- **WHEN** the new line appears after a reveal
- **THEN** the live region carries its text once, and a republish of the same report does not announce again

#### Scenario: Mount shows the committed report
- **WHEN** the panel mounts on a state that already carries a report
- **THEN** the line is shown at once without waiting for a reveal

#### Scenario: Not shown when finalized
- **WHEN** the session is finalized
- **THEN** the card shows no change line

### Requirement: The whole-wish view marks changes and names removed items

The whole-wish view SHALL mark each field the last change report touched, SHALL mark each added list item and requirement row, and SHALL list the removed items of a field by name under that field. Marks SHALL use text or a glyph and not colour alone. The view SHALL show the same wish and report the card currently shows.

#### Scenario: Added and removed are visible
- **WHEN** the report says a list gained one item and lost another
- **THEN** that field carries a changed mark, the gained item carries an added mark, and the lost item's text is listed under the field as removed

#### Scenario: Removed requirement row
- **WHEN** the report says a requirement row was removed
- **THEN** the row's text is listed as removed under the requirement section

#### Scenario: Untouched fields are unmarked
- **WHEN** a field is absent from the report's changes
- **THEN** it carries no changed mark and no removed list

#### Scenario: Summary state
- **WHEN** the report marks the summary as formed, and when it marks it as changed
- **THEN** the summary section's mark differs between the two

### Requirement: Requirement rows are editable when finalized

In the edit sheet of a finalized session the player SHALL be able to add a requirement row with a kind chosen from the closed set, edit a row's kind and text, and remove a row. The section SHALL show the row count against the limit of eight and SHALL offer no add control at the limit. A row whose text is blank SHALL block draft and confirm, be marked invalid with a message at that row, and keep every other local value. Unedited rows SHALL follow a republished proposal; edited rows SHALL be kept.

#### Scenario: Add, edit and remove
- **WHEN** the player adds a row, chooses its kind, types its text, removes an earlier row and saves a draft
- **THEN** `dream.draft` carries exactly the remaining rows with their kinds and trimmed texts in display order

#### Scenario: Limit
- **WHEN** eight rows exist
- **THEN** the count shows eight of eight and no add control is rendered

#### Scenario: Blank row blocks submission
- **WHEN** one row's text is blank and the player confirms or saves a draft
- **THEN** nothing is dispatched, that row is marked invalid with an alert message, and the other rows and fields keep their values

#### Scenario: Unsaved rows are protected on awaken
- **WHEN** the player has changed a row and activates the awaken row
- **THEN** the awaken check opens and names the unsaved edits

#### Scenario: Rows rehydrate like other fields
- **WHEN** the rows are unedited and a republish carries different rows, and when the player has edited a row before the republish
- **THEN** the first form shows the republished rows and the second keeps the player's rows
