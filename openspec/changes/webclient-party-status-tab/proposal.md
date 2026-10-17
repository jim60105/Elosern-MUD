# Proposal: Party window 狀態 tab

## Why

Design §6.3 of `docs/superpowers/specs/2026-10-18-party-member-management-ui-design.md`: the 狀態 tab shows the viewed member's hero row with the guild `GradeGem`, gauges, trait rows with a breakdown waterfall, condition rows with source detail, and an honest disguise footer, always with true values. It replaces `CharacterStatusDrawer`.

## What Changes

- New `PartyStatusTab.vue` rendering `character` v9 (viewed member, both modes) and the `party` v3 gauges; reuses `GradeGem`.
- Every opener of the character-status drawer (the 角色 navigation entry until `webclient-main-navigation-hotkeys`, the HUD openers) opens the party window on 狀態.
- **BREAKING (pre-release)** delete `CharacterStatusDrawer.vue`, `character-status-drawer.css`, `use-status-drawer-character.js`, `use-status-drawer-status.js`, their story `Data/CharacterStatusDrawer`, tests and `.elosern-root` duplicate rules; remove the drawer requirement.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `webclient-party-window`: adds the status tab requirements.
- `webclient-contextual-hud`: removes the character-status drawer requirement.
- `webclient-component-showcase`: the status/skill surfaces and breakdown-story requirements name the status tab.

## Impact

- `web/webclient-app/components/PartyStatusTab.vue`, `PartyWindow.vue`, `AppClient.vue`, `composables/use-drawers.js`, stories, manifest, Vitest; deletions above.

## Effort

**6 hours total, strictly less than 8 hours**, including implementation, focused verification, documentation and integration.

## Batch: party member management

Declared implementation order: **25 of 30**.

- depends-on: webclient-party-bag-tab
- depends-on: character-skill-growth-fields

### Code and spec conflicts within the new batch

- `webclient-party-bag-tab`: shared showcase requirements "The status, character, and skill surfaces…" and "Breakdown-state stories…" (S; that first, this delta keeps its edits); shared `PartyWindow.vue`, `AppClient.vue`, manifest (F).
- `character-panel-v8-viewed-member`: last modified the drawer requirement this change removes (S; ordered).
- `webclient-party-skill-tab`: re-modifies "The status, character, and skill surfaces…" (S; ordered after this).
- `webclient-main-navigation-hotkeys`: replaces the 角色 entry routed here (F; ordered).

### Active change coordination

No active OpenSpec change.
