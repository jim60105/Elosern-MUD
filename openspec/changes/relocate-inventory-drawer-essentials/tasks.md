## 1. Drawer Information Architecture

- [x] 1.1 Prerequisite satisfied: `fix-webclient-character-status-drawer-order` is archived. Preserve the character drawer's final section ordering (the archived intimate-status 親密狀態 section stays in its preserved position, after 偽裝 and before 背景/persona) while removing the moved equipment and wallet sections.
- [x] 1.2 Pass the committed character panel to `InventoryPanel`, compose `EquipmentDoll` before held items, and implement the independent services-versus-character unavailable states.
- [x] 1.3 Configure the inventory `HudDrawer` with the existing local inventory SVG and a valid character-wallet subtitle; remove the duplicated panel-body heading and all secondary wallet renderings.

## 2. Showcase And Regression Coverage

- [x] 2.1 Replace the generic inventory Storybook wrapper with the open shared drawer composition and add deterministic cases for filled, empty, unavailable, and unknown-slot equipment plus services ceiling and unavailable states.
- [x] 2.2 Update the inventory, equipment-doll, character-status-drawer, and app drawer tests for the new component ownership, one-wallet rule, header SVG/subtitle, and no fabricated independent-panel values.
- [x] 2.3 Verify focus trapping, Escape, scrim close, restore-to-opener behavior, keyboard service-frame hosting, and 1280x720 drawer scrolling remain unchanged.

## 3. Validation

- [x] 3.1 Annotate substantive tests for the modified contextual-HUD requirements and run the focused Vitest suite, Storybook build, showcase-coverage check, and `uv run --locked python -m tools.spec_traceability check`.
