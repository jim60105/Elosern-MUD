# Design

## Context

See `proposal.md`. `CreationOverlay.vue` currently calls `use-creation-stage.js::selectPreset(card)` directly on every card click. The store’s `creation.js::handleCreationItem` also dispatches `creation.preset` when a legacy router item has `presetKey`. `bridge.js::onDocumentKeydown` routes noneditable keys into that store and yields native-button Enter. Changing only Vue clicks would leave digit shortcuts saving a draft.

## Goals / Non-Goals

**Goals:** one local expansion owner and one deliberate selection path, sharing existing successful-save confirmation.

**Non-Goals:** custom steps/concept layout, generation UI, draft schema, server actions, confirmation fingerprints and activation rules. The existing three-region custom form remains until `creation-stepped-form`.

## Decisions

### Component contract and key ownership

Add `components/CreationPresetWall.vue` with props `presets`, `draftPresetKey`, `disabled`, `raceDisplayName`; emit `choose(card)` only for the explicit primary action. Keep `expandedKey` local to the wall, distinct from `selectedPresetKey`. On mode entry restore the supplied draft key if present, else the first supplied card. On equal-content republication preserve local expansion; if the expanded key disappears select the first surviving card. Render every supplied card; never encode the shipped roster in logic or tests.

Collapsed cards are native opening buttons; the expanded dossier and its primary button are siblings, never interactive elements nested inside an opening button. Names are supplied display names; expanded state exposes `aria-current`, an outline and visible focus. Pointer opening and horizontal arrows only move expansion. Digits address supplied ordinal positions supported by the existing shortcut range, without wraparound to a missing entry. Left/right clamp at the ends. Enter on a collapsed opening button opens it; Enter on an expanded card or its primary button emits `choose` once. Ignore repeat, modifiers, IME and text-entry targets. An active confirmation or nested drawer owns its keys first.

Add `composables/use-creation-wall-input.js`, owned by the mounted wall, with one document capture listener and explicit teardown on unmount. It handles keys targeted inside the creation preset surface or the persistent creation action dock; nested drawers/dialogs and text entries retain ownership. Focus the wall on preset-mode entry. Keep the legacy `creation.presets` frame as a navigation marker, but remove its direct mutation rows and the store’s `presetKey` dispatch branch. The document capture listener routes dock-focused wall keys to the same local handler and stops consumed keys before `bridge.js`. Keep shared root/confirm router behavior. `use-creation-stage.js::selectPreset` remains the sole selected-card save event producer after `choose`. Escape continues existing one-level back/confirmation cancellation. No raw command/text fallback receives a key consumed by the wall.

### Shell and art

Move existing `.ui-tabs` into the three-column header and preserve current hooks for modes, results, errors, reset and confirmation. Keep reset in the fixed footer; preset mode shows a keyboard hint there, with its primary action inside the expanded dossier. Extract wall CSS alongside the wall; remove obsolete grid rules from `creation-overlay.css` and conflicting creation selectors in `styles/app-shell.css` if present.

Pass each server `artwork` unchanged into `ArtworkPreview`; no client URL composition. Render collapsed art by top/face-rectangle crop, and the expanded art uncropped at 9:16 with the same height-based sizing definition. Use the canonical terminal’s geometry when a real image fails. Follow approved §5 for the common `cqh` sizing/transform and flex-grow transition, existing motion/easing tokens, and immediate reduced/off switching. No new design token or text below `--text-xs`; dimensions scale with `--ui-scale`.

### Human review and spec sequencing

`visual-review.md` in this change is the named human-reviewed record for composition, seven-to-one expansion intent, crop fidelity, palette and approved player-facing copy at 1451x790 and 2560x1440. Do not require tests to pin those words, a shipped preset count or literal markup. The workspace delta replaces the truthful-art scenario; it deliberately retains the old custom layout until change 3 replaces the same requirement. The existing two-step preset-selection scenario continues to mean deliberate primary selection, followed by activation confirmation. Local browsing produces neither a mutation nor a narrative echo, so no dispatch/input-narrative delta is needed here.

## Risks / Trade-offs

The legacy router is an alternate mutation path; integration tests must focus the persistent action dock as well as the wall to detect leftover digit submission. Child remounting on an art-only publication would erase expansion; use stable component keys and preserve surviving local selection.

## Acceptance and documentation

Extend `tests/overlays/creation_overlay.test.js`, `web/static/webclient/js/tests/creation_menu.test.js` and the creation store tests with synthetic cards. Assert zero actions/echoes while browsing by each input path, exactly one deliberate save, no confirmation on rejected save, draft restoration, vanished keys, repeat/IME and focus. Rewrite real `stories/Overlays/CreationOverlay.stories.js` preset states and register the new component in `component-manifest.json`; never import `docs/design/` into production. Update the creation section of `docs/development/frontend-developer-guide.md`. Implement `visual-review.md` with human findings, not a machine “looks good” assertion.

```text
pnpm exec vitest run web/webclient-app/tests/overlays/creation_overlay.test.js
node --test web/static/webclient/js/tests/creation_menu.test.js
pnpm run build
uv run --locked python -m web.tests.browser.unittest_driver web.tests.browser.test_browser_creation_preset.PresetCreationJourneys.test_preset_selection_confirm_activate_reaches_exploration
openspec validate creation-preset-card-wall --strict
```

The browser journey uses both reference viewports and asserts no page-level horizontal scrolling or overlap preventing operation, without asserting elapsed time.
