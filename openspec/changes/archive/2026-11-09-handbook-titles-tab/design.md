# Design: handbook-titles-tab

## Context

Source of truth: `docs/superpowers/specs/2026-11-09-handbook-codex-titles-design.md` (§2 D1, D2, D8, D9, D10; §5). The visual reference is the approved prototype in `docs/design/handbook-codex-titles/`: `HandbookPrototype.vue`, `TitlesTabProto.vue`, `TileWall.vue`, `CodexEmblem.vue` and `prototype-data.js`. The prototype is reference only. Never import it from the app.

Current state (observed):

- `AppClient.vue` mounts `QuestDrawer` inside the generic `HudDrawer` when `store.view.hudDrawer === 'quest'`. It passes `:route-request="store.view.serviceReadRequest"` and no `close-guard`.
- `QuestDrawer.vue` (513 lines) owns the first-level `IconTabs` (`book`, `counter`), the book and the counter bodies. Its `routeRequest` watcher reacts only to `slot === "counter"`.
- `quest-drawer-memory.js` holds `top`, `bookState`, `boardGrade`, `boardBasis` and `selectedByTab`, scoped to `<generation>|<epoch>`.
- `stores/elosern/hud.js`: `requestServiceRead(slot, npcId, section)` writes `ctx.serviceReadRequest = {seq, slot, npcId, section}` for `shop` or `counter` only. `HUD_OVERLAY_NAMES` contains `codex`.
- `AppClient.vue`'s `[hudDrawer, serviceReadRequest.seq]` watcher calls `openServices(request.slot, request.npcId)` for any request whose drawer matches. On a plain `quest` open it also calls `openServices("counter", …)`, in every mode.
- `nav-tools.js`: `{ key: "codex", label: "稱號冊", testid: "nav-tool-codex" }` has no `drawer`, so `DesktopNavigation.activateTool` emits `overlay("codex")` and `OverlayHost` renders `TitleCodexPanel`.
- `QuestDetail.vue` owns the pinned footer (`.quest-detail__actions`, `__why`, `__btn`, `__btn--primary|--ghost|--danger`, `__spacer`) and the abandon arm/disarm focus logic.
- `HudDrawer.vue` already supports `closeGuard` (a guard returning `false` blocks Escape, ✕ and scrim).
- `styles/app-shell.css` has no `.elosern-root` rule for `quest-detail`, `quest-drawer`, `codex-panel` or `title-codex`. This must stay true for every new class.
- `syncHudDrawer` (`stores/elosern/creation.js`) closes the `quest` drawer on any mode change. This change keeps that, so entering or leaving combat closes the handbook.

## Goals / Non-Goals

**Goals:**

- Add a `titles` first-level tab to `QuestDrawer`, rendered by a new `TitleCodexTab.vue`, with the behavior in this change's spec deltas.
- Mount the shared `DetailFooter`, `TileWall`, `CodexEmblem` and `CodexDetail` delivered by `handbook-primitives` (prerequisite).
- Move the 稱號冊 tool from the overlay to the handbook route request.
- Remove `TitleCodexPanel.vue` and the `codex` overlay.

**Non-Goals:**

- No codex (圖鑑) tab. The `lore` drawer and `LoreCodexDrawer.vue` stay unchanged until `handbook-codex-tab`.
- No change to `title_codex` v1, its Python or JS validators, `title_view.py` or any title action adapter.
- No change to the book or counter bodies. Do not move the book or counter markup out of `QuestDrawer.vue` in this change. The new tab must not grow the file by more than the dispatch lines listed in D3.
- No new hotkey and no change to J's opener (`tabToRootAndConfirm("quests")`).
- No `ActionBar` usage.

## Decisions

### D1. Handbook tab model in one pure module

New `web/webclient-app/components/handbook/handbook-tabs.js`:

```js
export const HANDBOOK_TAB_META = Object.freeze({
  book: { label: "任務簿", glyph: "quest_book" },
  counter: { label: "公會櫃檯", glyph: "guild_counter" },
  titles: { label: "稱號", glyph: "codex" },
});
// Tab keys present for one mode, in bar order.
export function handbookTabs({ combat }) {
  return combat ? ["titles"] : ["book", "counter", "titles"];
}
```

`handbook-codex-tab` later inserts `codex` before `titles` in both arrays. Alternative considered: hard-coding the list in `QuestDrawer.vue`. Rejected because the store's route entry needs the same list.

### D2. Route request reuses the `serviceReadRequest` slot

The design's D2 requires "the existing `routeRequest` mechanism". The `routeRequest` prop of `QuestDrawer` is already fed by `store.view.serviceReadRequest`, so the handbook route uses that slot with a new `slot` value. Add to `stores/elosern/hud.js`, beside `requestServiceRead`:

```js
ctx.openHandbook = function openHandbook(tab) {
  const view = ctx.view.value || {};
  if (!handbookTabs({ combat: view.mode === "combat" }).includes(tab)) return false;
  ctx.serviceReadSeq += 1;
  ctx.serviceReadRequest = { seq: ctx.serviceReadSeq, slot: "handbook", npcId: null, section: tab };
  return ctx.openHudDrawer("quest");
};
```

`openHudDrawer` publishes the view. `requestServiceRead` keeps rejecting every slot other than `shop` and `counter`. Edit the `AppClient.vue` watcher:

- The first branch runs only for `request.slot === "shop" || request.slot === "counter"`. A `handbook` request falls through to the ordinary `drawer === "quest"` branch.
- Immediately after that branch, add: `if (request?.slot === "handbook" && seq !== previous?.[1] && previous?.[0] === "quest" && drawer === "quest") return;`. A handbook request that only switches the tab of an already open drawer dispatches no read. A handbook request that opens a closed drawer falls through to the ordinary opening read below, exactly as a plain 任務 opening does.
- In the `drawer === "quest"` branch, when `store.view.mode === "combat"`, call `closeServices("shop")` and return without `openServices("counter", …)`.

Alternative considered: a second `tabRequest` prop. Rejected because D2 names the existing mechanism, and a second sequenced slot would need its own reset in `transport.js`.

### D3. QuestDrawer becomes the tab dispatcher for the new tab

`QuestDrawer.vue` changes are limited to the following:

- New props: `combat: { type: Boolean, default: false }`, `titleCodex: { type: Object, default: null }`. AppClient passes `:combat="store.view.mode === 'combat'"`, `:title-codex="panel('title_codex')"` and `ref="questDrawerRef"`.
- The `routeRequest` watcher consumes each request once. It returns when `!request || request.seq === memory.appliedRouteSeq`, then records `memory.appliedRouteSeq = request.seq` before acting. `request.slot === "handbook"` sets `memory.top = request.section`. The `counter` branch keeps its body. This fixes a stale request being re-applied by the `immediate: true` watcher on every later mount, because `serviceReadRequest` is never cleared on close.
- `topTabs` is built from `handbookTabs({ combat: props.combat })` and `HANDBOOK_TAB_META`. The existing counter disabled and reason fields are kept. The titles tab is `disabled` with `reason` = the panel's `reason.message` exactly when `titleCodexStatus(props.titleCodex) === "unavailable"`.
- Effective `top`: in combat it is `"titles"`. Outside combat, `memory.top === "counter"` gives `counter` only when the counter is enabled. `memory.top === "titles"` gives `titles` only when the titles tab is not disabled. Every other value gives `book`. The computed never writes `memory.top`.
- A new `<TitleCodexTab v-else-if="top === 'titles'" ref="titlesTab" … @action="forward" />` branch. The tab owns its own `role="tabpanel"` root with `:id="panelId('titles')"`. In combat with an unavailable panel, the tab body shows `EmptyState` with the panel's reason.
- `defineExpose({ closeGuard: () => (top.value === "titles" ? titlesTab.value?.guardClose() ?? true : true) })`.
- Header: when `top === 'titles'` and the panel is available, render `<p class="quest-drawer__full-title" data-testid="handbook__full-title">` with the `全銜` kicker and `full_title` verbatim. Copy the layout from `HandbookPrototype.vue` `.hb__full-title`.
- The section `aria-label` becomes `手帳`. The top `IconTabs` `aria-label` becomes `手帳分類`.

AppClient: `<HudDrawer … :close-guard="store.view.hudDrawer === 'quest' ? questCloseGuard : null">` with `const questDrawerRef = ref(null); const questCloseGuard = () => questDrawerRef.value?.closeGuard?.() ?? true;`. `HudDrawer` treats only a strict `false` as a block.

### D4. Session memory

`quest-drawer-memory.js` gains `titlesRail: null` and `appliedRouteSeq: null` (both reset by `clear()`). Title selection reuses `selectedByTab` with keys `titles:<rail key>`. The effective rail is `memory.titlesRail` when it is still present in `titleRail(panel)`. Otherwise it is `defaultTitleRail(panel)`: the first fixed category in closed order holding an unlocked row, else the first category. A ballot rail that vanished falls back to `epithet`. The computed never overwrites the remembered key. Selecting a rail entry writes `memory.titlesRail`.

### D5. Pure title model

New `web/webclient-app/components/handbook/title-codex-model.js`. Every function is pure and takes the committed panel. Exports:

| Export | Contract |
| --- | --- |
| `TITLE_CATEGORIES` | `[{key:"combat",label:"戰鬥"},{key:"spell",label:"法術"},{key:"explore",label:"探索"},{key:"guild",label:"公會"},{key:"clergy",label:"聖職"},{key:"romance",label:"風流韻事",short:"韻事"}]`, the order of the retired `TitleCodexPanel.CATEGORY_TABS` |
| `titleCodexStatus(panel)` | `"absent"` for null, `"unavailable"` when `available !== true`, else `"available"` |
| `titleRail(panel)` | the six categories `{key, label: short ?? label, count: unlocked rows in that category}`, then `{key:"epithet", label:"異名", count: epithet_rows.length}`, then `{key:"ballot", label:"提名", count: pending_ballot.length, hot:true}` only when `pending_ballot.length > 0` |
| `defaultTitleRail(panel)` | as D4 |
| `guildGrade(row)` | for `row.category === "guild"`, the upper-cased letter of `/^g_([a-z])_rank$/` on `row.key`, else `null` |
| `medalItems(panel, rail)` | for a fixed rail, `fixed_rows` of that category in payload order as `{id: row.key, selectable: true, label, locked: !row.unlocked, equipped: equipped.fixed === row.key, grade: guildGrade(row), row}` |
| `titleListRows(panel, rail)` | for `epithet` and `ballot`, QuestList rows `{id: row.display, name: row.display, glyph: "codex", sub, grade: null, progress: null, tracked: false}`. `sub` is `row.basis`, and for an equipped epithet it is `★ 裝備中・${row.basis}` |
| `defaultTitleSelection(panel, rail)` | for a fixed rail the first unlocked row key, else the first row key. For list rails the first row display. `null` when empty |
| `titleDetail(panel, rail, id)` | `{kind: "fixed"|"epithet"|"ballot", id, name, ribbon, emblem, grade, locked, equipped, stamp, subtitle, sections, index}`. Field values follow `TitlesTabProto.vue`'s `detail` computed. `index` is the zero-based ballot position. Returns `null` for an unknown id |
| `titleFooter(detail, { armed })` | the footer model of D6, following `TitlesTabProto.vue`'s `bar` computed and the copy table below |
| `titleIntent(detail, key)` | `equip`: `{action_id:"title.equip", payload:{kind:"fixed", identifier: row.key}}` or `{kind:"epithet", identifier: row.display}`. `confirm-remove`: `{action_id:"title.remove", payload:{display}}`. `accept`: `{action_id:"title.accept", payload:{index: index + 1}}`. `decline`: `{action_id:"title.decline", payload:{}}`. Returns `null` for a disabled or unknown key |

The `guildGrade` key grammar is the only client-side reading of a title key. A row that does not match draws the category emblem instead of a `GradeGem`.

### D6. Shared primitives (from `handbook-primitives`)

`DetailFooter.vue`, `handbook/TileWall.vue`, `handbook/CodexEmblem.vue` (title emblems) and `handbook/CodexDetail.vue` already exist with the contracts in that change's design. This change only consumes them: `CodexDetail` `detail` and `footer` props, `press` and `focus`; `TileWall` `groups`, `selectedId`, `variant` and `select`.

### D7. Titles tab components

All new components live under `web/webclient-app/components/handbook/`:

- `CodexMedalGrid.vue`: `TileWall variant="medal"` over `medalItems`. The medal face is `GradeGem` when `grade`, else `CodexEmblem :name="row.category"`. A locked medal draws a dashed silhouette face. The caption is the row display. Each cell has `data-testid="handbook__medal--<row key>"`.
- `TitleCodexTab.vue`: the rail (`IconTabs` vertical, `show-labels`, `aria-label="稱號分類"`, the `#icon` slot draws `CodexEmblem :name="tab.key"`, `data-testid="handbook__titles-rail"`). The divider before `epithet` follows the prototype's `:deep([data-tab-key="epithet"])` rule. The list column is `CodexMedalGrid` for a fixed rail and `QuestList` (`:rows="titleListRows(...)"`) for `epithet` and `ballot`. The detail column is `CodexDetail`. It also handles the armed state and `guardClose()`. The root is `data-testid="handbook__titles"` with the grid template of `.quest-drawer__body--book` (`--quest-drawer-rail-w` rail, then `minmax(calc(360px * var(--ui-scale)), 0.82fr)` and `minmax(0, 1.18fr)`). Armed state: `armed` (a ref holding the armed row display or null) is cleared by a rail change, a selection change, or a `titleDetail` result whose `id` differs. On arm, `await nextTick(); detailRef.focus("cancel")`. `guardClose()` returns `false` and disarms when armed, else `true`. Footer `press(key)`: `remove` arms, `cancel` disarms and focuses `remove`, and every other key emits `action` with `titleIntent(detail, key)` when that value is non-null.
- Status forms: `"absent"` renders `EmptyState` (glyph `codex`). `"unavailable"` cannot be selected outside combat (the tab is disabled). In combat it renders `EmptyState` with `reason.message`.

Footer testids: `handbook__actions` (root), `handbook__action-reason`, `handbook__equip`, `handbook__remove`, `handbook__remove-cancel`, `handbook__remove-confirm`, `handbook__ballot-decline` and `handbook__ballot-accept`.

### D8. Tool shortcut and naming

- `nav-tools.js`: the `codex` record becomes `{ key: "codex", label: "稱號冊", testid: "nav-tool-codex", handbook: "titles" }`. Update the header comment.
- `DesktopNavigation.vue` `activateTool`: `if (tool.handbook) emit("handbook", tool.handbook); else if (tool.drawer) …`. Add `"handbook"` to `defineEmits`. AppClient binds `@handbook="(tab) => store.openHandbook(tab)"`.
- `stores/elosern/hud.js`: remove `codex` from `HUD_OVERLAY_NAMES` and from the header comment's overlay list.
- `AppClient.vue`: delete the `TitleCodexPanel` import and the `openName === 'codex'` branch. `QuestDrawer`'s `@action` handler stays `onQuestAction`, which already forwards `{action_id, payload}` through `dispatchIntent`, so title intents need no new handler. Delete `onTitleCodexAction` from `composables/intents.js`, its return object, and the AppClient destructuring, after confirming with `git grep -n onTitleCodexAction` that nothing else uses it.
- `components/OverlayHost.vue`: remove the `codex` entries (the overlay-name comment, the `codex` icon key, and the `name === "codex"` subtitle branch).
- Rename: `nav-primary.js` `quests.label` becomes `手帳`. `use-drawers.js` `DRAWER_TITLES.quest` becomes `手帳`. The glyph is unchanged. The region width is unchanged because both labels are two glyphs.

### D9. Copy table (verbatim, human-reviewed)

These strings come from the approved prototype. They are not pinned by any requirement or test.

| Where | Text |
| --- | --- |
| window title, primary nav label | 手帳 |
| first-level tab | 稱號 |
| header kicker | 全銜 |
| rail | 戰鬥 法術 探索 公會 聖職 韻事 ／ 異名 ／ 提名 |
| detail ribbon | `<category label>稱號`, 異名, 異名提名 |
| stamps | 未取得, 裝備中, 提名中 |
| locked section label | 取得條件 |
| footer equip | 裝備 / 已裝備 (disabled) |
| footer reason | ★ 目前裝備中 / 尚未取得，無法裝備 |
| removal | 移除…, 取消, 確認移除, reason 移除後無法恢復，確定要移除這個異名嗎？ (danger tone, `role="alert"`) |
| ballot | 放棄提名, 接受此異名 |
| absent tab | EmptyState headline 稱號冊尚未載入 |

### D10. Removal of the overlay

Delete `components/TitleCodexPanel.vue`, `stories/Overlays/TitleCodexPanel.stories.js` and `tests/overlays/title_codex_panel.test.js`. Remove `Overlays/TitleCodexPanel` from `component-manifest.json` and from the lists in `web/webclient/tests/test_vue_showcase_{action,data,overlays,world}_evidence.py`. In `tests/test_data_independence_js_webclient.py`, drop the removed path from `MIGRATED_FILES` and scan the new `tests/handbook/*.test.js` suites through a separate `HANDBOOK_FILES` tuple (zero findings, no ledger exemption). They cannot join `MIGRATED_FILES`, whose seed pin requires every listed path to be in `seedDebtPaths`. Remove `web/webclient-app/tests/overlays/title_codex_panel.test.js` from both `tools/test_data_freeze.json` and `tools/test_data_lint_seed.json`, so the ledger and the seed stay equal and `tools.test_data_lint` reports no stale path. In `web/tests/browser/test_browser_contextual_hud_stage.py` (the `expected_tools` tuple near line 1676), point `nav-tool-codex` at `[data-testid="handbook__titles"]` instead of the `codex` overlay host. In `docs/development/webclient-vue-frozen-contract-audit.md` §2.3, replace the `title-codex-panel` row with a `handbook__` family row (testids from D7 and D3) and add a dated `handbook-titles-tab` section like the existing per-change sections.

## Risks / Trade-offs

- [A reused `serviceReadRequest` slot could be consumed as a provider read] → D2 adds the slot guard in AppClient. The vitest store test asserts that `openHandbook` dispatches no `services` read.
- [The handbook closes when combat starts, while the old overlay did not] → This is accepted. `syncHudDrawer` already treats `quest` as services-backed, and the tool reopens it in combat.
- [`.elosern-root` duplicates silently override component styles] → Before handoff, grep `styles/app-shell.css` for every new class prefix (`detail-footer`, `codex-detail`, `tile-wall`, `codex-medal`, `title-codex-tab`, `quest-drawer__full-title`) and expect zero matches. Geometry is asserted on the live client (task 5).
- [The main `webclient-desktop-shell` spec still names the primary entry 任務 in requirements this change does not modify] → The label is copy (D9), not pinned by a requirement; the entry, its glyph, hotkey and behavior are unchanged. No further delta is added, since `handbook-codex-tab` modifies the same spec against this change's archived text.
- [Eight labelled rail entries overflow the drawer body at 1451×790 with the default 58px tab height] → The titles rail sets `--icon-tabs-tab-h` to 52px; the live geometry journey (task 5.2) guards it.
- [A confirmed removal or an answered ballot unmounts the focused footer control] → TitleCodexTab returns focus that was inside the tab to the rail's selected entry, as QuestDrawer already does, so Escape still reaches the drawer.
- [The `g_<letter>_rank` grammar is a data convention] → It lives in one pure function with a synthetic-key test, and a non-matching row falls back to the emblem.

## Review document (human-reviewed)

This section is the named review document. A human reviews it at apply time, and no requirement or automated test covers it:

1. Visual fidelity of the titles tab against Storybook `Design/Handbook` (titles states) at 1451×790 and 2560×1440: medal faces, the dashed locked silhouette, the rail divider, the ribbon, the stamp and the full-title kicker.
2. Every string in the D9 copy table, plus the renamed 手帳 label.
3. That the quest book and counter detail footers look unchanged after the extraction.

The apply worker attaches screenshots of the live client at both viewports to the final handoff for this review.
