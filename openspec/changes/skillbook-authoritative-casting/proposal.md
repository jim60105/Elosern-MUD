## Why

SkillBook currently exposes practice and a typed cast hint, leaving ordinary skill use without a graphical target-selection path. Its literal `combat` badge labels skills that permit field use incorrectly; a coherent casting workflow and a redesigned book should make availability and consequences readable without memorizing keys, as architecture decision D14 requires.

## What Changes

- Add an on-demand, server-authored versioned skill-use preview and an allowlisted field-cast action, connecting SkillBook to the existing deterministic settlement and field-combat initiation APIs without composing commands.
- Support NONE, SELF, SINGLE and explicit AREA targets, the existing monster-anchored AREA opening behavior, and allowed scales with authoritative costs and disabled reasons. Revalidate current state before mutation.
- Keep one keyboard/focus owner for cast selection through the existing action dock. Opening use during combat hands control to the existing combat Skills route, without submitting a field cast or introducing a second combat implementation.
- Replace the misleading `combat` field-use badge with truthful Traditional Chinese wording or an equally unambiguous affordance. Separate field permission from current cast availability and from the warning that a monster target starts combat.
- Redesign SkillBook's information hierarchy and use/practice discoverability. The future apply worker must read the UI skills, design the actual visual and interaction solution before editing, and verify the live browser surface; this proposal supplies acceptance constraints, not a mockup.
- **BREAKING**: remove the SkillBook cast-syntax footer as its prescribed primary entry, updating the corresponding HUD contracts and fixtures. Text casting remains supported with unchanged syntax and mechanics.
- Preserve practice, passive read-only browsing, category/group order, offline deterministic play and existing combat behavior. Update player documentation and test traceability/shard ownership with implementation.

## Capabilities

### New Capabilities

- `webclient-skillbook-casting`: on-demand skill-use read model, exact field intent, deterministic routing, committed refresh, accessible selection and redesigned SkillBook acceptance.

### Modified Capabilities

- `webclient-action-dispatch`: add `explore.skill_preview` and `explore.cast` to the exact production allowlist.
- `webclient-oob-protocol`: register the read-only `skill_use` panel and expose only epoch-scoped presentation selection through read context.
- `webclient-contextual-hud`: replace the prescribed cast-syntax footer while retaining drawer lifecycle, skill counts and practice workflow.

## Impact

One bounded engineer-day vertical slice, reusing the working rules preview, field initiation, settlement, dispatcher and dock router. Affected seams are `world/rules/action_preview.py`, `combat_initiation.py` and a narrow shared field-cast entry; `commands/action.py` if its existing routing is extracted; WebClient action/presentation registration and schemas; mirrored browser validation/store/router; SkillBook, AppClient/composables, details, relevant styles/stories; focused tests and `docs/game/commands.md` / `docs/game/command-reference.md`. No new game mechanic, content change, dependency, persistent schema, migration or compatibility layer is proposed. A single selected-skill preview bounds publication size and avoids sending every skill-by-target-by-scale combination.

## Non-goals

No new exploration root entry, arbitrary mixed monster/non-monster AREA initiation, combat shorthands outside combat, invented effect context, balance/progression changes, innate-condition suppression, broad HUD refactoring or fixed visual mockup.

## Batch:

depends-on: none
code-conflicts: equipment-condition-hud-attention (shared browser protocol registration/validation and parity fixtures; AppClient/composable or app-shell.css integration if touched; shared test ownership manifests).

## Dependency and Conflict Matrix

| Change | Dependency | Contract overlap | Application constraint |
| --- | --- | --- | --- |
| `equipment-condition-hud-attention` | None | Both modify `webclient-contextual-hud`, but distinct requirements. Its status schema/provenance and attention rules remain unchanged here. Potential shared protocol, shell and manifest edits. | Reconcile shared hunks and schema parity against the landed primary branch; serialize shared-file edits if applying concurrently. No semantic ordering required. |
| Existing targeting, freeform casting, cast settlement and field initiation | Already landed | Reused gameplay authority | Preserve their semantics; add only the shared transport entry and pure preview seam needed here. |
