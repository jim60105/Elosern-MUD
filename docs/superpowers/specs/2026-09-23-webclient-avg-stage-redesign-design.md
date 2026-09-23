# WebClient AVG Stage Redesign — Design

Date: 2026-09-23
Status: approved by the requester in the brainstorming session
Related: `openspec/specs/webclient-contextual-hud/spec.md` (the H1–H5 shell this
design replaces), `openspec/specs/webclient-dialogue-session/spec.md`,
`openspec/specs/webclient-exploration-menu/spec.md`,
`openspec/specs/webclient-local-map/spec.md`,
`openspec/specs/webclient-combat-menu/spec.md`,
`docs/design/elosern-redesign/REDESIGN.md` (the previous visual reference).
Pending changes that must land first: `make-shop-drawer-frameless`,
`make-quest-drawer-frameless`, `retire-service-keyboard-frames`.

## 1. Problem

The exploration screen grew one feature at a time. Every feature received a
permanent region, so every context shows every region. Observed defects
(requester's review of the live client at 1920×1080):

- **Irrelevant information is always on screen.** HP / MP / stamina bars sit in
  the left column while walking through a city, where they carry no meaning.
  The head card (name, rank, guild, wallet) duplicates the top bar's character
  switcher. The empty party strip (`0 / 4`, four `+ 邀請` slots) and the
  `美術展示` panel (an NPC face stuck in the bottom-left corner) take space
  without purpose.
- **The minimap wastes its column.** It claims the whole right column, but the
  lattice uses roughly the centre quarter of its own box behind a thick frame.
  Its legend grows with every visited place and eventually pushes the map out
  of view entirely. The bottom-right of the screen is empty.
- **Reading is hard.** The narrative caption is a small box in the centre; the
  backdrop is almost entirely covered; the full log opens scrolled to the top
  although the player wants the last one or two replies.
- **The action dock changes height** with its active frame and pushes the
  narrative caption up and down while the player reads.
- **The flow is fragmented.** After moving, the player must switch to the
  `互動` tab to learn who is in the room. Pressing `交談` does not open a
  conversation; it asks for a topic first, and the dialogue view opens only
  after that topic has been sent.
- **There is no stage for characters.** The player's own portrait (generated
  and customised through the SD-WebUI gallery) is shown, but NPCs have no
  standing-portrait slot during dialogue.
- **The full map does not fit** one screen at its default zoom.
- **Nothing is animated.** Mode switches, scene changes, and incoming text are
  instant. Combat has no sense of exchange: pressing a skill jumps straight to
  the settled round.

Root cause: the layout is organised by feature, not by context. JRPG and AVG
titles do the opposite — the screen shows only what the current context
needs, and reference information lives behind a menu.

## 2. Decision summary (requester-approved)

1. **AVG + RPG hybrid, image-first.** A full-bleed stage fills the top of the
   screen; a fixed bottom band holds the message window (2/3 width) and the
   command panel (1/3 width, bottom-right). The previous "narrative column +
   side minimap" idea was rejected because it left too little width for art.
2. **Desktop 16:9 only.** 1920×1080 is the reference; 2560×1440 scales
   proportionally. No narrow, portrait, or mobile layout.
3. **The player's portrait stands on stage at all times** (exploration,
   dialogue, combat). The character is player-authored and the stage is where
   it is shown. An appearance change crossfades.
4. **Vitals are hidden at full health** and auto-appear when any vital is below
   its maximum or any condition is active. In combat they are always shown.
5. **Dialogue shows both portraits:** the player on the left, the NPC on the
   right. The command panel collapses during dialogue.
6. **`交談` enters the dialogue screen immediately**, opened by the NPC's
   authored greeting, before any topic is chosen.
7. **The command line is hidden by default** and expands on `/` or an icon.
8. **The message window pages AVG-style**: click / Enter / Space advances;
   text types out. Pages are cut per action response and never mid-sentence.
   The player may act while pages remain; a new action flushes the unread
   pages to the log.
9. **A motion layer** adds scene and mode transitions, typewriter text, and a
   reduced/off setting that honours `prefers-reduced-motion`.
10. **Combat is choreographed beat by beat** from structured, server-authored
    combat beats. The requester accepts the server protocol change.
11. **Quick fixes:** the minimap loses its legend and thick frame; the full map
    opens fitted to the viewport; the full log opens scrolled to the bottom.
12. **No standalone prototype.** The real client differs too much from any
    throwaway page; work goes straight into OpenSpec changes.

## 3. Goals and non-goals

Goals:

- Each game mode shows exactly the surfaces its context needs (§4).
- At least 65% of the viewport height is unobstructed stage art in every mode.
- Text is read one page at a time at a comfortable measure (≤ 42 CJK
  characters per line).
- One action reaches the people in a room; one action opens a conversation.
- No surface changes size in response to content; the bottom band has a fixed
  height.
- Every visual transition has a reduced-motion equivalent that preserves all
  information.

Non-goals:

- Mobile, tablet, portrait, or sub-1600px layouts.
- A save/load/auto/skip AVG system menu (the game is a persistent MUD).
- Voice, sound, or music.
- Changing how drawers present their content (bag, quests, shop, status,
  party, codex, gallery). Only where their openers live changes (§5.4).
- A redesigned combat menu hierarchy. The existing combat choice tree moves
  into the command panel unchanged.
- Parsing narrative prose to derive any state (still forbidden; §9 adds
  structured data instead).

## 4. Principles and per-mode visibility

Principle: **show when meaningful, hide completely otherwise** (hidden surfaces
use `display:none` and leave the accessibility tree, as today). Reference data
is one click away in a drawer, never permanently on screen.

| Surface | Exploration | Dialogue | Combat | Creation |
|---|---|---|---|---|
| Slim top bar (nav, switcher, connection) | ✓ | ✓ | ✓ | ✓ |
| Place card (location + game time) | ✓ | ✓ | ✓ | — |
| Vitals | only when not full / any condition | same as exploration | always | — |
| Minimap (top-right) | ✓ | ✓ | — | — |
| Objective tracker (one line) | ✓ | — | — | — |
| Player standing portrait (left) | ✓ | ✓ (dimmed when not speaking) | ✓ | — |
| Opposite portrait (right) | — | dialogue host | foes (existing participant catalog) | — |
| Party mini-portraits | only when party size > 0 | — | ✓ (in participant frame) | — |
| Message window | 2/3 width | full width, with name plate | 2/3 width | — |
| Command panel | scene overview | collapsed | combat choice tree | — |
| Dialogue choices | — | centred over the stage | — | — |
| Command line | collapsed; expands on `/` or ⌨ | same | same | — |

Removed outright: the head card (`CharacterHead`), the art showcase panel
(`ArtPanel` in the left column), the quick-word chips (`QuickWordChips`)
together with their quickbar letter bindings (`l g s t w`, `c` in combat —
every one duplicates a command-panel entry), and the top-bar `探索` tab (it
names the screen the player is already on). Typed commands remain available
through the command line.

## 5. Layout

### 5.1 Geometry (1920×1080 reference)

```
┌ top bar 48px ─ ELOSERN │ 角色 任務 背包 地圖 設定 │ switcher · ● ──────────┐
│ ┌ place card ─────┐                                   ┌ minimap 208px ┐ │
│ │ 冒險者公會大廳    │                                   │               │ │
│ │ 春季 1 日 11:25  │                                   └───────────────┘ │
│ └─────────────────┘                                   objective (1 line)│
│ [vitals: only when not full]                                            │
│    ┌─────────┐                                         ┌─────────┐      │
│    │ player  │            stage: backdrop full-bleed    │ NPC /   │      │
│    │ portrait│            (≈ 732px tall)               │ foes    │      │
│    │         │                                         │         │      │
├────┴─────────┴──────────────────────┬──────────────────┴─────────┴──────┤
│ message window  1280 × 300          │ command panel  640 × 300          │
│ [name plate]                        │                                   │
│ page text, typewriter            ▼  │                                   │
│                     [日誌] [⌨]      │                                   │
└─────────────────────────────────────┴───────────────────────────────────┘
```

- The stage anchor `hud-left` and `hud-right` islands, the centred `feed`
  caption, and the floating `dock` panel are replaced by five anchors:
  `place` (top-left), `vitals` (under `place`), `map` (top-right, with the
  objective line under it), `band-message`, and `band-command`. Two portrait
  anchors, `actor-left` and `actor-right`, sit on the stage above the
  backdrop and below the band.
- The band height is `--band-h: 300px` at the reference size and scales with
  the viewport height (`clamp(260px, 27.8vh, 400px)`). It never depends on
  content.
- The message window is `66.667%` of the band width; the command panel takes
  the rest. Page text is 28px at the default `fontScale`, which keeps the
  measure at ≤ 42 CJK characters per line inside the window's padding. In dialogue mode the command panel collapses to zero width and
  the message window takes the full width (§8).
- Portraits are bottom-aligned to the band's top edge, height `min(62vh,
  680px)`, horizontally inset 6% from their side. They never cover the band.
- The command line, when expanded, is a single 44px row docked to the top edge
  of the message window. It overlays the stage, not the text.

### 5.2 Components

| Component | Fate |
|---|---|
| `HudFrame` | Rewritten: new anchors (§5.1), the band, the two portrait anchors. Mode gating by `data-elosern-mode` is kept. |
| `AppShell` | Slots rewired to the new anchors; the always-visible command line becomes collapsible. |
| `TopBar` / `DesktopNavigation` | Height 48px; the `探索` entry removed; location and time move to the place card. |
| `CharacterHead`, `ArtPanel` (left-column showcase), `QuickWordChips` | Deleted, with their tests and spec requirements. |
| `VitalsTrack` | Kept; wrapped by a new `VitalsBadge` visibility rule (§5.3). |
| `PartyStrip` | Renders nothing when the party is empty; otherwise compact avatars under the vitals slot. |
| `ReferenceArtwork` (`.stage-portrait`) | Becomes `StageActor`, used for both portrait anchors. Source for the player: the roster's current character portrait (unchanged). Source for the opposite side: the `art` panel's `portrait_catalog` entry for the dialogue host or foes (unchanged data). |
| `LocalMap` | Minimap mode: thin 1px frame, no legend, fit-to-content (§10). |
| `NarrativeFeed` | Replaced by `MessageWindow` (§6). The full-log surface stays, fed by the same narrative log. |
| `ActionDock` + `DockMenu` | Hosted in `band-command` at fixed size; exploration root replaced by the scene overview (§7). |
| `CommandLine` | Collapsible (§5.5). |

### 5.3 Vitals visibility

`vitalsVisible = mode === "combat" || lowHp || anyVitalBelowMax || conditions.length > 0`,
derived client-side from the committed `status` panel (the same panel
`VitalsTrack` already reads). The low-HP vignette rule is unchanged. The badge
fades in and out through the motion layer (§9).

### 5.4 Top bar and reference drawers

The top bar keeps 角色 / 任務 / 背包 / 地圖 / 設定 and the character switcher.
Drawers and overlays open exactly as today. The location label and time move
out of the top bar into the place card, so the switcher is no longer
truncated.

### 5.5 Command line

Collapsed by default. `/` (outside an editable control) or the ⌨ button at the
message window's bottom-right expands it and focuses the field. Escape or a
successful send collapses it and returns focus to the command panel. The
freeform-dialogue row (§8) expands it the same way. History and Tab completion
are unchanged.

## 6. Message window and the message sequencer

### 6.1 Responses

The narrative log stays the single store of text (`ctx.narrative`, lines of
kind `in` / `out` / `sys` / `err`). The sequencer is a pure view over it:

- A **response** starts at each `in` line (the typed-command echo or the
  dispatched-action echo, both already appended today) and collects every
  following `out` / `sys` / `err` line until the next `in` line.
- Lines that arrive with no preceding `in` (connection notices, a late
  asynchronous freeform reply) append to the current response. Because the
  game is single-player, this only happens right after the player's own
  action.
- The `in` line itself is not paged; it appears only in the full log.

### 6.2 Paging

Each response is cut into pages that exactly fit the message window:

1. **Blocks.** Each line is a block. An `err` or `sys` block always starts a
   new page.
2. **Measure.** A hidden measuring element with the window's exact width,
   font, and `fontScale` lays out blocks in order. A page holds as many whole
   blocks as fit `floor(textAreaHeight / lineHeight)` lines (6 lines at the
   reference size and default scale).
3. **Split.** A block taller than the remaining room is split at the last
   sentence end that fits (`。！？…」』`, followed by any closing quote), then
   at a clause mark (`，、；：`), and only then at a character boundary.
4. **Markup.** Paging runs on the `NarrativeMarkup` token stream, never on
   rendered HTML. A split inside a styled span yields two spans with the same
   class. The allowlist pipeline is unchanged and runs exactly once per line.
5. **Re-measure.** A resize or a `fontScale` change re-pages the current
   response and keeps the reader on the page containing the first character
   they had not yet seen.

Paging is a presentation-only function of `(response lines, box metrics)`.
It never mutates the log and never reaches the server.

### 6.3 Reading controls

- Click on the message window, Enter, or Space (when focus is on the message
  window or the stage): if the page is still typing, show it in full;
  otherwise advance to the next page.
- The end-of-page marker is a blinking `▼`; the last page of a response shows
  `■`.
- Scrolling up over the message window, or the `日誌` button, opens the full
  log. The full log opens scrolled to the bottom.
- **Acting while reading:** any action (command panel, map node, command line,
  dialogue choice) is accepted immediately. When its `in` line arrives, the
  remaining pages of the previous response are marked read and the new
  response starts on page 1. Nothing is lost; everything remains in the log.
- The polite live region announces each page's full text once, when the page
  is shown, not per typed character.

### 6.4 Settings

The settings overlay gains three client-local preferences, stored through the
existing versioned layout store:

- `textSpeed`: slow / normal / fast / instant (default normal, ≈ 45
  characters per second).
- `autoAdvance`: off / on (default off). When on, a finished page advances
  after `1.2s + 60ms × characters`.
- The existing `reducedMotion` preference forces `instant` typing (§9.1).

## 7. Command panel: scene overview

In exploration mode the command panel's root is a single scrollable overview
built from the committed `exploration` panel (no new server data):

```
出口   [外]  [櫃檯]  [酒館（鎖）]
人物   [葛里安·衛登]  [布蘭]
物件   [任務板]
───────────────────────────────
查看房間 · 等待／休息 · 建議 (5)
```

- **出口** lists `move` rows; disabled rows stay visible with their reason.
  Activating one dispatches `explore.move` as today.
- **人物** lists `interact` targets. Activating one opens a verb popover inside
  the panel listing that target's `affordances` in payload order (交談, 邀請,
  交付, 交易, 戰鬥, …) plus 查看. Navigation affordances open their drawer as
  they do after the pending frameless changes.
- **物件** lists `look.objects`; activating one looks at it.
- The footer row holds 查看房間, 等待／休息, and 建議.
- After any movement settles, the panel returns to the overview.
- Keyboard: arrow keys move across chips, Enter activates, Escape closes the
  popover, digits 1–9 address the first nine chips in reading order. The
  keyboard router's frame model is kept; the overview is its new root frame
  and the popover is one child frame.
- The panel has a fixed size; the overview scrolls inside it.

The tab bar (`移動 / 查看 / 互動 / 等待 / 建議`) is removed; its content is
now all on the root.

## 8. Dialogue stage

### 8.1 Opening a conversation

New action `explore.talk_open` with payload exactly `{npc_id}`:

- The adapter re-resolves the NPC from the actor's current location exactly
  like `explore.talk_scripted` does, and re-verifies presence and that the
  NPC is a dialogue host (a scripted dialogue component or an `LLMNPC`).
- The session line is `world.rules.dialogue.greeting_for(npc)`. When it
  returns `None`, the line is a fixed server-authored fallback from
  `world/rules/player_messages.py` (`「{name}看向你，等你開口。」`).
- It records the session through the deterministic dialogue-session seam (a
  new writer, added to the seam's writer list) and publishes at one newer
  revision, so the mode becomes `dialogue` together with the panel.
- It calls no LLM, advances no clock, and changes no affinity or memory.
- Rejections reuse the stable codes of `explore.talk_scripted`.

`explore.talk_open` joins the shared `ACTION_CODE_ALLOWLIST`. In the
exploration panel, every dialogue host's target descriptor carries exactly one
`交談` affordance, `explore.talk_open`; the target-level `talk_scripted`
keyword rows and the `talk_freeform` affordance no longer appear in the
exploration root, because both now live inside the dialogue stage.
`explore.talk_scripted` (the choice rows) and `explore.talk_freeform` (the
freeform row) keep their adapters and contracts unchanged.

### 8.2 Layout

```
│   ┌─────────┐                                        ┌─────────┐     │
│   │ player  │         ① 關於註冊                       │  NPC    │     │
│   │ (dimmed)│         ② 任務板的事                     │(speaking)│    │
│   │         │         ⌨ 自由對話                       │         │     │
│   │         │         ✕ 結束對話                       │         │     │
├───┴─────────┴────────────────────────────────────────┴─────────┴─────┤
│ ┌ 葛里安·衛登 · 羈絆 初識 ┐                                           │
│ 「先在櫃檯註冊成為冒險者……」                                     ▼   │
└───────────────────────────────────────────────────────────────────────┘
```

- The command panel collapses; the message window spans the full band and
  shows a name plate (`display_name`, plus `· 羈絆 <stage>` only when
  `bond_stage` is non-null).
- The session line is paged like any response (§6).
- The choice list appears centred over the stage **after the last page of the
  current line is fully shown**. Rows are the committed `dialogue.choices`,
  then `⌨ 自由對話`, then `↦ 移動…`, then `✕ 結束對話`. Digits 1–N, Enter, and pointer work as
  in the current dialogue variant, and dispatch the same actions.
- The speaking side is at full brightness; the other side is dimmed to 60%.
  After a player choice or freeform line, the player is lit until the reply
  commits.
- Movement stays reachable: minimap nodes stay actionable, and the choice
  list ends with a `↦ 移動…` row that swaps the list for the exits list
  (Escape returns to the choices). Movement clears the session through the
  existing seam.
- Drawers stay openable from the top bar.

This replaces the contextual-HUD requirement "The dock keeps its regular
exploration form in dialogue mode".

## 9. Motion layer

### 9.1 Motion levels

`motionLevel`: full / reduced / off. Default: `full`, or `reduced` when the
OS reports `prefers-reduced-motion: reduce`. The existing `reducedMotion`
preference maps to `reduced`. Rules:

- `full`: every animation below.
- `reduced`: fades only (≤ 150ms), no translation, no shake, typing is
  instant, combat beats keep their order and pauses but skip the motion.
- `off`: all state changes are instant; combat beats render as text only.

All durations come from `--motion-*` tokens in `styles/tokens.css`; no
component hard-codes a duration.

### 9.2 Presentation queue

The store keeps committing the server's state immediately (the source of
truth, unchanged). A new client-local **presentation queue** decides *when*
the view shows each change. It owns three kinds of steps: page steps (§6),
transition steps (§9.3), and combat beat steps (§10). Rules:

- Steps play in arrival order; a step never reorders or drops committed data.
- A player click skips the current step to its end state.
- A new player action flushes all queued non-combat steps to their end state
  before the new response starts.
- Input locking rules are unchanged except as §10 states for combat.

### 9.3 Transitions

| Trigger | Full motion |
|---|---|
| Location change (a new `art.scene`) | backdrop crossfade 500ms; place card slides in from the left; minimap pans to the new node; the message window clears with a 150ms fade |
| Exploration → dialogue | command panel slides out right (250ms); message window widens; NPC portrait slides in from the right and fades in (350ms); name plate appears; the greeting types |
| Dialogue → exploration | reverse of the above |
| Exploration → combat | 120ms white flash, veil fades in, foes slide in from the right, command panel flips to the combat root |
| Combat → exploration | foes fade out, veil fades out, command panel flips back |
| Player appearance change | portrait crossfade 400ms |
| Vitals appear / disappear | fade and a 12px slide |
| Dialogue choices appear | 40ms stagger per row |
| Drawer / overlay open | kept as today; drawers slide from the right |

## 10. Combat choreography

### 10.1 Server: structured combat beats

Today a round emits every `EventLog` as text and then publishes `status`,
`context_actions`, and `art` at one newer revision. The view cannot tell which
hit caused which HP loss, and must not parse prose to find out.

Change: the combat result publishes a new read-only presentation panel
`combat_beats` at the same revision as `status`. Its payload is a bounded list
(at most 64) of beats in `EventLog` order, derived only from `EventEntry`
records:

| Field | Source |
|---|---|
| `seq` | ordinal within the round |
| `kind` | a closed presentation set built from the kinds combat settlement emits today: `skill`, `roll`, `damage`, `target_defeated`; every other entry kind maps to `other`. A new kind joins the set only through a spec change |
| `actor` / `target` | the same opaque participant identities the `art` portrait catalog and combat panel already use |
| `amount` | integer from `data.amount` when the kind is `damage`, else null |
| `hp_after` | target HP after this beat, computed **on the server** by applying the round's ordered `damage` amounts to the pre-round HP snapshot, clamped at 0. The presenter asserts the last `hp_after` per target equals the committed `status` HP; on mismatch the panel is unavailable for that round (the client then uses the fallback below) |
| `text` | the already-rendered, escaped line for this entry (`render_plain_text` per entry) |

The panel is available only in combat mode, uses the common unavailable form
elsewhere, and carries a `round` id so a replay after reconnect is never
choreographed twice. It never carries hidden rolls or data the combat panel
does not already disclose (the disguised-stats boundary applies).

### 10.2 Client: beat playback

For each new `round` id, the presentation queue plays one step per beat:

1. The beat's `text` types into the message window (one beat per page).
2. `skill`: the actor portrait steps 24px toward the centre and back.
3. `damage`: the target portrait shakes (6px, 180ms) and flashes; a floating
   number rises from it; that target's HP bar animates to `hp_after`, with the
   existing trailing damage bar following 300ms later.
4. `target_defeated`: the portrait fades and drops out.
5. `roll` and `other`: text only.
6. A 400ms pause (`--motion-beat`) separates beats.

The displayed HP values come from `hp_after` during playback and snap to the
committed `status` values when playback ends. The command panel unlocks when
playback ends **and** the declared revision is accepted (the existing rule).
Clicking skips to the end of the round. With `motionLevel=off`, beats render
as sequential text pages only.

Without a `combat_beats` panel (old server, panel unavailable), the client
falls back to paging the round's text and animating vitals once to the
committed values.

## 11. Quick fixes

- **Minimap legend removed.** The minimap renders no legend and no beyond-state
  info chips. The legend content moves into a `?` popover on the full-map
  overlay. The frame becomes a 1px border; the lattice fits the bounding box
  of the visible nodes with 8px padding and keeps the current node centred
  when the box exceeds the minimap.
- **Full map fits the viewport.** `MapOverlay` opens with a zoom that fits the
  whole known lattice inside the overlay body, and offers zoom (wheel, `+` /
  `-`) and drag-pan, plus a `置中` control.
- **Full log opens at the bottom.** `FullLogOverlay` scrolls to its last line
  on open; the reader scrolls up for older text.

## 12. Edge cases and error handling

- **Font or layout not ready:** paging waits for `document.fonts.ready` before
  measuring; until then the page shows the first block unpaged.
- **A single block larger than a page** after all split points (for example,
  box-drawing map art): it gets its own page with internal scrolling, never
  truncated.
- **Reconnect / resync:** the sequencer rebuilds from the log and shows the
  last response's last page, fully typed. No transition or combat beat
  replays.
- **Dialogue host leaves mid-conversation:** the existing clear seam ends the
  session; the NPC portrait slides out and the command panel returns.
- **Portrait missing:** `StageActor` shows the existing truthful placeholder
  (initial glyph and label), never a stock image.
- **`combat_beats` out of order or with an unknown participant:** the client
  plays the beats it can map and ends at the committed status; the beat panel
  never overrides committed state.
- **Offline / mutation locked:** reading, paging, and the log keep working;
  actions are rejected exactly as today.

## 13. Testing

- **Unit (Vitest):** the paging function (block packing, sentence / clause /
  character splits, markup spans across a split, re-page on resize); response
  segmentation (`in` boundaries, late lines); vitals visibility; the
  presentation queue (ordering, skip, flush on new action); beat playback
  state (`hp_after` display, snap to status, fallback without beats).
- **Component tests:** `HudFrame` anchors per mode against the §4 matrix;
  `MessageWindow` controls; scene overview and verb popover keyboard paths;
  dialogue stage (choices appear only after the last page; dimming); command
  line collapse and focus return.
- **Server (Python):** `explore.talk_open` (greeting, fallback line, stale NPC,
  non-host, no clock or memory change, session writer list); `combat_beats`
  presenter (schema, bound, closed kind set, `hp_after` equals settlement
  state, unavailable outside combat, no disguised data).
- **Browser verification:** keyboard-only journeys at 1920×1080 for move →
  scene overview → talk_open → choice → leave, and for one combat round with
  beats; screenshots checked for the §3 stage-height goal and a fixed band
  height across all three modes; a reduced-motion run.

## 14. Spec impact

| Capability | Change |
|---|---|
| `webclient-contextual-hud` | Largely rewritten: stage anchors, band, per-mode visibility, head card / art showcase / quick chips removed, message window replaces the caption, dialogue-mode dock rule replaced, motion levels |
| `webclient-desktop-shell` | Direct-child and anchor rules follow the new anchors |
| `webclient-input-narrative` | Paging, response segmentation, reading controls, full log opens at bottom |
| `webclient-exploration-menu` | Dock root becomes the scene overview; `交談` affordance maps to `explore.talk_open`; new `explore.talk_open` requirement |
| `webclient-dialogue-session` | `explore.talk_open` added as a session writer |
| `webclient-local-map` | Legend requirements move from the minimap to the full-map popover; fit rules for minimap and full map |
| `webclient-combat-menu` | Combat panel hosted in `band-command`; beat playback and unlock rule |
| `webclient-oob-protocol` | New `combat_beats` panel |
| `webclient-options-surface` | `textSpeed`, `autoAdvance`, `motionLevel` |
| `webclient-art-panel` | Unchanged data; consumers change |

## 15. OpenSpec change breakdown

| # | Change | Depends on | Server change |
|---|---|---|---|
| 0 | `webclient-map-and-log-quick-fixes` (§11) | — | no |
| 1 | `webclient-avg-stage-layout` (§4, §5) | the three pending drawer changes | no |
| 2 | `webclient-message-sequencer` (§6) | 1 | no |
| 3 | `webclient-scene-overview-dock` (§7) | 1 | no |
| 4 | `webclient-dialogue-stage` (§8) | 2, 3 | yes (`explore.talk_open`) |
| 5 | `webclient-motion-layer` (§9) | 2 | no |
| 6 | `webclient-combat-choreography` (§10) | 5 | yes (`combat_beats`) |

Order: 0 can start now (it touches only map and log files). The three pending
drawer changes land next, because they delete dock and drawer-hosting code
that change 1 would otherwise have to carry. Change 1 and change 2 are
designed together: the band's fixed metrics are the paging function's input.
Changes 3 and 5 may run in parallel after 2. Change 4 needs the sequencer and
the overview; change 6 needs the presentation queue from 5.

File-conflict hot spots: `AppClient.vue`, `AppShell.vue`, `HudFrame.vue`, and
`stores/elosern/view.js` are touched by 1, 2, 3, and 4. Run those
sequentially, never in parallel worktrees.
