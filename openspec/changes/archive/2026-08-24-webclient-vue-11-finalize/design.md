## Context

Part **D1** (finalize; depends on C4). This is the cleanup + documentation + source-of-truth-amendment step
that closes the migration.

## Goals / Non-Goals

**Goals** — dead legacy code removed; AGENTS/design-docs/docs updated; the D13 implementation amendment
applied; the final quality gate locked.
**Non-Goals** — no new features, no OOB/presentation change, no new frontend code (the client is complete
after C4).

## Decisions

- **D1 — Delete only what C4 made dead.** The retired view files and dead CSS are removed and a check
  confirms nothing imports them; the preserved `js/elosern/*` logic and `evennia.js` are untouched.
- **D2 — Amend the source-of-truth docs, not just this change's specs.** The D13 "browser is the
  first-class graphical client" is unchanged in intent; only its *implementation* (GoldenLayout shell →
  Vue SPA on the same Evennia extension points) is amended in the engine design doc webclient row +
  `webclient-ui-design.md`, per roadmap §3.
- **D3 — Lock the gate, don't grow it.** The mandatory-gate requirement is set to its final form
  (all Vue gates + the offline-degradation browser regression + exact-root/aggregate ≥ 80% + Codecov); no
  gate is weakened.

## Risks / Trade-offs

- **Deleting a file something still imports** → a check confirms zero references before deletion; the Node
  gate and all suites rerun clean.
- **Doc drift after the amendment** → the amendment is the roadmap's single documented edit to the source
  docs; future re-ordering is gated by roadmap §9.

## Migration Plan

Pure refactor + docs + gate lock; rollback = restore the removed files and the doc text. No server/protocol
impact.

## Open Questions

- None.
