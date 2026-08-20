## Context

Part **A1** of the Vue SPA WebClient migration (see
`docs/superpowers/specs/2026-08-19-webclient-vue-migration-roadmap-design.md`; depends on nothing).
No frontend, npm, or transport code is touched. Two independent, low-risk deliverables are produced:
(a) a Phase-0 public-contract audit that freezes the façade surface the later bridge must preserve, and
(b) the validated 設計稿 committed as a design reference under `docs/`.

Constraints that shape this change:
- The `openspec` main specs for `webclient-*` and the managed Playwright suite name implementation-bound
  identifiers (`window.Elosern.*`, the Evennia plugin `onKeydown` path, specific DOM ids, layout-persist
  keys). These become true-at-archive only when `webclient-vue-08-wire-bridge-contracts` (C2) builds the
  bridge, not in A1.
- The 設計稿 was validated as a standalone static single-screen showcase; its source currently lives
  outside the repo (`/tmp/opencode/elosern-redesign/index.html`). Committing it makes it reproducible and
  disposable in `/tmp`.

## Goals / Non-Goals

**Goals**
- Produce a committed, reviewed audit deliverable: the frozen `window.Elosern.*` façade-bridge surface +
  the complete `MODIFIED`/`RENAMED` delta list (each entry naming the affected requirement, the
  classify-as-bridge-or-delta decision, and which downstream change applies it).
- Commit the 設計稿 into `docs/design/` (self-contained, offline, self-hosted fonts) linked from
  `docs/_sidebar.md`, with a dependency-free check.

**Non-Goals**
- No application of the deltas to `openspec/specs/*` (that is C2).
- No npm/Node toolchain, no `package.json`, no Vue code.
- No server, OOB-protocol, action-dispatch, or `js/elosern/*` changes.
- No Playwright/Evennia code changes (the audit reads them, it does not edit them).

## Decisions

- **D1 — Freeze the plan, not the specs.** The audit commits a plan document at the stable path
  `docs/development/webclient-vue-frozen-contract-audit.md` (deliberately outside the change directory:
  the change directory moves under `openspec/changes/archive/` at A1's archive, and the applying changes
  must consume one canonical, path-stable deliverable): the exact façade members the browser bridge must
  expose (`window.Elosern.Protocol`, `.KeyboardRouter`, `.narrativeInput`, `.actions`, including
  `actions.submit`) and an entry per implementation-bound contract (preserve-via-bridge vs delta, the
  affected requirement, the applying change named per entry — C2 for bridge-contract re-expressions, C4
  for shell-identity and DOM-remap edits — and the rationale). Alternatives: (a) edit the affected
  `webclient-*` specs now — rejected, it would create requirements whose traceability tests do not exist
  yet (red) for a behavior that is unimplemented; (b) keep the list informal — rejected, C2 needs a
  frozen, reviewed input; (c) commit the plan inside this change directory — rejected, the archive move
  breaks every later path reference to it. Chosen: a committed plan at a stable docs path consumed by
  C2 (bridge-contract entries) and C4 (flip entries).

- **D2 — Enumerate by search, classify by contract.** The audit is reproducible: it greps
  `openspec/specs/webclient-*/spec.md` and the `web/tests/browser/` suite for `window.Elosern.`,
  `getElementById` / `#` target ids, the `onKeydown` plugin path, and layout-persist keys, then classifies
  each hit. Every implementation-bound identifier lands in exactly one bucket (preserve-via-bridge or
  delta), so the delta list is complete rather than remembered.

- **D3 — 設計稿 is copied verbatim and statically checked.** The showcase HTML + assets (self-hosted
  fonts) are copied byte-for-byte into `docs/design/`, keeping `fonts.css` untouched: `index.html`,
  `fonts.css`, and `REDESIGN.md` (the showcase's authoritative feature/IA inventory) go to
  `docs/design/elosern-redesign/`, and the woff2 set goes to `docs/design/fonts-dl/` so `fonts.css`'
  relative `../fonts-dl/` references resolve without a single byte of edit. A small **top-level**
  (dependency-free) test asserts the design draft exists under `docs/`, is linked from
  `docs/_sidebar.md`, references no remote/CDN asset, and that every local `url()`/`href`/`src`
  reference in the committed set resolves (self-contained offline check). A full interactive render is
  left to the docs/browser harness rather than booting a server here; this keeps A1 free of even a
  browser dependency. The top-level check establishes no new main-capability requirement, so it carries
  no `covers_requirement`.

## Risks / Trade-offs

- **Audit under/over-enumeration** → mitigated by the grep-driven enumeration (D2) with explicit
  classification, and re-checked by C2 at implementation; the frozen list is a starting contract, and C2
  surfaces any omission.
- **The 設計稿 source is in `/tmp` (disposable)** → A1's job is exactly to commit it; after A1 lands the
  repo copy is the source of truth and the `/tmp` mockup may be discarded. The static no-remote check
  guards against an accidentally CDN-linked copy.
- **Sidebar/doc drift** → A1 owns the single 設計稿 sidebar entry (roadmap §6.1); D1 (finalize) finalizes
  remaining doc links, so ownership stays single-writer.

## Migration Plan

No runtime change; nothing to deploy. Rollback is removing the `docs/design/` file, the sidebar entry,
the top-level check, and the `audit.md` deliverable — no game, server, or spec impact.

## Open Questions

- None. The exact façade member set is determined by the audit itself (D1/D2) and committed with it.
