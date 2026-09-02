## Why

The registry (`webclient-frame-resolver-registry`) can derive exploration menus from committed state, but the shipped keyboard router still stores frozen menu copies per frame, the store rebuilds only on a root-items signature, and open submenus keep showing (and submitting) the previous room's rows — the silent-failure bug in `docs/superpowers/specs/2026-09-02-declarative-frame-refresh-design.md` §1–§2. This change performs the router cutover and migrates the exploration family (the bug's surface): frames become declarative `{descriptor, focusKey}` stacks, the exploration refresh machinery is deleted, unresolvable frames auto-pop, and the suggestions frame gets its status-driven rules. Services/drawer-hosted, combat, and creation frames are migrated by the follow-up change `webclient-services-combat-creation-frames`, which finishes the deletion list.

## What Changes

- **BREAKING (internal architecture)**: `web/static/webclient/js/elosern/keyboard_router.js` frames become `{descriptor, focusKey}` (transitional dual form: frames still carrying a legacy `menu` copy pass through unchanged, deleted by the follow-up change); `createRouter({resolve})` injects the store resolver; reads operate on `resolve(descriptor)` at access time. Node-gate tests updated in the same commit.
- Exploration push sites in `web/webclient-app/stores/elosern.js` (root, move, look, interact, wait, target, keywords, suggestions) become descriptor pushes; `rebuildFocusMenu` and its `lastMenuSig`/`lastSuggSig` gates are deleted; `replaceSuggestionsFrameInPlace` is deleted — the suggestions frame resolves declaratively and keeps its four-status contract.
- Focus tracking: frames store `focusKey`; re-resolution lands on the same-key row's new geometry, nearest surviving row on key loss (ties earlier), null when empty; any confirm writes the focused key back.
- Degradation: unresolvable identity frames auto-pop one level (cascade while unresolvable, opener-row focus, no timers — design §5.3 jitter analysis); an unresolvable root renders one disabled server-reason row; suggestions `generating`/`ready`/`degraded` never pop, while an open suggestions frame on an `unavailable` envelope deterministically returns to the exploration root (no reason row — the surface owns no pane at that status).
- Teardown (declarative modes): mode switch / epoch reset / transport loss / no-puppet resets the stack to the mode's root descriptor from the single teardown decision point; the stack never sits empty in a declarative mode.
- `view.rootMenu`/`view.dockTrail` derive from the declarative stack with unchanged item shapes; components expected zero-change or binding-source-only. Vitest suites and `stories/fixtures.js` updated in the same commit.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `webclient-frame-resolution`: adds the declarative stack rules — descriptor-only storage, key-based focus tracking, cascade pop with root disabled-reason fallback, the suggestions status split (`generating` exempt, `unavailable` exits to root), the teardown rule, and dispatch-time payload freshness.

The combat dock and hosted drawers keep their shipped observable contracts through this change via the transitional legacy-frame pass-through; their declarative rules arrive with the follow-up change.

## Impact

- Code: `keyboard_router.js` (UMD, in place with its Node gate), `stores/elosern.js` exploration paths, component bindings only if shapes shift, Vitest suites, `stories/fixtures.js`.
- Tests: the existing three-exit south-gate browser fixture (commit `1de5d1d`) gains the failing regression first, then turns green; store-level Vitest covers freshness, focus keys, pop/cascade, suggestions status split, teardown.
- Server/protocol/Python/player-command surface: zero changes; `docs/game/commands.md` untouched.
- Depends on: `webclient-frame-resolver-registry` (consumes the registry; archives first so this delta can extend its capability). Blocks: `webclient-services-combat-creation-frames` (finishes the cutover; deletes the dual-form pass-through). Order per design doc §9: feedback → registry → this → services/combat/creation.
