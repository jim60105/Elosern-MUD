# vitals-bar-redesign

## Why

The left island column spends most of its vertical space on the vitals stack (a header row plus a track per gauge, plus a separate conditions island), while the stage's lower-left area sits empty. The vitals are glanceable cockpit data: they belong docked at the stage's bottom edge over the actor's feet, compact enough to read in one saccade. The conditions island's panel chrome costs another window for a handful of transient effects whose names are noise until hovered.

## What Changes

- The vitals island (hp/mp/sp tracks) moves from the top-left `vitals` anchor to a stage-bottom dock: the left gutter, standing on the band's top edge at the bottom of the stage box. It is now the stage's only left-column island.
- Each gauge becomes one compact bar: the label icon stays at the left end, the `current / maximum` numerals move from the trailing header row onto the bar itself, and the vertical gap between the three bars shrinks so the window occupies a fraction of its former height. The 危險 low-HP text marker moves onto the bar with the numerals; the trailing (ghost) damage bar, epoch reset rule, and the non-colour sp texture are unchanged.
- The conditions island's background window (`status-panel__conditions`, the bordered chip island) is removed. Active conditions render as standalone chromeless icon glyphs in a row directly above the vitals dock — no panel, no header, no labels. Each icon shows its severity glyph only; hovering or focusing it opens a tooltip carrying the full label, duration, and readable modifiers (the content of today's chip accessible name). Overflow past the row's width collapses into a `+N` icon that discloses the same tooltip list.
- The island-visibility rule (combat / low HP / vital below maximum / attention-severity condition) is unchanged and gates the whole bottom dock (bars plus icon row) exactly as it gates the island today, including the fade-and-slide reveal, focus rescue, and trailing-bar memory while hidden.
- The `vitals` anchor is redefined as a bottom-anchored stage dock (`data-anchor="vitals"` keeps its name, moves its geometry). The player's standing portrait may be slightly overlapped by the dock's lower edge (the dock paints above the portrait, which is already true by layering); the portrait keeps its full height and standing line.

## Capabilities

### New Capabilities

_None._

### Modified Capabilities

- `webclient-contextual-hud`: the island-stack requirement redefines the left anchor as the stage-bottom vitals dock (and, with `place-card-relocation` landed, leaves the vitals dock as its only content); the vitals-row requirement moves the numerals onto the bar and tightens the vertical rhythm; the condition-chips requirement becomes a chromeless hover/keyboard tooltip icon row above the dock; the visibility-matrix cell for the vitals island names the dock; the transition requirement's reveal applies to the dock.

## Impact

- `web/webclient-app/components/HudFrame.vue`: `[data-anchor="vitals"]` geometry moves from a top-left top-anchored column to a bottom-anchored left-gutter dock standing on the band's top edge; the anchor's scroll rules and `max-height` shrink to the compact dock's own bound.
- `web/webclient-app/components/VitalsTrack.vue`: row structure collapses from a header line + track to one bar carrying icon, numerals, and 危險 marker; gap/padding tokens shrink.
- `web/webclient-app/components/ConditionChips.vue`: drop the `.hud` island chrome and the `狀態` header; chips become icon-only buttons in a wrapping row; add the shared tooltip pattern (hover + focus + Escape, like `DesktopNavigation.vue`) carrying `conditionLabel()` prose; keep the `+N` overflow disclosure.
- `web/webclient-app/components/StatusPanel.vue`: stacks the icon row above the bars inside the dock root (reveal/inert/focus-rescue contract unchanged).
- `web/webclient-app/AppClient.vue`: `#vitals` slot composition updated (`PartyStrip` removal is owned by `companion-portrait-lineup`; this change keeps it below the stack until then).
- `web/webclient-app/styles/app-shell.css`, `tokens.css`: mirrored anchor geometry; new compact gap token if needed.
- Tests/stories: `status_panel.test.js`, `condition chips tests`, `scene_transitions.test.js`, `VitalsTrack.stories.js`, `ConditionChips.stories.js`, `StatusPanel.stories.js`, browser vitals journeys, `component-manifest.json` story titles unchanged.
