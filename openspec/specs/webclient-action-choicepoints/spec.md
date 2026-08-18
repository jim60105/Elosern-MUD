## Purpose

The narrative-stream placement of AI action suggestions (overview decision A-6, webclient design
doc §4): a movable stream-end block that renders the `generating` line and the `ready` card group,
replaces one with the other in place, and disappears on `unavailable`, dismiss, or any
non-exploration presentation state. `degraded` rule cards are a dock-only surface and never enter
the stream. The block is owned by the `window.Elosern.narrativeInput` facade so scroll-keep and
the unread marker stay single-owner, and its cards are the exact dock card component with one
click path.

## Requirements

### Requirement: The choice-point renders generating and ready states at the stream end
The browser SHALL append one muted line "AI 正在構思建議…" at the narrative stream end when the
committed `panels["context_actions"].suggestions.status` becomes `generating`, and SHALL render
nothing new for a `generating` → `generating` commit (the line, if present, stands until `ready`
replaces it). When the committed status becomes `ready`, the SHALL line be replaced **in place**
by the card group: every card of the committed `cards` list rendered through the shared dock card
component (label + optional hint + action code semantics), with no line or card duplication and
no stacking of a generating line above a ready group. The block SHALL be inserted only while the
committed panel state is a valid exploration-mode `context_actions` payload carrying a
`suggestions` section; a snapshot or update that removes the panel, carries `kind` other than
`"exploration"`, or carries a malformed or unknown suggestions status SHALL remove the block
instead of rendering it.

#### Scenario: A situation change produces the generating line then ready cards
- **WHEN** the player moves into a room and the trigger service publishes
  `suggestions.status = "generating"`, and later a `ui_update` commits
  `suggestions.status = "ready"` with 3–5 cards
- **THEN** the muted line is appended at the stream end on the first commit, the second commit
  replaces that exact line in place with the card group, and the narrative shows exactly one
  choice-point block with no duplicate line or card

#### Scenario: A generating commit while generating renders nothing new
- **WHEN** a `generating` status was already committed and a second commit again reports
  `generating`
- **THEN** no new line or element is appended and the existing muted line remains unchanged

#### Scenario: The block disappears when the panel leaves exploration
- **WHEN** a committed snapshot or update changes `context_actions` to `kind = "combat"`, or the
  panel is absent, or `kind` is creation-pending
- **THEN** any choice-point line or card group is removed from the stream and no replacement is
  rendered

### Requirement: The choice-point is a movable stream-end block owned by the narrative facade
The choice-point SHALL be attached to the narrative stream through the
`window.Elosern.narrativeInput` facade and SHALL NOT create a separate append path. The narrative
facade's `StreamEndBlock.appendNode()` path SHALL place every newly committed narrative text node
before a mounted choice-point block, so the block remains the final stream node within the same
single scroll/unread decision. The existing scroll-keep and polite unread-marker behavior SHALL
count each committed narrative text event exactly once, unaffected by a mounted block. The facade
SHALL expose attach, replace-in-place, and remove operations as the single owner of choice-point
geometry; it SHALL NOT expose a separate move-to-end operation, and no other module SHALL mutate
the narrative container directly for the choice-point.

#### Scenario: Text appended after a ready commit stays before the block
- **WHEN** `ready` cards are committed at the stream end and the server then appends a look
  output, a talk reply, or a scene-flavor push
- **THEN** the newer text appears between the stream's older content and the choice-point block,
  the block remains last without a second relocation call, and the player can still click the cards

#### Scenario: The block never splits the stream unexpectedly
- **WHEN** multiple narrative appends and one choice-point insertion happen in any order
- **THEN** the narrative reads as exactly one ordered sequence with the choice-point always last,
  and remove leaves the remaining narrative contiguous with no empty placeholder

### Requirement: Choice-point cards share the dock card component and click path
Every `ready` card in the stream SHALL be the same DOM component the dock section renders (one
card renderer, one sizing, one label/hint presentation), and activating it SHALL dispatch exactly
the same `ui_action` envelope the dock card dispatches for the same card (`action_code` + params
for `known_action`; `explore.talk_freeform` with `speech: label` for `freeform`), with the
existing rejection/stale/busy toast surface and the existing input-line echo behavior
(`webclient-input-narrative` catalog) applying identically to stream cards and dock cards. The
stream group SHALL carry a dismiss control ("✕ 清除建議") that dispatches `options.dismiss`
exactly as the dock section's does.

#### Scenario: A stream card and its dock twin dispatch identically
- **WHEN** the same `ready` card exists in both the dock section and the stream block and the
  player activates first the dock card, then the stream card
- **THEN** both activations produce byte-identical `ui_action` requests (same action id, same
  payload, same request semantics) and identical visual result handling

#### Scenario: Freeform speech is the card label in the stream too
- **WHEN** a `freeform` card is activated from the stream
- **THEN** the stream card dispatches `explore.talk_freeform` with `payload = {npc_id,
  speech: label}` and exactly one `talk <NPC> <speech>` echo line appears, with no raw second
  echo

#### Scenario: The stream dismiss clears both surfaces
- **WHEN** the player activates the "✕ 清除建議" control on the stream block, `options.dismiss`
  is admitted, and the corresponding `unavailable` presentation commit is subsequently accepted
- **THEN** the stream block is removed, the dock section hides its suggestions section, and the
  chosen-card narrative sequence shows no leftover block

#### Scenario: A dismissed-while-blocked request keeps the ready cards until the next commit
- **WHEN** the player activates the dismiss control while a mutation is in flight, the action
  client is locked, or the request is rejected as stale/busy, or the transport drops before the
  publish
- **THEN** no `options.dismiss` request is sent (or it is rejected at the action client), the
  ready block and the dock section remain exactly as the last committed state, and the next
  accepted commit alone decides removal — the committed-state invariant is never violated to
  "help" the UI

### Requirement: Degraded rule cards never enter the stream
The browser SHALL NOT render `degraded` suggestions in the narrative stream under any condition:
a commit whose `suggestions.status` is `degraded` SHALL leave any existing choice-point block
removed or absent and SHALL render the rule cards exclusively through the dock section. The
stream is the AI-only surface (webclient design doc §4); the dock remains the reference surface
for rule cards.

#### Scenario: Offline LLM degradation stays out of the narrative
- **WHEN** the AI service is offline and the trigger service publishes
  `suggestions.status = "degraded"` with rule cards
- **THEN** the dock section shows the rule cards with the muted "AI 建議目前不可用" note, and the
  narrative stream contains no generating line, no card group, and no choice-point block for the
  degraded state

#### Scenario: Degraded after ready removes the stream block
- **WHEN** a `ready` card group is displayed and a later commit reports `degraded` (rule cards)
- **THEN** the stream block is removed, the cards move out of the narrative, and the dock section
  is the only place the rule cards appear

### Requirement: The choice-point recovers deterministically across sessions
The block state SHALL derive only from committed `context_actions` presentation state, never from
transport metadata or generation-side hints: `beginTransport` (connection reset) SHALL remove any
mounted block synchronously on its own store notification — the block never survives into the
retired epoch even before the first new snapshot arrives — and a `ready` block from a retired
epoch SHALL never become clickable again after a reconnect. The choice-point layer SHALL keep no
server-side or persistent state and SHALL be safe to initialize once per page.

#### Scenario: Reconnect removes the block on the transport reset itself
- **WHEN** the browser begins a new transport generation (`beginTransport`) while a `ready` card
  group is mounted
- **THEN** the block is removed during that same store notification — before any new snapshot is
  received — no card from the retired epoch remains clickable, and a later `generating`/`ready`
  commit starts a fresh block

#### Scenario: Malformed suggestions state degrades to absence
- **WHEN** a commit carries a `suggestions` section with an unknown status or an
  out-of-contract card list
- **THEN** the stream renders no choice-point block (the client mirror's rejection path already
  keeps such a payload from committing) and the narrative continues to accept subsequent
  commits normally