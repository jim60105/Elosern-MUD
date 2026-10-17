# Proposal: Party management help content and assembled acceptance

## Why

Design §3.4, §9 and §11 of `docs/superpowers/specs/2026-10-18-party-member-management-ui-design.md`: rule text removed from the windows moves to the help overlay, the replaced components must leave nothing behind, and the batch needs assembled runtime evidence: an `agent-browser` journey (buy potions for 艾拉, transfer some to 卡恩, re-equip 艾拉, cast a field heal as 艾拉, let 艾拉 open combat through the confirmation, possess 艾拉, walk her through an exit with the whole party following, and confirm the windows are unchanged, and in combat re-equip a companion and observe transfer disabled) and an exercised path for each text command.

## What Changes

- Help overlay (`HelpOverlay.vue` content source) gains the party section: follow rules, transfer rules, combat restrictions, the 系譜 legend, the one-price shop convention and the hotkeys.
- Residual sweep: no remaining references, stories, manifest titles, CSS or `.elosern-root` duplicate rules for `InventoryPanel`, `EquipmentDoll`, `CharacterStatusDrawer`, `SkillBook`, `LineagePanel`, `PartyDrawer`, `ShopPanel`; the manifest is re-frozen at the complete set.
- Assembled acceptance evidence recorded in this change's tasks: the agent-browser journey above and an exercised text path for `給`, `取回`, `裝備 … = 成員`, `買`/`賣 … = 成員`, `使用 … = 成員`, `cast … 由 成員`, `修煉 … = 成員`, `狀態`, `技能`, `系譜`.
- No new rule, protocol or schema. A defect found by the journey is recorded and fixed by a follow-up change outside this change's budget; this change's acceptance stays open until those follow-ups land.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `webclient-contextual-hud`: adds the help-overlay party rules requirement.

## Impact

- `web/webclient-app/components/HelpOverlay.vue` (or its content module), stories `Overlays/HelpOverlay`, Vitest, `component-manifest.json` re-freeze check, `docs/game/commands.md` overview paragraph for the party window, one consolidated browser method if not already covered.

## Effort

**7.5 hours total, strictly less than 8 hours**, including implementation, focused verification, documentation and integration.

## Batch: party member management

Declared implementation order: **32 of 32**. Assembled acceptance of the batch is accepted only after this change.

- depends-on: webclient-main-navigation-hotkeys

### Code and spec conflicts within the new batch

- All client changes: shared `component-manifest.json`, `AppClient.vue` (F; this change only removes residue).
- `webclient-main-navigation-hotkeys`: hotkey list documented here (D).
- `.github/browser-shards.json`: conditional manifest conflict.

### Active change coordination

No active OpenSpec change.
