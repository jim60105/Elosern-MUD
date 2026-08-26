## Why

A post-hoc critique of the completed `webclient-hud-01` through `webclient-hud-06` waves
(`docs/superpowers/specs/2026-08-25-webclient-hud-redesign-roadmap-design.md`) looked specifically at
the seams *between* waves and between the roadmap-family design documents and the shipped code — not at
any single wave's own implementation, which was already independently validated. It found three small,
concrete gaps that fell through the cracks precisely because each wave owned its own slice and no wave's
acceptance criteria covered the intersection with a pre-existing or sibling-wave contract:

1. The pre-existing, "preserved unchanged" `#elosern-offline-overlay` DOM contract sits at a lower
   z-index than four full-screen surfaces the HUD redesign introduced or left in place, so a
   disconnect that happens while any of those surfaces is open is invisible to a sighted player.
2. H6's rewrite of `webclient-ui-design.md` §5.1 kept a leftover sentence from the pre-redesign
   three-column/GoldenLayout layout claiming the stage anchors are resizable — a capability the shipped
   cinematic HUD does not have. (The rest of that paragraph, describing the still-real layout-version
   persistence and migration behavior, is accurate and stays.)
3. `webclient-ui-design.md` §5.3 (deliberately left un-superseded by the roadmap, so still binding)
   still describes `/` as opening a "command drawer" — the collapsed, openable control H5 replaced with
   a permanently-visible field that has no open/closed state at all.

None of these is a defect in any individual `webclient-hud-0N-*` proposal's own scope. They are
finalize-class gaps at the boundaries the roadmap didn't assign to anyone, and they should be closed
before the HUD redesign is considered fully settled.

## What Changes

- Raise `#elosern-offline-overlay` (`web/webclient-app/components/AppShell.vue`) above every other
  full-screen surface introduced or retained across H1–H6, so a connection-loss notice is always the
  topmost visible layer regardless of what the player had open. Introduce a single documented z-index
  scale in `styles/tokens.css` that the offline overlay and the four affected surfaces (`HudDrawer`'s
  scrim/panel, `ArtPanel`'s portrait full-view, `SceneBackdrop`'s scene full-view, `FullLogOverlay`)
  consume, rather than leaving each surface's magic number to be reconciled by hand again next time.
- Remove only the stale "players may resize the stage anchors" sentence from
  `docs/superpowers/specs/2026-08-02-webclient-ui-design.md` §5.1 — no component implements anchor
  resizing. The rest of that paragraph (the layout-version, migration, and reset behavior) stays: it is
  still implemented by `web/static/webclient/js/elosern/layout_store.js` and `main.js`, still tested by
  `web/tests/browser/test_browser_layout.py`, and still required, unchanged, by this same capability's
  own "Browser persistence is versioned and presentation-only" requirement — only the anchor-resizing
  clause was ever superseded by the HUD redesign.
- Reword `docs/superpowers/specs/2026-08-02-webclient-ui-design.md` §5.3 to describe the command line's
  actual, shipped focus behavior (a permanently-present field that `/` moves focus into) instead of the
  pre-H5 "command drawer" language, without changing any actual behavior — the OpenSpec capability specs
  (`webclient-desktop-shell`, `webclient-contextual-hud`) already describe this correctly; only the
  supplementary design document text is stale.
- **BREAKING**: none. This is a visual z-index adjustment and two documentation corrections; no
  component API, protocol message, or DOM contract identifier changes.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `webclient-desktop-shell`: the "Connection loss locks stale controls" requirement gains an explicit
  stacking guarantee — the offline overlay SHALL render above every other open surface (drawer,
  full-screen overlay, or full-view), not merely "non-dismissible" in the DOM.

## Impact

- **Code**: `web/webclient-app/components/AppShell.vue` (offline overlay z-index),
  `web/webclient-app/styles/tokens.css` (new z-index scale tokens), and
  `web/webclient-app/components/HudDrawer.vue`, `ArtPanel.vue`, `SceneBackdrop.vue`, `FullLogOverlay.vue`
  (consume the shared scale in place of their existing ad hoc `z-index: 3000`/`2900` literals — same
  numeric values, no visual change). `OverlayHost.vue` is untouched — out of scope, see design.md D1.
- **Docs**: `docs/superpowers/specs/2026-08-02-webclient-ui-design.md` §5.1 and §5.3 (text-only
  corrections; no normative meaning changes since the OpenSpec capability specs already reflect the
  correct behavior).
- **Tests**: a new real-browser assertion (extending `web/tests/browser/test_browser_reconnect.py`,
  which already exercises the offline overlay) that the overlay is the actual topmost element at the
  browser level while a drawer/overlay/full-view is open, plus a fast source-level unit check that every
  affected surface's CSS references the shared z-index tokens.
- **No protocol, read-model, or component-inventory changes.** `component-manifest.json` stays frozen at
  40; no new component is added.
