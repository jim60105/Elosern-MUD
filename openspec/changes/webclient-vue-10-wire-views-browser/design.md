## Context

Part **C4** (wiring wave; depends on C3). The atomic production flip: production becomes the Vue client and
the re-mapped behavioral suite must be green in the same change.

## Goals / Non-Goals

**Goals** — `base.html` defaults to the Vue bundle; legacy loads removed; `webclient-desktop-shell` renamed
GoldenLayout→Vue SPA; the production Playwright behavioral suite re-mapped; offline/behavior regression
proven; no legacy view plugin in the load path.
**Non-Goals** — no transport binding (C3), no store creation (C1), no dead-file deletion (D1), no new data.

## Decisions

- **D1 — Atomic flip.** The flip (default → Vue), the legacy load removal, the desktop-shell rename, the
  flip-time `webclient-narrative-markup` wording fix (frozen audit entry C4-03), and the production
  Playwright re-map land **together**, so at C4's archive production IS the Vue client and the
  re-mapped suite is green. C3 already made the store-bound components live-capable, so the flip points
  production at a working app rather than a half-wired one.
- **D2 — Preserve hooks, re-map the rest (row-by-row per the frozen audit).** The per-identifier decision
  lives in the Phase-0 frozen audit (`docs/development/webclient-vue-frozen-contract-audit.md` §2.3): the
  PRESERVE-SAME-HOOK rows (`#action-dock`, the `action-`/`target-` keys, `#combat-row-0`, `#inputfield`,
  `.inp` / `.narrative-divider`, `#narrative-unread`, `#elosern-action-live`, `#elosern-offline-overlay`,
  `data-node` / `data-node-id`) stay unchanged; the REMAP-TO-TESTID rows (including `combat-detail` and
  `local-map-detail`) are served as `data-testid` with the same string; every other interactive surface
  carries a stable `data-testid`; the Playwright slices are re-mapped per surface in lockstep.
- **D3 — Legacy files are unreferenced here, deleted in D1.** C4 removes the loads so the legacy view
  files are dead; D1 deletes them. No legacy view code remains in the load path at C4.

## Risks / Trade-offs

- **Selector churn across ~28 tests** → re-map per surface, running the slice after each before the next.
- **Flip regresses offline/invariant** → the no-remote-request + text-fallback + not-color-only checks run
  in the same change as the flip.
- **A hidden dependency on a removed legacy load** → the re-mapped suite green confirms none.

## Migration Plan

`base.html` is the switch; rollback reverts the default to legacy (C3's harness slice still proves the Vue
path). Single production default; no compatibility layer.

## Open Questions

- None.
