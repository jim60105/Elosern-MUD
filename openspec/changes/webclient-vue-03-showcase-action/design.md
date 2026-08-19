## Context

Part **B2** (showcase wave, Wave B serial chain; depends on B1). The action dock is the highest-churn
surface (keyboard + pointer), so its contract is fixed in the requirement and exercised offline before any
transport wiring.

## Goals / Non-Goals

**Goals** — the action-dock family as documented, offline, component-tested SFCs; the manifest extended.
**Non-Goals** — no live keyboard router dispatch (C4), no store (C1), no other families.

## Decisions

- **D1 — Present the exact server shape; emit intents only.** Cards/rows render the `context_actions` v5
  shape verbatim; activation emits the OOB action intent (no local dispatch yet). The `action-`/`target-`
  keys and a `data-testid` are component-owned (preserved here so C3/C4 keep the browser contract).
- **D2 — Extend, don't restructure, the manifest.** B2 appends the action-dock keys to B1's manifest;
  B5 freezes it. This keeps Wave B serial (one coordination point).

## Risks / Trade-offs

- **Menu enumeration can balloon** → presenters render bounded, context-specific menus (matching the suite
  design; no unbounded room enumeration).
- **Focus/disabled confusion in tests** → explicit story states for focused, hovered, and disabled cells.

## Migration Plan

Offline/Storybook only; rollback = delete the family + its manifest keys. B1 and all gates unaffected.

## Open Questions

- None.
