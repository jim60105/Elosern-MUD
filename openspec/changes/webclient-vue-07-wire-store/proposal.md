## Why

This is change **C1**, the start of the wiring wave, of the Vue SPA WebClient migration (see
`docs/superpowers/specs/2026-08-19-webclient-vue-migration-roadmap-design.md`; depends on **A2**
`webclient-vue-01-foundation`; parallel-safe with Wave B because it writes `stores/` while the
showcase writes `components/`). The showcase components (B wave) are offline and mock-driven. This
change introduces the reactive **store** — the single writer of client view state — built *on top of the
preserved protocol reducer*, so that later the transport (C3) has a store to drive and the components
(C4) have committed state to bind. It is pure client state logic: no transport wiring, no mount, so it
stays offline and fully testable.

## What Changes

- A **Pinia store** that uses the preserved `js/elosern` protocol reducer (imported via A2's Vite CJS
  interop) as its core, consumes **every** preserved DOM-independent logic module through A2's `lib/*`
  ES-module wrappers (protocol reducer, keyboard router, narrative markup pipeline, local-map model,
  choice-point and option-card logic), and publishes committed view state **atomically** — no subscriber
  ever observes partially applied state. The store enforces a single writer.
- **Store integration tests** verify the reducer ordering the migration relies on: atomic new-epoch
  snapshot adoption, active-epoch revision ordering, old-epoch / stale-revision rejection, and panel
  replacement.
- No evennia.js OOB binding (that is C3), no `window.Elosern.*` façade bridge (C2), and no re-binding of
  the B-wave components (C4). The store is driven in tests by raw reducer inputs through a captured
  sender seam.

## Capabilities

### New Capabilities
(none — `webclient-vue-application` was introduced in B1.)

### Modified Capabilities
- `webclient-vue-application`: adds the requirement that the app binds the preserved strict
  DOM-independent logic to a single reactive store with committed-only reads.

## Impact

- **New:** `web/webclient-app/stores/*` and store integration tests. Consumes A2's `lib/*` wrappers for
  all six preserved modules (a consumer, not an edit).
- **Depends on (A2):** the `lib/*` wrappers, `vitest`, and the store-slice contract in the A2
  architecture reference.
- **Preserved:** the preserved reducer/keyboard/markup/map logic (unchanged); no transport, OOB, server,
  `base.html`, or template change.
