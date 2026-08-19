## Context

Part **C2** (wiring wave; depends on A1 + C1, may overlap B5). The DOM can become Vue only if the public
contract the existing specs/browser tests bind to is preserved; this change provides that contract as a
bridge and applies the frozen audit deltas.

## Goals / Non-Goals

**Goals** — the `window.Elosern.*` bridge over the store + imported logic; A1's frozen deltas applied to
the façade-referencing capabilities with traceability re-pointed.
**Non-Goals** — no transport binding/mount (C3), no view behavior migration (C4), no new façades (the
bridge preserves the existing set only).

## Decisions

- **D1 — Shims over real modules, single entry points.** The bridge is thin: `Protocol`/`KeyboardRouter`
  point at the imported UMD modules; `narrativeInput` is the store's append path (one, not two);
  `actions.submit` is the one dispatch entry. Key events reach the KeyboardRouter and are claimed exactly
  when consumed (matching the existing onKeydown claim semantics); unconsumed keys fall through. This
  keeps the contractual API byte-identical while the DOM is Vue.

- **D2 — Apply A1's frozen list, not a remembered one.** The delta set for the other capabilities is
  A1's audited list (the authoritative "which requirements are implementation-bound" net). C2 applies each
  and re-points its traceability test in the same change, so every re-expressed requirement has a passing
  test at C2's archive. C2 surfaces any A1 omission rather than silently leaving a bound spec broken.

## Risks / Trade-offs

- **A missing façade/contract reference** → A1's grep-based enumeration is the net and C2 re-checks the
  Playwright suite before flipping the shell (C3/C4).
- **A second append or dispatch path appears** → `narrativeInput`/`actions.submit` are store-owned single
  entry points asserted by a browser test.
- **Traceability re-point churn across several capabilities** → confined to C2 (where the bridge + tests
  exist), so no requirement is left without a test.

## Migration Plan

Bridge is additive (re-exposes existing globals); the existing façade/keyboard tests pass through the
shims without change. Rollback = revert the bridge + the applied deltas together.

## Open Questions

- None; the frozen set comes from A1.
