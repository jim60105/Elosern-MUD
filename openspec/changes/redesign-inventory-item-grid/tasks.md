## 1. Local Item Visual Primitives

- [ ] 1.1 Add a closed local SVG icon map and Traditional Chinese accessible labels for every services-v2 item icon key plus the neutral unknown-item fallback.
- [ ] 1.2 Add a small inventory inspector that accepts only one committed row and renders its shared hover/focus content without an action, mutation, or persisted selection.

## 2. Inventory Presentation

- [ ] 2.1 Replace the inventory row list with responsive native tile buttons, lower-corner counts, equipped check markers, non-colour rarity treatment, null-presentation fallback, and motion-token-gated inspector transitions.
- [ ] 2.2 Handle long localized labels, 32 rows, independent services/character availability, and reset local selection when committed panel data changes.

## 3. Storybook And Tests

- [ ] 3.1 Update the composed `World/InventoryPanel` story for each known icon/rarity, unknown metadata, equipped and un-equipped items, long labels, 32 rows, unavailable states, and keyboard-focused inspection.
- [ ] 3.2 Add focused Vitest coverage for SVG-key mapping, no inference for null metadata, counts, rarity pattern and text, equipped marker, focus/hover content equivalence, the focused tile's `aria-describedby` link to the current inspector, no state-changing control, and reduced-motion behavior.
- [ ] 3.3 Use Storybook and agent-browser to review the composed drawer at 1280x720 and 1440x900, including inspector bounds, body scrolling, focus visibility, Escape, and focus restoration.

## 4. Validation

- [ ] 4.1 Annotate substantive tests for the modified contextual-HUD and component-showcase requirements.
- [ ] 4.2 Run the focused Vitest suite, `npm run build-storybook`, `npm run showcase-coverage`, `npm test`, and `uv run --locked python -m tools.spec_traceability check`.
