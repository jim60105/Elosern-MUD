## Context

See proposal.md (Why). The current state was checked in code. C1, C2, and C3 (`webclient-minimap-and-log-quick-fixes`, `webclient-full-map-fit-view`, `webclient-retire-redundant-hud`) are assumed archived first.

- `components/HudFrame.vue` renders these absolutely positioned `.stage-anchor` elements: `hud-left`, `hud-right`, `feed`, `dock`, and `command-line`. It also renders the `backdrop` and `objectives` slots, the vignette (z 1), and the combat veil (z 2).
  - Its own CSS paints the dock anchor as the draft's full-width `.dockwrap` band: gradient, `--line` top border, upward shadow, and padding `11px 18px 12px`, with `height: var(--dock-h)` and `bottom: var(--command-line-h)`.
  - The command line is a full-width 64px row at the stage bottom (`--command-line-h: 64px`).
- `styles/app-shell.css` overrides this into a floating panel:
  - `[data-anchor="dock"]` sits at `left: 35%; right: calc(var(--right-column) + 12px); bottom: calc(var(--command-line-h) + 6px)`, with a border and radius.
  - `[data-anchor="feed"]` sits at `left: 35%`, `height: 30vh`, above `--stage-content-bottom`.
  - The stage sets `--dock-h: clamp(260px, 34vh, 340px)` and changes it for:
    - `:has(.dock-pane-host:empty)`: 144px
    - `:has(.interaction-workspace)`: `clamp(300px, 40vh, 390px)`, plus `left: calc(var(--left-column) + 12px)`
    - `:has(.waiting-screen)`: `clamp(360px, 46vh, 430px)`, plus the same `left`
    - combat: `clamp(230px, 29vh, 290px)`; 100px when empty; separate feed and dock offsets
  - Dialogue sets the feed height to `clamp(390px, 56vh, 540px)`.
  - Two narrow media blocks (`max-width: 1000px`, `720px`) widen the dock.
  - `tokens.css` defines `--dock-h: clamp(126px, 17vh, 160px)` and `--stage-content-bottom: calc(var(--dock-h) + var(--command-line-h))`.
- Other consumers of those tokens:
  - `SceneBackdrop.vue` positions five captions from `--stage-content-bottom`.
  - `ObjectiveTracker.vue` uses `bottom: calc(var(--dock-h) + 60px)`.
  - `app-shell.css` positions the scene label, alt text, and full-view control from `--dock-h + 28vh`.
- The player portrait is `<ReferenceArtwork class="stage-portrait">` in `AppClient.vue`'s `#backdrop` slot, `v-if` not creation.
  - Its source is `store.view.rosterCharacters.find(c => c.current).portrait`.
  - `app-shell.css` places it at `top: calc(var(--header-h) + 14px); bottom: var(--command-line-h); left: 15%; width: 25%`, with a combat override and a 1000px override.
- `AppShell.vue` defines `HIDDEN_BY_MODE.creation = "[data-anchor='feed'], [data-anchor='hud-left'], [data-anchor='command-line'], .local-map"`.
- C1 deleted `LocalMap`'s anchor height budget (`anchorHeightBudget` read the `dock` anchor), so no island measures the band.

## Goals / Non-Goals

**Goals:**
- One bottom band of fixed height (`clamp(260px, 27.8vh, 400px)`), split two thirds (message region) and one third (command region), that no frame, mode, or content resizes.
- `NarrativeFeed` and `ActionDock` re-homed into the band with no behaviour change.
- The player portrait standing on the band in its own anchor.
- The command line kept always present, placed where C5 will expand it.

**Non-Goals:**
- `hud-left`, `hud-right`, the objective tracker's content, `TitleBallotMenu`, and `ParticipantFrame` placement (C4c). Here they only clear the band.
- The top bar height, the 探索 entry, location and time, and `.scene-heading` (C4b). The header stays 80px (72px at ≤1350px) in this change.
- Any dock or feed behaviour: router, frames, keyboard, dispatch, dialogue rows, unread indicator.
- Retiring the 1440x900 and 1280x720 acceptance viewports. They stay, and 1920x1080 is added as the reference.

## Decisions

### D1. HudFrame: a band container with two in-flow regions
`HudFrame` renders `<div class="stage-band" data-testid="stage-band">`: `position: absolute; left: 0; right: 0; bottom: 0; height: var(--band-h); display: grid; grid-template-columns: minmax(0, 2fr) minmax(0, 1fr)`.
- It carries the draft band chrome moved from the old dock anchor (the gradient, `border-top: var(--line)`, and `box-shadow: 0 -14px 34px -24px #000`).
- Its children are:
  - `<div class="stage-anchor" data-anchor="band-message" data-testid="anchor-band-message">`, with the `band-message` slot
  - `<div class="stage-anchor" data-anchor="band-command" data-testid="anchor-band-command">`, with the `band-command` slot
- Both regions are `position: relative`, overriding `.stage-anchor`'s absolute default, with `min-height: 0` and their own padding: the message region `10px 12px 12px 18px`, the command region `10px 18px 12px 6px`.
- In creation mode the message region is `display: none` and `.stage-band` switches to `grid-template-columns: minmax(0, 1fr)`.

*Why a container:* the two regions share one top edge and one height by construction, the band chrome paints once across both, and "the band never depends on content" is one declaration (`height: var(--band-h)`) on one element.

*Alternative:* two absolutely positioned anchors each sized `var(--band-h)`. Rejected: the chrome would be painted twice with a seam, and the width split would be two `calc()`s that can drift.

z-order:
- backdrop 0
- vignette 1
- combat veil 2
- portrait anchors 2, painted after the veil so the player stays bright in combat as today
- caption and islands 4
- band 5
- command line 6

`.elosern-stage .stage-vignette`'s inset shadow stays on the full stage.

The open-surface recession (`data-menu-open`) dims `.stage-band` itself and every `.stage-anchor` outside it (`:not(.stage-band > .stage-anchor)`), so the band chrome recesses with its regions and the regions are not dimmed twice.

The command-line row's chrome (`app-shell.css` `.cmdline`) is a tab-like strip that reads as part of the band: a band-coloured gradient, a hairline gold border on three sides with no bottom border, rounded top corners, and a soft upward shadow. The bar fills the anchor's `--command-line-h` height.

### D2. Tokens
`tokens.css`:
- gains `--band-h: clamp(260px, 27.8vh, 400px)`: 300.24px at 1080, 260px at 900 and 720, 400px at 1440 tall
- deletes `--dock-h`
- sets `--stage-content-bottom: calc(var(--band-h) + var(--command-line-h))`

`--stage-content-bottom` keeps its name and its role: it is the edge every stage surface above the band must clear, and every `SceneBackdrop` caption already derives from it. `--command-line-h` stays 64px (the bar's existing chrome). C5 owns the design's 44px expanded row.

### D3. The command line sits on the message region's top edge
`[data-anchor="command-line"]` gets `left: var(--left-column); right: 33.3333%; bottom: var(--band-h); height: var(--command-line-h)`. That is the row C5 expands and collapses (design §5.5), so C5 changes visibility only and moves nothing.

*Why start at `--left-column`:* the `hud-left` island stack occupies the left column down to the band. Starting the row at the column edge keeps the island anchor and the command row disjoint. Otherwise the island stack would have to stop 64px higher, and at 1280x720 the populated stack would lose that height (see Risks).

*Alternatives rejected:*
- Under the band, at the stage bottom: this removes 64px from the stage. At 1920x1080 with C4b's 48px bar the stage would be 1080 − 48 − 300 − 64 = 668px (61.9%), which breaks the design's 65% goal permanently.
- Inside the message region: the message window's text area would change height when C5 collapses the line, and that area is C6's paging input.

Trade-off: until C5 collapses the line, the row covers the lowest 64px of the stage box over the message column, including the player portrait's feet. The design accepts exactly this for the expanded state ("It overlays the stage, not the text").

### D4. The player portrait anchor
`AppClient.vue` moves `<ReferenceArtwork :portrait="currentPortrait">` from `#backdrop` into a new `#actor-left` slot, forwarded by `AppShell`. It keeps `v-if` not creation, and drops `class="stage-portrait"` in favour of the anchor's rules:

```
[data-anchor="actor-left"], [data-anchor="actor-right"] {
  bottom: var(--band-h);
  height: min(62vh, 680px, calc(100% - var(--header-h) - var(--band-h)));
  aspect-ratio: 2 / 3;
  pointer-events: none;
  z-index: 2;
}
[data-anchor="actor-left"]  { left: 6%; }
[data-anchor="actor-right"] { right: 6%; }
[data-anchor="actor-left"] .reference-artwork { height: 100%; }
```

The third `min()` term clamps the portrait to the stage box. At 1280x720, `min(62vh, 680px)` is 446px but the stage box is 720 − 72 − 260 = 388px, so without the clamp the portrait would pass under the top bar. At 1920x1080 the first term wins (669.6px).

The `.stage-portrait` blocks in `app-shell.css` are deleted: the base rule, `.stage-portrait img` (the horizontal mask moves to the anchor selector), the combat `left: -2%` override, and the 1000px override. The portrait keeps its truthful placeholder (`ReferenceArtwork` is unchanged).

Presentation inside the anchor:
- The portrait image (and the placeholder) carry two intersected masks, soft side edges and a long fade at the feet, so the figure dissolves into the band instead of ending in a hard rectangle.
- The `figcaption` becomes a small left-aligned serif name plate at the figure's lower left, bounded to end before the command-line row starts at `--left-column`. When the placeholder renders, the figcaption is hidden, because the placeholder already states the same label on the figure.

`actor-right` renders an empty anchor, reserved:
- C10 (`webclient-dialogue-stage`) puts the dialogue host's `StageActor` there.
- C13 animates foe portraits there.
- The combat `ParticipantFrame` is a list of numbers and tokens, not a standing portrait, so it stays a HUD island (C4c places it in the top-right `map` anchor, where the minimap is hidden in combat) and leaves `actor-right` free for those later changes.

### D5. Retiring the frame-adaptive band, and fitting frames to the command region
These are deleted from `app-shell.css`:
- the `.elosern-stage { --dock-h; --stage-content-bottom }` override
- the three `:has()` blocks and the two `:has()` `[data-anchor="dock"]` left overrides
- the combat `--dock-h` pair and the combat feed / dock / `hud-left` offset rules (lines under `[data-elosern-mode="combat"] .elosern-stage [data-anchor="feed"]`)
- the dialogue feed height
- `.elosern-root .elosern-stage [data-anchor="feed"]` and `[data-anchor="dock"]`, with their two narrow media blocks
- the creation `[data-anchor="dock"]` override, now handled by D1's one-column grid

`HudFrame.vue`'s `feed` and `dock` rules are deleted with the anchors.

What the command region still needs, all inside the region:
- `.waiting-screen` uses `grid-template-columns: minmax(0, 1fr)` in every viewport. The `(max-width: 1000px)` rule already did this for narrow screens and is folded in.
- `.dock-pane-host.interaction-workspace` keeps its two columns; that is the exploration-menu contract. Its `.interaction-target-grid` (`auto-fit, minmax(min(170px, 100%), 1fr)`) collapses to one column on its own at the region's width.
- Inside `[data-anchor="band-command"]`, the combat skill detail pane (`SkillDetailPane` root, `flex: 1 1 260px; min-width: 220px`) and the generic dock detail (`flex: 0 0 220px`) get `min-width: 0` and a basis of `min(220px, 45%)`. At 1280x720 the region's content width is about 400px, so the row region and the detail pane stay side by side, which the direct-children requirement requires, without horizontal overflow.
- The combat tab-bar rules (`flex-wrap: nowrap`, `flex: 1` tabs, hidden hint) stay.
- The exploration root tab bar inside the region keeps every tab on its first row (`flex: 1 1 0`, centred, `min-width: 0`), and the shortcut hint takes its own right-aligned row (`flex-basis: 100%`). Without this, the fifth tab wraps into the breadcrumb at 1280x720.
- `[data-anchor="band-command"]` is an inline-size container (`container: band-command`). Below 560px of region width (the 1440 and 1280 wide viewports), the combat root's seven tabs stack icon over label, so they keep one row without touching.
- The interaction workspace's target cells keep the router's column count. `DockMenu` sets it as an inline `grid-template-columns` from `gridCols`, and changing the router is out of scope. So the cells compact to the region instead: a 34x40 avatar, smaller gaps, and ellipsized names. The design's "collapses to one column on its own" does not hold for that inline grid. C8c deletes the workspace.
- The waiting frame's router keeps `gridCols: 3` while its cards stack in one column, so ArrowRight moves to the next card, which is now visually below. This keeps the router untouched (Non-Goals). C8b/C8c replace these frames.

The 400x720 case in `test_browser_exploration_tiles.py` pins a roughly 384px outlet pane that only existed through the deleted narrow rule. At 1280x720 the command region's pane is about 400px, so the same last-row invariant is re-pointed there.

### D6. Feed re-home
`AppShell` renders `NarrativeFeed` in `#band-message` with unchanged props and emits. The existing `.elosern-root .elosern-narrative { height: 100%; display: flex; flex-direction: column }` and `.narrative-scroll { flex: 1; min-height: 0; max-height: none }` overrides already make the card fill its host.
- The dialogue variant's rows scroll inside `.narrative-scroll`. The dialogue pin (`offsetTop` against the scroll viewport) is unchanged, so the box is at the top when the picks first render.
- The `(max-height: 780px)` dialogue compaction rules stay.
- The `.elosern-narrative::before` gutter rule (`left: -16px`) now falls into the band's left padding, as it did outside the old caption. Keep it.
- Inside the message region the card uses a slightly lighter vertical gradient and a warm hairline border (`[data-anchor="band-message"] > .elosern-narrative`), so it reads as a window set into the band rather than a second band.

### D7. Mode gating and focus rescue
- HudFrame's creation rule hides `[data-anchor="band-message"]`, `[data-anchor="hud-left"]`, and `[data-anchor="command-line"]`.
- `HIDDEN_BY_MODE.creation` becomes `"[data-anchor='band-message'], [data-anchor='hud-left'], [data-anchor='command-line'], .local-map"`.
- The portrait is not rendered in creation (`v-if`) and has no focusable content, so it needs no rescue entry.

### D8. Surfaces positioned from the band
- `.elosern-root .scene-backdrop` gets `bottom: var(--band-h)`, so the cover crop is the stage box (the "A done scene paints the stage" scenario).
- The scene label, alt text, generating notice, and full-view control in `app-shell.css` switch from `var(--dock-h) + 28vh + …` to `var(--command-line-h) + 28vh + …` (same `28vh` lift). These captions are positioned inside `.scene-backdrop`, whose box now ends at the band's top edge, so they clear only the command-line row that overlays the box's lowest 64px. `var(--stage-content-bottom) + 28vh + …` would count the band twice and push every caption past the box's top edge at all three viewports (1920x1080: 708px offset in a 700px box; 1280x720: 570px in 388px), where `overflow: hidden` would clip it.
- The `app-shell.css` placeholder and caption overrides are written as `.elosern-root .scene-backdrop .scene-backdrop__…` (specificity 0,3,0). Before this change they were `.elosern-root .scene-backdrop__…` (0,2,0) and lost to `SceneBackdrop.vue`'s equally specific base rules, which load later, so the truthful-placeholder card was stretched from `top: 14px` down to the base `bottom` into a large empty box in the middle of the stage. With the override winning, the card is the intended small chip at the top right. `SceneBackdrop.vue`'s base rules keep `--stage-content-bottom`: they only apply standalone, where the backdrop spans the whole stage.
- `ObjectiveTracker.vue` uses `bottom: calc(var(--band-h) + 12px)`. It is on the right, above the command region, which the command row does not cover.
- Drawers and full-screen overlays keep their current bottom inset (`--workspace-bottom` and `OverlayHost`'s `calc(var(--command-line-h) + 12px)`). Stopping them above the band would make a drawer about 310px tall at 1280x720, too short for the inventory and status layouts, and the design keeps drawer presentation unchanged (§3 non-goals). While a drawer or overlay is open, it covers the band and the command-line row. Both stay present in the DOM behind it, as the desktop-shell requirement asks, and closing the drawer returns focus to its opener. `ToastQueue`'s stack is bounded by `--stage-content-bottom`, so a tall stack never covers the band.
- `hud-left` and `hud-right` use `max-height: calc(100% - var(--header-h) - var(--band-h) - 32px)` in every mode, both in `HudFrame.vue` and in `app-shell.css`'s `.elosern-root .elosern-stage [data-anchor="hud-left"|"hud-right"]` overrides (the overrides outrank the component rule, so both must change). The old values were bounded by the command line, not the band, so they would now overlap it.

### D9. Stage height and viewports
The design's "at least 65% of the viewport is stage" is not asserted here. With the unchanged 80px header, the 1920x1080 stage box is 1080 − 80 − 300 = 700px (64.8%). C4b's 48px bar makes it 732px (67.8%) and adds the assertion. This change asserts the band's fixed height and split at 1920x1080 (the design's reference), 1440x900, and 1280x720, and keeps every existing non-overlap check at 1440x900 and 1280x720.

### D10. Spec strategy, traceability, and archive order
- MODIFIED blocks written on top of C3's text:
  - "Surface visibility is gated by the committed game mode"
  - "The command line is a permanently present bar in the stage's command-line anchor"
  - `webclient-desktop-shell` "Required desktop surfaces remain visible and usable"

  C1 and C2 touch none of the requirements this change modifies. The other MODIFIED blocks are written on the main specs.
- Every existing scenario title is kept. `webclient-desktop-shell`'s "A tall frame grows the band without touching the narrative" keeps its title, as `openspec validate` requires, and its body now asserts the opposite: the band keeps its height.
- The dock requirement's subject changes, so it is REMOVED and ADDED as "The action dock fills the band's command region at a fixed size". Its two annotations re-anchor.
- The contextual-hud Purpose paragraph ("the centred floating dock panel") is edited in the main spec at sync.

**Archive order: C1 → C2 → C3 → C4a (this change) → C4b (`webclient-avg-place-card-top-bar`) → C4c (`webclient-avg-stage-hud-anchors`).**
- C4b modifies this change's stage requirement, visibility matrix, and desktop-shell block.
- C4c modifies C4b's texts plus the C1 / C2 / C3 island requirements.
- Both must be archived after this change.

## Risks / Trade-offs

- [The populated `hud-left` stack at 1280x720 must fit above the band] Available height: 720 − 72 − 16 − 260 − 16 = 356px. It was bounded by the command line before (≈ 552px). C3's `test_populated_island_stack_fits_its_anchor_at_both_viewports` injects vitals, a harmful condition, and a two-slot party. → Task 5.3 runs that test first. If it fails at 1280x720, the stack gap drops from 12px to 8px and the party island uses the `(max-height: 780px)` compact cell padding. C4b's 48px bar adds 24px and C4c's compact avatars shrink the party island further.
- [The command row covers the portrait's feet and 64px of the stage until C5] → Accepted and documented (D3). The design specifies this position for the expanded line.
- [The narrow command region at 1280 (≈ 427px) crowds the interaction workspace and the combat master-detail] → D5 keeps both side by side with bounded bases. The row region scrolls, and the fixed-column rule already compresses tracks. `test_browser_combat_menu` and `test_browser_combat_scales` re-run at 1280x720.
- [The dialogue exchange at the 260px band needs scrolling] → The requirement is restated: the reply box stays visible at the top, and the rows scroll inside the caption. C10 replaces this surface.
- [The objective tracker (`.obj`, right, above the band) and the `hud-right` island stack share the right column's lower half, as they did before with the old offsets] → This change keeps their relative placement: `.obj`'s bottom moves from `--dock-h + 60px` to `--band-h + 12px` (272px at 1280x720, against 320px before). Task 5.2's anchor checks include it. C4c moves the tracker into the `map` anchor as one line and removes the shared column.
- [Browser tests reading `anchor-feed` / `anchor-dock`] → Task 5.1 greps `anchor-feed\|anchor-dock\|data-anchor=\"feed\"\|data-anchor=\"dock\"` across `web/tests/browser` and `web/webclient-app/tests` and re-points every hit.

## Migration Plan

None. The client is unreleased, and no stored layout references the anchors.
