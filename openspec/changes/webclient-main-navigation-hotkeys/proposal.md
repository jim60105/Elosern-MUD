# Proposal: Main navigation and window hotkeys

## Why

Design §8 of `docs/superpowers/specs/2026-10-18-party-member-management-ui-design.md`: the labelled entries become 隊伍, 任務 and 地圖; the icon tool group holds 信件, 圖鑑, 稱號冊, 肖像圖庫 (when available) and 說明, with 設定 fixed at the end; 隊伍 opens the party window on its last tab; hotkeys P B C K L J M act only outside text inputs. Today the bar carries 角色狀態/任務/背包/地圖/設定 and a tool group starting with 技能系譜.

## What Changes

- `DesktopNavigation.vue`: primary region 隊伍/任務/地圖 (隊伍 present in exploration and combat; 任務 and 地圖 absent in combat as today), then the `工具` group (`nav-tools.js`: letters, lore, codex, gallery, help), then 設定 last; stable trailing placement retained.
- `隊伍` opens the party window on its remembered tab; the old 角色狀態 and 背包 entries and the 技能系譜 tool are removed (their surfaces live in the window).
- A single hotkey handler in the app shell (`composables/use-window-hotkeys.js`) for P B C K L J M with the text-input and modal guards.
- The 隊伍 availability follows the committed `party` panel; the exploration panel's availability fields stay unchanged (no protocol change).
- Help overlay hotkey list updated in `party-management-acceptance`.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `webclient-desktop-shell`: the tool-group and stable-placement requirements, plus an added hotkey requirement.

## Impact

- `web/webclient-app/components/DesktopNavigation.vue`, `nav-tools.js`, `AppClient.vue`, new composable, stories `Core/DesktopNavigation`, Vitest and Node tests for navigation geometry, one browser method.

## Effort

**6 hours total, strictly less than 8 hours**, including implementation, focused verification, documentation and integration.

## Batch: party member management

Declared implementation order: **29 of 30**.

- depends-on: webclient-shop-window

### Code and spec conflicts within the new batch

- `webclient-party-window-member-tab`, `webclient-party-status-tab`, `webclient-party-lineage-tab`: rerouted the old 角色/背包/技能系譜 openers that this change removes (F on `AppClient.vue`, `nav-tools.js`; ordered).
- `party-management-acceptance`: documents the hotkeys in the help overlay (D).
- `.github/browser-shards.json`: conditional manifest conflict.

### Active change coordination

No active OpenSpec change.
