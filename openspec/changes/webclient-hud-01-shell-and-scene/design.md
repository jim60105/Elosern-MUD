## Context

The shipped `AppShell` is a four-row CSS grid whose middle row is
`grid-template-columns: minmax(0,300px) minmax(0,1fr) minmax(0,300px)`. Every data panel is a boxed
`<aside>` stacked inside one of the two scrolling side columns; the narrative fills the centre column;
the dock is a full-width row beneath. Nothing is layered, nothing is blurred, nothing is anchored, and
`data-elosern-mode` — rendered on the shell root since B1 — is selected by no rule anywhere in the
codebase.

The design draft (`docs/design/elosern-redesign/index.html`) is architecturally different, not
stylistically different: `.game{position:fixed;inset:0}` is a stage; `.scene` is a full-bleed backdrop
at `z-index:0`; the HUD is a set of absolutely-positioned islands at `z-index:4`; the narrative is a
lower-centre caption card at `z-index:3`; the dock floats at `z-index:5`; the command line sits at
`z-index:6`. Mode is the primary visibility axis (`.mode-explore` / `.mode-dialogue` / `.mode-combat`),
and `menu-open` dims the stage behind drawers.

H1 changes the *container*. It deliberately does not change any panel's own chrome — H2 owns the
status islands, H3 the dock, H4 the drawers — so this change is reviewable as "the frame moved" and
the client remains fully operable the whole time.

Constraints inherited from the roadmap: no server or protocol change; preserve the DOM contract
identifiers; every surface backed by a real read model or absent; both 1440×900 and 1280×720 supported.

## Goals / Non-Goals

**Goals**

- Replace the layout container with the draft's stage + anchor model, at parity of function.
- Make `mode` load-bearing with one attribute and CSS-only gating.
- Render the scene backdrop from the existing `art.scene` payload, truthfully.
- Bound the narrative and give it a complete-log escape hatch so nothing becomes unreachable.
- Leave every panel's internal markup and every preserved identifier untouched.

**Non-Goals**

- Panel chrome (H2), dock chrome (H3), drawers (H4), command line and overlays (H5).
- Any new read model. No companion strip, toast queue, or objective tracker.
- Layout persistence/resizing. The draft has no user-resizable panels; the stage anchors are fixed.

## Decisions

### D1 — Stage + anchors, not a grid with absolute children

`AppShell`'s root becomes `position:relative; inset:0; overflow:hidden` with children positioned
against it. Anchors are named slots (`hud-left`, `hud-right`, `feed`, `dock`, `command-line`) rather
than free-form absolute positioning by each panel, so a later wave adds a surface by filling a slot,
not by inventing coordinates.

*Alternative rejected:* keeping the grid and overlaying only the backdrop. That preserves the column
scroll traps (today half the left column is below the fold) and cannot express "the minimap disappears
in combat" without leaving a grid gap.

### D2 — Mode gating is CSS on one attribute, using `display:none`

`data-elosern-mode` on the shell root is the only mode selector. Hidden surfaces use `display:none` so
they leave the accessibility tree and the tab order — REDESIGN.md §0.1's "不顯示的絕對隱藏（不是灰掉）"
is an accessibility requirement, not a visual one. A dimmed-but-focusable surface would keep stale
controls reachable by keyboard during combat, which the current keyboard router does not expect.

*Alternative rejected:* `v-if` gating in `AppClient`. It would scatter the matrix across a dozen
conditions instead of expressing it once, and it re-mounts components on every mode flip (losing
scroll position and focus).

### D3 — The backdrop is a component over the existing `art.scene` payload

`SceneBackdrop.vue` reads the already-allowlisted `art` panel and keeps every existing truth rule,
only changing where the pixels land:

- `scene.status === "done"` with a `url` → render the image, `object-fit:cover`, behind the vignette.
- `pending` **with a prior image already rendered** → retain that prior image visibly dimmed and keep
  the explicit `目前場景圖片生成中` label — the existing "never silently present old art as current"
  rule, unchanged.
- `missing` / `failed` / invalid / `pending` without a prior image / panel `available:false` → render
  the per-mode gradient stage only, with the truthful placeholder label as text.

The gradient is therefore the *always-correct* base layer, not a fallback that can fail, and a
degraded OOB channel is visually indistinguishable from an ungenerated scene — it never shows a broken
frame. The scene's `alt`, its label and the placeholder label stay **outside the bitmap** as text on
the stage, so the "no required information exists only inside an image" rule survives the move.

*Alternative rejected:* keeping `ArtPanel` as a boxed panel and adding a separate backdrop. Two
surfaces would consume the same payload with different truth rules, and the "truthful placeholder"
requirement would have two owners.

### D4 — The narrative is bounded, with the full log one action away

The caption card takes `width:min(880px,90vw); max-height:30vh` per the draft. This is a real
reduction in visible log, so the card carries a `完整日誌` control that opens `FullLogOverlay` — a
full-screen, scrollable, focus-trapped view of the same `store.narrative` array. The overlay reuses
`narrative-renderer.js` unchanged, so there is one renderer and no second markup path.

The existing `#narrative-unread` indicator, its polite live region, and the jump-to-latest behaviour
are unchanged and continue to live on the card.

This is the requirement that most visibly contradicts the current spec text ("the narrative log SHALL
occupy the primary reading area"). The `MODIFIED` delta re-expresses it as *the visual centre of the
stage* plus *the complete log reachable in one action* — the intent (the narrative is the authoritative
surface and nothing is lost) is preserved; the geometry is not.

### D5 — The header splits into brand + top-meta pill

`webclient-login-gate` requires the game name on the top bar. The draft has no title bar — it has a
top-right meta pill (location · day · coin). H1 keeps a top-left brand element carrying 「伊洛瑟恩」
and moves location / world time / connection state into the top-right pill. Both are anchors on the
stage, so the brand-surface set (connect overlay, top bar, page `<title>`) stays complete.

The wallet is deliberately **not** added to the pill in H1: it lives in the `character` panel and its
presentation belongs with H2's island stack.

### D6 — Preserved-identifier list is frozen before any DOM moves

Before touching `AppShell`, the change records the identifiers it must not move — `#action-dock` (with
its `data-mode`, `tabindex` and listbox composite role), `#elosern-action-live`,
`#elosern-offline-overlay`, `#inputfield`, `#narrative-unread`, `data-testid="narrative-feed"`,
`data-testid="command-drawer"`, `data-testid="action-dock"`, and the `action-*` / `target-*` item keys
— and adds a test that asserts each is present after the restructure. Everything else re-maps to
`data-testid` in this same change, per roadmap §5.

### D7 — Motion is token-gated; the low-HP vignette waits for H2

The stage's vignette and the `menu-open` dim use `--motion-base`/`--ease-standard`. The red low-HP
vignette and the combat pulse are *driven by* HP state, which is H2's island work; H1 ships the CSS
hooks (`[data-lowhp="true"]`, `elosern-combat-pulse` bound to the combat stage) and H2 supplies the
state. Splitting it this way keeps H1 free of any `status` payload dependency.

## Risks / Trade-offs

- **A 30vh caption card is a large reduction in visible narrative, and the server currently emits raw
  telnet text (room description, exit list, ASCII map) into it.** → D4's full-log overlay; the card
  never truncates without the escape hatch. Curating the emitted prose is a server-side follow-up the
  roadmap explicitly places out of scope — this change must not compensate by filtering the stream.
- **Absolutely-positioned islands can overlap at 1280×720.** Measured against the draft: the left
  stack ends at y=474, the dock begins at y=515 — a 41px margin that shrinks as the island stack grows.
  → H1's browser acceptance asserts no HUD anchor overlaps the dock, the feed, or the command line at
  **both** supported viewports, and the assertion is re-run by every later wave.
- **`display:none` mode gating can hide a surface that owns focus.** → The shell moves focus to
  `#action-dock` before applying a mode change that hides the focused surface, reusing the existing
  focus-restore path rather than adding a second one.
- **Re-mapping `.art-panel__scene-frame` breaks selectors pinned in spec text, not just tests.** → The
  `webclient-art-panel` `MODIFIED` delta re-expresses those requirements in the same change that moves
  them, so no window exists where the spec and the DOM disagree.
- **Scope creep into H2–H5.** → The file-ownership table (roadmap §7) makes `StatusPanel`, `LocalMap`,
  `ActionDock`, the drawers and the command line off-limits here; H1 only re-parents them.

## Migration Plan

0 released users, so there is no data migration. Any persisted layout structure from the grid era is
version-reset rather than migrated (`webclient-desktop-shell`'s existing versioned-persistence rule).
Rollback is `git revert` of the change: the preserved identifiers are unchanged, so the store, the
bridge, the keyboard router and the transport are untouched by a revert.

## Open Questions

None blocking. Two deferred to their owning wave: whether the top-meta pill shows the wallet (H2, with
the character island) and whether the full-log overlay gains a filter control (H5, with the overlay
family).
