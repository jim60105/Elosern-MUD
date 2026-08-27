## 1. Drawer Information Architecture

- [ ] 1.1 Start only after `fix-webclient-character-status-drawer-order` is complete and preserve its final character-status ordering while removing the moved equipment and wallet sections.
- [ ] 1.2 Pass the committed character panel to `InventoryPanel`, compose `EquipmentDoll` before held items, and implement the independent services-versus-character unavailable states.
- [ ] 1.3 Configure the inventory `HudDrawer` with the existing local inventory SVG and a valid character-wallet subtitle; remove the duplicated panel-body heading and all secondary wallet renderings.

## 2. Showcase And Regression Coverage

- [ ] 2.1 Replace the generic inventory Storybook wrapper with the open shared drawer composition and add deterministic cases for filled, empty, unavailable, and unknown-slot equipment plus services ceiling and unavailable states.
- [ ] 2.2 Update the inventory, equipment-doll, character-status-drawer, and app drawer tests for the new component ownership, one-wallet rule, header SVG/subtitle, and no fabricated independent-panel values.
- [ ] 2.3 Verify focus trapping, Escape, scrim close, restore-to-opener behavior, keyboard service-frame hosting, and 1280x720 drawer scrolling remain unchanged.

## 3. Validation

- [ ] 3.1 Annotate substantive tests for the modified contextual-HUD requirements and run the focused Vitest suite, Storybook build, showcase-coverage check, and `uv run --locked python -m tools.spec_traceability check`.
