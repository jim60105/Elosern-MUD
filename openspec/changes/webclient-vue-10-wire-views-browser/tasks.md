## 1. Production flip to Vue

- [ ] 1.1 Set `web/templates/webclient/base.html` default to the Vite bundle (XOR flag permanently Vue); remove the legacy GoldenLayout/jQuery/plugin `<script>` loads; keep `evennia.js` + the vanilla text console; confirm no remote runtime request
- [ ] 1.2 Make the app the live mounted client in `web/templates/webclient/webclient.html` and retire the GoldenLayout `#main-sub` mount; retire the GoldenLayout runtime css in `web/static/webclient/css/`
- [ ] 1.3 Confirm the store-bound components (C3) are the production renderers and the legacy view files are now unreferenced (dead) in the load path

## 2. Desktop-shell rename + production Playwright re-map

- [ ] 2.1 Apply the `webclient-desktop-shell` rename (GoldenLayout → Vue SPA desktop shell) and reword only its mount/fallback + tab-strip scenarios; confirm the behavioral shell requirements are otherwise unchanged
- [ ] 2.2 Re-map the production per-surface Playwright slices to the preserved hooks (`#action-dock`, `action-`/`target-` keys, `#combat-row-0`, panel ids) + `data-testid` (layout/shell, local map, exploration, combat, combat-rejection, creation, services, input/narrative, options, art, choicepoints, pointer, session lifecycle, reconnect)
- [ ] 2.3 Make each re-mapped slice green before proceeding to the next surface

## 3. Offline / behavior regression

- [ ] 3.1 Prove bundle blocked → text playable via the vanilla console; incompatible OOB → graphical locked with text round-tripping
- [ ] 3.2 Assert reduced-motion honored, not-color-only status holds, and 1440x900 + 1280x720 remain usable

## 4. Gate + traceability

- [ ] 4.1 Full Evennia + managed browser (re-mapped) + Node + Vitest + Storybook green; the load path includes no legacy view file
- [ ] 4.2 Add `@covers_requirement`-annotated Python tests (wrapping the re-mapped browser + Node execution) for each main requirement this change adds or modifies; run `uv run --locked python -m tools.spec_traceability check` and the `verify --evidence` flow so the traceability gate is green at this change's archive
