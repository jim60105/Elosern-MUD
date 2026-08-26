## Context

The `webclient-hud-01` through `webclient-hud-06` waves each owned a disjoint slice of the contextual
HUD (roadmap §7 file ownership) and each landed green. A cross-wave critique — deliberately looking only
at the seams between waves and between the roadmap-family documents and the shipped code, not
re-verifying any wave's own scope — found three loose ends that no wave's acceptance criteria covered:

1. `#elosern-offline-overlay` (`AppShell.vue:335-349`) is a DOM-ID contract preserved unchanged since
   before the redesign (roadmap §5: "Preserve the DOM contract, re-map the rest"). Its `z-index: 2000`
   predates every full-screen surface the redesign introduced. Four surfaces now sit above it, all
   `position: fixed` with no intervening stacking context: `HudDrawer`'s scrim (`z-index: 2900`) and
   panel (`3000`), `ArtPanel`'s portrait full-view (`3000`), `SceneBackdrop`'s scene full-view (`3000`),
   and `FullLogOverlay` (`3000`). A connection loss while any of these is open is invisible to a sighted
   player — the aria-live region still announces it, but nothing is visible on screen.
2. H6 rewrote `webclient-ui-design.md` §5.1 to describe the new cinematic HUD but kept a sentence
   claiming the stage anchors are resizable — a capability that belonged to the pre-redesign
   GoldenLayout-style three-column layout and was never carried into the HUD. (The rest of that
   paragraph — the layout-version, migration, and reset behavior — is *not* stale: it is still
   implemented by `web/static/webclient/js/elosern/layout_store.js` and loaded by `main.js` on every
   mount, still tested by `web/tests/browser/test_browser_layout.py`, and still required verbatim by
   this same capability's "Browser persistence is versioned and presentation-only" requirement. Only the
   anchor-resizing clause is the orphaned claim.)
3. `webclient-ui-design.md` §5.3 was deliberately left un-superseded by the roadmap (§4: it "retains
   authority over ... the focus model of §5.3"), so no wave had standing to rewrite it. It still
   describes `/` as opening a "command drawer" — language H5 made obsolete when it replaced the
   collapsible drawer with a permanently-visible field.

## Goals / Non-Goals

**Goals:**
- Make the offline overlay visible above every surface a player can have open, with a fix durable
  enough that a future surface doesn't reopen the same gap by picking another ad hoc number.
- Bring `webclient-ui-design.md` §5.1 and §5.3 back into agreement with the shipped client and with the
  OpenSpec capability specs that already describe the correct behavior
  (`webclient-desktop-shell`, `webclient-contextual-hud`).

**Non-Goals:**
- Rearchitecting the full stacking order of every HUD surface (drawer vs. overlay vs. full-view
  relative to *each other*). The store enforces mutual exclusion between the reference-drawer and the
  full-screen-overlay pair specifically (`openHudDrawer` closes the open overlay and vice versa); the
  `ArtPanel`/`SceneBackdrop` full-view states are local component refs with no such store-level guard
  against a drawer or overlay opening at the same time. That is not a defect this change introduces or
  needs to fix: the offline overlay's new `--z-offline` sits far above the shared `--z-surface-modal`
  tier those surfaces already share, so it wins regardless of which of them happen to be open
  simultaneously. Only the order of every surface *relative to the offline overlay* is this change's
  concern; their order relative to each other is unchanged and out of scope.
- Reopening the HUD roadmap or amending its Status/Governance sections. This is a small finalize-class
  fix, not a new wave.
- Implementing anchor resizing. §5.1's stale sentence is removed, not fulfilled.

## Decisions

**D1 — A named z-index scale in `tokens.css`, not a single hard-coded bump.**
The minimal fix is "give the offline overlay a bigger number." But four components already carry the
literal `3000` independently, which is exactly how the current gap happened — a fifth surface added
later would need the same manual reconciliation. Instead:
- Add two tokens to `:root` in `styles/tokens.css`: `--z-surface-modal: 3000` (the shared tier for
  drawer/full-view/full-log — the value already in use, only now named) and `--z-offline: 9000` (a tier
  reserved above every surface tier). The token's comment must note that `OverlayHost.vue` is a
  full-screen surface that deliberately stays outside this tier (at `z-index: 92`, see below) so a
  future maintainer adding a fifth surface isn't misled into thinking the invariant is universal.
- `HudDrawer.vue`, `ArtPanel.vue`, `SceneBackdrop.vue`, and `FullLogOverlay.vue` switch their existing
  `z-index: 3000` declarations to `z-index: var(--z-surface-modal)` — a mechanical rename with the same
  numeric value, so no visual or stacking behavior changes for those four.
- `HudDrawer.vue`'s scrim (`2900`) becomes `calc(var(--z-surface-modal) - 100)` so it keeps sitting one
  layer below the drawer panel without a second unrelated magic number.
- `AppShell.vue`'s `#elosern-offline-overlay` switches from `z-index: 2000` to `z-index: var(--z-offline)`.
- `OverlayHost.vue` (`z-index: 92`) is left untouched. It is not one of the surfaces implicated in the
  gap analysis, the drawer/overlay pair is already mutually exclusive at the store level
  (`openHudDrawer` calls `closeOverlay()` and vice versa), and folding it into the same numeric tier
  buys nothing while adding unrelated risk to a file this change doesn't otherwise need to touch.

Alternative considered: hard-code `z-index: 9000` directly on `#elosern-offline-overlay` and stop there.
Rejected because it fixes today's four surfaces without leaving a documented reason the *next* new
full-screen surface must stay under 9000 — the same silent-drift failure mode the roadmap's own §1
spent a section describing, just at the CSS layer instead of the document layer.

**D2 — Delta-spec the stacking guarantee under `webclient-desktop-shell`'s existing "Connection loss
locks stale controls" requirement, not a new requirement.**
The requirement already owns the offline overlay's behavior end to end (appearance, dismissal,
reconnection). A stacking guarantee is a property of the same overlay, not a new concern — adding a
sentence and a scenario to the existing requirement keeps the capability's requirement count coherent
and avoids a second requirement that would just cross-reference the first.

**D3 — `webclient-ui-design.md` §5.1/§5.3 edits are plain text corrections, not delta specs.**
`webclient-ui-design.md` is a supplementary design reference (roadmap §4 precedence item 4), not an
OpenSpec capability spec under `openspec/specs/`. The actual behavioral contracts for the command line
(`webclient-desktop-shell`'s "Keyboard routing is menu-first and submission-safe" and "The command
drawer preserves ordinary text control" requirements), for browser persistence
("Browser persistence is versioned and presentation-only"), and for the HUD layout
(`webclient-contextual-hud`) already correctly describe the permanent command line, the still-real
layout-version/migration behavior, and the fixed-anchor stage — confirmed by reading all three. Only two
narrow slivers of the design document's prose lag (the anchor-resizing sentence in §5.1, and the
"command drawer" phrasing in §5.3). Fixing them is a documentation task tracked in `tasks.md`, scoped
tightly to those slivers, not a spec delta and not a rewrite of the surrounding paragraphs.

**D4 — The delta spec's new scenarios are covered by a real-browser test, not a jsdom source-text
check.** This bug is a real-DOM paint-order defect: nothing about it is observable in jsdom, which has
no layout or paint engine. A test that only greps component source for `var(--z-surface-modal)` /
`var(--z-offline)` proves the source references the right token names; it cannot prove the browser
actually stacks them correctly, and it would keep passing if some unrelated future change introduced a
stacking context between the offline overlay and the document root (e.g. a `transform`/`filter` on a
shared ancestor) that broke the guarantee without touching any of these token references. `web/tests/
browser/test_browser_reconnect.py` already exercises this exact overlay in a real Playwright-driven
browser and already carries `@covers_requirement("webclient-desktop-shell::connection-loss-locks-
stale-controls")` on a sibling test — `tools/spec_traceability.py` only discovers coverage through that
decorator on `test_*.py` files, so this is also the only place a new scenario here can be tracked at
all. The plan is therefore: add one real-browser test there (open a drawer, disconnect, assert via
`document.elementFromPoint` that the offline overlay — not the drawer — is the topmost element at a
point inside the overlay), carrying the `@covers_requirement` decorator for the modified requirement.
A fast jsdom/unit check (source references the right custom properties; `--z-offline` is numerically
greater than `--z-surface-modal` in `tokens.css`) is still worth keeping as a cheap first line of
defense, but it is a supplement to the real-browser test, not a substitute for it, and does not itself
carry spec-traceability weight.

## Risks / Trade-offs

- **[Risk] Renaming four components' `z-index: 3000` to a shared token could be mistaken for a
  behavior change during review.** → Mitigation: the token's value is `3000`, identical to today's
  literal; the change is a rename, not a renumber, and this design doc states that explicitly so a
  reviewer can verify by diffing the resolved value, not just the source line.
- **[Risk] A future surface still picks an ad hoc z-index above `--z-offline` (9000) if nobody consults
  the scale.** → Mitigation: `--z-offline` is deliberately far above the shared surface tier ordering
  headroom, and the token's own comment in `tokens.css` states the invariant ("nothing else may exceed
  this"), giving the next author something to grep for.
- **[Risk] Editing `webclient-ui-design.md` without a delta spec could look like drift outside OpenSpec
  governance.** → Mitigation: both edits are pure corrections back to documented, already-shipped
  behavior (confirmed against `webclient-desktop-shell` and `webclient-contextual-hud`), not new
  decisions; `tasks.md` records the exact diff intent so the change's own record shows why no delta
  spec applies.

## Migration Plan

No data migration. Deploy is a normal merge: CSS token rename + one new token, four `z-index` literal
swaps, one `AppShell.vue` line, and two doc edits. Rollback is a plain revert; nothing is persisted or
versioned that depends on the old z-index values.

## Open Questions

None outstanding — scope is fully bounded by the three gaps in the proposal.
