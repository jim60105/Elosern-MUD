# Tasks

## 1. Wall and shell

- [ ] 1.1 Add `CreationPresetWall.vue` with the props/event contract in design and local `expandedKey`. Connect only `choose` to `use-creation-stage.js::selectPreset`. Extend `tests/overlays/creation_overlay.test.js` with synthetic cards proving opening sends zero actions and deliberate selection saves once; the focused Vitest command in design must pass.
- [ ] 1.2 Extract wall styles and move tabs into the header/footer shell in `CreationOverlay.vue`/`creation-overlay.css`. Preserve confirmation/error hooks and use `ArtworkPreview` with supplied crop geometry. Update real overlay stories and register the component; verify both reference viewports have no page-level horizontal overflow, using the browser command in design after build.

## 2. Keyboard cutover

- [ ] 2.1 Add the wall-owned `use-creation-wall-input.js` capture listener with teardown, native-button Enter semantics and nested-surface exclusions. Retire direct preset mutation rows in `creation_menu.js` and the `presetKey` dispatch branch in `stores/elosern/creation.js`; keep root/confirmation navigation. Extend Node creation-menu and component/store tests to exercise wall-focused and dock-focused digits/arrows/Enter, repeated/modified/IME keys and Escape; no browsing action or echo may reach transport.
- [ ] 2.2 Update `web/tests/browser/test_browser_creation_preset.py` for local expansion then deliberate save/confirmation. Keep rejected-save and escape assertions; run the named focused browser journey in design only after `pnpm run build`. Expected actions are one preset save and one explicit activation, never a digit-triggered save.

## 3. Review and delivery

- [ ] 3.1 Update the creation section of the frontend developer guide and produce this change’s human-reviewed `visual-review.md` against approved §§4–5/11, including crop, motion, focus and both reference viewports. No automated assertion pins copy, roster size or exact markup.
- [ ] 3.2 Run the focused commands in design, `pnpm run build-storybook` and `pnpm run showcase-coverage`; all real-component stories must build and be registered. Register any new browser methods with `uv run --locked python -m tools.shard_register fix`, then run `uv run --locked python -m tools.contract_gate` and `openspec validate creation-preset-card-wall --strict`; expect no warning/failure.
