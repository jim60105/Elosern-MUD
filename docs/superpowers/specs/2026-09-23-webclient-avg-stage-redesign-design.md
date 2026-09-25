# WebClient AVG Stage Redesign — Design

Date: 2026-09-23 (revised 2026-09-25 with the decisions taken while writing
the OpenSpec proposals, §15)
Status: approved by the requester in the brainstorming session
Related: `openspec/specs/webclient-contextual-hud/spec.md` (the H1–H5 shell this
design replaces), `openspec/specs/webclient-dialogue-session/spec.md`,
`openspec/specs/webclient-exploration-menu/spec.md`,
`openspec/specs/webclient-local-map/spec.md`,
`openspec/specs/webclient-combat-menu/spec.md`,
`docs/design/elosern-redesign/REDESIGN.md` (the previous visual reference).
Prerequisites (landed): `make-shop-drawer-frameless`,
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
  Its remembered-place list grows with every visited place and eventually
  pushes the map out of view entirely. The bottom-right of the screen is empty.
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
   proportionally. No narrow, portrait, or mobile layout is designed. The
   existing 1440×900 and 1280×720 acceptance viewports stay as non-overlap
   checks; they are not retired.
3. **The player's portrait stands on stage at all times** (exploration,
   dialogue, combat). The character is player-authored and the stage is where
   it is shown. An appearance change crossfades.
4. **Vitals are hidden at full health** and auto-appear when any vital is below
   its maximum or an abnormal condition (severity `warning` or worse) is
   active. In combat they are always shown.
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
   three-level motion setting (full / reduced / off) that follows
   `prefers-reduced-motion` until the player chooses.
10. **Combat is choreographed beat by beat** from structured, server-authored
    combat beats. The requester accepts the server protocol change.
11. **Quick fixes:** the minimap loses its remembered-place list and thick
    frame; the full map opens fitted to the viewport; the full log opens
    scrolled to the bottom.
12. **No standalone prototype.** The real client differs too much from any
    throwaway page; work goes straight into OpenSpec changes.
13. **Implementation profiles.** Every OpenSpec change is labelled `visual`
    (needs aesthetic judgement) or `logic` (tests define done), so the
    requester can route visual work to a stronger implementer (§15).

## 3. Goals and non-goals

Goals:

- Each game mode shows exactly the surfaces its context needs (§4).
- At least 65% of the viewport height is stage art in every mode, measured at
  1920×1080 as the box between the top bar's bottom edge and the band's top
  edge (48px bar + 300px band → 732 / 1080 = 67.8%).
- Text is read one page at a time at a comfortable measure (≤ 42 CJK
  characters per line).
- One action reaches the people in a room; one action opens a conversation.
- No surface changes size in response to content; the bottom band has a fixed
  height.
- Every visual transition has a reduced-motion equivalent that preserves all
  information.

Non-goals:

- Mobile, tablet, portrait, or new sub-1600px layouts.
- A save/load/auto/skip AVG system menu (the game is a persistent MUD).
- Voice, sound, or music.
- Changing how drawers present their content (bag, quests, shop, status,
  party, codex, gallery). Only where their openers live changes (§5.4).
- A redesigned combat menu hierarchy. The existing combat choice tree moves
  into the command panel unchanged.
- Parsing narrative prose to derive any state (still forbidden; §10 adds
  structured data instead).

## 4. Principles and per-mode visibility

Principle: **show when meaningful, hide completely otherwise** (hidden surfaces
leave the accessibility tree and the tab order). Reference data is one click
away in a drawer, never permanently on screen.

| Surface | Exploration | Dialogue | Combat | Creation |
|---|---|---|---|---|
| Slim top bar (nav, tool group, switcher, connection) | ✓ | ✓ | ✓ | ✓ |
| Place card (location + game time) | ✓ | ✓ | ✓ | — |
| Vitals + condition chips | only when a vital is below max or a `warning`+ condition is active | same as exploration | always | — |
| Minimap (top-right `map` anchor) | ✓ | ✓ | — | — |
| Objective tracker (one line under the minimap) | ✓ | — | — | — |
| Combat participant frame (numbers) | — | — | ✓ (in the `map` anchor) | — |
| Player standing portrait (`actor-left`) | ✓ | ✓ (dimmed when not speaking) | ✓ | — |
| Opposite portrait (`actor-right`) | — | dialogue host | foes | — |
| Party mini-portraits | only when party size > 0 | only when party size > 0 | ✓ | — |
| Message window | 2/3 width | full width, with name plate | 2/3 width | — |
| Command panel | scene overview | collapsed | combat choice tree | full band |
| Dialogue choices | — | centred over the stage | — | — |
| Command line | collapsed; expands on `/` or ⌨ | same | same | closed |

Removed outright: the head card (`CharacterHead`), the art showcase panel
(`ArtPanel` in the left column), the quick-word chips (`QuickWordChips`)
together with their quickbar letter bindings (`l g s t w`, `c` in combat —
every one duplicates a command-panel entry; the server's single-letter typed
aliases stay), the unread indicator (`UnreadIndicator`, replaced by the page
markers), and the top-bar `探索` home tab (it names the screen the player is
already on). Every field the head card showed stays reachable: title, guild
rank and merit in the character-status drawer, the wallet in the bag drawer,
the name in the switcher.

## 5. Layout

### 5.1 Geometry (1920×1080 reference)

```
┌ top bar 48px ─ ELOSERN 伊洛瑟恩 │ 角色 任務 背包 地圖 設定 │ 工具 │ switcher · ● ┐
│ ┌ place card ─────┐                                   ┌ minimap 208px ┐ │
│ │ 冒險者公會大廳    │                                   │               │ │
│ │ 春季 1 日 11:25  │                                   └───────────────┘ │
│ └─────────────────┘                                   objective (1 line)│
│ [vitals: only when needed]                                              │
│    ┌─────────┐                                         ┌─────────┐      │
│    │ player  │            stage: backdrop full-bleed    │ NPC /   │      │
│    │ portrait│            (≈ 732px tall)               │ foes    │      │
│    │         │                                         │         │      │
├────┴─────────┴──────────────────────┬──────────────────┴─────────┴──────┤
│ message window  1280 × 300          │ command panel  640 × 300          │
│ [name plate]                        │  (legend strip)                   │
│ page text, typewriter               │                                   │
│ ▼                   [日誌] [⌨]      │                                   │
└─────────────────────────────────────┴───────────────────────────────────┘
```

- Anchors (`HudFrame`): `place` (top-left), `vitals` (under `place`: the
  status island and the party strip), `map` (top-right: minimap, one-line
  objective, the combat participant frame, the title ballot), `band-message`
  and `band-command` (the band), `actor-left` and `actor-right` (portraits,
  above the backdrop and below the band), `choices` (dialogue only, centred),
  and `command-line`. The old `hud-left` / `hud-right` / `feed` / `dock` /
  `objectives` anchors are gone.
- The band height is `--band-h: clamp(260px, 27.8vh, 400px)` (300px at the
  reference size). It never depends on content, frame, or mode. `--dock-h`,
  `--stage-content-bottom`, and every frame-adaptive band rule are deleted.
- The message window is `66.667%` of the band width; the command panel takes
  the rest. In creation mode the command region spans the whole band. In
  dialogue mode the command panel collapses and the message window takes the
  full width (§8.2).
- Portraits are bottom-aligned to the band's top edge, height
  `min(62vh, 680px, stage box)`, inset 6% from their side. The stage-box clamp
  keeps the portrait under the top bar at 1280×720.
- The command line, when expanded, is a single 44px row docked to the top edge
  of the message region, running from the island column's edge to the message
  region's right edge. It keeps that geometry in every mode, so in dialogue it
  never covers the host.
- The narrow command panel reflows its frames: the waiting screen becomes one
  column; the combat skill detail pane uses `min(220px, 45%)`.

### 5.2 Components

| Component | Fate |
|---|---|
| `HudFrame` | Rewritten: the anchors of §5.1. Mode gating by `data-elosern-mode` is kept; a live mode change also sets `data-mode-change` for transitions (§9.3). |
| `AppShell` | Slots rewired to the new anchors; owns the collapsible command line, the ⌨ and 日誌 buttons, and the mode focus-rescue. |
| `TopBar` / `DesktopNavigation` | 48px, one-row brand `ELOSERN 伊洛瑟恩`; the `探索` home button and `onNavigateHome` removed; location and time moved to `PlaceCard`; the tool group added (§5.4). |
| `PlaceCard` (new) | Location + world time in the `place` anchor, taking over the top-meta location-resolution rule. `.scene-heading` is deleted. |
| `CharacterHead`, left-column `ArtPanel`, `QuickWordChips`, `NarrativeFeed`, `UnreadIndicator` | Deleted, with their tests, stories, manifest titles, and spec requirements. |
| `StatusPanel` | Now only `VitalsTrack` + `ConditionChips`; carries the visibility rule itself (no separate `VitalsBadge`). |
| `PartyStrip` | Renders nothing when the party is empty; otherwise compact cells (avatar, HP hairline, combat token badge; name and numbers in `aria-label`). The `+ 邀請` padding cells are gone. |
| `ObjectiveTracker` | One 32px line: the first objective plus a `+N` count; exploration only. Details stay in the quest drawer. |
| `ReferenceArtwork` | Kept for the drawer art slot; wrapped by the new `StageActor`. |
| `StageActor` (new) | The standing portrait in `actor-left` / `actor-right`, with a truthful placeholder and a static speaking dim. |
| `LocalMap` | Fixed square island (§11). |
| `MessageWindow` (new) | Replaces `NarrativeFeed` in `band-message` (§6). |
| `SceneOverview`, `DockVerbPopover` (new) | The exploration root of the command panel (§7). |
| `DockTabBar` | Kept for the combat root only. |
| `DialogueChoices` (new) | The centred dialogue choice list (§8.2). |
| `ActionDock` + `DockMenu` | Hosted in `band-command` at fixed size with internal scroll; `ActionDock` owns one legend strip. |
| `CommandLine` | Collapsible (§5.5). |

This series is a governed redesign wave: every component added or deleted
updates `component-manifest.json`, its Storybook story, and the
`webclient-component-showcase` spec in the same change.

### 5.3 Vitals visibility

`vitalsVisible = mode === "combat" || lowHp || anyVitalBelowMax || anyAbnormalCondition`,
a pure `isVitalsVisible()` in `components/vitals.js`, derived client-side from
the committed `status` panel. A condition is abnormal when its `severity`
(vocabulary in `world/rules/status_display.py`) is `warning`, `harmful`, or
`critical`. `beneficial` and `informational` conditions — including passive
skill-owned combat-modifier rows — never force the vitals visible; they would
otherwise keep the vitals on screen permanently for characters owning such
skills. Missing or unknown severities count as not abnormal. While the island
is visible its chips show every condition, whatever the severity.

The island hides with `v-show` (`display:none`), not `v-if`, so `VitalsTrack`
keeps its trailing-bar memory and the first hit at full health still shows a
damage gap. Hiding the island while it holds focus rescues focus to the
command panel first. The low-HP vignette rule is unchanged. The island fades
and slides through the motion layer (§9.3).

### 5.4 Top bar and reference drawers

The top bar keeps 角色 / 任務 / 背包 / 地圖 / 設定 and the character switcher,
and gains a 工具 icon group after 設定: 技能系譜, 圖鑑, 稱號冊, 角色肖像圖庫
(only while the `gallery` panel is available), and 說明. These moved there from
the command line's utility strip (§5.5); the command line's duplicate 設定
button is deleted. Every tool is one click, or one Tab stop plus Enter, away.
The party drawer stays reachable with an empty party through a
`同伴 · 隊伍` control in the character-status drawer. Drawers and overlays
open exactly as before.

### 5.5 Command line

Collapsed by default on every mount; the expanded state lives only in
`AppShell` and is never persisted. Collapsed means the `command-line` anchor
is `display:none` while `CommandLine` stays mounted, so the preserved
`#inputfield` stays in the DOM and an unsent draft and the history walk
survive a collapse.

- **Open:** `/` outside an editable control (the existing bridge → router →
  `focusCommandField` route), the ⌨ button at the message window's
  bottom-right, or the dialogue free-form row. Clicking ⌨ while open closes it.
- **Close:** Escape (the draft is kept for the next opening), a send the field
  accepts (`CommandLine` emits `sent`), or entering creation. Focus returns to
  the command panel, or to the focus home of the current mode (§8.2).
- **Stays open:** on a rejected send (text and focus kept), on blur, and while
  drawers or overlays open. The open state carries across combat and dialogue.
- The field's accept rule is one store predicate:
  `connected && !mutationsLocked && phase === "active" && !inFlight`. A
  refused borrowed dialogue send keeps its dialogue target (§8.2).
- History and Tab completion are unchanged.

## 6. Message window and the message sequencer

### 6.1 Responses

The narrative log stays the single store of text (`ctx.narrative`, lines of
kind `in` / `out` / `sys` / `err`, each with a monotonic `seq`; `out`, `sys`,
and `err` are tokenized once at append). The sequencer is a pure view over it
(`lib/message_pages.js`):

- A **response** starts at each `in` line **or** at a dispatch-time response
  mark, whichever comes first. The mark is recorded in `dispatchAction`,
  because declared silent actions (`explore.dialogue_leave`,
  `account.character.switch`, the `gallery.*` actions, and others in
  `SILENT_PRESENTATION_CONTROLS`) append no `in` line. A mark and its echo form
  one response. A blocked or failed dispatch records no mark.
- Lines that arrive with no new boundary (connection notices, a late
  asynchronous freeform reply) join the current response. Lines before any
  action form a leading response.
- The `in` line heads its response and is never paged; it appears only in the
  full log.

### 6.2 Paging

Each response is cut into pages that exactly fit the message window:

1. **Blocks.** Each line is a block. An `err` or `sys` block always starts a
   new page.
2. **Measure.** A hidden twin of the text area (same width, font, and
   `fontScale`; `composables/use-message-measure.js`) decides through an
   injected `fits(candidateBlocks)` whether a page still fits. Capacity is
   measured pixel height, not a line count, because `sys` and map lines use
   other line heights. Page text is `--message-text: clamp(20px, 2.593vh,
   38px) × prose scale` (28px at 1080) with a `max-width: 42em` cap: 6 lines at
   1080, 7 at 720. A 36px control strip under the text holds the marker, 日誌,
   and ⌨.
3. **Split.** A block taller than the remaining room is cut at a hard break or
   the last sentence end that fits (`。！？…」』` with closing quotes kept;
   ASCII `.!?` followed by whitespace also counts), then at a clause mark
   (`，、；：`, ASCII `,;:` + whitespace), and only then at a character
   boundary, never inside a surrogate pair.
4. **Markup.** Paging runs on the `NarrativeMarkup` token stream, never on
   rendered HTML. A cut inside a styled span closes it and re-opens a copy with
   the same classes. Box-drawing map blocks are never split; a block that fits
   no empty page gets its own `oversize` page with internal scrolling.
5. **Re-measure.** A resize or a `fontScale` change re-pages the current
   response and keeps the reader at the typing position (the next character
   while typing, the last shown character once complete).

Paging is a presentation-only function of `(response lines, box metrics)`. It
never mutates the log and never reaches the server.

### 6.3 Reading controls

- **Advance:** a click on the message window (except on buttons or with a text
  selection, so players can copy text), or Enter / Space **only while the page
  surface itself has focus**. The handler stops propagation and ignores key
  repeat, so the document-level bridge never turns the key into a dock
  confirm. If the page is still typing, the press shows it in full; otherwise
  it advances.
- **Markers:** a blinking `▼` when more pages follow, `■` on the last page,
  rendered only once the page is fully shown. There is no head row: the mode
  label and the old `完整日誌` capsule are dropped in favour of the `日誌`
  button in the control strip.
- **Log:** the `日誌` button, or scrolling up when the page has nothing left to
  scroll, opens the full log, which opens scrolled to its latest line. New lines
  arriving while the log is open do not move the reader.
- **Acting while reading:** any action is accepted immediately. As soon as the
  action is out (its mark), typing stops and the previous response's last page
  shows complete; the new response starts on page 1 when its lines arrive.
  Nothing is lost; everything remains in the log.
- **Mount / reconnect:** the window opens on the last page of the last
  response, fully shown.
- The polite live region announces each page's full text once, when the page
  starts, never per character and never on a re-page or a mount.

### 6.4 Reading preferences

Client-local, stored through the versioned layout store, edited in the
settings overlay's 閱讀設定 section:

- `textSpeed`: slow 20 / normal 45 (default) / fast 90 characters per second,
  or instant. A change applies from the next page; switching to instant
  completes the page on screen.
- `autoAdvance`: off (default) / on. A finished page advances after
  `1.2s + 60ms × characters`. It stops at the last page of a response, never
  advances past an oversize or map page, and pauses while any drawer, overlay,
  or the full log is open.
- Typing is instant whenever the motion level is not `full` (§9.1).

Reveal technique: the page is always rendered in full; the unrevealed tail is
hidden with `visibility: hidden` and `aria-hidden` (whole later lines get an
`unrevealed` class, and the line being typed is split with the span-preserving
cut). Layout therefore never re-wraps while typing. One `requestAnimationFrame`
clock with a 100ms per-frame clamp drives typing and the auto-advance wait;
time in a hidden tab does not count.

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

- **出口** lists `move` chips; disabled chips stay visible, focusable, and
  dimmed, with their reason, and never submit.
- **人物** lists `interact` targets, then look-only chips for present
  characters that have no interact descriptor. Activating a target opens a
  verb popover: its affordances in payload order, then 查看, then a back row.
  A target with no affordances opens with 查看 only. Navigation affordances
  open their drawer.
- **物件** lists `look.objects`; activating one looks at it.
- The footer always renders: 查看房間, 等待／休息, and `建議 (N)` (only while the
  suggestions panel is not unavailable). 等待／休息 and 建議 open child frames
  that replace the overview inside the panel.
- Rows with no chips are omitted, label included. Chips wrap; the panel scrolls
  internally and keeps the focused chip in view.
- The popover is a card anchored to the bottom of the command region, with the
  overview inert behind it; a click outside it closes it like the back row.
- The dock returns to the overview whenever the committed room identity
  changes (dock, minimap, or typed movement) and when the mode turns
  `dialogue`.
- **Keyboard:** the router gains a `sections` geometry — Left/Right move in
  reading order and wrap; Up/Down keep the chip's position within the next row,
  clamped to its length. Enter activates, Escape closes the popover or child
  frame and restores the chip that opened it (or the nearest survivor). Digits
  1–9 address the first nine chips in reading order (exits, people, objects,
  footer) in every dock frame. DOM focus stays on `#action-dock`.
- The shortcut legend moves out of the tab bar into one strip owned by
  `ActionDock` (`數字鍵 1–9 · Enter 執行 · Esc 返回`). The exploration tab bar
  (`移動 / 查看 / 互動 / 等待 / 建議`), the move/look/interact submenus, the
  interaction workspace, and the exit-outlet pane are deleted. `DockTabBar`
  remains only for the combat root.

## 8. Dialogue stage

### 8.1 Opening a conversation

New action `explore.talk_open` with payload exactly `{npc_id}`:

- The adapter re-resolves the NPC from the actor's current location exactly
  like `explore.talk_scripted` does and rejects in the same order with the same
  codes (possessed actor, `no_npc`, `schedule_blocked`, `not_dialogue_host`).
- One predicate, `world.rules.dialogue.opens_dialogue(npc)`, decides who is a
  host (an `LLMNPC`, or a `ScriptedDialogue` host whose table resolves). The
  adapter and the exploration presenter share it; a scripted host whose table
  does not resolve shows a disabled 交談 (`dialogue_unavailable`).
- The session line is `world.rules.dialogue.greeting_for(npc)`; when it returns
  `None`, the line is `dialogue_open_fallback_line(npc.key)` from
  `world/rules/player_messages.py`: `{name}看向你，等你開口。` (narration, no
  corner brackets).
- It records the session through `open_or_refresh_dialogue` (a new writer in
  the dialogue-session writer list) and publishes a full snapshot at one
  newer revision, so mode `dialogue` and the panel arrive together.
- It calls no LLM, advances no clock, changes no affinity or memory, and
  triggers no action-options generation. The echo catalog renders it as
  `talk <NPC>`. The typed `talk <npc>` command is unchanged.

The exploration panel moves to schema v3: each dialogue host carries exactly
one `交談` affordance, `explore.talk_open`; the target-level `keywords` field
and the `talk_scripted` / `talk_freeform` affordances are removed, because the
dialogue panel's `choices` already carry the keywords once a session is open.
`explore.talk_open` joins `ACTION_CODE_ALLOWLIST` but is never suggested.
`explore.talk_scripted` (the choice rows) and `explore.talk_freeform` (the
free-form row) keep their adapters and contracts.

The dialogue panel moves to schema v2: `host.portrait_ref` is the art-catalog
key of the host (computed on the server through `build_art_view`), or `null`
when the host is not in the catalog. The client never constructs a catalog key.

### 8.2 Layout

```
│   ┌─────────┐                                        ┌─────────┐     │
│   │ player  │         ① 關於註冊                       │  NPC    │     │
│   │ (dimmed)│         ② 任務板的事                     │(speaking)│    │
│   │         │         ⌨ 自由對話                       │         │     │
│   │         │         ↦ 移動…                          │         │     │
│   │         │         ✕ 結束對話                       │         │     │
├───┴─────────┴────────────────────────────────────────┴─────────┴─────┤
│ 葛里安·衛登 · 羈絆 初識                                                  │
│ 葛里安·衛登說：「先在櫃檯註冊成為冒險者……」                         ▼   │
└───────────────────────────────────────────────────────────────────────┘
```

- **Collapse:** the band becomes one column; the command region becomes inert
  at once and leaves the accessibility tree (`#action-dock` stays mounted). The
  router claims only `/` in dialogue, so no key drives the hidden dock. The
  focus home in dialogue is the message window's page surface instead of
  `#action-dock`.
- **Name plate:** a header row inside the message window: `display_name`, plus
  ` · 羈絆 <stage>` only when `bond_stage` is non-null. It sits inside the
  window because the expanded command-line row would cover a plate straddling
  the edge. The text keeps its 42em cap.
- **Line:** the session line is paged and typed like any response. It is paged
  verbatim, so the host name may appear both in the plate and in the `X說：`
  prefix (stripping it would mean parsing prose).
- **Choices:** `DialogueChoices` in the `choices` anchor (`min(560px, 40%)`
  wide) appears only in dialogue mode with an available panel, once the last
  page is fully shown and no dispatch is in flight. Rows: the committed
  `dialogue.choices` with badges 1–N, `⌨ 自由對話`, `↦ 移動…`, `✕ 結束對話`. It
  is one tab stop (a menu with `aria-activedescendant`), takes focus when it
  appears, and consumes arrows (wrapping), Home/End, Enter/Space, digits, and
  Escape; `/` passes through. `↦ 移動…` swaps in the exit chips of the
  committed overview; Escape or the back row returns. Each row dispatches the
  same action as before.
- **Speaking state:** `view.dialogueSpeaker` is `"player"` while an
  `explore.talk_scripted` or `explore.talk_freeform` action is in flight,
  otherwise `"host"`. The non-speaking `StageActor` is dimmed with
  `--actor-dim: 0.6`.
- **Portraits:** `actor-left` holds the player; `actor-right` holds the host's
  catalog entry looked up by `host.portrait_ref`. A still-generating portrait
  shows its own placeholder; a missing one shows the name's initial and the
  name.
- **Free-form borrow:** the free row expands the command line; a refused send
  keeps the dialogue target; a successful send returns focus to the choice
  list.
- Movement stays reachable through `↦ 移動…` and the minimap. Drawers stay
  openable from the top bar.

## 9. Motion layer

### 9.1 Motion levels

`motionLevel`: full / reduced / off replaces the old reduced-motion boolean
everywhere. The store is the only resolver: a stored level, or — while
nothing is stored — the OS `prefers-reduced-motion` followed live. It writes
the effective level to `<html data-motion>`. The settings overlay shows three
buttons, 動態效果 `完整` / `減少` / `關閉`, with the effective level pressed.

- `full`: every animation below.
- `reduced`: stage-transition tokens cap at 150ms fades; the general
  `--motion-fast/base/slow` tokens go to 0 (drawers and control feedback
  become instant); `--motion-travel` goes to 0 (no translation or shake);
  looping animations (pulses, blink, spinners) stop; the white flash is
  dropped; typing is instant.
- `off`: every duration is 0ms (Vue ends transitions at once, which keeps the
  browser suite deterministic).

All durations come from `--motion-*` tokens in `styles/tokens.css`; a Vitest
guard fails on any literal duration in a component. An OS fallback media block
covers Storybook and the frames before the store loads. The layout store is
at version 3 (`textSpeed`, `autoAdvance`, `motionLevel`); older wrappers reset
to defaults (no migration; the project is unreleased). The browser suite runs
at `off` by default.

### 9.2 Presentation contract

There is no general presentation-queue module: pages are sequenced by the
message window's reader state, and transitions are declarative CSS / Vue
transitions driven by committed state. Every presentation step obeys one
contract:

- Committed state is never gated by presentation, and input is never held
  longer than a transition's duration.
- Steps play in commit order; a click shows the current step's end state.
- A new player action flushes non-combat steps to their end state.
- An element that is leaving is inert from the moment its state commits
  (`inertWhileLeaving`); focus may land on an entering element, never on a
  leaving one.
- Only a live mode change animates; mounting, reconnect, and same-mode resync
  play nothing.

Combat beats have their own queue beside the reader state (§10.2).

### 9.3 Transitions

| Trigger | Full motion |
|---|---|
| Location change (a new `art.scene`) | backdrop crossfade 500ms, started only after the next image is decoded (until then the previous image stays dimmed); place card slides in from the left (a time-only change does not animate); minimap pans with a FLIP transform anchored on the previous current node |
| Every new response | the previous content leaves as an opaque inert layer fading over 150ms while the new page mounts and types at once |
| Exploration → dialogue | message window widens at once (animating the grid would re-page every frame); command panel slides and fades out over it in 250ms, then goes `visibility:hidden`; NPC portrait slides in from the right and fades in (350ms); name plate fades in |
| Dialogue → exploration | reverse of the above |
| Exploration → combat | 120ms white flash (dropped under reduced), veil fades in, command panel flips to the combat root; foes enter per §10.2 |
| Combat → exploration | veil fades out, command panel flips back, foes leave |
| Player appearance change | portrait crossfade 400ms; the speaking dim eases |
| Vitals appear / disappear | fade and a 12px slide |
| Dialogue choices appear | 40ms stagger per row; keys work from the first frame; leaving rows are removed at once |
| Drawer / overlay open | as before, obeying the motion level |

## 10. Combat choreography

### 10.1 Server: structured combat beats

Today a round emits every `EventLog` as text and then publishes `status`,
`context_actions`, and `art` at one newer revision. The view cannot tell which
hit caused which HP loss, and must not parse prose to find out.

Change: a new read-only presentation panel `combat_beats` (new capability
`webclient-combat-beats`), published at the same revision as `status`. Its
payload is `round` (`"<session_id>/<rounds_elapsed>"`) plus at most 64 beats in
`EventLog` order, derived only from the settled round's `EventEntry` records
(the defeat-aftermath logs are excluded):

| Field | Source |
|---|---|
| `seq` | ordinal within the round |
| `action` | 0-based ordinal of the source `EventLog` (the actor's gesture plays on the first beat of each group) |
| `kind` | closed set `roll`, `damage`, `target_defeated`; every other entry kind (including `target_knocked_out`) maps to `other`. There is no `skill` entry kind in combat settlement |
| `actor` / `target` | art-catalog keys of the participants (`portrait_catalog_key`), or `null` when the entry names no participant |
| `amount` | integer from `data.amount` for `damage`, else `null` |
| `hp_after` | target HP after this beat, projected on the server from the damage amounts, clamped at 0 (or at 1 when the round knocks that target out, matching the damage floor) |
| `text` | `strip_ansi(render_entry_text(entry))`, at most 256 code points |

- **HP source:** the round records every roster participant's stored HP before
  `run_round` and again inside the round transaction, before terminal
  settlement, and passes that record to the presenter through an internal
  result slot that never reaches the wire. The presenter checks each damaged
  target's last `hp_after` against the recorded end-of-round HP; on a
  mismatch, an over-bound, or an unknown damage target it returns the common
  unavailable form and logs a warning. Rounds with heals, drains,
  `damage_divert`, or silent upkeep ticks are therefore unavailable and use
  the fallback.
- **Availability:** only on the publication that completes `combat.cast`,
  `combat.flee`, or `inventory.use` in combat — **including a terminal round**,
  whose snapshot mode is already `exploration`. Reconnect snapshots, forfeits,
  typed commands, pushes, rejected actions, the overwhelm opening, and fights
  opened by the typed `cast` command carry the unavailable form, so nothing is
  replayed.
- **Disclosure:** `hp_after` is a number for foes too, because the combat panel
  already ships every participant's true HP from the same source; nothing reads
  the disguise layer.
- **Bounds reject rather than truncate:** 64 beats, `round` ≤ 160 code points,
  panel JSON ≤ 12,288 bytes.

### 10.2 Client: beat playback

Foes stand in `actor-right` as `StageActor`s during combat; the participant
frame stays in the `map` anchor as the numbers panel. For each new `round` id a
beat queue beside the message window's reader state plays one step per beat:

1. The beat's `text` is one page, typed.
2. On the first beat of each `action` group, the actor portrait steps 24px
   toward the centre and back.
3. `damage`: the target shakes (6px, 180ms) and flashes; a floating number
   rises; that target's HP display animates to `hp_after`, with the trailing
   damage bar following 300ms later.
4. `target_defeated`: the portrait fades and drops out.
5. `roll` and `other`: text only.
6. `--motion-beat` (400ms) separates beats.

The displayed HP values come from `hp_after` during playback and snap to the
committed values when playback ends. The command panel unlocks when playback
ends **and** the declared revision is accepted. A click skips to the end of the
round. A **terminal round's beats play before the combat → exploration
transition**: committed state is not gated, so the presentation holds the
combat stage until the beats finish or are skipped. `reduced` keeps the order
and the pauses without motion; `off` renders the beats as sequential text
pages only. Without an available `combat_beats` panel, the client pages the
round's text and animates the vitals once to the committed values. Script-side
durations are read from the `--motion-*` tokens and are 0 at `off`.

**Foe line-up (`FoeLineup`, C13a).** At most three foes stand in `actor-right`,
in presenter order, in a row that grows leftward: each later foe is offset by
65% of a slot and stands behind the one before, scaled 1 / 0.9 / 0.8 for one /
two / three foes, staying right of the stage centre and clear of the player at
1920 and 1280. Further foes appear only in the participant frame, which stays
the complete numbers panel (no "+N" plate). Foes slide in on a live change into
combat and fade out on leaving it; a reload plays nothing. Each slot carries
`data-portrait-ref` so beats can address it. During a round, a committed
defeated foe stays on stage until its own defeat beat, and each foe shows a
decorative HP gauge with a trailing bar (hidden from assistive technology).

**Beat queue (C13b).** `lib/motion_tokens.js` (`readMotionMs`) is the
script-side token reader; `--motion-beat` is 400ms at full and reduced, 0 at
off. `lib/beat_queue.js` is a pure planner and reducer (text → act → pause →
done). The store slice `stores/elosern/beats.js` starts a round only for a new
`round` id in the epoch while `combat.cast`, `combat.flee`, or `inventory.use`
is in flight, bound to that dispatch's response mark. Pre-round roster and HP
come from the previous view (a terminal snapshot is already the exploration
kind); the player's key is `status.actor.identity`. The round's own event lines
(`max(action) + 1` output lines) are replaced by one page per beat, then the
response's remaining lines page normally. HP displays (`VitalsTrack`,
`StatusPanel`, `ParticipantFrame`) take a `displayHp` value that steps with the
beats and snaps to committed values; the low-HP marker and vignette stay on
committed values. The lock joins `dispatchAction` and the router gates; a typed
command flushes the round; a generation change or detach resets it. At `off`
the beats are ordinary pages and nothing locks.

**Choreography and terminal hold (C13c).** Gesture tokens
`--motion-beat-step` 240ms, `-hit` 180ms, `-float` 600ms, `-defeat` 350ms
(150ms at reduced), with distances scaled by `--motion-travel`; the hit flash
is scaled by `--motion-flash-peak`; `--motion-trail-delay` is 300ms. The `act`
phase lasts the longest gesture of the step; `StageActor` takes `gesture`,
`gestureKey`, and `floatAmount`, and the player never plays `defeat`. While a
fight-ending round still plays, `data-beat-hold="combat"` keeps the veil and
the (inert) line-up on stage until the round ends or is skipped; the mode
attribute, minimap, dock, focus, and accessibility tree still change at
commit. At `off` nothing is held.

## 11. Quick fixes

- **Minimap island.** A fixed card (1px frame, 4px padding, a 208 × 208 px
  canvas, a readout row that always keeps its height), right-aligned in the
  `map` anchor. The graph-variant remembered-place list and the whole
  height-budget measurement machinery are deleted. Fill rules:
  - lattice: the cell pitch grows up to 1.5× to fill the square, leftover room
    becomes dotted coordinate margin, and the drawing scales down only when the
    minimum pitch does not fit (no crop around the current node — a crop would
    cut the outer ring of `map_visual_range: 2` maps);
  - graph: the view is cropped to the drawn footprint plus 8px and centred on
    the current node, never magnified.
  Remembered rooms stay readable: a visually-hidden list on the island for
  assistive technology, and a visible non-focusable list under the graph
  variant on the full-map overlay.
- **Full map fits the viewport.** The overlay opens at
  `min(1, (vw−24)/W, (vh−24)/H)` so the whole known map (including the
  edge-marker gutter) fits, never magnified. Zoom by `viewBox` (range: fit to
  2×) with the wheel about the pointer, `+`/`=`/`-` keys, and 放大 / 縮小
  buttons in 1.25× steps; primary-button drag pans past a 4px threshold (the
  click after a drag never submits a move); `置中` recentres at the current
  zoom; Tab focus on an off-screen node pans it into view. The view refits on
  resize and travel until the reader zooms or pans; nothing is persisted. The
  state legend moves into a `?` (圖例) popover; Escape closes the popover
  before the overlay. No zoom-level figure is shown.
- **Full log opens at the bottom** (§6.3).

## 12. Edge cases and error handling

- **Font or layout not ready:** paging waits for `document.fonts.ready`; until
  then the window shows the first block unpaged.
- **A single block larger than a page** after all split points (for example,
  box-drawing map art): it gets its own `oversize` page with internal
  scrolling, never truncated.
- **Reconnect / resync:** the window rebuilds from the log and shows the last
  response's last page, fully shown. No transition or combat beat replays.
- **Dialogue host leaves mid-conversation:** the existing clear seam ends the
  session; the NPC portrait leaves and the command panel returns.
- **Portrait missing:** `StageActor` shows the truthful placeholder, never a
  stock image.
- **`combat_beats` unavailable or inconsistent:** the server refuses to publish
  an inconsistent round; the client falls back (§10.2). The beat panel never
  overrides committed state.
- **Offline / mutation locked:** reading, paging, and the log keep working;
  actions are rejected exactly as before.

## 13. Testing

- **Unit (Vitest / Node):** paging (block packing, sentence / clause /
  character splits, markup spans across a cut, re-page anchor); response
  segmentation (`in` lines, dispatch marks, late lines); vitals visibility
  including severities; typewriter reveal; motion-level resolution and the
  literal-duration guard; the `sections` router geometry; the beat queue
  (ordering, skip, flush, `hp_after` display, snap, fallback).
- **Component tests:** `HudFrame` anchors per mode against the §4 matrix;
  `MessageWindow` controls; `SceneOverview` / `DockVerbPopover` keyboard paths;
  `DialogueChoices` (appears only after the last page; key ownership);
  `StageActor` dimming; command-line collapse and focus return.
- **Server (Python):** `explore.talk_open` (greeting, fallback, stale NPC,
  non-host, no clock or memory change, session writer list); exploration panel
  v3; dialogue panel v2 `portrait_ref`; `combat_beats` (schema, bounds, closed
  kind set, round record, `hp_after` check, availability, no replay, no hidden
  data).
- **Browser:** the suite runs with motion `off`; keyboard-only journeys at
  1920×1080 for move → scene overview → talk_open → choice → leave and for a
  combat round with beats; the 65% stage and fixed-band checks; paging and
  re-paging; a reduced-motion run and full-motion computed-style checks.

## 14. Spec impact

| Capability | Change |
|---|---|
| `webclient-contextual-hud` | Largely rewritten: stage anchors, band, place card, per-mode visibility, vitals rule, head card / art showcase / quick chips removed, message window replaces the caption, scene overview and combat-only tab bar, dialogue collapse, stage actors, choices, reading and motion preferences, transitions |
| `webclient-desktop-shell` | Anchors and direct children, collapsible command line, top-bar tool group, paged narrative output, layout store v3 |
| `webclient-input-narrative` | Response segmentation, paging, reading controls, typing, full log opens at its latest line, echo heads its response |
| `webclient-exploration-menu` | Exploration panel v3, `explore.talk_open`, dock rooted at the scene overview |
| `webclient-dialogue-session` | Dialogue panel v2 (`portrait_ref`), `explore.talk_open` as a session writer |
| `webclient-local-map` | Fixed square island, remembered-room readability, full-map fit/zoom/pan, legend popover |
| `webclient-combat-menu` | Combat results carry the beats at the status revision; beat playback and the unlock rule |
| `webclient-combat-beats` (new) | The `combat_beats` panel |
| `webclient-oob-protocol` | `combat_beats` registration; the round record reaches only the completing publication |
| `webclient-component-showcase` | The AVG series as a governed wave; manifest additions and deletions |
| `webclient-pointer-activation`, `webclient-options-surface`, `webclient-context-actions-suggestions`, `webclient-action-dispatch`, `exploration-affordances`, `webclient-context-actions`, `webclient-lore-codex-panel`, `webclient-art-panel`, `webclient-browser-verification`, `webclient-narrative-markup` | Restated where they named retired surfaces, keys, or the reduced-motion boolean |

## 15. OpenSpec change series

Each change fits one engineer-day. Changes run one at a time in archive order
because most share `AppClient.vue`, `AppShell.vue`, `HudFrame.vue`,
`MessageWindow.vue`, `app-shell.css`, or the store; later changes write their
MODIFIED requirement blocks on top of earlier changes' text. Only the pure
server changes (C10a, C12) can run in parallel with the client chain.

| # | Change | Profile | Status |
|---|---|---|---|
| C1 | `webclient-minimap-and-log-quick-fixes` | visual | archived |
| C2 | `webclient-full-map-fit-view` | visual | archived |
| C3 | `webclient-retire-redundant-hud` | logic | archived |
| C4a | `webclient-avg-stage-shell` | visual | archived |
| C4b | `webclient-avg-place-card-top-bar` | visual | archived |
| C4c | `webclient-avg-stage-hud-anchors` | visual | archived |
| C5 | `webclient-collapsible-command-line` | logic | archived |
| C6a | `webclient-message-pages` | logic | archived |
| C6b | `webclient-message-window-component` | visual | archived |
| C6c | `webclient-message-window-swap` | logic | archived |
| C7 | `webclient-typewriter-reading-prefs` | visual | archived  |
| C8a | `webclient-scene-overview-component` | visual | archived  |
| C8b | `webclient-scene-overview-swap` | logic | proposed |
| C8c | `webclient-retire-exploration-submenus` | logic | proposed |
| C9a | `explore-talk-open-action` | logic | proposed |
| C9b | `webclient-talk-open-dock` | logic | proposed |
| C10a | `dialogue-panel-host-portrait` | logic | proposed (server; parallel-safe) |
| C10b | `webclient-dialogue-stage-actors` | visual | proposed |
| C10c | `webclient-dialogue-choices-overlay` | visual | proposed |
| C11a | `webclient-motion-level` | logic | proposed |
| C11b | `webclient-scene-transitions` | visual | proposed |
| C11c | `webclient-mode-transitions` | visual | proposed |
| C12 | `combat-beats-panel` | logic | proposed (server; parallel-safe) |
| C13a | `webclient-combat-foes-on-stage` | visual | proposed |
| C13b | `webclient-combat-beat-queue` | logic | proposed |
| C13c | `webclient-combat-beat-choreography` | visual | proposed |

Archive order: C1 → C2 → C3 → C4a → C4b → C4c → C5 → C6a → C6b → C6c → C7 →
C8a → C8b → C8c → C9a → C9b → C10a → C10b → C10c → C11a → C11b → C11c → C12 → C13a → C13b → C13c.
The "component first, swap second" pairs (C6b/C6c, C8a/C8b) follow the
showcase rule that a component is never wired into the live application
before its story exists.
