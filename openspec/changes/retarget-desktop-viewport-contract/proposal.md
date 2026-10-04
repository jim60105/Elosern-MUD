# Proposal: retarget-desktop-viewport-contract

## Why

The desktop contract was drawn against a 1920x1080 reference viewport with a 12 CSS px chrome floor, but the player's actual browser viewport is 1451x790 CSS px: below the old reference, chrome renders at the floor while the reference never applies, and the 12px chrome steps are too small at real viewing distance. The reference viewport and the readability floor are retargeted to the real viewport so the drawn geometry is the geometry the player sees, and every visible glyph grows to at least 16 CSS px.

## What Changes

- **BREAKING** The reference viewport becomes 1451x790 CSS px: `UI_SCALE_REFERENCE_HEIGHT` 1080→790, `UI_SCALE_REFERENCE_WIDTH` 1920→1451. The chrome-factor mechanism `S = clamp(1, min(h/790, w/1451), 1.4)` is unchanged; every derived constant (band-height clamp bounds, stage-box percentage, portrait anchor sizes, island canvas) is re-derived from 790x1451. Because the reference is now 16:8.7 rather than 16:9, a taller, narrower viewport caps on its width ratio earlier — accepted as part of the retarget.
- **BREAKING** The chrome type floor rises from 12px to 16px: every visible text — chrome labels AND drawn-map labels (node labels, edge-marker names) AND message/log prose — SHALL render at >= 16 CSS px at the reference scale. The `--text-*` ramp starts at 16 (`--text-xs`) with the larger steps re-stepped accordingly.
- **BREAKING** The bottom band's reference height shrinks 300px→220px (`clamp(190px, 27.85vh, 400px)` with px bounds multiplied once by the chrome factor); the top band stays 48px, so the >=65% stage-box invariant holds at 790px height (790 − 48 − 220 = 522px = 66.1% >= 65% = 513.5px).
- The message window's page text and the full log's lines are re-specified: set in the bundled **Jim Mono TC** monospace face (replacing the serif reading face for these two surfaces), on a three-step reader prose scale re-stepped to 16 / 18 / 20 px at the reference scale, with **A− = 16px the floor** and A/A+ larger. The reference-scale step is multiplied once by `--ui-scale`; the reader's prose scale multiplies on top, exactly as the existing re-paging contract already tolerates.
- The minimap island's reference square grows 208px→240px and its drawn label step 12→16 units so the fitted 3x3 lattice still draws labels at >= 16px at the reference scale; the island's chrome follows the new `--text-xs` = 16px step.
- Larger-display proportional scaling ABOVE the reference is retained (2560x1440 renders the new reference at the 1.4 cap); nothing else about the proportional-scale-once contract changes. The reader prose-scale preference, reduced-motion, offline, and DOM-contract behaviour are untouched.
- Desktop-only stance unchanged; no mobile support.

## Capabilities

### New Capabilities

(None)

### Modified Capabilities

- `webclient-vue-application`: the reference-scale and scale-once requirements re-anchored to 1451x790; the "Chrome type is legible" floor amended 12px→16px and extended to the drawn map.
- `webclient-contextual-hud`: the stage-anchors requirement's band/header/stage-box reference geometry re-derived from 790px; the message-window requirement's page-text contract (face, size, prose-scale floor); the prose-scale preference requirement (new steps, A− = 16px); the place-card numerals' floor reference.
- `webclient-desktop-shell`: required-surface visibility viewports re-anchored; settings-switch chrome floor 12px→16px; the reading sample and the serif-for-narrative theme clause amended.
- `webclient-local-map`: island reference square 208→240px, chrome step 12→16px, drawn node-label step 12→16 units with the fitted-label floors re-derived; below-reference acceptance clauses re-pointed to the reference.
- `webclient-input-narrative`: the re-paging scenario's resize viewport tuple re-anchored; the full-log column clause (mono face at the new reading size).

## Impact

- `web/webclient-app/lib/ui_scale.js` (reference constants + comments), `web/webclient-app/tests/ui_scale.test.js`.
- `web/webclient-app/styles/tokens.css` (type ramp, `--message-text`/`--log-text`, `--header-h`, `--band-h`, `--actor-h`, island/stage literals) and every `calc(npx * var(--ui-scale))` literal re-derived from the new reference; `MessageWindow.vue`, `FullLogOverlay.vue`, `ReadingSample.vue`, `SettingsOverlay.vue` (prose-scale steps), `preferences.js`.
- Map geometry: `use-map-lattice-geometry.js`, island canvas/label steps, the cell-advance budgeting stays manifest-driven but its floor assertions move to 16px.
- This change is the engine half; the acceptance half (browser-verification viewport matrix, per-feature acceptance amendments, browser test viewport tuples, `browser_base.DEFAULT_VIEWPORT`) lands in the companion change `retarget-browser-acceptance-viewports`, which depends on this one.
- Traceability: amended requirements keep their canonical IDs; test updates ride with the acceptance change. `docs/game` is unaffected — no player commands change.
