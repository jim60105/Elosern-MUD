## Context

Part **C1** (wiring wave; depends on **A2**, parallel-safe with Wave B). B components render from mock
data. This change stands up the reactive store that will become their source of truth, on top of the
preserved reducer. The store is the single writer the roadmap's "strict and atomic" invariant names.

## Goals / Non-Goals

**Goals**
- A single-writer Pinia store over the preserved protocol reducer that publishes committed state
  atomically.
- Store integration tests covering epoch/revision ordering and panel replacement.

**Non-Goals**
- No evennia.js / OOB transport binding (C3); no `window.Elosern.*` façade bridge (C2); no re-binding of
  B components (C4); no mount, no `base.html`, no template change; no invented data (the store holds only
  allowlist / text-sourced state).

## Decisions

- **D1 — Wrap the preserved reducer, don't rewrite it.** The store imports the reducer through A2's
  `lib` CJS-interop wrapper and delegates epoch/revision/panel semantics to it; the store's own job is the
  reactive boundary (commit + subscribe). Alternatives: (a) reimplement ordering in Pinia state —
  rejected, it would discard the tested reducer and its Node gate; (b) Vuex — rejected, Pinia is the Vue 3
  standard and is ESM-first.

- **D2 — Commit atomically, read only committed.** The store accepts a snapshot/update, runs it through
  the reducer, and then publishes one new committed object (replacing panel state wholesale). Readers are
  never handed an in-progress object. This preserves the "strict and atomic, subscribers see only
  committed state" invariant now described in `webclient-desktop-shell`.

- **D3 — Contract is shared, binding is later.** The store's view-slice shapes match the A2
  `frontend-vue-architecture.md` contract so B's mock-driven props and C1's store slices agree; B
  components bind to these slices in C4, not here.

## Risks / Trade-offs

- **CJS-interop edge cases importing the UMD reducer** → covered by the store adoption integration tests
  and the untouched Node gate; A2 froze the interop config.
- **Two write paths emerge later** (store + a stray direct mutation) → the store is the only writer; a
  lint/test asserts components dispatch only through the store.
- **Slice shape drift vs B components** → pinned by D3's shared contract; C4's re-binding is the
  integration point where mismatches surface.

## Migration Plan

No runtime effect (no transport/mount). Rollback: delete `stores/` + its tests; A2 toolchain, B
components (mock-driven), and all existing gates are unaffected.

## Open Questions

- None; the reducer is the trusted core and the slice contract is fixed by the A2 reference doc.
