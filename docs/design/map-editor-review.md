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
"Interior tools review").
**Viewports:** 1451x790 (reference), 2560x1440, and 200 % zoom of the
reference emulated as a 725x395 CSS viewport at device scale 2 (it reproduces
the layout width, not every media feature of a real browser zoom).

## Disposition key

| Disposition | Meaning |
| --- | --- |
| Matches | The shell presents the scenario as the design describes. |
| Shell ready | The shell's part (chips, banner, diagnostics, inspector, keyboard) is in place; the scenario's domain command arrives in the named later change. |
| Withdrawn | The design withdrew the scenario. |

## Shell-wide review

| Element (design §) | Review notes | Disposition |
| --- | --- | --- |
| Header, domain pill tabs with key chips, breadcrumb (§2) | Seal glyph and serif gold title first; tabs as one pill group; the breadcrumb gains the 「← 返回」 button after cross-map navigation. | Matches |
| Status chips (§5.1) | Four buttons in fixed order, glyph and text with colour. 分區 regenerate/cancel arrive with `map-editor-partition-jobs`; the chip currently expands the partition diagnostics. | Matches (partition action: Shell ready) |
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
| Edit an entrance | §4.4 | Shell ready: entrance relations link both ends with return context; 前往另一端 and 更換端點… arrive with `map-editor-entrance-tools`. |
| Incomplete number / duplicate identity | §5.3 | Matches for numbers (inline error, focus kept, nothing written). Settlement creation forms (P16) state a duplicate node ID inline with a link to the existing node, and the service refuses a duplicate ID, coordinate or ordered road with nothing written. |
| Save semantic work-in-progress | §8 | Matches: the save chip shows saved while the strip lists unfinished rows; nothing claims game readiness. |
| Remove a referenced object | §5.4 | Matches for locations (P15): a location still named by a local map, anchor or landmark, or by a current external index, shows 無法刪除 inline with its references and 不會連帶刪除; an unreferenced one is one undoable command checked again on the fresh disk baseline. Settlement nodes (P16) list every road, gate, city gate, interior entrance and landmark that must be removed first, each linked; an unreferenced node with a current index is one command. Rooms (P17) list every connection, the exterior, interior link and landmark that must go first, each linked; a room joined by a service place or host is refused by the current index; connections are removed directly. |
| Stale or missing external index | §5.4 | Matches: 索引 chip, an external diagnostics row explaining unsupported external claims, and the inline refusal; editing continues. |
| ~~Fail a save during handoff~~ | — | Withdrawn by D3; a failed save is §5.2 ②. |
| Browse while AI edits | §1.1 | Matches (P13): no mode; external changes load automatically. |
| Malformed then corrected YAML | §5.2 ④ | Matches (P13), and the copied context names the stale preview and failing file. |
| ~~Return after AI leaves an inaccessible landmark~~ | — | Replaced: a loadable change with semantic diagnostics loads; the strip's 前往 locates the landmark object. |
| Unexpected manual-mode file change | §1.1 | Matches (P13). |
| Reconnect an old tab / restart service | §5.2 ① | Matches (P13). |
| Source change during partition generation | §9 | Shell ready: 分區 chip and partition diagnostics; generation arrives with `map-editor-partition-jobs`. |
| Selected object moves or disappears | §1.1 | Matches: the selection (also a multi-selection) is kept by identity and removed members are named. |
| Copy context for OMP | §1.1 | Matches: plain text with qualified IDs, relative paths, frames and units and currentness; no token, ownership claim or action. |
| Keyboard-only edits | §6 | Matches for the shell, layout edits, continent edits and settlement edits (N, R, object-list road endpoints, schema-typed fields, Shift+arrow group nudges) and interior edits (N, R, object-list connection endpoints, room fields, 自動排列); entrance edits follow their change. |
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
| Derived results (§4.1, §3) | The inspector section shows the terrain preview state and the partition's input signature against the current one. National borders draw dash-dot ink with no handles. 重新產生分區 and the partition district outlines arrive with `map-editor-partition-jobs`, which also adds rejection of commands during generation (its task 1.2). | Matches (regeneration: Ready, P19) |
| Region prose and classifier fields | Name, nation keys, scene and one-variant-per-line descriptions; a variant containing a line break is shown as external-edit only. A reviewer should confirm that this is acceptable for authored prose. | Matches |

## Settlement tools review

Rows for the settlement screen of design §4.2, delivered by
`map-editor-settlement-tools` (P16). The person reviewing judges tone,
wording and visual polish here; the tests establish only mechanisms. A
"Ready" row lists the elements a later change completes.

| Element (design §) | Review notes | Disposition |
| --- | --- | --- |
| Tools (§4.2, §6) | 選取 V, 節點 N and 道路 R in the tool pill; Escape cancels a picked road source or an open form first. 入口 E is registered by `map-editor-entrance-tools`. | Matches (E: Ready, P18) |
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
| Tools (§4.3, §6) | 選取 V, 房間 N (opens the creation form at once, since a room has no position), 連接 R (source then destination room, then the name and optional 建立雙向) and 自動排列 in the tool pill. 外部入口 E is registered by `map-editor-entrance-tools`. | Matches (E: Ready, P18) |
| Room fields | Name, multiline description, scene from the current index (✓/✕/▲ status; free text when the index is not current) and art key; the ID is shown read-only. | Matches |
| Service rooms (§4.3) | A 服務 · 唯讀 section lists the joining `places` / `service_hosts` records from the index, or states that a standalone room needs none. Host and goods authoring stays out of the editor. | Matches |
| Layout writes (§4.3) | Drag, Shift+arrow, the 版面 X/Y fields (labelled editor-only) and 自動排列 write only `content/map-editor-layouts/<id>.yaml`; the strip names it after the save. Creating a room writes no layout; the new room appears at the list position. 自動排列's button states that it overwrites the layout and can be undone. | Matches |
| The exterior entrance (§4.3) | The dashed exterior card and editing of the exterior and interior links arrive with the entrance tools; the room inspector lists the entrance as a relation. | Ready, P18 |
| New and removed interiors | ＋ 新室內 creates a standalone interior with its first room and opens it; 刪除室內文件 sends one command that the service guards like a room deletion and leaves the layout for cleanup. A reviewer should judge whether removing a whole document needs more emphasis than an inline action. | Matches |
| Duplicate identity (§5.3) | The room forms state an ID already used by any interior inline with 前往現有房間; the service refuses it on the fresh disk as well. | Matches |
