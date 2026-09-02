## Context

Exploration frames are declarative; `keyboard_router.js` still accepts a transitional legacy `{menu, focusRow, focusCol}` shape, and `rehomeFrame`, `dockRawByKey`, the `router.reset` fuse, and the services/combat/creation push sites still serve the unmigrated families. The registry currently implements only the exploration family. This change completes design §5.2–§5.5's deletion list and table.

## Goals / Non-Goals

**Goals:**

- All dock frames declarative; legacy frame shape and every copy-driven refresh mechanism deleted.
- Drawer-hosted transitions specified with their state-discard contract; combat selection preserved through the declared model-state exception.
- Teardown posts a declarative one-frame root stack for every mode; the empty-stack fuse is gone because the stack is never empty.

**Non-Goals:**

- Protocol/server changes; component redesign; anything touching the options surface's four-status contract (already restated and passing).

## Decisions

**D-A: Family-at-a-time resolver additions, one commit.** Each family's resolver is a thin binding from its table params to its existing builder call (`ServiceMenu.buildMenus` + `questMenuFor`/`confirmMenu`; `CombatMenu.buildMenus`/`openCategory`/`openGroup`/`openSkill`/`openSkillTargets` + `rebuildForPanel` seam; `CreationMenu.buildMenus` + confirm items from the committed panel). Alternatives (rewriting builders stateless) rejected: the builders are the shipped contract; wrapping them preserves behavior exactly.

**D-B: Combat purity exception is declared, not smuggled.** The delta amends the purity requirement: resolver reads/writes limited to the combat model's own selection state through `rebuildForPanel`, with a repeat-resolution idempotency scenario. The prohibition keeps its teeth by category: commit-driven refresh/rehome/replace over copied menus. A grep-level acceptance (no `rehomeFrame`, `replaceMenu`-as-refresh, `lastMenuSig`-style signature gates) is asserted by a router/store contract test.

**D-C: Drawer-hosted pops are stack events, not drawer events.** The drawer follows the stack (single source of truth per `webclient-contextual-hud`): the frame-hosting watcher already opens the matching drawer for the current surface; when a declarative pop removes the hosted surface's frame, the same watcher closes the drawer and the existing payload-loss cleanup discards selection/quantity/confirmation state. Closing the drawer calls one `popMenu` exactly as today. No new drawer state is introduced.

**D-D: Creation form-marker frames become a `creation.form{view}` descriptor** resolving to the same empty marker menu, so Escape still pops one level without discarding typed values (typed values live in the creation model/overlay, untouched).

**D-E: Fuse deletion is structural, not defensive.** With every family declarative and teardown posting a one-frame stack, the stack cannot be empty; `keyboard_router.js` throws on an empty stack read instead of the store catching it, converting the old runtime fuse into a testable invariant.

## Risks / Trade-offs

- [Combat chain conversion touches the most coupled store code] → step-by-step descriptor parity: each combat descriptor resolves via the same builder call the current site makes; Vitest pins each step's menu to the current builder output before conversion, converts, and re-pins.
- [Drawer close/pop double-counting] → the single-path rule is spec'd and browser-tested (Escape from a hosted frame: exactly one pop, drawer closes once).
- [Deleting the fuse exposes a stack-empty path] → the router throws loudly on empty-stack reads; tests cover teardown for all three modes plus transport loss.

## Migration Plan

One commit per family group inside the change (services+drawers, combat, creation, deletion sweep), all landing together. Rollback = revert.

## Open Questions

None blocking.
