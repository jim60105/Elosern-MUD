# Design: title-codex-removal

Implements D5 (§8) and D7 (§10) of
`docs/superpowers/specs/2026-08-30-title-system-design.md`.

## Context

F owns `world/rules/titles.py` (bank/equip/compose) and the `title` command; G
owns the pending ballot and `accept_epithet`. The OOB pattern to copy is the
combat-menu schema (`{schema_version, items}` + `MAX_*` constants + four mirrors
+ pure service). The deletion matrix (design §12) and error table (§13) are
explicit, so this design only pins the seam choices.

## Goals / Non-Goals

- Goals: `TitleCodexView` read model + OOB v1 + WebClient window; two-gate
  two-step `remove_epithet`; EventLog removal record; re-nominatable names.
- Non-Goals: fixed-title deletion (none exists, structurally), unequip,
  recycle bin, free-text removal, client-side gate logic.

## Decisions

### DH1: gates precede the confirm flow, at step one

`remove_epithet` validates in one pass before any review state exists:
unknown display or wrong kind ⇒ stable rejection; equipped ⇒
`TITLE_EQUIPPED_UNREMOVABLE`; last remaining epithet ⇒ `TITLE_LAST_EPITHET`.
Only an un-gated target echoes review info (display + basis quote) and accepts
the literal `confirm` suffix. Because every gate runs first, the "collection
non-empty ⇒ slot non-empty" invariant (D8) survives deletion: the last epithet
is by construction the equipped one, so a successful removal can never empty a
slot. Removal never touches `title_equipped`.

### DH2: the client renders flags, never decides

Every epithet row carries server-derived `can_remove` (computed from equipped +
collection size); the client hides the 「移除」 button on `false` with zero rules
of its own. The confirm card verbatim-displays display + basis and the warning
「此操作不可恢復」. Fixed rows expose no delete affordance at all.

### DH3: one read model, four mirrors

`TitleCodexView` is pure: fixed rows (registry order, `unlocked` by collection,
`hint_zh` only while locked, flavor only when unlocked), epithet rows
newest-first with `basis`/`equipped`/`can_remove`, `equipped` dict, live
`full_title`, unlocked/total counters; all strings ≤ `TITLE_MAX_*` (display 24,
basis 160, 50 rows/yaml, names per design §10.2) and category enum mirrored
across the four faces like every other OOB surface.

### DH4: removal is an EventLog citizen

A successful removal appends `title_epithet_removed` (entity, display, tick) so
Director summaries see the shed epithet; G's live-collection collision filter
then makes the name nominatable again. The deletion itself is a single
collection-list mutation inside one snapshot-registered transaction.

## Risks

- Telnet confirm-state lifetime: review info is echoed only; the executing call
  re-validates both gates (never trusts the echoed step).

## Migration Plan

One-shot (unreleased).

## Open Questions

None.
