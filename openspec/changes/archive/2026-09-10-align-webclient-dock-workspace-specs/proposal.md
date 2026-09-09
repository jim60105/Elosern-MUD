# Proposal: Align the dock workspace geometry contract with the shipped layout repair

## Why

The `feat/webclient-obsidian-gold` branch shipped a dock workspace geometry
repair (the `dock-layout` verification round) that no main spec records:

1. **Content-adaptive dock height.** The stage derives one `--dock-h` custom
   property and adapts it to the frame the dock carries: non-empty ordinary
   frames keep the base clamp (`clamp(260px, 34vh, 340px)`), the interaction
   workspace raises it (`clamp(300px, 40vh, 390px)`), the three-card waiting
   frame raises it further (`clamp(360px, 46vh, 430px)`), and combat keeps its
   own shorter clamp (`clamp(230px, 29vh, 290px)`). An empty pane host
   collapses the band in two tiers: any mode's empty host — which includes the
   ordinary non-degraded exploration root, whose row region the tab bar alone
   fills — collapses to 144px, and combat's empty host overrides that to
   100px. The narrative feed's position and the dock's height both derive from
   that one property outside combat (each with its own fixed/viewport offsets;
   combat coordinates its feed and dock through its own shorter band plus
   explicit offsets), so feed and dock cannot overlap at any supported
   viewport. No spec states this coupling;
   `webclient-desktop-shell` only says the surfaces are "visible" and the
   earlier wrap/overlap failures were found live, not by spec.
2. **Two-column interaction workspace.** The Interact frame renders as a
   workspace pane (`dock-pane-host.interaction-workspace`): a target-selection
   column carrying the auto-fit target grid, and — once a target is
   selected — an active-target heading plus that target's affordance rows in
   the second column, with the affordance buttons in one full-width column.
   At narrow width the target grid collapses to a single column. The waiting
   and interaction frames also widen the dock anchor to the left HUD column
   edge, because their content does not fit the centred default band. The
   synced `webclient-exploration-menu` dock requirement pins the two-step
   *composition* (select target, then affordances) but not this rendered
   workspace, and no spec mentions the anchor widening.
3. **Bounded dialogue feed.** In dialogue mode the narrative feed grows to its
   own clamp (`clamp(390px, 56vh, 540px)`) so the host, the line, the two
   choice rows, the free-form input and the exit control all stay reachable
   at 1280x720 — the live requirement that drove the repair.

All behavior is already shipped and verified (pointer selection, Enter/Space
target switching, vertical action-key navigation, exit visible at 1280x720 at
1568x806, 1280x720, and 1440x900). This change records the contract; it edits
no code.

## What changes

- `webclient-desktop-shell`: MODIFIED `Required desktop surfaces remain
  visible and usable` — adds the single-`--dock-h` coupling sentence (the
  content-adaptive band, the feed anchored above it, pane-internal scrolling,
  the bounded dialogue feed) plus three scenarios: tall frames grow the band
  without overlap, a tall pane scrolls inside itself with the breadcrumb and
  tab bar fixed, and the dialogue mode feed stays bounded at 1280x720.
- `webclient-exploration-menu`: MODIFIED `The exploration dock is
  keyboard-first and re-homes the service submenus` — the interact step gains
  the rendered workspace clause (target column left, selected target's
  heading + single-column affordance rows right, single-column collapse at
  narrow width, anchor widened for the workspace and waiting frames) with one
  added scenario.

## Out of scope

- Gallery face-rect consumption and the ReferenceArtwork/participant-frame
  crop — `align-gallery-art-consumption-specs`.
- The three-operation waiting frame and `explore.practice` — already synced
  into `webclient-exploration-menu` by the archived
  `align-webclient-waiting-practice-specs`.
- Top navigation bar, gold theming, and root projection filtering — already
  synced by the archived `align-webclient-shell-theme-navigation-specs`.
- Exact clamp pixel values are named as the shipped implementation's choice;
  the requirements pin the observable properties (ordering of band sizes,
  non-overlap, internal scroll), not the constants.

## Managed-browser evidence status (recorded at archive 2026-09-10)

The standing managed row for this requirement's geometry family is
`test_no_stage_anchor_overlaps_at_supported_viewports`
(`web/tests/browser/test_browser_layout.py`), which asserts stage-anchor
non-overlap at 1440x900 and 1280x720. No dedicated managed row yet (a) grows
the band with a tall frame (interaction workspace / waiting cards) and asserts
feed clearance, (b) scrolls the pane host to a last row while the tab bar and
breadcrumb stay fixed, or (c) bounds the dialogue caption at 1280x720. These
three new scenarios were verified live in the dock-layout repair round; their
managed-row coverage is the requirement's open evidence gap and should be
closed by a future browser-suite change rather than retrofitted here.
