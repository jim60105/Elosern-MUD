## Context

The binding inventory drawer uses 58–74 px square cells, local line icons, lower-corner quantities, rarity borders, a compact two-column paper doll, and an inspector popup. The current `InventoryPanel` is a three-column text list and `EquipmentDoll` is three horizontal text cards. The completed services-v2 row carries the immutable metadata required to render item cells; `presentation: null` remains a valid case for a canonical key that is not registered.

The drawer is desktop-only, supports 1280x720 as its minimum viewport, and already traps focus. The implementation must leave item ownership and mutation inside deterministic server rules; selecting an item in the client is presentational state only.

## Goals / Non-Goals

**Goals:**

- Match the reference's held-item density and hierarchy with a CSS grid, local SVG symbols, quantity badges, rarity borders, and a contained inspector.
- Give mouse and keyboard users the same authoritative item identification without adding a second data path.
- Make empty, equipped, normal, rare, and unknown states distinguishable by text or shape as well as colour.
- Preserve visible drawer content and inspector placement at both supported desktop sizes, including long localized names and a 32-row inventory.

**Non-Goals:**

- No changes to the existing keyboard-router, action-dock, focus-trap, gamepad, or transport abstractions. The WebClient has no gamepad input contract; this change provides complete mouse and keyboard support only.
- No equipment, use, consume, drop, drag, sort, filter, search, price, image, item art, or mutation behavior.
- No numeric stat line, recovery amount, requirement, set bonus, comparison value, or synthetic item type. A later deterministic item-effects capability must own such facts before an inspector shows them.
- No `EquipmentDoll` visual restructuring. The dependent `restyle-inventory-equipment-slots` proposal owns compact square-slot styling and its visual acceptance coverage.
- No client-side persistence of selection; every panel replacement resets selection to avoid presenting stale inventory metadata.

## Decisions

### Render bounded native buttons, not a faux drag grid

The item listing becomes a responsive CSS grid of native `button` elements. Each cell contains one local SVG selected solely by `presentation.icon_key`, a lower-right held-count badge, and an upper-corner check marker when the committed equipped flag is true. Rarity changes a data-attribute-driven border colour and border pattern; the inspector spells the rarity word so colour is never the only available representation.

Native buttons preserve keyboard activation, browser focus, and assistive technology semantics without claiming a drag/drop model the action registry does not provide. The inventory contains at most 32 aggregate rows, so ordinary Tab navigation remains bounded and predictable inside the existing focus trap. Arrow-key grid navigation and gamepad handling are rejected because neither belongs to the current input contract and would overlap the drawer's established key ownership.

### Use one non-interactive inspector for hover and focus

`InventoryPanel` keeps one selected row in local reactive state. Pointer enter and keyboard focus select it; pointer leave clears only when focus is elsewhere. The inspector is a non-focusable `role="tooltip"` surface positioned within the drawer body, flips above or below its anchor when needed, and never leaves the drawer's visible bounds. It receives the identical name, kind, rarity, quantity, equipped state, and summary carried by the focused button's accessible name.

The reference's floating tooltip is preserved as a visual pattern while avoiding an inaccessible hover-only path. Click does not dispatch or persist anything. A fixed details pane was rejected because it changes the drawer's compact reference layout and uses height needed by a 32-row grid.

### Map only closed server icon keys to local SVG

A narrow `item-icons.js` module maps the services-v2 closed keys to inline SVG paths and Traditional Chinese accessible labels. It accepts no URL, HTML, emoji, raw SVG, or inferred key. A null presentation projects to a neutral unknown-item icon and a visible `未知` marker; it does not select the `misc` icon or invent missing metadata.

The mapping is intentionally view-layer-owned. The lore registry names a presentation category; it never ships presentation markup, and the browser does not import server data directly.

### Keep all animation token-gated

Cell outline, inspector opacity, and drawer-safe position transitions use existing `--motion-*` tokens. The current `prefers-reduced-motion` token override therefore makes them effectively instant. No per-frame geometry work, background filter, or new image asset is introduced.

## Risks / Trade-offs

- [A 32-cell grid and inspector can exceed drawer height at 1280x720] -> The drawer body scrolls while its header remains fixed; use grid cell minimums from the reference and verify no inspector overlaps the close control or command line.
- [Pointer and keyboard selection can diverge] -> Use one selected-row source, derive the button accessible name and tooltip content from it, and test focus then pointer transitions.
- [Future server enum values arrive before the local SVG map] -> Render the labelled neutral fallback and record test coverage for every known mapping; do not interpolate a path or class name.
- [Rarity colours fail for colour-vision deficiency] -> Combine colour with a per-rarity border pattern and inspector text; focus and equipped states have their own outlines and check symbol.
- [Long CJK names overflow a compact tooltip] -> Allow multi-line wrapping and constrain the tooltip within the drawer, never truncate an item name without an accessible full label.

## Migration Plan

Land after the registry, services-v2, and inventory-drawer-essential proposals. The change replaces only the inventory component markup, styles, local selection state, stories, and tests. It has no persisted state or compatibility surface; rollback restores the prior composed drawer without converting inventory data.
