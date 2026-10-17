# Proposal: Party window shell and 成員 tab

## Why

Design §3.2, §6 and §6.1 of `docs/superpowers/specs/2026-10-18-party-member-management-ui-design.md`: one party window, styled after the quest drawer, presents the whole party through a member rail and first-level tabs; the 成員 tab shows bond, membership, intimate state and member actions for a companion, persona fields for the commander, and the invite target for an empty slot. It replaces `PartyDrawer`.

## What Changes

- New `PartyWindow.vue` (shell: `WindowFrame`, tabs 成員/背包/狀態/技能/系譜, purse extra, `MemberRail` from `party` v3, `party.view_member` dispatch, remembered tab and member, server-fallback reset) and `PartyMemberTab.vue` (bond pips, membership tags, intimate, 請其離隊 two-step, 人物卡 → `NpcPersonaEditor`, 附身/解除附身, commander persona with 編輯人物設定, 空位 invite descriptor). Tabs not yet implemented render the registry-unavailable state of their panel and no invented content (they land in the next changes).
- Every current opener of the party drawer opens the window on 成員; activating a companion figure on the stage lineup opens 成員 with that companion selected (design §8).
- **BREAKING (pre-release)** delete `PartyDrawer.vue` with its story, manifest title `Overlays/PartyDrawer`, tests and any `.elosern-root` duplicate rules.
- Persona editing moves from the drawer to the 成員 tab.

## Capabilities

### New Capabilities

- `webclient-party-window`: the window shell, rail behaviour, session memory, no-rule-text rule and the 成員 tab.

### Modified Capabilities

- `webclient-party-panel`: the possession-controls requirement moves to the 成員 tab (renamed).
- `persona-editing`: the persona sections move to the 成員 tab (renamed).
- `webclient-component-showcase`: the deferred-surface scenario names the party window.

## Impact

- `web/webclient-app/components/PartyWindow.vue`, `PartyMemberTab.vue`, `AppClient.vue`, `composables/use-drawers.js`, `composables/use-status-drawer-persona.js` (moved), `components/CompanionLineup.vue` activation, stories, `component-manifest.json`, Vitest tests; deletions listed above.

## Effort

**7 hours total, strictly less than 8 hours**, including implementation, focused verification, documentation and integration.

## Batch: party member management

Declared implementation order: **22 of 30**.

- depends-on: webclient-window-primitives
- depends-on: party-member-panel
- depends-on: character-panel-v8-viewed-member

### Code and spec conflicts within the new batch

- `character-panel-v8-viewed-member`: shared spec requirement `persona-editing` (renamed here after that change modified it; S, ordered; informational archive notice not expected because the FROM header exists in main).
- `webclient-party-bag-tab`, `webclient-party-status-tab`, `webclient-party-skill-tab`, `webclient-party-lineage-tab`: shared files `PartyWindow.vue`, `AppClient.vue`, `component-manifest.json` (F; ordered); each fills one tab.
- `webclient-shop-window`: reuses the shared viewed-member selection (D) and shares `AppClient.vue` (F).
- `webclient-main-navigation-hotkeys`: shares `AppClient.vue`, `use-drawers.js` (F; ordered).

### Active change coordination

No active OpenSpec change. `NpcPersonaEditor` is reused unchanged.
