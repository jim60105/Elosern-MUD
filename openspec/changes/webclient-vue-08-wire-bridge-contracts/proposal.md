## Why

This is change **C2** (wiring wave, depends on **A1** and **C1**; may overlap **B5**) of the Vue SPA
WebClient migration (see the migration roadmap at
`docs/superpowers/specs/2026-08-19-webclient-vue-migration-roadmap-design.md`). esbuild's CJS interop does
not set the `window.Elosern.*` browser globals the current `<script>`-load path exposes, and several
`webclient-*` specs + the Playwright suite are bound to those façades and to the plugin `onKeydown` path.
This change builds the **browser-bridge** that re-exposes the stable public contract over the store +
imported logic, and **applies A1's frozen contract deltas** to the façade-referencing capabilities so the
public contract survives the DOM becoming Vue.

## What Changes

- A **public-contract bridge** (browser shims): `window.Elosern.Protocol` and `.KeyboardRouter` are the
  imported UMD modules; `window.Elosern.narrativeInput` is the store's single narrative/choice-point
  append path; `window.Elosern.actions.submit` is the single action-dispatch entry. Document key events
  route through the KeyboardRouter and are claimed exactly when consumed (unconsumed keys fall through to
  the text path).
- The frozen contract set from **A1** is **applied** as `MODIFIED`/`RENAMED` deltas to the
  façade-referencing `webclient-*` capabilities, and their traceability tests are re-pointed. The complete
  set is A1's frozen delta list.
- A new requirement on `webclient-vue-application` capturing that the DOM contract hooks and the stable
  public façades are preserved.

## Capabilities

### New Capabilities
(none.)

### Modified Capabilities
- `webclient-vue-application`: adds the requirement that the app preserves the client DOM contract hooks
  and the stable public façades via the bridge.
- **Audit-driven additions (applied here, per A1's frozen list):** the façade-referencing `webclient-*`
  capabilities — candidates include action-choicepoints, options-surface, pointer-activation,
   character-creation-ui, narrative-markup, and the desktop-shell keyboard-routing requirement — each
   re-expressed for the bridge. The exact set is A1's frozen `MODIFIED`/`RENAMED` list; those delta specs
   are finalized and applied during C2 implementation against that list. A1 is a hard dependency, so it is
   implemented and archived before C2's full delta set is finalized from its committed `audit.md`; the
   `webclient-vue-application` requirement authored here is complete and valid on its own.

## Impact

- **New:** the browser-bridge shims over the store + imported `lib` logic; the applied contract deltas +
  re-pointed traceability tests.
- **Depends on:** A1 (the frozen façade surface + delta list), C1 (the store the façade/`narrativeInput`
  route through).
- **Preserved:** the contractual API (`window.Elosern.*`) and the keyboard-consumption contract; no
  transport/OOB/server change, no mount (C3).
