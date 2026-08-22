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

- **D4 — Every preserved module is consumed through its lib wrapper; none is reimplemented.**
  Beyond the reducer core (D1) and the keyboard router for focus state, the store derives the
  remaining view slices through the A2 `lib/*` wrappers:
  - the **choice-point state** slice (`absent | generating | ready`) is driven by
    `ChoicePointLogic.nextChoicePointState` over the committed `context_actions.suggestions`
    envelope, so the stream state machine stays the tested pure function;
  - the **suggestions view** (status/cards/visible/emptyState plus the content-change signature)
    is derived with `OptionCards.buildOptionsView` / `suggestionsSignature`;
  - the **local-map model** slice is `LocalMap.reducePanel(panel)` when the committed
    `local_map` panel is present, `null` otherwise;
  - the **narrative slice** holds the transport text-stream lines, and each `out` line has its
    renderable token view attached at commit time by the preserved `NarrativeMarkup.tokenize`
    allowlist pipeline (degraded-to-literal-text behavior included);
  - the **focus slice** is the imported `KeyboardRouter` loaded with the committed
    `context_actions` frame (exploration affordances, combat participants), using the
    component dock's preserved `action-`/`target-` item keys as the single key contract.

  Alternatives: (a) components derive these slices at render time — rejected, the contract is
  passive components over store slices, and per-component derivation would let B (mock) and
  live (wired) views drift; (b) the store re-implements each model — rejected by D1/D2.

- **D5 — One dispatch entry, the tested lock semantics.** Components emit only user-intent
  dispatches; the store is the single writer and routes every mutation through one entry
  (`dispatchAction`) that mirrors the Node-gated legacy action-client semantics: the exact
  `ui_action` envelope (`protocol_version` / `presentation_epoch` / `request_id` /
  `base_revision` / `action_id` / `payload`), dispatch only while
  `connected && !mutationsLocked && phase === "active"` and no mutation is in flight, and the
  in-flight lock releases only on a matching `ui_action_result` once the committed revision
  reaches the result's declared `presentation_revision` (immediately when none was declared, or
  unconditionally for a `no_puppet` rejection). Ordinary text (`sendText`) never holds the
  mutation lock. The transport send is an attachable seam (`setSender`); C3 attaches it to
  `evennia.js`, C1 drives it in tests by raw reducer inputs plus a captured sender.

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
