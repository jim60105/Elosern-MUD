## Why

This is change **A1** of the Vue SPA WebClient migration, governed by
`docs/superpowers/specs/2026-08-19-webclient-vue-migration-roadmap-design.md` (depends on: nothing).
Two up-front, non-frontend prerequisites gate the rest of the migration and both can be delivered
before any Vue code exists. First, several existing `webclient-*` specs and the managed Playwright
suite are *implementation-bound*: they reference the `window.Elosern.*` public façades, the Evennia
plugin `onKeydown` path, and specific DOM ids. The DOM can become Vue only if that public surface is
preserved or each such requirement is re-expressed — and those deltas must be **frozen before wiring**
so later changes carry a stable contract. Second, the validated single-screen design (the 設計稿) is
not yet a committed, linked design reference in `docs/`.

## What Changes

- A **Phase-0 contract audit** deliverable that enumerates every implementation-bound contract across
  `openspec/specs/webclient-*` and the managed Playwright suite — the `window.Elosern.{Protocol,
  KeyboardRouter, narrativeInput, actions}` façades, the WebClient-plugin `onKeydown` path, the DOM ids
  the keyboard router and Playwright target, the versioned layout-persistence keys, and the input path —
   and classifies each as *preserve-via-bridge* vs *delta*. It commits a frozen façade-bridge surface plus
   the complete `MODIFIED`/`RENAMED` delta list, every delta entry naming its applying change (C2 for
   bridge-contract re-expressions, C4 for shell-identity and DOM-remap edits). The deltas are **not
   applied here**; C2 (`webclient-vue-08-wire-bridge-contracts`) consumes the frozen façade surface and
   applies the entries that name it once the bridge exists, and C4 applies the flip-time entries.
- The **設計稿** (the validated static single-screen showcase) is copied into `docs/` as a
  self-contained, offline design-draft reference (self-hosted / local fonts, no CDN), linked from
  `docs/_sidebar.md`, with a check that it exists, is linked, and references no remote asset.
- No npm/Node toolchain, no app code, and no server/OOB/transport change in this change; it is
  contract-freezing (audit) plus documentation only.

## Capabilities

### New Capabilities
(none)

### Modified Capabilities
- `webclient-browser-verification`: adds the requirement that the implementation-bound public contract is
  enumerated and frozen (as a committed `audit.md`) before the shell is swapped, and that this frozen list
  is the binding input to the bridge change. (The audit does not edit the *other* capabilities' specs — C2
  applies those; the 設計稿-in-docs is a plain design-reference check, not a capability requirement.)

## Impact

- **New:** a committed audit deliverable at the stable path
  `docs/development/webclient-vue-frozen-contract-audit.md` (the frozen façade-bridge surface + the
  `MODIFIED`/`RENAMED` delta list with evidence; stable path chosen so the applying changes consume one
  canonical deliverable that survives this change's archive); `docs/design/elosern-redesign/` holding the
  設計稿 (`index.html`, `fonts.css`, `REDESIGN.md`) and `docs/design/fonts-dl/` holding its woff2 set; a
  `docs/_sidebar.md` entry; a small top-level check that the 設計稿 file exists, is linked, and
  references no remote/CDN asset and that its local asset references resolve (a plain regression test —
  it establishes no new main-capability requirement, so it carries no `covers_requirement`); plus a
  dependency-free top-level Python test that verifies the frozen-contract audit (the frozen façade
  surface + the complete, non-overlapping `MODIFIED`/`RENAMED` delta list, declared the bridge change's
  binding input), annotated with `@covers_requirement` for the new `webclient-browser-verification`
  requirement at archive-time spec sync (the canonical requirement ID exists in the main spec only after
  the delta is synced, per the repository's traceability convention).
- **Modified:** `docs/_sidebar.md` (one design-draft entry).
- **Preserved / untouched:** every source spec, the server, the OOB protocol, the transport, and all
  `js/elosern/*` logic. This change deletes nothing.
- **Feeds downstream:** C2 (`webclient-vue-08-wire-bridge-contracts`) consumes this change's frozen
  façade surface + delta list as its binding input; the 設計稿 is the design reference B1–B5 build
  against.
