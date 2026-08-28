## 1. Square Slot Presentation

- [x] 1.1 Add a closed local SVG map for the four fixed equipment slot roles (the off-hand entry is the iconless position, matching the binding design) and keep item keys and display names out of icon selection.
- [x] 1.2 Refactor `EquipmentDoll` markup and scoped CSS to a compact two-column square layout with visible slot captions, dashed singleton-empty state, occupied names, and accessory summary count.
- [x] 1.3 Retain the complete accessory group, unknown-slot labelled fallback rows, duplicate-singleton overflow rows, unavailable state, true-value language, and existing non-interactive behavior.

## 2. Showcase And Verification

- [x] 2.1 Extend `Data/EquipmentDoll` and composed inventory stories for empty, each occupied singleton slot, zero through three accessories, an unknown slot, unavailable character data, long labels, and the 1280x720 drawer composition.
- [x] 2.2 Add focused Vitest coverage for fixed slot-symbol mapping, visible/dashed empty state, accessory count and complete rows, unknown-slot preservation, no inferred item presentation, and no additional focusable control.
- [x] 2.3 Review the composed Storybook drawer with agent-browser at 1280x720 and 1440x900 for no horizontal overflow, readable labels, body scrolling, focus visibility, Escape, and focus restoration.

## 3. Validation

- [x] 3.1 Annotate substantive tests for the modified contextual-HUD requirement and run the focused Vitest suite, `npm run build-storybook`, `npm run showcase-coverage`, and `uv run --locked python -m tools.spec_traceability check`.
