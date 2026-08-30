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

`remove_epithet` validates in one pass before any review state exists, in
precedence unknown/wrong-kind ⇒ stable rejection; last remaining epithet ⇒
`TITLE_LAST_EPITHET`; equipped ⇒ `TITLE_EQUIPPED_UNREMOVABLE`. Last-remaining
precedes equipped because the D8 invariant makes the sole epithet necessarily
the equipped one, and the one-epithet scenario must name `TITLE_LAST_EPITHET`.
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
`full_title`, unlocked/total counters, and the pending ballot (safe read); all
strings ≤ `TITLE_MAX_*` (display 64 — equal to the epithet storage cap so a
rendered action identifier is never a truncated non-matching string — basis
160, 50 rows; names per design §10.2) and category enum mirrored across the
four faces like every other OOB surface.

### DH4: removal is an EventLog citizen and a durable record

A successful removal appends `{tick, display}` to a bounded persistent
`title_epithet_removals` log (snapshot-registered, written inside the same
transaction — the same durable-feed discipline as G's decline log, which the
nomination prompt digests for the Director's soft learning) and returns a
renderable `title_epithet_removed` EventLog for the answering surface, like
`decline_epithet_ballot` does. The deletion itself is a single
collection-list mutation inside one snapshot-registered transaction.

## Risks

- Telnet confirm-state lifetime: review info is echoed only; the executing call
  re-validates both gates (never trusts the echoed step).

## Migration Plan

One-shot (unreleased).

## Open Questions

None.

## Rubber-Duck Review Ledger — run #2 (final implementation diff)

Scope: the full staged diff (45 files, +4290/−107), reviewed read-only
against the delta specs, this design, and the master design §8/§10.

| # | Severity | Finding | Disposition |
|---|----------|---------|-------------|
| 1 | MAJOR→NON-ISSUE | Caps 50/64/160 "violate a 47/256 contract" | The "47/256" figure appeared only in the review brief (a bad handoff memory — 47 was an envelope-trim outcome in the panel tests, never a contract). The delta spec and master design pin only "display maxima = storage caps (64/63)" + four-mirror parity, which the code satisfies exactly (all mirrors ship 50/64/160; display 64 = epithet storage cap). No code change. |
| 2 | MAJOR | Echo/quote round-trip; echo truncates at 60 < contract 64 | Gameplay displays are form-gated to 2–8 pure-CJK code points (no whitespace/quotes, `display_form_valid`), so embedded-quote targets are unreachable state, and the reviewer's own `甲" confirm` worked example re-parses correctly (the trailing `confirm` token is split-clean before quote-stripping). The real half: `command_echo.js` capped title identifiers at the generic 60 while the validator admits 64. Fixed: `titleLabel` at the 64 contract cap (worst-case quoted line 97 ≤ 120), `title.equip`/`title.remove` resolvers switched, exported, pinned by a new Node boundary test. |
| 3 | MAJOR | AST fixed-title pin vacuous: `assertNotIn('"fixed"', ast.unparse(fn))` can never fire (unparse canonicalizes to `'fixed'`) | Fixed structurally in `test_removal_source_structurally_preserves_equipment_and_fixed`: assert on `ast.Constant` VALUES ("fixed" absent from every string constant in `remove_epithet`), `_FIXED_KIND` absent as any `ast.Name` load, every `entry["kind"] ==` comparison compares only to `_EPITHET_KIND`, plus a non-vacuity probe running the identical constant-value detector on a fixed-kind mutant. |
| 4 | MINOR | tasks.md checkboxes not marked after verification | Done: §1–§4.4 and V1–V5 marked as their verifications landed. |
| 5 | NON-ISSUE | Single-writer boundary, snapshot/transaction registration | Confirmed clean. |
| 6 | NON-ISSUE | Gate precedence, confirm-time re-validation, prompt arity/digest | Confirmed clean. |
| 7 | NON-ISSUE | Vue injection surface, server-only `can_remove` | Confirmed clean (mustache-only rendering, no v-html). |

Post-remediation verification: Node 377 pass (incl. the new boundary test),
Vitest 583, AST-pin test green, V1 aggregate 3555 OK (--parallel 16),
V2 1124/1124 0 errors, V3/V4/V5 green, browser class 3/3 journeys green
(the header assertion normalizes the DOM newline between the two header spans).
