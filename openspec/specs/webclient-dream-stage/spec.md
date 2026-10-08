# webclient-dream-stage Specification

## Purpose
Defines how the browser presents and operates the collaborative dream of the cloud throne. The dream is staged as an AVG scene over its official artwork, with visible exchange and excitement tracks, paced reveals, a legible story-direction (念頭) keepsake, and exits that never lose the player's words by accident. All of it runs on the unchanged server-authored `dream` panel.

## Requirements

### Requirement: The dream is a full-stage AVG scene over its official artwork

While the committed `dream` panel state is open, the browser SHALL present the dream as one modal dialog covering the stage. The dialog SHALL be named by its visible title 雲上王座之夢 and SHALL contain these regions:
- the server-resolved scene artwork;
- a keepsake card naming the current story direction and the exits;
- a reply bar for free text;
- a message band that presents the narration and the goddess's lines under her name plate.

#### Scenario: Open dream renders the stage regions
- **WHEN** an open dream state with artwork is committed
- **THEN** a modal dialog shows the artwork, the keepsake card with four exit rows, the reply bar and the message band, and contains no `<details>` element

#### Scenario: Artwork fails to load
- **WHEN** the artwork request fails
- **THEN** the image is removed and the stage stays usable without a broken-image glyph, and a republished URL is loaded again

#### Scenario: An empty artwork URL is removed
- **WHEN** the artwork URL is empty
- **THEN** the surface removes the image and stays fully usable without it, never showing a broken-image glyph

#### Scenario: A changed artwork URL is attempted afresh
- **WHEN** the artwork URL changes
- **THEN** the new URL is attempted afresh

#### Scenario: The surface stays flat and standard-styled
- **WHEN** the stage is rendered
- **THEN** it uses no nested disclosure widgets and surfaces no command syntax or JSON, and every button outside the 念頭 sheet's inline controls shares the client's standard button styling

### Requirement: Exchange budget and goddess excitement have visual, non-colour-only forms

The reply bar SHALL show the six-exchange budget as six pips, with spent exchanges hollow, plus a remaining-count label. The goddess's name plate SHALL show a five-segment excitement gauge lit up to the server-supplied track ordinal, plus the server-supplied level label.

Both SHALL be exposed as meters:
- the budget meter's value text SHALL be `尚可交談 {remaining} 次，共 6 次`;
- the gauge meter's value text SHALL be `女神的興奮：{level}`.

#### Scenario: Fresh dream
- **WHEN** a dream with zero completed exchanges and level 平靜 is shown
- **THEN** six live pips with the label `尚餘 6`, five gauge segments with one lit, and the value texts `尚可交談 6 次，共 6 次` and `女神的興奮：平靜` are present

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

The reply bar SHALL accept free text only while the server allows input and the transport is unlocked. Enter SHALL send `dream.say` with the current session id and revision and the message split at 2000 code points into two parts. Shift+Enter SHALL insert a newline, and Enter during an IME composition SHALL NOT send. A successful dispatch SHALL clear the field.

#### Scenario: Bounded send on Enter
- **WHEN** the player types 4000 characters and presses Enter
- **THEN** `dream.say` is dispatched with two 2000-code-point parts and the field clears

#### Scenario: Shift+Enter and IME do not send
- **WHEN** the player presses Shift+Enter, or Enter while composing
- **THEN** nothing is dispatched

#### Scenario: Failed generation is retryable
- **WHEN** a sent message's generation fails
- **THEN** the field holds the sent words, the control reads 再說一次, and no pip is hollow

#### Scenario: Budget exhausted
- **WHEN** all six exchanges are spent
- **THEN** no free-text form is present and the end bar is shown

#### Scenario: Converging captions
- **WHEN** the track is converging with two, then one, exchange remaining
- **THEN** the caption reads 夢將抵達盡頭, then 夢將抵達盡頭 · 最後一次交談

#### Scenario: Transport locked
- **WHEN** the client is disconnected, mutations are locked, the session is inactive, or a dispatch is in flight
- **THEN** the reply field and all four keepsake rows are disabled, and while disconnected the reconnect caption is shown

#### Scenario: The transport lock conditions are enumerated
- **WHEN** deciding whether the transport is locked
- **THEN** it is locked while the client is disconnected, mutations are locked, the session is not active, a dispatch is in flight, or combat playback holds the command panel

#### Scenario: Converging caption needs at most two exchanges left
- **WHEN** deciding whether to show the converging caption
- **THEN** it appears only when at most two exchanges remain and the server reports the track is converging, reads 夢將抵達盡頭, and is extended with 最後一次交談 when one exchange remains

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
- **WHEN** all six exchanges are spent
- **THEN** the reply bar is replaced by an end bar reading 六次交談已盡，女神靜候你的決定。

### Requirement: The keepsake card shows the 念頭 that would be carried out and offers distinct exits

The keepsake card SHALL show:
- the current story-direction summary, or an empty-state invitation;
- a provenance label: 取自你剛才的話 when it is the server's last-said direction, 已記下 when a saved draft matches it, and 已改寫・未記下 when local edits differ;
- the attachment line, either 歸屬：一段新的故事 or 歸屬：延續：{thread label}.

The card SHALL offer four rows in this order:
1. edit the 念頭 (opens the sheet);
2. 帶著這個念頭醒來 (confirm);
3. 記下念頭，繼續作夢 (draft; 記下念頭 once all exchanges are spent);
4. ✕ 醒來 (awaken).

#### Scenario: Decisive action follows the phase
- **WHEN** the dream allows input
- **THEN** the only primary control is 訴說, and after the sixth exchange the only primary control is the confirm row

#### Scenario: Exits stay usable in every failure state
- **WHEN** the dream is pending, failed or at its cap
- **THEN** the confirm, draft and awaken rows are enabled and awaken dispatches `dream.awaken` with the latest revision

#### Scenario: Digit shortcut
- **WHEN** the player presses 1 outside a text field
- **THEN** the 念頭 sheet opens, while Ctrl+1 or a 1 typed into a text field does nothing

#### Scenario: Sixth exchange moves focus
- **WHEN** a live exchange reaches six with a summary present
- **THEN** focus rests on the confirm row and the draft row reads 記下念頭

#### Scenario: Digits 1 to 3 activate rows 1 to 3
- **WHEN** a digit 1–3 is pressed outside text fields and without a Ctrl, Meta or Alt modifier
- **THEN** it activates the row of that number

#### Scenario: Sixth exchange without a summary focuses the edit row
- **WHEN** a live exchange spends the sixth turn and there is no summary
- **THEN** focus moves to the edit row instead of the confirm row

#### Scenario: Exits are disabled only while the transport is locked
- **WHEN** deciding when to disable the confirm, draft and awaken rows
- **THEN** they stay enabled during a pending response, after a failure and after the sixth exchange, and are disabled only while the transport is locked

### Requirement: The 念頭 sheet edits the direction in one flat modal layer

Opening the edit row SHALL show a modal sheet that traps focus and renders the rest of the stage inert. It SHALL contain, without nested disclosure:
- the summary field, with a code-point counter out of 2000 and a revert-to-server control when the field differs;
- a radio group offering 一段新的故事 and each server-offered thread;
- five chip lists: themes, atmosphere, participants, emphasis, exclusions.

#### Scenario: Chips and draft
- **WHEN** the player adds the theme 重逢 twice and saves a draft
- **THEN** one chip exists, `dream.draft` carries `themes: ["重逢"]`, the sheet closes, and the draft toast appears only after the newer state with the saved draft is committed

#### Scenario: Revision follows reconnect
- **WHEN** the summary is edited, a newer revision is committed, and the player confirms
- **THEN** `dream.confirm` carries the newer revision and the edited summary as a new story

#### Scenario: Many threads
- **WHEN** more than eight threads are offered and the player filters by text
- **THEN** only matching threads remain listed

#### Scenario: A vanished saved thread stays selectable
- **WHEN** a saved thread is no longer offered by the server
- **THEN** it remains selectable in the radio group as 先前選定的故事線（已不在清單中）

#### Scenario: The thread filter appears above eight threads
- **WHEN** more than eight threads are offered
- **THEN** a text filter narrows the list

#### Scenario: Chip editing rules
- **WHEN** the player presses Enter in a chip input, or Backspace on an empty chip input
- **THEN** Enter adds a trimmed, de-duplicated chip and Backspace removes the last chip

#### Scenario: The draft button closes the sheet and keeps the dream
- **WHEN** the sheet's draft button is activated
- **THEN** it dispatches `dream.draft`, closes the sheet, and keeps the dream open

#### Scenario: Draft confirmation waits for the committed state
- **WHEN** a draft save is in progress
- **THEN** 念頭已記下，夢仍在繼續。 is shown and announced only once a newer committed state carries a saved draft, and a refused draft shows no confirmation

#### Scenario: Both buttons send the same payload shape
- **WHEN** the sheet's draft or confirm button dispatches (`dream.draft` / `dream.confirm`)
- **THEN** both send `{kind, thread_id, summary}` plus only the non-empty preference lists, at the latest committed revision

#### Scenario: Escape keeps the sheet's edits
- **WHEN** the player presses Escape with the sheet open
- **THEN** the sheet closes and keeps its edits

### Requirement: Direction confirmation is validated locally without discarding words

Confirming with an empty summary SHALL NOT dispatch. It SHALL open (or keep) the 念頭 sheet with the alert 念頭還是空的。寫下一句想帶走的話，或直接醒來。 and focus the summary. The confirm row SHALL be marked unavailable with the reason 尚無念頭 while the summary is empty, but SHALL stay focusable.

#### Scenario: Empty confirm
- **WHEN** the player activates the confirm row with no summary
- **THEN** nothing is dispatched and the sheet shows the empty-direction alert

#### Scenario: Over-length direction
- **WHEN** the server direction is 2001 code points and the player confirms
- **THEN** the field holds all 2001 code points, nothing is dispatched, and an alert names the 2000 limit

#### Scenario: Overflow is marked, never truncated
- **WHEN** a server direction is longer than 2000 code points
- **THEN** it is shown in full, the counter marks the overflow, the text is never truncated silently, and draft and confirm are refused with an alert until the player shortens it

### Requirement: Escape never awakens and awakening protects unsaved local words

Escape SHALL NOT dispatch any dream action. It SHALL do the first of these that applies:
1. close an open awaken check or 念頭 sheet;
2. move focus out of a text field to the message band;
3. otherwise, move focus to the ✕ 醒來 row.

#### Scenario: Escape focuses the awaken row
- **WHEN** the player presses Escape with no layer open and focus outside a text field
- **THEN** focus moves to the ✕ 醒來 row and nothing is dispatched

#### Scenario: Unsent words are protected
- **WHEN** the reply field holds text and the player activates 醒來
- **THEN** the 就此醒來？ alert dialog appears with focus on 回到夢中, and only its 醒來 button dispatches `dream.awaken`

#### Scenario: A clean awaken dispatches at once
- **WHEN** 醒來 is activated with no local unsent reply and no unsaved 念頭 edit
- **THEN** `dream.awaken` is dispatched at once, with no confirmation dialog

#### Scenario: The awaken guard names what would be lost
- **WHEN** 醒來 is activated while local unsent reply or unsaved 念頭 edits exist
- **THEN** an alert dialog titled 就此醒來？ opens naming what would be lost

#### Scenario: The awaken guard dialog behaves predictably
- **WHEN** the 就此醒來？ dialog is open
- **THEN** initial focus rests on 回到夢中, Escape or 回到夢中 returns to the dream without dispatching, and 醒來 dispatches `dream.awaken`

### Requirement: Republished drafts rehydrate without overwriting the player's own edits

On mount, a saved draft's summary, thread and preferences SHALL load as the unedited local values, labelled 已記下. When the server republishes the direction, thread or preferences for the same session (after an exchange or an external draft save), each local field the player has not edited SHALL adopt the server value. A field the player has edited SHALL keep the player's text. Unsent reply text SHALL never be cleared by a republish. Clearing an edited summary SHALL restore following the server.

#### Scenario: External draft change
- **WHEN** a draft with a known thread and preferences is republished while the reply field holds unsent text
- **THEN** the unsent text remains, the card names the thread, the sheet selects it, and confirm sends the server summary, thread and preferences

#### Scenario: Saved preferences load on mount
- **WHEN** the surface mounts with a saved draft carrying `themes: ["重逢"]`
- **THEN** the card reads 已記下, 醒來 dispatches at once, and confirm sends the saved themes

#### Scenario: Edited summary is kept
- **WHEN** the player has edited the summary and an exchange republishes a different direction
- **THEN** the player's summary remains, and after clearing it the next republish is adopted
