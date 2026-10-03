# vitals-bar-redesign — Design

## Context

See proposal.md — Why. The vitals surfaces today are two separate `.hud` islands (`VitalsTrack.vue` header+track rows, `ConditionChips.vue` chips) inside the top-anchored `vitals` anchor, composed by `StatusPanel.vue` under one `v-show` reveal root. The tooltip vocabulary already exists twice in the codebase: `DesktopNavigation.vue` (hover/focus/Escape, `aria-hidden` visual tip duplicating the accessible name) and `InventoryPanel.vue` (a `role="tooltip"` inspector). The condition prose rule is centralized in `lib/condition_label.js::conditionLabel()` and `conditionModifiers()`.

## Goals / Non-Goals

**Goals:**
- One compact bottom-left dock carrying an icon row over three slim bars
- Numerals rendered on the track, not on a header line
- Chromeless condition icons with hover/keyboard tooltips
- Preserve every behavioral contract: visibility rule, reveal/inert transition, focus rescue, trailing-bar memory, epoch reset, 危險 marker, sp texture

**Non-Goals:**
- Changing the party quickbar (owned by `companion-portrait-lineup`)
- Changing the visibility predicate (`vitals.js::isVitalsVisible` unchanged)
- Changing the beat-driven `displayHp` path
- Adding tooltips to anything but conditions

## Decisions

### D1 — Keep the `vitals` anchor name, move its geometry

`[data-anchor="vitals"]` stays the anchor's identity; its CSS moves from `top: …`-anchored to `bottom: var(--band-h); left: 16px * ui-scale; width: var(--vitals-dock-w)` in both HudFrame.vue and the app-shell.css mirror. `--vitals-dock-w` is a new tokens.css size token, `25vw` — a quarter of the viewport, so the three thin lines read as a long instrument and the readout spreads out in one row (viewport-relative, so not multiplied by the chrome factor). Because the dock is wider than the old left column, the command-line row docked on the same band edge now starts past it: `left: calc(var(--vitals-dock-w) + 32px * ui-scale)` (16px gutter past the dock's right edge — the existing browser relation "row left = vitals right + 16" holds unchanged). Keeping the name preserves every `data-anchor="vitals"` test hook, the `HIDDEN_BY_MODE` selector in `AppShell.vue`, the focus-rescue selector, and the mode-hide rules — no renaming cascade. The anchor is bottom-anchored with `max-height: calc(100% - header - band - insets)` so it can never grow over the top band, and keeps z-index 4 (below the band, per the layer order); the band's 28px seam feather lies over the dock's lowest strip, which reads as the dock settling into the band and costs no legibility (verified visually).

**Alternative:** Rename to `vitals-dock`. Rejected — churn across tests/browser journeys for no behavioral gain. **Alternative:** raise the anchor above the band to escape the seam feather. Rejected — it breaks the stage layer order.

### D2 — The gauges: one numeral readout over three thin, tapered lines

(Amended during apply at the user's direction; supersedes "numerals on a compact track".) A 16px track that can carry 12px numerals reads as three stacked boxes; the instrument reads better as **three thin (4px) lines laid almost edge to edge** — parted only by a 1px shadow seam — under **one readout row**. The readout states, in the lines' hp/mp/sp order, each gauge's icon (heart, star, bolt — distinct shapes in the gauge's hue) and its `current / maximum` value: the current value in `--paper-50` at `--text-sm` in the mono face's tabular figures, the maximum receding to `--paper-500` at 10px, with the 危險 marker (a small seal-ruled tag) after the hp value and the hp current value recoloured to `--crit` while low. The visible Traditional Chinese labels are dropped: each reading is a `role="group"` named by its label (生命/魔力/耐力), so assistive technology hears "生命 80 / 100" while the eye reads shape + hue + number. The readings sit as one phrase from the dock's spine (flex-start, 18px apart) and wrap rather than overflow on unusually long values.

The lines are not square bars: each is `clip-path`-tapered to a point at its far end, and mp and sp run 5% and 10% shorter than the line above, so the set fans out like three brush strokes from one hand. The empty ground is a faint paper wash; ghost/fill spans keep their classes, transitions, the 300ms trail delay, `data-instant`, and the epoch rule untouched, and `data-testid="status-panel__gauge--{key}"` stays on each line (browser journeys read `.track .ghost` there). `data-testid="status-panel__gauge-value--{key}"` moves onto the readout's numerals, which stay in the accessibility tree.

### D3 — Icons reuse the DesktopNavigation tooltip pattern, as `role="tooltip"`

Each condition icon is a `<button>` (keyboard-reachable like today's chips) showing only the severity glyph in its severity hue, chromeless; hover, focus, or an open tooltip lifts it to full strength and draws a short brass tick under it. On `mouseenter`/`focus` a single tooltip element (one per row, content-driven) opens above the icon with the condition's label, its verbatim `剩 N 秒` duration, and one line per readable modifier (`conditionModifiers()`), styled as the nav tooltip's ink plate with a gold tick pointing down at the icon. Unlike the nav tip (which duplicates the accessible name and is `aria-hidden`), this tooltip carries information found nowhere else visually, so it gets `role="tooltip"` with `aria-describedby` on the active icon; the icon's `aria-label` still carries the full `conditionLabel()` prose. Escape closes the tooltip and is consumed only while one is open (same guard the nav tools use), then the overflow disclosure, else it falls through.

The `vitals` anchor is an `overflow-y: auto` scroll container and the reveal applies a transform to the dock, so an absolutely- or fixed-positioned tip inside it would be clipped or mis-anchored. The tooltip is therefore teleported to `body`, `position: fixed` from the icon's `getBoundingClientRect()` at open time, and closes on any scroll or resize while open, when its condition stops being committed, or when the dock hides (`StatusPanel` passes its `visible` as the row's `revealed` prop — a hiding dock fires no `mouseleave`).

Overflow keeps the `+N` icon: clicking it discloses the hidden conditions as a bounded (96px) scrolling column in flow, each row the same content as the tooltip, divided by hairlines; the bottom-anchored dock grows upward to hold it. Closing is Escape/re-activation (today's disclosure behavior, restyled chromeless).

### D4 — StatusPanel root keeps the reveal contract; the dock is a feathered instrument plate

`StatusPanel.vue` keeps its `<Transition>` + `v-show` + `inertWhileLeaving` root (`data-testid="status-panel"`) — the visibility predicate, focus rescue, and reveal tests stay green untouched; the reveal travel flips to `+Y` (rising out of the band, sinking back), same names and tokens. Inside, children render `ConditionChips` (chromeless icons) then `VitalsTrack` (readout + lines). Both children are transparent; the dock's chrome is on the root and is deliberately **not a box**: a `::before` ground of `--panel` ink with the backdrop blur, masked so it is densest at the left and thins out towards the right and top edges (the art reads through), and an `::after` brass mounting — the band's own `--band-ornament` lozenge at the top-left corner, a hairline crown running right from it and fading out by ~70%, and a hairline spine running down the left side towards the band. No full border, no radius, no box shadow; every colour is a shared token (`--panel`, `--band-edge`, `--band-edge-dim`, `--band-ornament`). Content stands right of the spine (26px left padding).

### D5 — The 危險 hp-pulse and low vignette hooks are untouched

`isLowHp` still drives `stage[data-lowhp]` and `.vital.low .fill` pulse. The marker text simply relocates onto the row; `data-testid="vitals-low-marker"` moves with it.

### D6 — Anchor-geometry wording and the matrix row land in the chain, not in two halves

The visibility-matrix requirement (last rewritten by `place-card-relocation`) names the row "vitals island (vitals/conditions)". This change's delta does not touch the matrix: its own requirements fully define the dock's per-mode behavior, the row rename to "vitals dock" lands in `companion-portrait-lineup`'s matrix rewrite, and the dialogue cell lands in `hud-dialogue-declutter`. Likewise the full-bleed stage requirement's "vitals anchor sits at the stage box's top-left" sentence is re-anchored to the stage's lower-left in this change's own MODIFIED block, so the anchor's geometry has exactly one definition per change that lands.

## Risks / Trade-offs

- **[Numerals lose contrast on the stage art]** The readout sits on the dock's ink ground, densest at the spine where the readings start; the current value is `--paper-50` with a 1px dark text-shadow and the maximum `--paper-500`, verified in Storybook at full, damaged, low, and empty states and over the populated stage at 1920x1080 and 1280x720.
- **[Readout outgrows one row]** Four-digit values plus the 危險 tag at the 1280px minimum could exceed 25vw. → The readout wraps to a second row instead of overflowing; the dock grows upward within its bounded anchor.
- **[Icon row wraps unpredictably]** 32 conditions can't fit in one row. → Row is capped at six icons plus the `+N` icon; icons are fixed-size (22px), so the row is deterministic at the payload bound; overflow stays reachable.
- **[Dock overlapping the portrait may read as clutter]** The compact dock (icon row, readout, three 4px lines) covers at most the portrait's lowest quarter at 1280x720 and less at 1920x1080; its ground feathers out to the right, so the legs read through it. The interim party quickbar adds height until `companion-portrait-lineup` removes it.
- **[The band's seam feather dims the dock's lowest strip]** The dock keeps z-index 4 below the band (layer order). The feather only deepens the plate's lower edge into the band; the lines and readout stay clear of it in practice (visual check).
- **[Tooltip steals Escape from the band/dock]** → Escape is consumed by the icon row only while a tooltip (or the disclosure) is open (flag-guarded `stopPropagation`), mirroring `onToolKeydown` in `DesktopNavigation.vue`.
- **[Teleported tooltip drifts]** Placed once from the icon's box; any scroll or resize while it is open closes it, and it closes when the dock hides or its condition leaves the payload.
- **[Touch pointers have no hover]** Icons are buttons, so focus (keyboard or touch tap) opens the tooltip. Acceptable for the desktop-first shell.
