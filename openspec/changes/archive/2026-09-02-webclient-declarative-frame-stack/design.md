## Context

The registry change landed the exploration-family resolver (`createFrameResolver`, bridge-exposed `resolveFrame`). The shipped path still copies menus into router frames at push time and rebuilds only when a root-items signature changes, which the exploration root never does across rooms. The approved architecture is `docs/superpowers/specs/2026-09-02-declarative-frame-refresh-design.md` (D1, §5.1–§5.6); this document covers cutover mechanics for the router core and the exploration family — the family where the bug is observable. Services/drawers, combat, and creation migrate in `webclient-services-combat-creation-frames`.

## Goals / Non-Goals

**Goals:**

- Router frames declarative (`{descriptor, focusKey}`) with resolve-on-access, key-based focus, cascade-pop degradation, fixed teardown, zero timers.
- Exploration push sites (root, move, look, interact, wait, target, keywords, suggestions) converted; `rebuildFocusMenu`, `lastMenuSig`/`lastSuggSig`, `replaceSuggestionsFrameInPlace` deleted.
- The user-visible bug (stale move submenu, silent second click) dies with a committed red-first browser regression.

**Non-Goals:**

- Services/combat/creation frame migration, drawer-coupling rules, the combat `rebuildForPanel` resolver exception, deletion of `rehomeFrame`/`dockRawByKey`/the `router.reset` fuse (follow-up change — they still serve unmigrated surfaces).
- Registry changes, protocol/server changes, component redesign, action-result surfacing (done).

## Decisions

**D-A: Resolve-on-access inside the router, not pre-resolved push.** Every router entry point touching a declarative frame (`currentMenu`, `itemAt`, `move`, `confirm`, `trail`) calls `resolve(descriptor)`. The alternative (store re-pushes resolved menus on commit) re-creates dual-tracking and leaves reads between commits stale. Resolution is a pure builder over committed panels; the router is only touched on render/keydown/click.

**D-B: Transitional dual frame `{descriptor, focusKey} | {menu, focusRow, focusCol}`.** The router accepts both shapes; a legacy frame behaves exactly as today's frozen copy. This keeps the follow-up change (services/combat/creation) from having to migrate every surface while the router core sits unstable, and each family's cutover commit stays reviewable. The dual form is deleted by the follow-up change; the spec text marks it migration-only so it cannot fossilize.

**D-C: `focusKey` is the only focus state for declarative frames.** Geometry recomputes from the resolved menu on demand. Key loss picks the nearest surviving row by index (ties earlier), generalizing the suggestions rule that `replaceSuggestionsFrameInPlace` owned. `confirm` (keyboard or pointer) writes the item's key back before dispatch.

**D-D: Degradation is a stack invariant checked on access, with the suggestions status split.** Unresolvable top frame → pop until resolvable (root: single disabled reason row). Commits are atomic and identity panels never arrive as subsets, so unresolvable is always real loss — no debounce (design §5.3). Suggestions: `generating|ready|degraded` resolve to content (never pop); `unavailable` resolves to the marker, and because the options-surface contract forbids any pane at that status, the stack rule leaves the frame to the exploration root without a reason row.

**D-E: Teardown drives the existing decision point with a one-frame stack.** The event set (mode switch, epoch reset, transport loss, no-puppet) replaces the stack with the mode's root frame — declarative for exploration, the legacy root copy for unmigrated modes (their root menus are room-stable; their staleness dies with their family's change). The empty-stack fuse stays until the last mode is declarative; deleting it while combat can still be legacy would remove a live protection.

**D-F: Component item shapes frozen.** `view.rootMenu`/`view.dockTrail` keep producing identical item shapes; Storybook fixtures move in the same commit if anything shifts.

## Risks / Trade-offs

- [Dual-frame router hides a missed migration] → the follow-up change deletes the legacy branch entirely; a router test asserts unknown frame shapes throw.
- [Focus mapping diverges from old index behavior in edge cases] → Vitest pins same-key survival, nearest-row fallback, null-on-empty; the browser regression covers the real path.
- [Suggestions behavior cited by `webclient-options-surface` (in-place rows, focus survival) must survive deleting its implementation] → the new status-driven requirement restates those observables; the options-surface suite runs untouched as an oracle.
- [Resolver cost per render] → builders already run per publish; frames hold < 20 rows; memoization deferred (cacheable later because resolution is pure).

## Migration Plan

One commit (router + store exploration paths + tests + fixtures); browser regression committed red first in the same change. Rollback = revert; no data/protocol residue.

## Open Questions

None blocking.
