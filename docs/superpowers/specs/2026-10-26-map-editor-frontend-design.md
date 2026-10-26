# Standalone Map Editor Frontend Design

**Date:** 2026-10-26
**Status:** Visual and interaction direction approved section by section in conversation; written-spec review pending.
**Authority:** Amends the [architecture design](2026-10-26-map-editor-design.md) and the [frontend requirements](2026-10-26-map-editor-frontend-requirements.md) where this document says so. On every other point those documents still govern.
**Prototype:** `docs/design/map-editor/` (Storybook title `Design/MapEditor`). It is a reference prototype with mock data, outside the component-coverage manifest.
**Implementation status:** Not implemented by this document.

This document is the frontend specialist deliverable that §12.3 of the architecture design requires before editor UI work (P11 onward). It records the approved layout, visual language, state presentation, and keyboard contract. It also records three product decisions that change the earlier documents.

## 1. Decisions that amend the earlier documents

| # | Decision | Amends |
| --- | --- | --- |
| D1 | **The editor uses the game's visual language.** It uses the same ink-night palette, warm paper text, gold hairlines and focus accent, serif display headings, map-drawer pill tabs with key chips, and map ink glyphs. Seal red is reserved for errors. The editor imports only `web/webclient-app/styles/tokens.css`, `styles/fonts*.css`, and the pure `lib/ui_scale.js` from the game tree. This is the GM portal's boundary plus the scale function, enforced by an equivalent import-boundary check. It never imports the game shell CSS, stores, components, or transport. | Requirements §2 ("do not inherit the game client's … decorative theme") and §11 ("no … game-theme resemblance is mandated") |
| D2 | **The supported viewports are the project's desktop contract, 1451×790 (reference) and 2560×1440.** Chrome scales with the game's `--ui-scale` formula (`clamp(1, min(h/790, w/1451), 1.4)`), and `--text-xs` (16 px at scale 1) is the smallest rendered text. The 1280×800, 1920×1080, and 960×720 variants are withdrawn. WCAG 2.2 AA and 200 % browser zoom still apply: at 200 % the navigation and inspector columns collapse into drawers toggled from the header. | Requirements §2 and §10 (compact-dimension scenario) |
| D3 | **There is no explicit AI handoff.** Manual and AI editing alternate routinely, and the operator knows when they asked OMP to act. The editor continuously follows the workspace files. The *document fingerprint guard* alone prevents an editor write from overwriting AI output. No handoff, external-turn, or return state exists, and the UI has no "hand to AI" or "take back" action. | Architecture §7.2 (turn generation check), §8 (state table, handoff and return rules), §10 (handoff/resume HTTP routes), §11 (handoff verification); requirements §5.1, §6.1, §6.3, §7, §9 (manual/handoff rows), §10 (handoff scenarios) |
| D4 | **Prefer coarse mechanisms over per-control UI.** This is a developer-only tool. Workspace conditions are shown by header status chips, one priority banner, and the diagnostics strip. The frontend does not pre-disable individual controls per state; the service rejects inadmissible writes, and the rejection is shown in the banner or diagnostics. | Requirements §6.1 ("disable every mutation path …") and §8 ("disabled actions must have discoverable reasons", which now applies only to the delete action's inline refusal) |

### 1.1 Continuous file following (D3 in detail)

The service watches the source, layout, and artifact roots for creation, replacement, renaming, and deletion, then coalesces notifications after a short settle interval. This is unchanged from architecture §8.

- **Own writes** are recognised by the fingerprint the service recorded when it replaced the file. Its own writes never count as external changes.
- **An external change that loads** is published as a new snapshot. The undo/redo history is cleared, because history covers only the uninterrupted manual segment since the last adopted external change. Map, view, and selection are preserved by stable identity. A removed selection is cleared, and the inspector explains the removal.
- **An external change that does not load** keeps the last previewable snapshot. The snapshot is marked stale with file/line diagnostics, and the service rejects world-data and layout writes until a loadable candidate appears. Unchanged from architecture §8.
- **Open field drafts.** If the client holds an uncommitted field draft when a new snapshot arrives, it shows the "file changed externally" banner (§5.2 ③) instead of silently adopting. "Load new version" discards the draft and adopts the snapshot. A draft submitted against the old snapshot is rejected by the fingerprint guard anyway.
- **Every write** carries the target document's expected fingerprint and the snapshot revision. The service checks the fingerprint on disk immediately before the atomic replacement. On a mismatch it rejects the command and reloads; it never merges or replays.
- **Service session.** A restart creates a new session and invalidates the launch token. A client from the old session must reconnect and reread before writing. An uncertain post-replacement durability result also stops writes until an explicit reread.
- **Partition generation** blocks world-data mutations while it runs. An external source change invalidates the captured input signature, so the result cannot be published as current. Unchanged from architecture §9, minus the handoff clause.
- **Remaining limit.** If OMP and the editor write the same document within one settle interval, the guard rejects the editor's write. The operator is responsible for not editing in both places at once. The editor makes no claim about OMP's running state and never labels it.

The copied OMP context (requirements §7) states whether it came from current files or a stale preview, and includes source paths, qualified IDs, and coordinate frames and units. It no longer states turn ownership or a save-before/stop-before-return agreement.

## 2. Layout: three-column workbench

```
┌ header ──────────────────────────────────────────────────────────────────────────────┐
│ ✎ 地圖編纂  [大陸 1][據點 2][室內 3] │ 灰岩鎮 › 街道圖      [存檔][同步][索引][分區] │
├ priority banner (only when a condition is active) ───────────────────────────────────┤
├──────────────┬──────────────────────────────────────────────┬────────────────────────┤
│ navigation   │ canvas                                        │ inspector              │
│ world tree   │  tool pill (top left)    zoom pill (top right)│ name, qualified ID,    │
│ object list  │                                               │ source path, fields,   │
│ search       │  scale/frame label (bottom left)              │ relations, actions     │
├──────────────┴──────────────────────────────────────────────┴────────────────────────┤
│ diagnostics strip: ✕ n ▲ n · external index · partition       undo/redo · copy hints │
└──────────────────────────────────────────────────────────────────────────────────────┘
```

- **Header.** The circular seal glyph and the serif gold title 地圖編纂 come first. Next are the domain tabs (大陸／據點／室內 on keys 1／2／3), drawn as the map drawer's pill tab group with key chips. A hairline separates them from the breadcrumb of the current map. The status chips sit at the right end (§5.1).
- **Navigation column** (about 250 px at scale 1). It holds the world tree (continent → locations → local maps → interiors), with a domain tag on each entry and 無本地圖 on locations that have none. The object list for the open map follows with its count, and search sits at the top of the list. For the continent domain, a layer list precedes the tree.
- **Canvas.** Same-ink background as the game map drawer: a gold dot field for metric maps and a plain gradient for interiors. Floating pills match the drawer's: tools at the top left, zoom/fit/layers at the top right, and the north arrow, scale, and coordinate-frame label at the bottom left.
- **Inspector** (about 340 px). Serif heading. Monospace qualified ID and workspace-relative source path, both copyable. Fields with an explicit unit and frame suffix. Directed relationships. Contextual actions.
- **Diagnostics strip.** A one-line summary, expandable into a list grouped by class (requirements §5.2). Each row names its object, file, field, and line, and offers 前往. A target on a hidden layer is offered as 顯示圖層並前往 rather than selected silently.
- **Focus order and landmarks.** Header (`banner`), navigation (`navigation`), canvas (`main`, named by the current map), inspector (`complementary`), diagnostics (`region`). F6 / Shift+F6 cycle between these five.

At 200 % zoom, or whenever the viewport cannot hold both side columns at their minimum widths, both side columns become drawers. The header shows 導覽 and 檢查器 toggle buttons, and selecting an object opens the inspector drawer. A drawer traps focus, and Escape closes it and returns focus to its toggle.

## 3. Visual language

| Element | Treatment |
| --- | --- |
| Surfaces | `--ink-950` page, `--panel-solid` frame, side columns at `rgba(11,13,16,.45)` over the panel; 1 px gold hairlines (`--band-edge` / `--band-edge-dim`). |
| Text | `--paper-100` body, `--paper-500` secondary, `--f-sans`; headings and section labels in `--f-serif` `--gold-300`/`--gold-400`; IDs, paths, and numeric inputs in `--f-mono`. Every size is a `--text-*` token, `--text-xs` at minimum. |
| Section labels | Serif gold label followed by a fading gold hairline, as in the game drawers. |
| Selection | Gold ring plus the dock's corner brackets on the canvas, and a gold inset bar on list rows. Never colour alone: the inspector always names the selection. |
| Focus | The game's gold focus ring on every control; the canvas focus target gets the same bracket frame. |
| Status | ✓ saved/current (`--ok`), ⟳ busy (gold), ✎ draft (gold dashed), ▲ stale/unfinished (`--warn`), ✕ failed/error (`--seal-400`), ? uncertain (seal), ⦸ unavailable/disconnected (dashed neutral or seal). Glyph and text always accompany the colour. |
| Map ink | Reuses the shared glyph sources from `@elosern/map-view` (P10). Roads keep the dark casing and paper core; unfinished or one-way roads use the frontier dash; gateways use the gold arch. The editor adds only editor-specific marks: the control-point diamond handle, the direction chevrons on a selected road, and the interior room card. |
| Derived output | Partition districts and national borders in the world map's dotted/dash-dot ink, with no handles. They are not selectable as editable geometry. |

Motion uses the game's `--motion-*` tokens and honours `prefers-reduced-motion`. The editor has no motion-level setting of its own.

## 4. Domain screens

### 4.1 Continent

- **Layers:** 地形與通行, 水系, 山脊・隘口・渡口, 地點, 據點佔地, and 分區（衍生・唯讀）.
- **Tools:** 選取 V, 加控制點 A, 水系, 山脊, 地點, 佔地.
- **Control points** are diamond handles distinct from their feature. The inspector heading names the point (霜溪 · 控制點 5) and links 隸屬 to the feature. The fields are labelled with frame and unit (`km 地理`), followed by the corresponding wilderness cell (`1 km 格`). The inspector offers 前方插入 / 後方插入 / 移除控制點.
- **Footprint masks** are edited on a cell grid overlay. The equivalent inspector control is a monospace `#`/`.` grid, one row per line, toggled cell by cell with the arrow keys and Space.
- **Locations without a local map** show 無本地圖 in the tree and the inspector, with no fabricated rooms. Locations with one offer 開啟本地圖.
- **Derived results** appear in an inspector section: terrain preview freshness and partition state, with 重新產生分區.

### 4.2 Settlement

- **Tools:** 選取 V, 節點 N, 道路 R, 入口 E.
- **Nodes** use the area-map node glyphs. The inspector shows name, prototype, scene reference, multiline description, and position in `m 地方` (east/north).
- **Roads** are listed as directed rows (`北 → 北門 · 65 m`). The incoming direction is shown separately (`← 北 來自 鐘樓廣場`). Physical length comes from the core.
- **Creating a road** offers 建立雙向 as an explicit option. The result is two directed rows in one command.
- **Bends** are diamond handles on the selected road, with numeric rows in the inspector.
- **Moving a node** never changes its ID or authored direction. The inspector keeps listing the same relations after the move.
- **Multi-selection** works through Shift/Ctrl-click in the object list. The inspector shows the count, the owning document, and mixed values as `—`. A cross-document selection is inspect/copy only, with the reason 跨文件的選取只能檢視與複製 shown in place of the mutation actions.

### 4.3 Interior

- **Rooms** are cards with a name and a monospace ID. The canvas has no dot field or scale, and a fixed note at the bottom right reads 版面僅供編輯器使用 · 不代表距離或座標.
- **Connections** are curved arrows with their direction labels. Two-way pairs read 東 ⇄ 西, and one-way connections are marked 單向 in the inspector.
- **The exterior entrance** is a dashed card naming the other map and node.
- **Tools:** 選取 V, 房間 N, 連接 R, 外部入口 E, 自動排列.
- **Layout writes** go only to `content/map-editor-layouts/<id>.yaml`. The diagnostics strip names that file whenever a layout edit was the last save.
- **Service rooms** show their `service_place` reference read-only, and no service record is required.

### 4.4 Cross-layer entrances

- **Inspector heading:** both end names (北門大道 ⇄ 鍛冶工坊), then 擁有者 followed by the owning document ID and 單一紀錄.
- **Each endpoint** shows its domain, its qualified ID as a link, and its directional label. Direction is stated as 雙向 or 單向.
- **前往另一端** navigates to the other end. The breadcrumb then gains a leading 「← 返回 <map · object>」 button, also available as Alt+←, so the user can return to where they came from.
- **更換端點…** opens the qualified-object selector. Users can search by name, results show the parent map, and the submitted value is always the qualified ID.

## 5. States and recovery

### 5.1 Header status chips

The chips appear in a fixed order. Each is a button whose action is listed in the last column.

| Chip | Values | Activation |
| --- | --- | --- |
| 存檔 | ✓ 已存檔 hh:mm · ⟳ 存檔中 · ✎ 有未確認草稿 · ✕ 存檔失敗 · ? 存檔結果不確定 | Focuses the banner when failed or uncertain |
| 檔案同步 | ◉ 已同步 hh:mm · ◉ 已載入外部變更 hh:mm · ▲ 預覽過期 · YAML 錯誤 · ⦸ 無可用預覽 · ⦸ 服務未連線 | Expands the diagnostics with the failing file/line |
| 索引 | 索引 現行 · ▲ 索引不可用 · 無法刪除 · ✕ 外部引用無效 n | Expands the external-reference diagnostics |
| 分區 | 分區 現行 · ▲ 分區過期 · 重新產生 · ⟳ 分區產生中 · 取消 · 分區已取消 · 保留舊版 · ✕ 分區產生失敗 · 保留舊版 | Regenerates when stale; cancels while generating |

### 5.2 Priority banner

One banner slot sits under the header and shows the highest-priority active condition with a single action. It is persistent, never a transient toast, and its text is announced through a polite live region.

1. **服務未連線／已重啟** (seal): 畫面停留在 hh:mm 的快照，現在無法寫入。 Action: 重新連線並讀取. Pending commands are never replayed, and write permission is never restored from browser storage.
2. **存檔失敗／結果不確定** (seal): names the failed command and the cause, and states which version is on disk. Action: 重新讀取. There is no automatic retry. While the result is uncertain, writes stay stopped until the reread.
3. **檔案已被外部修改（有草稿）** (warn): names the document and states which drafts and history will be discarded. Action: 載入新版. Without drafts, adoption is silent apart from the 同步 chip time.
4. **預覽過期** (warn): 顯示的是 hh:mm 的最後可用版本, followed by the first failing `path:line — reason`. The canvas is desaturated and carries a 過期預覽 badge. There is no action; the user fixes the file externally, and recovery is automatic on the next loadable change. With no prior snapshot, the canvas shows 無可用預覽 and the diagnostics instead of an empty map.

Service rejections caused by states the frontend does not pre-check, such as a write during generation or while stale, appear in the banner slot with their reason until the next successful command or snapshot.

### 5.3 Fields, drafts, and errors

- **Draft:** a gold dashed underline and tinted background, plus the hint 草稿 · Enter 確認並存檔 · Esc 取消. Blur also confirms. Esc restores the saved value.
- **Field error:** an inline message under the field, associated through `aria-describedby`. Focus stays in the field, and nothing is written. Examples: 需要整數公尺, and a duplicate ID with a link to the existing object.
- **In-flight save:** the 存檔 chip shows ⟳. A drag is one command, committed on release, and is not shown as saved until acknowledged.

### 5.4 Deletion

- **Delete** is an inspector action and the Delete key. Refusal is shown inline in the inspector as 無法刪除：仍有 n 個引用. Each reference is listed with its kind, label, and source, and links to it. The note 不會連帶刪除 follows the list.
- **Unavailable index:** the same block states that the external index is unavailable, so external references cannot be checked and deletion is refused.
- **Admissible deletions** run without a confirmation dialog, because the operation is one undoable command. This is the recorded confirmation decision: no editor operation requires a confirmation dialog. Destructive loss of drafts or history is confirmed by the explicit banner action in §5.2 ③.

## 6. Keyboard and focus contract

| Keys | Behaviour |
| --- | --- |
| 1 / 2 / 3 | Switch to the continent, settlement, or interior domain. |
| V N R E A | Tools: select, add node or room, road or connection, entrance, add control point. The tool pill shows the chips. |
| F6 / Shift+F6 | Cycle focus through header → navigation → canvas → inspector → diagnostics. |
| Tab / arrow keys on the canvas | Tab walks objects in object-list order. An arrow key moves to the nearest object in that direction. Enter selects the object and focuses the first inspector field. |
| Shift+arrow | Nudges the selection by one grid step; each press is one undoable command. Exact values are typed in the inspector. |
| Ctrl/⌘+Z, Shift+Ctrl/⌘+Z | Undo / redo the current manual segment. Inside a text field, the field's own undo applies. |
| Ctrl/⌘+C outside text fields | Copies the OMP context for the selection. |
| Delete | Deletes the selection, or shows the inline refusal. |
| Esc | Cancels in order: incomplete tool operation → field draft → selection. Closes an open drawer or selector first. |
| Alt+← | Returns from cross-map navigation. |
| / or Ctrl/⌘+K | Focuses search. |

Single-key shortcuts never act while focus is in a text input, select, or the qualified-object selector, and they ignore IME composition and modified keys. Focus returns to the trigger when a drawer or selector closes. After following a diagnostic or relationship, focus moves to the destination object's inspector heading, and the return button remains available.

Every essential edit has a non-drag path:

- **Geometry:** numeric inspector fields, plus insert/remove buttons for control points and bends.
- **Roads and entrances:** endpoint selectors and direction selectors.
- **Footprints:** the cell grid control.
- **Interior layout:** Shift+arrow nudging, or 自動排列.

## 7. Prototype

`docs/design/map-editor/` contains `MapEditorPrototype.vue`, its mock data, and `MapEditor.stories.js` under the Storybook title `Design/MapEditor`. The stories render the approved screens at 1451×790 against the real `tokens.css`, with no game shell CSS:

| Story | Shows |
| --- | --- |
| `ContinentControlPoint` | §4.1, stale partition |
| `SettlementNodeSelected` | §4.2, directed roads, references |
| `SettlementBidirectionalRoad` | Road tool with 建立雙向 |
| `InteriorRooms` | §4.3 |
| `EntranceFollowed` | §4.4 with the return button |
| `FieldDraftAndError` | §5.3 |
| `DeleteRefused` / `DeleteIndexUnavailable` | §5.4 |
| `BannerDisconnected` / `BannerSaveFailed` / `BannerExternalChangeWithDraft` / `BannerStalePreview` / `NoPreview` | §5.2 |
| `PartitionGenerating` | Generating chip with cancel |
| `Zoom200Drawers` | Collapsed columns with drawer toggles |

The prototype is reference material for visual fidelity and state coverage. It is not the implementation and is not wired to any service.

## 8. Acceptance-scenario mapping

| Requirements §10 scenario | Design |
| --- | --- |
| Move a river control point | §4.1 diamond handle, `km 地理` fields; release is one command; 分區 chip turns ▲ 過期 |
| Add a location without a local map | §4.1 無本地圖 tag; searchable in navigation |
| Move a settlement node | §4.2; inspector relations unchanged |
| Create a bidirectional street | §4.2 建立雙向; two directed rows |
| Rearrange an interior | §4.3 layout-only note and layout file |
| Edit an entrance | §4.4 |
| Incomplete number / duplicate identity | §5.3 |
| Save semantic work-in-progress | Saved chip ✓ while diagnostics list ▲ rows; header never claims game readiness |
| Remove a referenced object | §5.4 |
| Stale or missing external index | 索引 chip ▲ plus inline delete refusal; editing unaffected |
| ~~Fail a save during handoff~~ | Withdrawn by D3; a failed save is §5.2 ② |
| Browse while AI edits | No mode: browsing and editing are always available; external changes load automatically (§1.1) |
| Malformed then corrected YAML | §5.2 ④, then automatic adoption |
| ~~Return after AI leaves an inaccessible landmark~~ | Replaced: any loadable external change with semantic diagnostics simply loads, and the diagnostics list the issue |
| Unexpected manual-mode file change | §1.1 automatic adoption; §5.2 ③ when drafts exist |
| Reconnect an old tab / restart service | §5.2 ① |
| Source change during partition generation | 分區 chip; the result is not published as current |
| Selected object moves or disappears | §1.1 selection preservation, removal explanation |
| Copy context for OMP | §1.1 copied-context content |
| Keyboard-only edits | §6 |
| Long names and 200 % zoom | §2 drawer collapse; inspector headings wrap and IDs break anywhere |

## 9. Consequences for the proposal batch

| Proposal | Required change |
| --- | --- |
| P11 `map-editor-standalone-service` | Remove the handoff/resume routes. Add the token/font/ui-scale import allowlist and its boundary check. Serve the game fonts locally. |
| P12 `map-editor-document-commands` | Commands carry expected fingerprint plus snapshot revision; no turn generation. Undo history resets on adopted external change. |
| P13 `map-editor-file-following` (renamed from `map-editor-turn-recovery`) | Replace the turn state machine with continuous file following and own-write recognition (§1.1); capability renamed to `map-editor-file-following`. |
| P14 `map-editor-interaction-shell` | Implement this layout, chips, banner, diagnostics, keyboard contract, and copied context. Cite this document and the prototype as the specialist deliverable. |
| P15–P18 domain tools | Adopt the domain screens of §4 and the inline delete refusal; no per-state control disabling. |
| P19 `map-editor-partition-jobs` | Drop the "block AI handoff" clause; keep blocking mutations and invalidation. |
| P20 `map-editor-integrated-acceptance` | Replace the handoff/return smoke paths with external-change following, the fingerprint-guard race, and stale-to-current recovery at 1451×790 and 2560×1440. |
