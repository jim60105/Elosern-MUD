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

`[data-anchor="vitals"]` stays the anchor's identity; its CSS moves from `top: …`-anchored to `bottom: var(--band-h); left: 16px * ui-scale; width: 262px * ui-scale;`. Keeping the name preserves every `data-anchor="vitals"` test hook, the `HIDDEN_BY_MODE` selector in `AppShell.vue`, the focus-rescue selector, and the mode-hide rules — no renaming cascade. The anchor is bottom-anchored with `max-height: calc(100% - header - band - insets)` so it can never grow over the top band.

**Alternative:** Rename to `vitals-dock`. Rejected — churn across tests/browser journeys for no behavioral gain.

### D2 — The bars: one row per gauge, numerals absolutely positioned on the track

New row anatomy: `grid-template-columns: auto auto 1fr` collapsing to a single visual line — icon + label, then the track filling the rest; the numerals sit inside the track element as an overlay span (`inset: 0; display:flex; align-items:center; justify-content:flex-end; padding-right: 6px`), text-shadowed and with a subtle dark text plate so they stay legible over the red/blue fill and over the empty ink ground. The 危險 marker renders right after the label, same line. Row height drops to the track height (~10px) + the compact gap token. Ghost/fill spans keep their existing classes, transitions, and `data-instant` rule untouched — the numerals overlay is `pointer-events: none; aria-hidden` on the visual copy while the accessible values stay on the row's accessible text.

The numerals must stay in the accessibility tree: the overlay span carries no `aria-hidden` (it IS the numeral content), matching the old `.num` span. `data-testid="status-panel__gauge-value--hp"` moves onto it so browser journeys keep their hooks.

### D3 — Icons reuse the DesktopNavigation tooltip pattern, as `role="tooltip"`

Each condition icon is a `<button>` (keyboard-reachable like today's chips) showing only the severity glyph. On `mouseenter`/`focus` a single tooltip element (one per row, content-driven) opens next to the icon with the `conditionLabel(condition)` prose. Unlike the nav tip (which duplicates the accessible name and is `aria-hidden`), this tooltip carries information found nowhere else visually, so it gets `role="tooltip"` with `aria-describedby` on the icon; the icon's `aria-label` still carries the full prose so AT users get it without hovering. Escape closes the tooltip and is consumed only while one is open (same guard the nav tools use).

Overflow keeps the `+N` icon: clicking it discloses the hidden conditions as a bounded column of the same tooltips, closing on Escape/re-activation (today's disclosure behavior, restyled chromeless). The tooltip surfaces live in normal flow-adjacent absolute boxes within the dock; the dock's own z-index (4) keeps them above the portrait.

### D4 — StatusPanel root keeps the reveal contract; internal order flips to icons-over-bars

`StatusPanel.vue` keeps its `<Transition>` + `v-show` + `inertWhileLeaving` root (`data-testid="status-panel"`) — the visibility predicate, focus rescue, and reveal tests stay green untouched. Inside, children render `ConditionChips` (now chromeless icons) then `VitalsTrack` (bars). The dock chrome (panel fill/blur/border) moves from the two child islands to the `StatusPanel` root only; children become transparent.

### D5 — The 危險 hp-pulse and low vignette hooks are untouched

`isLowHp` still drives `stage[data-lowhp]` and `.vital.low .fill` pulse. The marker text simply relocates onto the row; `data-testid="vitals-low-marker"` moves with it.

### D6 — Anchor-geometry wording and the matrix row land in the chain, not in two halves

The visibility-matrix requirement (last rewritten by `place-card-relocation`) names the row "vitals island (vitals/conditions)". This change's delta does not touch the matrix: its own requirements fully define the dock's per-mode behavior, the row rename to "vitals dock" lands in `companion-portrait-lineup`'s matrix rewrite, and the dialogue cell lands in `hud-dialogue-declutter`. Likewise the full-bleed stage requirement's "vitals anchor sits at the stage box's top-left" sentence is re-anchored to the stage's lower-left in this change's own MODIFIED block, so the anchor's geometry has exactly one definition per change that lands.

## Risks / Trade-offs

- **[Numerals over bright fills lose contrast]** The hp fill is a saturated gradient. → The overlay carries a 1px dark text-shadow plus a right-edge ink plate (gradient fade inside the track), verified at full fill (numerals sit over fill) and at empty fill (over the ink ground). Both states are already Storybook stories.
- **[Icon row wraps unpredictably at 262px]** 32 conditions can't fit in one row. → Row is capped to the width with the `+N` icon; glyphs are fixed-size (16px), so wrap is deterministic at the payload bound; overflow stays reachable.
- **[Dock overlapping the portrait may read as clutter]** Mitigated by limiting the overlap to the feet strip: the dock's top is `min(compact content height, 22vh)` above the band while the portrait is ≥55vh tall, so the covered fraction is small; the portrait keeps `z-index` below the dock (already true).
- **[Tooltip steals Escape from the band/dock]** → Escape is consumed by the icon row only while a tooltip is open (flag-guarded `stopPropagation`), mirroring `onToolKeydown` in `DesktopNavigation.vue`.
- **[Touch pointers have no hover]** Icons are buttons, so focus (keyboard or touch tap) opens the tooltip; a tap focuses the button, which opens it. Acceptable for the desktop-first shell.
