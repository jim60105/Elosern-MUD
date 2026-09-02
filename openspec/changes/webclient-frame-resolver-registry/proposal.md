## Why

Every pushed action-dock frame (Move, Look, Interact, Wait, target affordances, scripted keywords, Suggestions, service drawers, combat steps) freezes the panel rows as a copy taken at open time, so after any committed panel update the open frame keeps showing stale rows and its rows submit stale payloads. The upstream push protocol is healthy — the server already publishes a fresh snapshot after every command and every action completion, including rejections — so the defect is entirely the client's last hop. The fix is the declarative-frame model approved in `docs/superpowers/specs/2026-09-02-declarative-frame-refresh-design.md` (D1). This change is its foundation step: the store-side resolver registry that derives every menu frame from committed state on demand.

## What Changes

- Add a store-owned resolver registry in `web/webclient-app/stores/elosern.js` that maps a frame descriptor `{source, params}` to a menu derived from the committed panels at access time, built on the existing `ExplorationMenu` / `ServiceMenu` / `CombatMenu` / `CreationMenu` models.
- Implement the finite descriptor table defined by the delta spec — every source the action dock pushes today, with its required params (identity-bearing exploration frames, `questIndex` for quest-detail/confirm, `categoryIndex`/`groupIndex`/`skillKey` for combat steps, `view` for creation form frames, `kind`/`presetKey` for creation confirms).
- Define the shared degradation result: a descriptor that no longer resolves (identity absent, panel unavailable, resolver throw) yields an unresolvable marker carrying the server-authored `reason.message` when present; consumers decide pop-versus-disabled per the follow-up change's rules.
- Expose the registry through the store's UMD/ESM surface with a pure functional contract (same committed state and params → deep-equal menu, no internal mutation), so the keyboard router can consume it by injection without importing store internals.
- No behavior change for players: this change adds the resolver alongside the existing copy-based frames; switching the router and the ~20 push sites to descriptors is the dependent change `webclient-declarative-frame-stack`.

## Capabilities

### New Capabilities

- `webclient-frame-resolution`: the descriptor-to-menu resolver registry — source vocabulary, committed-state-only reads, pure functional derivation, first-wave source coverage, and the shared unresolvable degradation marker.

### Modified Capabilities

None. No shipped requirement's behavior changes in this step; the frame-freshness and degradation requirements land with the dependent change that makes frames declarative.

## Impact

- Code: `web/webclient-app/stores/elosern.js` (registry + source bindings); a new sibling module `web/webclient-app/stores/frame-resolvers.js` keeps the registry testable without the full store mount.
- Tests: new Vitest suite under `web/webclient-app/tests/` deriving frames from synthetic committed snapshots; the dependency-free Node gate and existing suites stay green untouched.
- Servers, OOB protocol, Python surface, player commands: zero changes. `docs/game/commands.md` untouched.
- Depends on: `webclient-action-result-feedback` lands first (shared `stores/elosern.js`, serialized per design doc §9; no functional coupling). Blocks: `webclient-declarative-frame-stack` (consumes the registry and must archive after this change, whose delta creates the `webclient-frame-resolution` capability it extends) and `webclient-services-combat-creation-frames` (the drawer/combat/creation cutover slice).
