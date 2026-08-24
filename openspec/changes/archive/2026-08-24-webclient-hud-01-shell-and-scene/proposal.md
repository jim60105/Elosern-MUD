## Why

This is change **H1** of the WebClient Contextual HUD Redesign, governed by
`docs/superpowers/specs/2026-08-25-webclient-hud-redesign-roadmap-design.md` (depends on: nothing).

The Vue SPA migration shipped every gate green but built `2026-08-02-webclient-ui-design.md` §5.1's
three-column dashboard, not the validated design draft the migration's own §1 named as its motivation
(roadmap §1 traces the four steps that lost the intent). The draft's contribution to the shipped
product is `tokens.css` and the font faces; its layout, information architecture, and — most
importantly — its *contextual HUD* thesis were never built. `data-elosern-mode` is rendered onto the
shell root and no stylesheet selects on it; `--dock-h` and the three motion keyframe sets are defined
in `tokens.css` and referenced by nothing.

H1 lays the foundation the other five waves build on: the cinematic stage, the scene backdrop, the
HUD anchor frame that replaces the CSS grid, and the mode × surface visibility matrix that makes
`mode` load-bearing. It re-homes the existing panels into the new anchors **without changing their own
chrome** (H2–H4 own that), so the client stays fully usable at every landing.

## What Changes

- **New capability `webclient-contextual-hud`** — the mode × surface visibility matrix
  (REDESIGN.md §2), the full-bleed cinematic stage and its scene backdrop, the HUD anchor model that
  replaces fixed layout columns, and the bounded narrative caption card with its full-log escape hatch.
- **The shell root becomes a full-bleed stage.** `AppShell` replaces its
  `grid-template-columns: 300px 1fr 300px` main row with absolutely-positioned HUD anchors
  (`hud-left`, `hud-right`, `dock`, `command-line`, and a lower-centre `feed`), sized from `--dock-h`.
- **A scene backdrop layer** renders behind every surface, driven by the already-allowlisted
  `art.scene` payload: the resolved image when `status` is `done`, and the per-mode gradient stage
  (explore / dialogue / combat) plus the inset vignette otherwise. A missing, pending, or failed asset
  degrades to the gradient — never to an invented image.
- **`data-elosern-mode` becomes load-bearing.** Surface visibility is gated by mode in CSS with
  `display:none` (so hidden surfaces leave the accessibility tree and the tab order), per the matrix in
  the new capability's spec. A `menu-open` state dims the stage behind an open drawer or overlay.
- **The narrative becomes a bounded caption card** — `width:min(880px,90vw)`, `max-height:30vh`,
  blurred panel chrome, anchored above the dock — plus a new **full-log overlay** reachable in one
  action from the card, so the complete stream stays available. `#narrative-unread` and the
  `role="log"` live-region contract are unchanged.
- **The header becomes the top-meta pill** anchored top-right (location · world date/time · connection),
  with the game-name brand preserved as a distinct top-left element so `webclient-login-gate`'s brand
  surface set stays intact.
- **BREAKING (test-facing only):** the shell's layout DOM changes. The preserved contract identifiers
  (`#action-dock`, `#elosern-action-live`, `#elosern-offline-overlay`, `#inputfield`,
  `#narrative-unread`, `data-testid="narrative-feed"`, the `action-*` / `target-*` item keys) are kept
  byte-identical; the browser assertions that target the old column structure are re-mapped in this
  change.

## Capabilities

### New Capabilities

- `webclient-contextual-hud`: the WebClient presents a full-bleed cinematic stage whose surfaces are
  gated by the committed game mode, with a truthful scene backdrop, corner-anchored HUD islands, and a
  bounded narrative caption card whose complete log is reachable in one action.

### Modified Capabilities

- `webclient-desktop-shell`: the required-surfaces requirement is re-expressed for the stage layout —
  the narrative occupies the visual centre and its complete log is reachable in one action (replacing
  "occupies the primary reading area"); the non-closable set narrows to the dock, the narrative and the
  command line; the header requirement is re-expressed as the brand plus the top-meta pill.
- `webclient-art-panel`: the scene is re-expressed as the stage backdrop rather than a bounded 16:9
  panel frame; the truthful-placeholder rule is preserved and strengthened (the degrade target is the
  mode gradient, never an invented image), and the portrait catalog's presentation moves to H3's
  participant frame.
- `webclient-vue-application`: the design-system requirement is re-expressed so the design draft is the
  binding layout reference, not only the token palette.
- `webclient-component-showcase`: adds the redesign-wave manifest rule — the frozen required set may
  grow only through a roadmap wave that ships each new component's story and offline args first, and
  re-freezes at H6. The existing frozen-set requirement is left untouched here; H6 re-states it at the
  final set.

## Impact

- **New:** `web/webclient-app/components/SceneBackdrop.vue`, `HudFrame.vue`, `FullLogOverlay.vue` and
  their Storybook stories + Vitest suites; three new entries in `component-manifest.json` and the
  matching `webclient-component-showcase` frozen-set extension.
- **Modified:** `components/AppShell.vue` (grid → stage + anchors), `components/TopBar.vue`
  (header → brand + top-meta pill), `components/NarrativeFeed.vue` (bounded caption card + full-log
  control), `AppClient.vue` (mount the backdrop and the full-log overlay; slot the existing panels into
  the anchors), `styles/app-shell.css`, `styles/tokens.css` (consume `--dock-h`; add the stage
  gradients as tokens).
- **Re-mapped browser assertions:** `web/tests/browser/test_browser_layout.py`,
  `test_browser_shell.py`, `test_browser_art.py` — the column-structure and `.art-panel__scene-frame`
  selectors move to `data-testid` hooks; every preserved id is asserted unchanged.
- **Preserved / untouched:** the server, all eight presenters, the action allowlist, the OOB envelope,
  `transport.js`, `bridge.js`, `stores/elosern.js`, the preserved `js/elosern/*` logic, the keyboard
  router contract, and the dependency-free text fallback.
- **Not built (no backing read model, roadmap §2.4):** companion strip, event toasts, persistent
  objective tracker. The stage reserves no space for them and the deferred-surface assertion is
  extended to name them.
