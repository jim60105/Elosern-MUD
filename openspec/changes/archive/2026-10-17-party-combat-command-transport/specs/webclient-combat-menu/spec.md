# Spec Delta

## MODIFIED Requirements

### Requirement: Reconnect rebuilds combat without replaying intent
WebSocket loss SHALL preserve the last rendered combat view under the foundation offline
overlay and lock every combat mutation. After reconnect, the first valid new-epoch
snapshot SHALL rebuild the current session ID, mode, round, participants, status,
actor summaries, requested actor choices, durable draft progress, targets and root menu from canonical persistence even when its revision is
lower than the retired epoch.

#### Scenario: Active combat reconnect resumes the same round boundary
- **WHEN** transport disconnects after a valid nonterminal round and reconnects without another game action
- **THEN** the new snapshot shows the same persisted session and round, restores confirmed progress and selects the first required actor still needing a command, and no additional round or world time is consumed

#### Scenario: Disconnect after submit never retries
- **WHEN** transport closes after sending a command confirmation but before its result is observed
- **THEN** reconnect synchronizes canonical combat state, displays the uncertain-result notice, and sends no automatic replacement confirmation

#### Scenario: Unreconstructable participant offers safe recovery
- **WHEN** a strictly parsed active record references a participant that can no longer be reconstructed
- **THEN** combat presentation exposes a bounded recovery state with no personal action, retains confirmed party surrender and ordinary text access, and performs no mutation while rendering

#### Scenario: Epoch hygiene on reconnect
- **WHEN** the browser reconnects into a new epoch
- **THEN** it discards old-epoch packets, restores no unsubmitted target selection as
  authority, and resubmits no uncertain prior mutation

### Requirement: A combat round plays beat by beat
When a committed publication carries an available `combat_beats` panel whose round the
client has not presented in the current epoch, and that publication completes the
player's own final `combat.command` or confirmed retreat `combat.exit_confirm` action that actually committed a round, the client SHALL
present that round as one step per beat, in the beats' order, attached to that action's
response. A round seen in any other way, including after a reconnect, SHALL NOT be
presented as steps, and no round SHALL be presented twice.

#### Scenario: A round plays one beat per page
- **WHEN** the effective level is `full` and an accepted basic attack settles a non-terminal round with a
  `roll` beat and a `damage` beat
- **THEN** the message window types the roll beat's text as a page, then after the beat pause types the
  damage beat's text as the next page, and then shows the round's closing line as the next page

#### Scenario: Displayed hit points follow the beats and snap at the end
- **WHEN** a foe at 30 hit points takes damage beats with `hp_after` 18 and then 0 in a playing round
- **THEN** the foe's plate shows 30, then 18 after the first damage beat, then 0 after the
  second, and once the round ends it shows the committed value

#### Scenario: The command panel unlocks after playback and the revision
- **WHEN** the declared revision of a combat action is accepted while its round is still playing
- **THEN** the dock accepts no activation and sends no `ui_action` until the round has ended, and
  accepts the next activation once it has

#### Scenario: A click ends the round
- **WHEN** a round is playing its first of three beats and the player clicks the message window
- **THEN** the lock from playback clears at once, every displayed hit-point value equals the committed
  value, and the window shows the page after the beat pages

#### Scenario: A typed command ends the round
- **WHEN** a round is playing and the player sends a typed command
- **THEN** the round ends before the command's input line is appended, and the command's response is
  presented from its first page

#### Scenario: Reduced keeps the order and the pauses
- **WHEN** the effective level is `reduced` and a round with three beats plays
- **THEN** each beat page appears in full at once, each next beat follows after the 400ms beat pause,
  and the order equals the beats' order

#### Scenario: Off presents the beats as text pages
- **WHEN** the effective level is `off` and a round with two beats settles
- **THEN** the command panel unlocks as soon as the declared revision is accepted, and the reader turns
  one page per beat, each holding that beat's text, followed by the round's closing line

#### Scenario: The round that ends the fight plays its beats
- **WHEN** an accepted attack defeats the last foe and the full snapshot commits mode `exploration`
  with an available `combat_beats` panel
- **THEN** the mode, the exploration surfaces, and the store's view carry `exploration` at once, the
  round's beats are presented in order ending with the defeat beat, and the outcome lines follow them

#### Scenario: Without beats the round pages as text
- **WHEN** an accepted combat action's publication carries the unavailable `combat_beats` form
- **THEN** the round's narrative is paged as an ordinary response, the vitals move once to the committed
  values, and the dock unlocks when the declared revision is accepted

#### Scenario: A reconnect replays no round
- **WHEN** the client reconnects after a round has played, or reloads while a round is playing
- **THEN** no beat is presented again, the window shows the last page of the last response fully shown,
  and every displayed value is the committed value

#### Scenario: An unknown participant is text only
- **WHEN** a beat's target names no participant known to the client
- **THEN** its text is presented as its page and no displayed hit-point value changes for it

#### Scenario: The ending round presents like any round
- **WHEN** the completing publication has already committed mode `exploration` (the
  round that ends the fight)
- **THEN** that round SHALL be presented the same way, and its committed exploration
  state is not held back

#### Scenario: A beat is exactly its plain text as one page
- **WHEN** a playing round's beats are paged into the message window
- **THEN** each beat is one page holding exactly the beat's text as plain text, split
  over more pages only when it does not fit one

#### Scenario: Beat pages replace the round's own event lines
- **WHEN** a playing response is paged
- **THEN** the response's first lines, one per event log the beats name, are not paged
  again, every later line of the response (the round's closing line, a fight's outcome
  and aftermath) follows the beat pages as ordinary pages, and the log keeps every line
  unchanged

#### Scenario: Full and reduced motion play the round by itself
- **WHEN** the effective motion level is `full` or `reduced`
- **THEN** the round plays by itself: each beat page is revealed at the reader's text
  speed (instant below `full`); once fully shown, the beat's stage gesture plays as
  `webclient-contextual-hud` "Combat beats are choreographed on the stage at the motion
  level" defines, and the next beat follows after that gesture and the beat pause of the
  client's motion tokens (400ms at `full` and at `reduced`)

#### Scenario: Off never plays the round by itself
- **WHEN** the effective motion level is `off`
- **THEN** the round does not play by itself: its beat pages and the following pages are
  ordinary pages the reader turns, and presentation of the round ends at once

#### Scenario: Displayed hit points track damage beats in both surfaces
- **WHEN** a playing round damages a participant whose previous committed hit points are
  known
- **THEN** that participant displays its previous committed value until its first damage
  beat, and after each of its damage beats that beat's `hp_after`, in the vitals and on
  its figure plate

#### Scenario: Playback end snaps every value and nothing else follows the beats
- **WHEN** a round's presentation ends
- **THEN** every displayed value is the committed `status` and participant value, and no
  other resource, marker, or visibility rule follows the beats

#### Scenario: Playback lock stacks on the revision lock
- **WHEN** a round plays by itself while the declared-revision lock is also pending
- **THEN** the command panel stays locked under both, and unlocks when both have cleared

#### Scenario: Pointer or keyboard skip ends the round at once
- **WHEN** the pointer activates the message window, or the player presses Enter or
  Space on its page surface, during playback
- **THEN** the round ends at once: every displayed value becomes the committed value,
  the lock from playback clears, and the window shows the response's first page after
  the beat pages, or the last beat page fully shown when none follows

#### Scenario: Transport loss ends the round without presenting the rest
- **WHEN** a new transport generation arrives or the client detaches during playback
- **THEN** the round ends without presenting the rest

#### Scenario: The unavailable form keeps only the revision lock
- **WHEN** the completing publication carries the unavailable `combat_beats` form
- **THEN** the round is paged as its ordinary narrative response, the vitals move once
  to the committed values, and the lock is the declared-revision lock alone

#### Scenario: The presentation never touches prose, timing, or requests
- **WHEN** any part of the beat presentation runs
- **THEN** it parses no narrative prose, delays no committed value or mode, and changes
  no request

## REMOVED Requirements

### Requirement: Production combat actions are narrow and server-authoritative
**Reason**: The approved party-combat design replaces this conflicting behavior.
**Migration**: Use the exact party-command and party-exit adapters below; retire combat.cast/flee/forfeit registrations and active-combat inventory.use without compatibility parsing. No compatibility route or data migration.

## ADDED Requirements

### Requirement: Party command and exit adapters accept only guarded exact payloads
Interactive actions SHALL be combat.actor_choices, combat.command, combat.exit_prompt and combat.exit_confirm. Command SHALL include session_id, round_revision, draft_version, actor_id and the closed skill/item/tactic command. Exit requests SHALL include session_id, round_revision and operation; confirmation SHALL also require its token. Unknown or irrelevant fields SHALL reject.

#### Scenario: Actor authorization
- **WHEN** a syntactically valid actor ID is not commandable by the authenticated commander
- **THEN** the shared rules boundary rejects without state change; menu contents never authorize it

#### Scenario: Reserved flee and old routes
- **WHEN** a client submits personal flee, a retired combat action or actorless inventory.use during combat
- **THEN** the request cannot mutate or bypass the party draft/confirmation

#### Scenario: Canonical pending result
- **WHEN** a confirmation saves a nonfinal member command
- **THEN** canonical progress publishes before its safe result, with no combat beats or implied round; final committed round and terminal results retain canonical refresh

### Requirement: Exit prompt result data is exact and ordinary results use canonical panels
Only success code party_exit_prompt SHALL carry exact operation,confirmation_token,scope,consequence data, with scope party and bounded token/text. Other command/query results SHALL carry no data; progress/reselection reasons SHALL come from canonical v7 panels. Non-success results SHALL retain the existing no-data rule.

#### Scenario: Prompt safety
- **WHEN** a retreat or surrender prompt succeeds
- **THEN** its token and consequence are returned in the bounded success data slot, with session/round bound to the initiating request and token rather than forbidden result state keys

#### Scenario: Draft result ordering
- **WHEN** a command is saved, needs reselection or commits a round
- **THEN** canonical panels publish first and codes draft_saved, needs_selection or round_committed distinguish outcomes; only a committed round carries beats


