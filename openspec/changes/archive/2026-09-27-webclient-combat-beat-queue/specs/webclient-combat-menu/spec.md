## MODIFIED Requirements

### Requirement: Combat results update canonical panels and preserve narrative logs
After an admitted combat action settles, the server SHALL emit every returned EventLog and terminal
message through Evennia's ordinary escaped text output path. The dispatcher SHALL then publish
canonical `status`, `context_actions`, and `art` replacements at one newer revision before sending
the matching safe `ui_action_result`, so a combat result that changes the participant roster, combat
mode, or session state replaces the portrait catalog and scene in the same `ui_update`. When the
action settled an ordinary round, the same publication SHALL also carry the `combat_beats` panel
owned by the `webclient-combat-beats` capability, at the same revision as `status`. The panel is
the only structured account of the round's exchange, and the text output stays the authoritative
narrative. The browser SHALL keep submission locked until that declared presentation revision is
accepted and, when the client plays that publication's round beat by beat, until the round's playback
has ended or the player has ended it, as "A combat round plays beat by beat" defines. It SHALL NOT parse narrative prose to update resources, participants, round, art, beats,
or menu state.

#### Scenario: One combat round updates text, panels, and art
- **WHEN** an accepted cast completes a nonterminal round
- **THEN** every committed EventLog appears in narrative, status, combat choices, and the art catalog
  reflect committed state at one newer revision, and the dock unlocks only after that revision is
  accepted and the round's beat playback has ended

#### Scenario: A defeated or fled participant leaves the art catalog in the same revision
- **WHEN** an accepted combat action removes a participant from the session (defeat, flee, or
  terminal settlement)
- **THEN** the `art` panel at the same newer revision no longer contains that participant's catalog
  entry, and the browser never keeps a portrait for a no-longer-present entity

#### Scenario: Rejected preflight emits no fabricated combat prose
- **WHEN** current deterministic validation rejects before initiative
- **THEN** no combat EventLog is fabricated, the result contains a stable safe reason, and refreshed panel state permits another legal choice

#### Scenario: Duplicate request does not repeat a round or prose
- **WHEN** one live request ID is delivered twice
- **THEN** the adapter and combat round execute once, EventLog text is emitted once, and the duplicate receives the cached result

#### Scenario: The round's beats ride the status revision
- **WHEN** an accepted cast completes a nonterminal round
- **THEN** the same `ui_update` that carries `status` also carries `combat_beats` for that round, and the `ui_action_result` names that revision and carries no beat, EventLog, or round-record field

## ADDED Requirements

### Requirement: A combat round plays beat by beat
When a committed publication carries an available `combat_beats` panel whose round the client has not
presented in the current epoch, and that publication completes the player's own `combat.cast`,
`combat.flee`, or `inventory.use` action, the client SHALL present that round as one step per beat, in
the beats' order, attached to that action's response. A round seen in any other way, including after a
reconnect, SHALL NOT be presented as steps, and no round SHALL be presented twice. A round whose
completing publication has already committed mode `exploration` (the round that ends the fight) SHALL be
presented the same way; its committed exploration state is not held back.

**Text.** Each beat SHALL be one page of the message window holding exactly the beat's text as plain
text, split over more pages only when it does not fit one. The beat pages SHALL replace the round's own
event lines in that response's pages: the response's first lines, one per event log the beats name, are
not paged again, and every later line of the response (the round's closing line, a fight's outcome and
aftermath) SHALL follow the beat pages as ordinary pages. The log keeps every line unchanged. While the
effective motion level is `full` or `reduced`, the round SHALL play by itself: each beat page is revealed
at the reader's text speed (instant below `full`), and once it is fully shown the next beat follows after
the beat pause of the client's motion tokens (400ms at `full` and at `reduced`). At `off`, the round SHALL
NOT play by itself: its beat pages and the following pages are ordinary pages the reader turns, and
presentation of the round ends at once.

**Displayed hit points.** While the round plays, each participant that a beat damages and whose
previous committed hit points are known SHALL display its previous committed value until its first
damage beat, and after each of its damage beats that beat's `hp_after`, in the vitals and in the
participant frame. When the round's presentation ends, every displayed value SHALL be the committed
`status` and participant value. No other resource, marker, or visibility rule SHALL follow the beats.
A beat that names no known participant SHALL be presented as text only and SHALL change no displayed
value.

**Lock, skip, and flush.** While the round plays by itself, the command panel SHALL stay locked, in
addition to the existing lock that waits for the declared revision; it SHALL unlock when both have
cleared. A pointer activation on the message window, or Enter or Space on its page surface, SHALL end
the round at once: every displayed value becomes the committed value, the lock from playback clears,
and the window shows the response's first page after the beat pages, or the last beat page fully shown
when none follows. A typed command SHALL be accepted during playback and SHALL end the round the same way
before its own line is appended. A new transport generation or a detach SHALL end the round without
presenting the rest.

**Fallback.** When the completing publication carries the unavailable `combat_beats` form, the round
SHALL be paged as its ordinary narrative response, the vitals SHALL move once to the committed values,
and the lock SHALL be the declared-revision lock alone.

No part of this presentation SHALL parse narrative prose, delay a committed value or mode, or change
any request.

#### Scenario: A round plays one beat per page
- **WHEN** the effective level is `full` and an accepted basic attack settles a non-terminal round with a
  `roll` beat and a `damage` beat
- **THEN** the message window types the roll beat's text as a page, then after the beat pause types the
  damage beat's text as the next page, and then shows the round's closing line as the next page

#### Scenario: Displayed hit points follow the beats and snap at the end
- **WHEN** a foe at 30 hit points takes damage beats with `hp_after` 18 and then 0 in a playing round
- **THEN** the participant frame shows 30, then 18 after the first damage beat, then 0 after the
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
