## Why

The AVG stage design (`docs/superpowers/specs/2026-09-23-webclient-avg-stage-redesign-design.md` §1, §3, §5.1, §5.2) found that the action dock changes height with its active frame and pushes the narrative caption up and down while the player reads. The caption is a small box in the centre of the stage, and the player's portrait is a backdrop decoration with no fixed place.

- `HudFrame.vue` places a centred `feed` caption and a floating `dock` panel.
- Both are sized from a frame-dependent `--dock-h`: `app-shell.css` redefines it for the empty host, the interaction workspace, the waiting frame, and combat.

The design replaces both with one fixed-height bottom band: the message window takes two thirds of the width and the command panel the remaining third. The player's portrait stands on that band. This change builds the band and the two portrait anchors, and moves the existing feed and dock into the band without changing their behaviour. It is the first of three stage-shell changes (C4a, C4b, C4c in the series). The project is unreleased, so the frame-adaptive band code is deleted, not kept as an option.

## What Changes

- **BREAKING (internal)**: `web/webclient-app/components/HudFrame.vue` loses the `feed` and `dock` anchors (testids `anchor-feed`, `anchor-dock`).
  - New anchors:
    - a full-width `div.stage-band` (`data-testid="stage-band"`) carrying the band chrome
    - its two regions `band-message` (testid `anchor-band-message`, left 2/3) and `band-command` (testid `anchor-band-command`, right 1/3)
    - two portrait anchors `actor-left` / `actor-right` (testids `anchor-actor-left`, `anchor-actor-right`)
  - `hud-left`, `hud-right`, and `command-line` stay.
  - The slots become `band-message`, `band-command`, `actor-left`, and `actor-right`.
  - The mode-gating CSS and the header comment are rewritten.
- New token `--band-h: clamp(260px, 27.8vh, 400px)` in `styles/tokens.css`.
  - `--dock-h` is deleted.
  - `--stage-content-bottom` becomes `calc(var(--band-h) + var(--command-line-h))`, the edge every surface above the band clears.
  - The band never depends on content, frame, or mode.
- **BREAKING (internal)**: delete the frame-adaptive band from `styles/app-shell.css`:
  - the stage `--dock-h` override
  - the `:has(.dock-pane-host:empty)`, `:has(.interaction-workspace)`, and `:has(.waiting-screen)` rules, and the anchor widenings that go with them
  - the combat `--dock-h`, feed, dock, and `hud-left` offsets
  - the dialogue feed height
  - the floating-panel `dock` rules and their `max-width: 1000px` / `720px` fallbacks
  - the `feed` anchor rules
- `components/AppShell.vue`:
  - renders `NarrativeFeed` in `#band-message` and forwards `#action-dock` into `#band-command`
  - forwards new `actor-left` / `actor-right` slots
  - updates the `HIDDEN_BY_MODE` creation selector to `band-message`
  - drops the `--dock-h` comments
- The command-line anchor becomes one row docked on the top edge of the message region. It runs from the left HUD column's right edge (`var(--left-column)`) to the message region's right edge, and overlays the lowest strip of the stage, never the band. C5 later collapses it in place.
- `AppClient.vue` moves `ReferenceArtwork` (the current roster character's portrait, previously `.stage-portrait` in `#backdrop`) into `#actor-left`, where it is bottom-aligned to the band.
  - Its height is `min(62vh, 680px)`, clamped to the stage box, with a 6% inset.
  - The `.stage-portrait` rules, their combat override, and the 1000px override are replaced by `[data-anchor="actor-left"]` rules. `actor-right` stays empty.
- The narrow command region lays out its own frames:
  - The waiting screen's cards stack in one column.
  - The interaction workspace keeps its two columns, and its target grid collapses to one.
  - The skill detail pane's basis shrinks, so list and detail stay side by side without horizontal overflow at 1280.
- The backdrop and captions are positioned from the band:
  - The scene backdrop spans the stage box (`bottom: var(--band-h)`).
  - The `SceneBackdrop.vue` captions and the `app-shell.css` scene-caption overrides clear the band and the command row.
  - `ObjectiveTracker.vue` sits above the band (`bottom: calc(var(--band-h) + 12px)`) until C4c moves it into the `map` anchor.
- Spec deltas restate the stage, visibility, backdrop, caption, command-line, dialogue-variant, and reference-surface requirements for the band. They replace the floating-dock requirement, and restate the desktop-shell and exploration-dock requirements that describe the frame-adaptive band.
- No OOB schema, presenter, server, store, router, or persistence change. No component is added or deleted, so the component manifest is unchanged.

Out of scope:
- The 48px top bar, removing the 探索 entry, the place card, retiring `.scene-heading`, and the 65% stage-height assertion are owned by `webclient-avg-place-card-top-bar` (C4b).
- The `place` / `vitals` / `map` anchors (replacing `hud-left` / `hud-right`), the one-line objective tracker, compact party avatars, and the placement of `TitleBallotMenu` / `ParticipantFrame` are owned by `webclient-avg-stage-hud-anchors` (C4c).
- Collapsing the command line is owned by `webclient-collapsible-command-line` (C5).
- Paging the message window is owned by `webclient-message-paging` (C6).
- The scene-overview dock root is owned by `webclient-scene-overview-dock` (C8).
- The dialogue portraits (`actor-right`), the collapsing command panel, and the full-width dialogue message window are owned by `webclient-dialogue-stage` (C10).
- Motion is owned by `webclient-motion-layer` (C11).

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `webclient-contextual-hud`:
  - MODIFIED:
    - "The WebClient renders a full-bleed cinematic stage with anchored HUD surfaces": the new anchors, the fixed band, and the portrait anchors.
    - "Surface visibility is gated by the committed game mode", on C3's text: adds the player-portrait row and the creation band.
    - "The scene backdrop renders the art payload truthfully behind the stage": backdrop in the stage box, captions clear the band.
    - "The narrative is a bounded caption whose complete log is reachable in one action": the caption fills the message region.
    - "The command line is a permanently present bar in the stage's command-line anchor", on C3's text: the row docks on the message region.
    - "The feed presents the dialogue variant from the committed panel": the exchange scrolls inside the fixed caption.
    - "The reference surfaces have no permanently visible home and are reached from the top navigation or the dock": the caption is no longer the stage's visual centre.
  - REMOVED "The action dock renders as a floating panel in the stage's dock anchor".
  - ADDED "The action dock fills the band's command region at a fixed size".
- `webclient-desktop-shell`: MODIFIED "Required desktop surfaces remain visible and usable", on C3's text: the fixed band replaces the frame-adaptive dock-band measure, and 1920x1080 joins the viewports.
- `webclient-exploration-menu`: MODIFIED "The exploration dock is keyboard-first and re-homes the service submenus". The workspace and waiting frames no longer widen the dock; they render inside the fixed command region.

## Impact

- Edited components:
  - `web/webclient-app/components/HudFrame.vue`, `AppShell.vue`, `SceneBackdrop.vue`, `ObjectiveTracker.vue`
  - `ActionDock.vue`, `NarrativeFeed.vue`: comments only
  - `web/webclient-app/AppClient.vue`
- Edited styles: `styles/tokens.css`, `styles/app-shell.css`.
- Story: `stories/Core/HudFrame.stories.js`.
- Vitest: `tests/hud_frame.test.js`, `tests/app.test.js`.
- Browser tests:
  - `web/tests/browser/test_browser_contextual_hud_anchors.py`
  - `test_browser_layout.py`
  - `test_browser_contextual_hud_stage.py`
  - `test_browser_contextual_hud_dock.py`
  - `test_browser_shell_dock.py`
  - `test_browser_combat_menu.py`
  - `test_browser_exploration_tiles.py`
- Spec traceability:
  - `webclient-contextual-hud::the-action-dock-renders-as-a-floating-panel-in-the-stage-s-dock-anchor` is removed. Its two annotations (`test_browser_contextual_hud_dock.py`, `test_browser_contextual_hud_stage.py`) re-anchor to `webclient-contextual-hud::the-action-dock-fills-the-band-s-command-region-at-a-fixed-size`.
  - Every other title is unchanged.
  - The `webclient-contextual-hud` Purpose paragraph ("the centred floating dock panel") is edited directly in the main spec at sync.
- Dependencies:
  - Archive order C1 → C2 → C3 → C4a (this change) → C4b → C4c.
  - This change writes three MODIFIED blocks on top of C3's (`webclient-retire-redundant-hud`) text and must be archived after it.
  - C4b and C4c build on this change's stage, visibility, and desktop-shell texts.
  - C5 and C8 depend on the band and the command-line row.
  - The hot-spot files are `HudFrame.vue`, `AppShell.vue`, `AppClient.vue`, and `app-shell.css`, so the series runs these changes one after another, never in parallel worktrees.
