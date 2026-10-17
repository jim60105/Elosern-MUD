# Tasks

Total estimate: **7 hours**, including implementation, focused verification, documentation and integration.

## 1. Glyphs and frame (2h)

- [ ] 1.1 Add the prototype's new glyphs to `components/dock-icons.js` and implement `WindowFrame.vue` over `HudDrawer`; verify a Vitest test for Escape/close focus restoration and tab selection through `IconTabs`, and a `Core/WindowFrame` story at both viewport sizes.

## 2. Rail, grid and bar (2.5h)

- [ ] 2.1 Implement `MemberRail.vue`, `ListDetail.vue` and `ActionBar.vue` with stories; verify Vitest roving focus (arrows, Home/End, Enter/Space), ▼倒地 text and unread accessible name, 空位 entry, independent scrolling, and the action bar reason slot.

## 3. Holdings strip (1.5h)

- [ ] 3.1 Implement `HoldingsStrip.vue` with a story driven by an `item_holdings` fixture; verify counts-only combat rendering, null-delta cells, ▲/▼ shape prefixes and the give event only for enabled receive facts.

## 4. Integration (1h)

- [ ] 4.1 Append the five manifest titles, document the primitives in `web/webclient-app/AGENTS.md`, run the touched Vitest files, `pnpm run build-storybook`, `pnpm run showcase-coverage`, `uv run --locked python -m tools.contract_gate` and `openspec validate webclient-window-primitives --strict`.
