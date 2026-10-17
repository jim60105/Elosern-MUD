# Proposal: Party window 系譜 tab

## Why

Design §6.5 of `docs/superpowers/specs/2026-10-18-party-member-management-ui-design.md`: the 系譜 tab lists the viewed member's skill graphs (roots joined with ‧, node diamonds, owned/total, 可解鎖) and draws the selected graph with merge nodes once, edges labelled with minimum level and non-colour node states; selecting a node opens it in 技能. It replaces `LineagePanel`.

## What Changes

- New `PartyLineageTab.vue` rendering `lineage` v2 (viewed member): grouped list with diamonds and a detail graph laid out by `depth` (siblings spread deterministically by payload order), edge labels, node selection → 技能 tab.
- The tool-group 技能系譜 opener opens the party window on 系譜 until `webclient-main-navigation-hotkeys` removes that tool.
- **BREAKING (pre-release)** delete `LineagePanel.vue`, its story `Overlays/LineagePanel`, tests and `.elosern-root` duplicate rules.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `skill-lineage-panel`: the window requirement becomes the 系譜 tab (renamed).
- `webclient-party-window`: adds the lineage tab requirements.

## Impact

- `web/webclient-app/components/PartyLineageTab.vue`, `PartyWindow.vue`, `AppClient.vue`, `components/nav-tools.js` routing, stories, manifest, Vitest; deletions above.

## Effort

**6 hours total, strictly less than 8 hours**, including implementation, focused verification, documentation and integration.

## Batch: party member management

Declared implementation order: **28 of 31**.

- depends-on: webclient-party-skill-tab
- depends-on: lineage-panel-v2-graphs

### Code and spec conflicts within the new batch

- `lineage-panel-v2-graphs`: last modified the window requirement renamed here and edited `LineagePanel.vue` (S/F; that first).
- `webclient-party-skill-tab`: node selection targets its tab; shared `PartyWindow.vue`, manifest (F; that first).
- `webclient-main-navigation-hotkeys`: shares `nav-tools.js`/`AppClient.vue` (F; ordered).

### Active change coordination

No active OpenSpec change.
