# Map Editor Fidelity Review

Human review of the standalone map editor against the approved frontend
design (`docs/superpowers/specs/2026-10-26-map-editor-frontend-design.md`)
and its prototype (`docs/design/map-editor/`, Storybook `Design/MapEditor`).
Tone, wording quality and visual polish are judged here by a person. They are
not requirements pinned by tests: the tests establish mechanisms and
interactions only.

**Reviewed slices:** `map-editor-interaction-shell` (P14), the workbench
shell; `map-editor-continent-tools` (P15), the continent screen of design
§4.1 (see "Continent tools review"); `map-editor-settlement-tools` (P16), the
settlement screen of design §4.2 (see "Settlement tools review");
`map-editor-interior-tools` (P17), the interior screen of design §4.3 (see
"Interior tools review"); `map-editor-entrance-tools` (P18), the cross-layer
entrances of design §4.4 and the deletion refusal of §5.4 (see "Entrance
tools review"); `map-editor-partition-jobs` (P19), the 分區 chip actions,
the regenerate control and the derived district outlines of design §3, §4.1
and §5.1 (see "Partition jobs review"); `map-editor-integrated-acceptance`
(P20), the whole editor in Chromium and Firefox at both viewports (see
"Integrated acceptance review").
**Viewports:** 1451x790 (reference), 2560x1440, and 200 % zoom of the
reference emulated as a 725x395 CSS viewport at device scale 2 (it reproduces
the layout width, not every media feature of a real browser zoom).

## Disposition key

| Disposition | Meaning |
| --- | --- |
| Matches | The shell presents the scenario as the design describes. |
| Shell ready | The shell's part (chips, banner, diagnostics, inspector, keyboard) is in place; the scenario's domain command arrives in the named later change. |
| Withdrawn | The design withdrew the scenario. |
| Flagged | The mechanism works; a person must decide whether the presentation is acceptable. |

## Shell-wide review

| Element (design §) | Review notes | Disposition |
| --- | --- | --- |
| Header, domain pill tabs with key chips, breadcrumb (§2) | Seal glyph and serif gold title first; tabs as one pill group; the breadcrumb gains the 「← 返回」 button after cross-map navigation. | Matches |
| Status chips (§5.1) | Four buttons in fixed order, glyph and text with colour. The 分區 chip (P19) regenerates when stale, unavailable, cancelled or failed, cancels while generating, and expands the partition diagnostics when current. | Matches |
| Priority banner (§5.2) | One persistent slot, polite live region, one action; ordering unchanged from P13. | Matches |
| Three columns and drawers (§2) | Columns at the two supported viewports; drawers with 導覽 / 檢查器 toggles when both side columns cannot fit. At 200 % an open drawer covers most of the canvas; flagged for the human reviewer. | Matches |
| Canvas chrome (§2) | Tool pill top left, zoom pill top right, north arrow, scale bar and frame label bottom left, interior layout note bottom right, stale badge. Only 選取 V is registered until the domain tool changes land. | Matches (tools: Shell ready) |
| Visual language (§3) | Game tokens and fonts only, gold focus ring, seal red only for errors, 16 px floor; selection uses the gold ring plus corner brackets and the list's inset bar. | Matches |
| Keyboard and focus (§6) | Full contract except the domain tool keys N R E A, which the domain changes register. | Matches (tool keys: Shell ready) |

## Acceptance scenarios (design §8)

| Requirements §10 scenario | Design | Disposition and notes |
| --- | --- | --- |
| Move a river control point | §4.1 | Matches (P15): diamond handles on the selected waterway; the release, or a confirmed `1 km 格` field, is one `continent.yaml` command; the core terrain preview redraws and the 分區 chip turns ▲ 過期. |
| Add a location without a local map | §4.1 | Matches (P15): the 地點 tool's creation form writes only `locations.yaml`; the new location is searchable, tagged 無本地圖 and fabricates no rooms. |
| Move a settlement node | §4.2 | Matches (P16): a node drag, or a confirmed `m 地方` field, is one settlement-document command; the ID, the authored road directions and the listed relations (gate, interior entrance, landmark) are unchanged, and the core lengths update. |
| Create a bidirectional street | §4.2 | Matches (P16): the 道路 R tool picks source then destination; the form requires a chosen direction and, with 建立雙向, a return direction; one command saves two directed rows with core lengths. |
| Rearrange an interior | §4.3 | Matches (P17): drag, Shift+arrow, the editor-only layout fields and 自動排列 write only the layout file, named in the strip after a save; the world fingerprint and every route length stay unchanged. |
| Edit an entrance | §4.4 | Matches (P18): the relationship inspector names both ends, the owning document as the one record and 雙向/單向; 前往另一端 and the endpoint links navigate with the 「← 返回」/Alt+← context; 更換端點… submits a qualified ID; every edit writes only the owner. |
| Incomplete number / duplicate identity | §5.3 | Matches for numbers (inline error, focus kept, nothing written). Settlement creation forms (P16) state a duplicate node ID inline with a link to the existing node, and the service refuses a duplicate ID, coordinate or ordered road with nothing written. |
| Save semantic work-in-progress | §8 | Matches: the save chip shows saved while the strip lists unfinished rows; nothing claims game readiness. |
| Remove a referenced object | §5.4 | Matches for locations (P15): a location still named by a local map, anchor or landmark, or by a current external index, shows 無法刪除 inline with its references and 不會連帶刪除; an unreferenced one is one undoable command checked again on the fresh disk baseline. Settlement nodes (P16) list every road, gate, city gate, interior entrance and landmark that must be removed first, each linked; an unreferenced node with a current index is one command. Rooms (P17) list every connection, the exterior, interior link and landmark that must go first, each linked; a room joined by a service place or host is refused by the current index; connections are removed directly. Entrances (P18) are listed as their relationship, each linked; removing one is a separate command on its owner, and the endpoint is deleted afterwards. |
| Stale or missing external index | §5.4 | Matches: 索引 chip, an external diagnostics row explaining unsupported external claims, and the inline refusal; editing continues. |
| ~~Fail a save during handoff~~ | — | Withdrawn by D3; a failed save is §5.2 ②. |
| Browse while AI edits | §1.1 | Matches (P13): no mode; external changes load automatically. |
| Malformed then corrected YAML | §5.2 ④ | Matches (P13), and the copied context names the stale preview and failing file. |
| ~~Return after AI leaves an inaccessible landmark~~ | — | Replaced: a loadable change with semantic diagnostics loads; the strip's 前往 locates the landmark object. |
| Unexpected manual-mode file change | §1.1 | Matches (P13). |
| Reconnect an old tab / restart service | §5.2 ① | Matches (P13). |
| Source change during partition generation | §9 | Matches (P19): the external change ends the job; the chip reads ✕ 分區產生失敗 · 保留舊版, the artifact is unchanged and nothing is labelled current. |
| Selected object moves or disappears | §1.1 | Matches: the selection (also a multi-selection) is kept by identity and removed members are named. |
| Copy context for OMP | §1.1 | Matches: plain text with qualified IDs, relative paths, frames and units and currentness; no token, ownership claim or action. |
| Keyboard-only edits | §6 | Matches for the shell, layout edits, continent edits and settlement edits (N, R, object-list road endpoints, schema-typed fields, Shift+arrow group nudges) and interior edits (N, R, object-list connection endpoints, room fields, 自動排列) and entrance edits (E or ⌂ 新入口 with the form, the keyboard selector, label fields). |
| Long names and 200 % zoom | §2 | Matches: headings, IDs and tree rows wrap or break anywhere; side columns become drawers; status chips stay in the viewport. |

## Continent tools review

Rows for the continent screen of design §4.1, delivered by
`map-editor-continent-tools` (P15). The person reviewing judges tone, wording and
visual polish here; the tests establish only mechanisms. A "Ready" row lists
the elements a later change completes.

| Element (design §) | Review notes | Disposition |
| --- | --- | --- |
| Layers (§4.1) | 地形與通行 holds the core terrain preview raster, the coast and the forest edge; 水系 the waterways; 山脊・隘口・渡口 the ridge walls, pass ticks and fords; 地點 the locations and reserved sites; 據點佔地 the footprint cells (hidden by default); 分區（衍生・唯讀） the derived national borders. Region tints are muted. A reviewer should check legibility against the dot field at both viewports. | Matches |
| Tools (§4.1, §6) | 選取 V, 加控制點 A, 水系, 山脊, 地點, 佔地 in the tool pill; Escape cancels an incomplete tool operation first. 水系, 山脊 and 地點 complete in an inspector creation form whose new ID is confirmed before creation. | Matches |
| Control points (§4.1) | Diamond handles appear only on the selected feature. The heading names the point, 隸屬 links the feature, the fields carry `km 地理` (coast) or `1 km 格` (everything else) with the other frame read-only, and 前方插入 / 後方插入 / 移除控制點 sit below. | Matches |
| Footprint masks (§4.1) | Painted cells on the canvas with the 佔地 tool; the inspector's monospace `#`/`.` grid (north row first, one-cell margin, arrows and Space) writes only the owning settlement. Review the grid density of the 9-row Altoria mask at 1451x790. | Matches |
| Locations without a local map (§4.1) | 無本地圖 in the tree and the inspector with no rooms; 開啟本地圖 for settlement-derived local maps. | Matches |
| Districts and landmarks | Names, kind and region membership, plus a structured landmark selector (domain, map, object or cell). Saving a landmark that is not reachable shows ▲ in the diagnostics strip. | Matches |
| Binding | Anchor cell `1 km 格` and local anchor `m 地方`, with the world-metre rule stated; interiors get no metres. | Matches |
| Derived results (§4.1, §3) | The inspector section shows the terrain preview state, the partition's input signature against the current one and 重新產生分區 / 取消產生 (P19). National borders draw dash-dot ink with no handles; the district outlines are described under "Partition jobs review". | Matches |
| Region prose and classifier fields | Name, nation keys, scene and one-variant-per-line descriptions; a variant containing a line break is shown as external-edit only. A reviewer should confirm that this is acceptable for authored prose. | Matches |

## Settlement tools review

Rows for the settlement screen of design §4.2, delivered by
`map-editor-settlement-tools` (P16). The person reviewing judges tone,
wording and visual polish here; the tests establish only mechanisms. A
"Ready" row lists the elements a later change completes.

| Element (design §) | Review notes | Disposition |
| --- | --- | --- |
| Tools (§4.2, §6) | 選取 V, 節點 N and 道路 R in the tool pill; Escape cancels a picked road source or an open form first. 入口 E (P18) opens the entrance form for the picked node. | Matches |
| Nodes (§4.2) | Area-map node glyphs with the gate arch; a larger transparent hit area; the inspector shows the name, prototype (with the anchor location for an anchor room), scene, typeclass, multiline description and the position in `m 地方` (east/north), each typed from the core schema. Check field order and density at 1451x790. | Matches |
| Scene references | A select of the current index's scene archetypes with ✓/✕ status; when the index is not current a free text field with ▲ 無法驗證. A reviewer should confirm that the status line reads clearly beside the field. | Matches |
| Roads (§4.2) | Directed rows `東北 → Yard · 500 m` and `← 南 來自 Yard`, using compass names (the codes appear in the road inspector); length is the core's. A selected road draws gold casing and downstream chevrons; one-way roads keep the dashed core. | Matches |
| Creating a road (§4.2) | 道路 R: source then destination (canvas or object list), then a form with explicit 去程方向, 建立雙向 and 回程方向; no direction is pre-selected. The node inspector's ⟶ 新道路 and the road inspector's 建立反向道路 open the same form. | Matches |
| Bends (§4.2) | Diamond handles on the selected road; numeric rows, 加彎點, 前方插入 / 後方插入 / 移除彎點. | Matches |
| Moving a node (§4.2) | Drag, `m 地方` fields or Shift+arrow (10 m); ID and authored directions unchanged; relations listed the same after the move. A refused move (a taken coordinate) snaps back with the banner reason. | Matches |
| Multi-selection (§4.2) | Ctrl/Shift in the object list; the inspector shows the count, owning document, mixed values as `—`, a group delta and 刪除這些節點. A cross-document selection shows 跨文件的選取只能檢視與複製 and no mutation actions. | Matches |
| New local map | 建立本地圖 in a location's inspector (ID, anchor cell, local anchor, optional map options) writes one new settlement document, opens it and shows ▲ 尚無節點 as unfinished. | Matches |
| Duplicate and route preview | 複製為新節點 asks for a new ID and states what is not copied (and the anchor demotion); 路徑預覽 lists the core planner's steps and total, marked when the snapshot has moved on. A reviewer should judge whether the route preview belongs below the roads. | Matches |
| Duplicate identity (§5.3) | The node and duplicate forms state an existing ID inline with 前往現有節點, which selects that node; the service refuses it as well. | Matches |

## Interior tools review

Rows for the interior screen of design §4.3, delivered by
`map-editor-interior-tools` (P17). The person reviewing judges tone, wording
and visual polish here; the tests establish only mechanisms. A "Ready" row
lists the elements a later change completes.

| Element (design §) | Review notes | Disposition |
| --- | --- | --- |
| Rooms (§4.3) | Cards with the name and the monospace ID on a plain gradient canvas with no dot field, north arrow or scale; the fixed note 版面僅供編輯器使用 · 不代表距離或座標 at the bottom right. A reviewer should check card overlap when rooms sit one layout step apart at 1451x790. | Matches |
| Connections (§4.3) | Curved arrows with one direction chevron each; a two-way pair bends apart and reads `去 ⇄ 回` once; the room inspector marks 單向 rows and a second exit with the same name. Judge whether the chevron reads clearly where an arrow passes close to a card. | Matches |
| Tools (§4.3, §6) | 選取 V, 房間 N (opens the creation form at once, since a room has no position), 連接 R (source then destination room, then the name and optional 建立雙向) and 自動排列 in the tool pill. 外部入口 E (P18) opens the entrance form for the picked room. | Matches |
| Room fields | Name, multiline description, scene from the current index (✓/✕/▲ status; free text when the index is not current) and art key; the ID is shown read-only. | Matches |
| Service rooms (§4.3) | A 服務 · 唯讀 section lists the joining `places` / `service_hosts` records from the index, or states that a standalone room needs none. Host and goods authoring stays out of the editor. | Matches |
| Layout writes (§4.3) | Drag, Shift+arrow, the 版面 X/Y fields (labelled editor-only) and 自動排列 write only `content/map-editor-layouts/<id>.yaml`; the strip names it after the save. Creating a room writes no layout; the new room appears at the list position. 自動排列's button states that it overwrites the layout and can be undone. | Matches |
| The exterior entrance (§4.3) | A fixed dashed card naming the settlement and node, one layout column left of its room and joined to it by a dashed link; selecting it opens the relationship inspector (P18). A reviewer should check the card's distance from the room card at both viewports. | Matches |
| New and removed interiors | ＋ 新室內 creates a standalone interior with its first room and opens it; 刪除室內文件 sends one command that the service guards like a room deletion and leaves the layout for cleanup. A reviewer should judge whether removing a whole document needs more emphasis than an inline action. | Matches |
| Duplicate identity (§5.3) | The room forms state an ID already used by any interior inline with 前往現有房間; the service refuses it on the fresh disk as well. | Matches |

## Entrance tools review

Rows for the cross-layer entrances of design §4.4 and the deletion refusal
of §5.4, delivered by `map-editor-entrance-tools` (P18). The person
reviewing judges tone, wording and visual polish here; the tests establish
only mechanisms.

| Element (design §) | Review notes | Disposition |
| --- | --- | --- |
| Inspector heading (§4.4) | Both end names joined by ⇄ (two-way) or → (one-way), then 擁有者 with the owning document and 單一紀錄, the kind and the direction. The prototype names the interior; the editor names the entrance room, because interiors have no display name. Judge whether that reads well. | Matches |
| Endpoints (§4.4) | Each end gives its domain, its qualified ID as a link, its name and its directional label. A node end shows its local metres; a gate's wilderness end shows the core's approach cell, read-only, and links to the settlement footprint on the continent. The exterior's return exit is stated as game-provided, without repeating the game's exit name. | Matches |
| 前往另一端 and return (§4.4, §6) | Goes to the end off the map on display, otherwise to the target. 「← 返回 <map · object>」 and Alt+← come back. Focus lands on the destination's inspector heading. | Matches |
| 更換端點… (§4.4) | Opens the qualified-object selector inline under its end. Results show the parent map and qualified ID, and equal names are marked. Escape returns focus to the trigger. Review the selector's height in the 340 px inspector at 1451x790. | Matches |
| Entrance tools (§4.2, §4.3, §6) | 入口 E and 外部入口 E pick a node or room and open one form. The settlement form offers a wilderness gate or the one-way start entry; the interior form offers the exterior doorway or an interior link with 建立雙向. Choosing a different kind keeps typed values. | Matches |
| Start entry | Labelled 起始房間入口 and stated as one-way, fixed. No return field is offered. | Matches |
| Deletion refusal (§5.4) | A referenced node or room lists each entrance as its relationship, linked. The relationship's own removal states that it writes only its owner and deletes no endpoint. The last wilderness gate is refused by the service; the whole-entry removal is a separate action that names the footprint mask it discards. | Matches |

## Partition jobs review

Rows for the explicit partition jobs of design §1.1, §3, §4.1 and §5.1,
delivered by `map-editor-partition-jobs` (P19). The person reviewing judges
tone, wording and visual polish here; the tests establish only mechanisms.

| Element (design §) | Review notes | Disposition |
| --- | --- | --- |
| 分區 chip (§5.1) | 分區 現行 · ▲ 分區過期 · 重新產生 · ⟳ 分區產生中 · 取消 · 分區已取消 · 保留舊版 · ✕ 分區產生失敗 · 保留舊版, plus ⦸ 分區不可用 · 重新產生 for a missing or malformed artifact (not in the prototype). The busy tone matches the save chip's ⟳. Judge whether the unavailable wording reads well next to the others. | Matches |
| 重新產生分區 (§4.1) | The continent inspector's 衍生結果 section offers 重新產生分區, or 取消產生 while generating, under the input revision line (產物輸入 · 現行輸入, eight hex digits each, as in the prototype's r41/r43 idea). A failed job lists its problems in monospace below. | Matches |
| District outlines (§3) | Derived rings in thin dotted paper ink on the 分區 layer with the national borders, never selectable and with no handles. Review their density against the dot field for the 120 shipped districts at 1451x790. | Matches |
| Older-input output (§5.1, architecture §9) | Outlines of an artifact for older inputs fade to the warning tone. The canvas keeps the label ▲ 分區輸出屬於舊輸入 · 不可作為遊戲就緒 at the bottom right while they are shown, and the inspector repeats it. Judge the label's placement against the frame label at both viewports. | Matches |
| Rejection during generation (§5.2) | A world-data edit during a job is refused by the service and shown in the banner slot as ▲「<command>」未存檔：分區產生中; layout edits still save. Browsing, inspection, search and cancellation stay available. | Matches |
| Cancel after completion | A cancel that arrives after publication finds no running job; the chip and inspector show the completed state, with no rollback claim. | Matches |

## Integrated acceptance review

Rows for the whole editor in desktop Chromium and Firefox, delivered by
`map-editor-integrated-acceptance` (P20), which replaced the withdrawn
handoff/return smoke paths (design §9). The mechanism behind each row is
established by the named test; the person reviewing judges how the
scenario reads and looks at both viewports. "Flagged" marks an observation
from the implementer's screenshots that a person should decide on.

| Scenario (design §) | Owning test, viewports, browsers | Review notes | Disposition |
| --- | --- | --- | --- |
| Continental authoring session (§4.1) | `test_map_editor_workflows` `MapEditorWorkflows*Test`, 1451x790, Chromium and Firefox | Location, control point, footprint cell and landmark in one session; each writes only its owner and reloads in the core. | Matches |
| Local map and interior session (§4.2–§4.4) | same, 1451x790, Chromium and Firefox | Node, two-way road, room, two-way connection, exterior endpoint by the keyboard selector, layout drag. | Matches |
| Automatic adoption (§1.1) | `MapEditorFollowing*Test`, 1451x790 and 2560x1440, Chromium; 1451x790, Firefox | Silent apart from the 同步 chip time; selection and inspector kept. | Matches |
| External change with a draft (§5.2 ③) | same | The banner names the document and the discarded drafts and history; 載入新版 discards the draft without writing (a pointer press no longer confirms the draft by blurring it), Esc resolves it from the keyboard. Tabbing to the banner button still confirms the draft by blur, which the guard then rejects; judge whether that is acceptable for keyboard users. | Matches (keyboard Tab path: Flagged) |
| Fingerprint-guard race (§1.1) | same | The rejected save shows in the banner; the external version follows; nothing is merged or retried. | Matches |
| Malformed then corrected YAML (§5.2 ④) | same | Stale badge and banner with `path:line — reason`; recovery is automatic and semantic diagnostics stay listed. | Matches |
| Old tab after a restart (§5.2 ①) | same | 重新連線並讀取 is required before a write; nothing replayed. | Matches |
| Inspector field width | `test_map_editor_accessibility` viewport methods, Chromium and Firefox at 1451x790 and 2560x1440; 2026-10-29 screenshots of settlement and interior fields in both browsers at both sizes | Border-box sizing includes scaled padding and borders; shrinkable grid fields stay within the inspector content edge. Browser assertions cover existing fields, layout coordinates and creation forms, preserve the scaled 16 px font floor, and write nothing. Screenshots show complete right borders on 名稱 and 描述. Measured settlement field widths are 315 px at scale 1 and about 441.4 px at scale 1.4; text remains 17 px and 23.8 px respectively. Game tokens and theme are unchanged. | Matches |
| Copy context for OMP (§1.1) | `MapEditorWorkflowsChromiumTest`, Chromium only | Playwright grants no clipboard permission in Firefox; the Firefox copy path is reviewed by hand. | Matches (Firefox: Flagged) |
| Reflow, long names, 200 % zoom (§2) | `test_map_editor_accessibility`, all three layouts, Chromium and Firefox | Long Chinese node names wrap in the inspector heading; drawers at 200 %. | Matches |
| Game readiness claims | manual check of chips, banner and strip | The editor never labels its static checks as live-save validation or game readiness; persistent safety stays with the game's adoption and synchronization (`world/maps/tests/test_editor_final_yaml_adoption.py`). | Matches |
