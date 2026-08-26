## MODIFIED Requirements

### Requirement: Every deliberate mutation echo appears exactly once at dispatch

The browser SHALL append the resolved display line to the narrative exactly once per deliberate
mutation in the single submit path: the echo fires at the moment the `ui_action` request is dispatched
(a request id is returned), never on retry, resync, reconnect-replay, or a second client-local toggle,
and never when submission is blocked (offline, mutations locked, not initialized, or a duplicate/
in-flight request). A button click and the identical keyboard activation SHALL each echo exactly once.
A borrowed free-form dialogue SHALL be owned by the action path: the command field's borrowed branch
SHALL not append its own line, so a single free-form send yields exactly one line (`talk <NPC> <speech>`),
and when submission is blocked the typed speech SHALL remain in the field and the field SHALL keep
focus (the borrowed interaction is not complete and nothing is lost). Because the command field is
permanently present, the completion of a borrowed dialogue SHALL be signalled by returning focus to the
action dock rather than by closing a surface. A quick-word chip SHALL NOT echo: it prepares text in the
field and dispatches nothing, so no line exists to append until the player sends. The echo line SHALL be
inserted as literal text via the same narrative append path (scroll-keep + polite unread marker) used by
server output, SHALL NOT enter the markup pipeline, SHALL NOT be sent or reused as a submitted command,
and SHALL have no effect on the validated action payload (`U9` intact: dispatch stays allowlist + exact).
A later rejection of the action SHALL NOT remove the line, because the line records what the player
acted.

#### Scenario: A staged submit echoes at dispatch
- **WHEN** a player activates a button that dispatches a valid `combat.cast`
- **THEN** exactly one input line appears in the narrative at that moment, the `ui_action` envelope is
  byte-identical with and without the echo, and a rejected outcome leaves the line in place

#### Scenario: Locked state never echoes
- **WHEN** the browser is offline, awaiting its first snapshot, or another mutation is in flight
- **THEN** a menu activation does not dispatch, no input line appears, and a borrowed free-form send
  keeps its typed speech in the field with focus retained in the field

#### Scenario: Free-form dialogue echoes exactly one line
- **WHEN** a player sends free-form speech to a present NPC and the `explore.talk_freeform` request
  dispatches
- **THEN** exactly one `talk <NPC> <speech>` line is appended at dispatch, the field clears and returns
  focus to the action dock, and no second raw-text echo appears

#### Scenario: Preparing a command from a chip echoes nothing
- **WHEN** the player activates a quick-word chip and the verb is written into the command field
- **THEN** no display line is appended and no request is dispatched, and exactly one line is appended
  only once the player sends the prepared command

#### Scenario: Reconnect replay does not double-echo
- **WHEN** a transport drops after a submit and reconnects
- **THEN** the store rebuilds panels, the uncertain-result notice shows, and no second echo is appended
