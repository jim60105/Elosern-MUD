## Why

The router cutover (`webclient-declarative-frame-stack`) made exploration frames declarative and left a transitional dual frame shape for the unmigrated families. Services surfaces and their hosted drawers, the combat dock, and the creation wizard still freeze menu copies, still re-home through `rehomeFrame`, still signature-compare through `dockRawByKey`, and still lean on the empty-stack `router.reset` fuse. Every remaining stale-frame surface dies in this change: their push sites convert to descriptors, the transitional legacy frame shape is deleted, the full deletion list from the design doc completes, and the drawer-combined transition rules get specified (a pop that removes a drawer's hosted frame closes the drawer and discards its local state).

## What Changes

- Add the services, combat, and creation families to the resolver table (spec-visible table extension): `services.root|guild|board|quests|quest-detail{questIndex}|shop|stock|sell|confirm{questIndex}`; `combat.root|categories|category{categoryIndex}|group{categoryIndex, groupIndex}|skill{skillKey}|target{skillKey}|forfeit`; `creation.root|presets|form{view}|confirm{kind, presetKey?}`.
- **BREAKING (internal architecture)**: delete the transitional legacy `{menu, focusRow, focusCol}` frame shape from `keyboard_router.js`; frames are declarative only, unknown shapes throw.
- Combat purity exception, declared spec-visible: the combat resolver preserves selection (`focusSkillKey`, page, scale, AREA candidates) through the unchanged `CombatMenu.rebuildForPanel` seam inside the combat model; the prohibited category is commit-driven refresh/rehome/replace over copied menus, and after this change none exists for any family (repeat-resolution idempotency scenario added).
- Cut all remaining push sites over: services submenus, quest-detail and abandon-confirm frames (with their `SERVICE_SURFACE_DRAWERS` hosting), the full combat step chain (categories/group/skill/scale/target/forfeit), creation presets/form-marker/confirm frames.
- Drawer coupling rules: a pop that removes a drawer's hosted surface closes that drawer and clears its local selection/quantity/confirmation state; a descendant-only pop leaves the drawer and its surviving frame intact; closing a drawer initiates exactly one pop (existing contract restated inside the declarative model).
- Delete `rehomeFrame`, `dockRawByKey`, and the wrapped empty-stack `router.reset` fuse; teardown posts a declarative one-frame root stack for every mode, so the stack is never empty (design §5.4).
- `view.combatMenu` and combat step views derive from the declarative stack with unchanged item shapes; components expected zero-change or binding-source-only; Vitest suites and `stories/fixtures.js` frame fixtures move in the same commit.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `webclient-frame-resolution`: extends the resolver table to all families, amends the purity rule with the declared combat-model exception, adds the drawer-combined transition requirement, and completes the final-state requirement (no legacy frame shape, no copy-driven refresh anywhere, non-empty stack without the fuse).

## Impact

- Code: `keyboard_router.js` (dual-shape deletion), `stores/elosern.js` (services/combat/creation paths + deletion list), `stories/fixtures.js`, Vitest suites, Node-gate suites for the shape deletion.
- Tests: browser methods for combat step freshness, drawer-hosted pop/state-discard coupling, creation confirm text following the committed panel; one-class local budget.
- Server/protocol/Python/player-command surface: zero changes; `docs/game/commands.md` untouched.
- Depends on: `webclient-declarative-frame-stack` (consumes the declarative core; archives after it). Order per design doc §9: feedback → registry → stack → this.
