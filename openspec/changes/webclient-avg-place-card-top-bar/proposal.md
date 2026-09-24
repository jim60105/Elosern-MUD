## Why

The AVG stage design (`docs/superpowers/specs/2026-09-23-webclient-avg-stage-redesign-design.md` §3, §4, §5.1, §5.2, §5.4) sets a 48px top bar and a stage of at least 65% of the viewport height at 1920x1080. After C4a (`webclient-avg-stage-shell`), the 80px header leaves a 700px stage (64.8%).

The top bar also carries three things the design moves or removes:
- a `探索` / `戰鬥` entry that names the screen the player is already on
- the location and time labels, which truncate the character switcher
- a duplicate location in the stage's `.scene-heading` (eyebrow `探索伊洛瑟恩`, location, time) floating over the backdrop

The design puts location and game time on a place card at the stage's top-left. This change slims the top bar, removes the home entry, and adds the place card, which replaces both the top-meta labels and `.scene-heading`. The project is unreleased, so the retired code is deleted, not hidden.

## What Changes

- **48px top bar.**
  - `styles/tokens.css`: `--header-h` becomes `48px`. The `(max-width: 1350px)` override in `styles/app-shell.css` no longer sets it; the column overrides stay.
  - The brand becomes one row: the `ELOSERN` wordmark plus `伊洛瑟恩`. The login-gate brand surface keeps the game name, and the long tagline tail `文字構築的另一個世界` is dropped.
  - `DesktopNavigation` buttons lay out icon and label in a row.
- **BREAKING (internal)**: remove the home entry.
  - `components/DesktopNavigation.vue` deletes the first button (`探索` / `戰鬥` with `aria-current="page"` when no drawer is open) and the `home` emit.
  - `composables/use-dock.js` deletes `onNavigateHome`, and `AppClient.vue` drops `@home` and the destructured name.
  - Escape and the dock's back controls stay the way back to the root.
- **BREAKING (internal)**: `components/TopBar.vue` loses the `locationLabel` / `timeLabel` props, the `meta-loc` (`topbar-location`) and `meta-clock` (`topbar-clock`) spans, and their separators. The top-meta keeps only the connection state (`connection-state`).
- New component `components/PlaceCard.vue` (`data-testid="place-card"`).
  - It renders the location heading (`place-card__location`) and the world time (`place-card__time`) with the `位置：--` / `時間：--` placeholders.
  - It is fixed height, truncates with the full text as accessible text, uses island chrome, and is display-only.
  - `AppShell.vue` renders it in a new `place` anchor from its existing `locationLabel` / `timeLabel` props. The store's location resolution (`statusSlice.locationLabel`) is unchanged.
- `components/HudFrame.vue`:
  - adds the `place` anchor (`data-anchor="place"`, testid `anchor-place`, slot `place`) at the stage box's top-left, height `var(--place-h)` (new token, 68px)
  - moves `hud-left` below it
  - hides `place` in creation
  - `AppShell.vue` adds `[data-anchor='place']` to `HIDDEN_BY_MODE.creation`
- **BREAKING (internal)**: delete `.scene-heading`.
  - Remove its `#backdrop` block from `AppClient.vue`.
  - Remove all its rules from `app-shell.css`: base, eyebrow, `h1`, `p`, the two combat rules, and the 1350px / 1000px overrides.
  - Remove the now-dead top-meta `meta-loc` / `meta-clock` rules.
- Manifest governance (C3 named the AVG series a governed wave): `web/webclient-app/component-manifest.json` adds `Core/PlaceCard`, with the story `stories/Core/PlaceCard.stories.js` and the showcase spec entry.
- Spec deltas:
  - The stage requirement gains the `place` anchor, the 48px top band, and the 65% stage rule.
  - The visibility matrix gains the place-card row.
  - A new place-card requirement takes over the location-resolution rule.
  - The desktop-shell requirement moves location and time from the top-meta to the place card and forbids the home entry.
  - The showcase enumeration names the place card.
- No OOB schema, presenter, server, store, or persistence change.

Out of scope:
- The `vitals` / `map` anchors that replace `hud-left` / `hud-right`, the one-line objective tracker, compact party avatars, and `TitleBallotMenu` / `ParticipantFrame` placement are owned by `webclient-avg-stage-hud-anchors` (C4c).
- Collapsing the command line is owned by C5 (`webclient-collapsible-command-line`).
- Place-card motion (the slide-in on a location change) is owned by C11 (`webclient-motion-layer`).

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `webclient-contextual-hud`:
  - MODIFIED "The WebClient renders a full-bleed cinematic stage with anchored HUD surfaces", on C4a's text: the `place` anchor, a 48px top band without location or time, and the 65% stage box at 1920x1080.
  - MODIFIED "Surface visibility is gated by the committed game mode", on C4a's text: the place-card row.
  - ADDED "The place card names the current location and the world time".
- `webclient-desktop-shell`: MODIFIED "Required desktop surfaces remain visible and usable", on C4a's text:
  - the top-meta carries only the connection state
  - location and time live in the place card
  - the bar carries no 探索 / 戰鬥 entry
  - the top bar is 48px
- `webclient-component-showcase`: MODIFIED "Every required UI component is a Vue SFC with a documented Storybook story", on C3's text: the manifest names the place card.

## Impact

- New files:
  - `web/webclient-app/components/PlaceCard.vue`
  - `stories/Core/PlaceCard.stories.js`
  - `tests/place_card.test.js`
  - `tests/desktop_navigation.test.js`
- Edited client code:
  - `components/TopBar.vue`, `DesktopNavigation.vue`, `HudFrame.vue`, `AppShell.vue`
  - `web/webclient-app/AppClient.vue`, `composables/use-dock.js`
  - `styles/tokens.css`, `styles/app-shell.css`, `component-manifest.json`
- Edited stories: `stories/Core/TopBar.stories.js`, `stories/Core/DesktopNavigation.stories.js`, `stories/Core/HudFrame.stories.js`.
- Vitest: `tests/top_bar.test.js`, `tests/app.test.js`, `tests/overlays/deferred_surfaces_absent.test.js`.
- Python evidence:
  - `web/webclient/tests/test_vue_showcase_{action,data,world,overlays}_evidence.py` (manifest snapshots)
  - `web/webclient/tests/test_node_suite_evidence.py` (a place-card suite)
- Browser tests:
  - `web/tests/browser/test_browser_shell_surfaces.py` (location / time moves to the place card)
  - `test_browser_contextual_hud_stage.py` (a 65% stage / 48px band test)
  - `test_browser_contextual_hud_anchors.py`, `test_browser_layout.py`, `test_browser_contextual_hud_drawers.py` (`anchor-place` joins the anchor lists)
  - `.github/browser-shards.json`
- Spec traceability:
  - No requirement is renamed or removed.
  - The new ID `webclient-contextual-hud::the-place-card-names-the-current-location-and-the-world-time` is covered by the node-suite evidence test and the browser test.
- Dependencies:
  - Archive order C1 → C2 → C3 → C4a → C4b (this change) → C4c.
  - This change's contextual-hud and desktop-shell blocks are written on top of C4a (`webclient-avg-stage-shell`), and its showcase block on top of C3 (`webclient-retire-redundant-hud`). It must be archived after both.
  - C4c builds on this change's stage and visibility texts.
