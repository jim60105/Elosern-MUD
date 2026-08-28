## Context

`EquipmentDoll` is now composed only by the inventory drawer and exposes the true committed `character.equipment` rows. Its current three text cards preserve data but do not communicate equipment slot state at a glance. The binding design uses four compact square cells, a dashed empty state, visible slot captions, and fixed generic line symbols; it does not supply data for item-specific icons, rarity, or numeric statistics in the character panel.

This proposal is deliberately separated from the inventory grid and inspector so both visual changes remain independently reviewable within one workday.

## Goals / Non-Goals

**Goals:**

- Make named equipment slots scannable through a compact two-column square layout at 1280x720.
- Distinguish primary hand, off hand, armor, accessory capacity, empty state, and occupied state without relying on colour alone.
- Preserve every committed row, including multiple accessories and unrecognised future slot keys.

**Non-Goals:**

- No change to the `character` payload, item presentation projection, inventory grid, item inspector, or any data ownership boundary.
- No inferred item type icon, rarity treatment, description, numeric stat, effect, requirement, set bonus, comparison, or state-changing control.
- No new focusable element or keyboard route; this is static read-only equipment presentation inside the existing drawer.

## Decisions

### Use slot identity as the only icon selector

The component owns a closed map from the four existing equipment-slot names to local inline SVGs. A symbol represents a fixed slot role, never the item in it. The off-hand position is the iconless position (the binding design leaves its box empty/dashed with no symbol); its map entry carries a null path and the cell renders only the caption and, when occupied, the committed display name. The three single-item slots display their actual item name beneath the cell; the accessory summary cell displays the committed accessory count and the existing detail list still displays every accessory name.

Mapping from an equipped `item_key` or `display_name` was rejected because the character payload has no immutable item-presentation field and guessing would conflict with the inventory grid's registry-backed symbols.

### Reserve the fourth square for accessory summary without dropping rows

The layout uses primary hand, off hand, armor, and accessory summary as four stable cells. The accessory summary communicates that the bounded multi-item slot is populated; below it, the retained accessory section renders zero to three committed rows. This follows the reference's four-cell rhythm while respecting the actual `ACCESSORY_MAX_SLOTS` contract rather than pretending it is one slot with one item.

### Keep duplicate singleton rows as labelled overflow rows

The character panel validator accepts more than one committed row for a recognised singleton slot. The square grid consumes only the first row per slot; every further row for that slot renders as a labelled overflow row (slot label + display name), so the no-drop guarantee holds for duplicated singleton slots, not just unknown slots.

### Use text and outline treatment for state

Every cell has a visible Traditional Chinese slot caption. Empty single-item slots use a dashed outline and the text `未裝備`; occupied slots use a solid outline and real item name. The accessory square uses a static accessory glyph plus visible count. An unknown server-authored slot remains a labelled fallback row, preserving the current no-drop guarantee.

### Keep styling token-based and geometrically bounded

Cells use the existing panel, line, paper, gold, spacing, radius, and motion tokens. The square grid has a fixed minimum cell size that fits the 560 px drawer with the item grid present, while long item names wrap below rather than expanding square cells or overflowing horizontally. The component adds no animation except token-gated focus/hover feedback already covered by the global reduced-motion rule.

## Risks / Trade-offs

- [Accessory contents are not visible in one square] -> Retain the existing detail list immediately beneath the summary cell and test multiple accessories.
- [A long localized item name can make the section taller] -> Allow line wrapping below a stable cell; the drawer body scrolls rather than clipping content or shrinking text below existing readable sizes.
- [Unknown slots become less prominent] -> Keep their explicit labelled fallback row, not a silent grid omission.
- [A future slot is added server-side] -> It remains in the fallback row until a separate design decision adds a fixed visual slot; no fake cell is created.

## Migration Plan

Land after the equipment relocation and inventory grid changes. There is no persistent state or API change. Validate focused component tests and Storybook at 1280x720 and 1440x900; reverting restores the previous textual layout with no data conversion.
