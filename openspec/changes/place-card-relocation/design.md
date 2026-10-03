# place-card-relocation — Design

## Context

The stage layout is governed by CSS custom properties and absolute-positioned anchors in `HudFrame.vue`. The `place` anchor is a dedicated div with a fixed height token (`--place-h`), and the `vitals` anchor offsets its `top` by that token. The `map` anchor is a flex-column that stacks islands vertically. Moving the PlaceCard is primarily a slot reassignment and CSS restructure — no server protocol, no store logic, and no new component.

## Goals / Non-Goals

**Goals:**
- Move PlaceCard from `#place` slot to `#map` slot, rendering above the minimap
- Remove the `place` anchor div from HudFrame
- Reclaim the vertical space `--place-h` freed on the left column
- Shrink PlaceCard to the minimap column width with a smaller type step
- Keep the place card visible in combat (while minimap is hidden)

**Non-Goals:**
- Changing the PlaceCard's data flow (locationLabel, timeLabel props unchanged)
- Changing the `map` anchor's column width (stays `calc(230px * var(--ui-scale))`)
- Altering mode visibility rules beyond the anchor change
- Touching the band, portraits, or command-line layout

## Decisions

### D1 — Remove the `place` anchor entirely instead of leaving it empty

The `place` anchor is a dedicated div that exists only for the PlaceCard. An empty anchor wastes a z-index layer and a DOM node. Removing it is cleaner than keeping a vestigial element.

**Alternative:** Keep the anchor for future use. Rejected — adding an anchor back is trivial if needed; dead DOM is not.

### D2 — PlaceCard becomes the first child in the `map` anchor's flex column

The `map` anchor is `display: flex; flex-direction: column; gap: calc(9px * var(--ui-scale))`. Placing PlaceCard as the first slot child means it naturally sits above the minimap, objective line, and other islands. In combat, `display: none !important` on `.local-map` hides the minimap while PlaceCard remains.

**Alternative:** Separate the PlaceCard outside the map anchor but visually adjacent. Rejected — adds layout complexity for no gain; the map anchor's flex column already provides the right stacking and gap.

### D3 — Type step: `--text-xl` → `--text-lg` for location heading

At 230px width, `--text-xl` is too wide for most location names. `--text-lg` is one step down, still visually prominent as a heading. The time line stays at `--text-sm` (already compact). The gold rule between them shortens to `calc(40px * var(--ui-scale))` to fit proportionally.

### D4 — `--place-h` token shrinks, vitals top offset simplifies

The vitals anchor's `top` currently includes `var(--place-h) + 12px`. With the place card gone from the left column, `top` simplifies to `calc(var(--header-h) + var(--stage-inset-y))` — the same formula the map anchor uses. `--place-h` still exists but is smaller (for the narrower card in the map column) and referenced only by the PlaceCard's own `height: 100%` on its flex item.

### D5 — Combat visibility: PlaceCard stays visible, minimap hides

The existing rule `.elosern-stage[data-elosern-mode="combat"] .local-map { display: none !important; }` hides the minimap class specifically, not the whole map anchor. PlaceCard sits in the same anchor but is not `.local-map`, so it stays visible without any new CSS. The combat participant frame renders below it.

## Risks / Trade-offs

- **[Right column taller at short viewports]** The map anchor now holds one more island. At 1280×720 the place card + minimap + objective line must still fit above the band. The place card at `--text-lg` is ~55px; the existing max-height clamp on the map anchor handles overflow with internal scroll. → Mitigated by the card's compact height.
- **[Actor-right face clearing]** The map column's width is unchanged (230px), so the `--actor-right-inset` formula does not change. The place card does not widen the column. → No risk.
- **[Transition animation on location change]** `PlaceCard` uses `<Transition name="place-card">` for the location slide. This is internal to PlaceCard and works regardless of which anchor parents it. → No risk.
