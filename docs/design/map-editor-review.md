# Map Editor Fidelity Review

Human review of the standalone map editor against the approved frontend
design (`docs/superpowers/specs/2026-10-26-map-editor-frontend-design.md`)
and its prototype (`docs/design/map-editor/`, Storybook `Design/MapEditor`).
Tone, wording quality and visual polish are judged here by a person. They are
not requirements pinned by tests: the tests establish mechanisms and
interactions only.

**Reviewed slice:** `map-editor-interaction-shell` (P14), the workbench shell.
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
| Move a river control point | §4.1 | Shell ready: layers, inspector frame/unit fields and 分區 chip are in place; control points arrive with `map-editor-continent-tools`. |
| Add a location without a local map | §4.1 | Shell ready: 無本地圖 tags in the tree and inspector, and search finds every location; creation arrives with `map-editor-continent-tools`. |
| Move a settlement node | §4.2 | Shell ready: the inspector lists the node's directed relations from authored fields; moving arrives with `map-editor-settlement-tools`. |
| Create a bidirectional street | §4.2 | Shell ready: roads read as directed rows; the road tool with 建立雙向 arrives with `map-editor-settlement-tools`. |
| Rearrange an interior | §4.3 | Matches: drag, Shift+arrow and layout fields write only the layout file, named in the strip after a save; 自動排列 arrives with `map-editor-interior-tools`. |
| Edit an entrance | §4.4 | Shell ready: entrance relations link both ends with return context; 前往另一端 and 更換端點… arrive with `map-editor-entrance-tools`. |
| Incomplete number / duplicate identity | §5.3 | Matches for numbers (inline error, focus kept, nothing written); duplicate identity arrives with the identity-editing domain tools. |
| Save semantic work-in-progress | §8 | Matches: the save chip shows saved while the strip lists unfinished rows; nothing claims game readiness. |
| Remove a referenced object | §5.4 | Shell ready: Delete shows the inline explanation (external references listed, internal references shown as dangling, 不會連帶刪除); the delete commands arrive with the domain tools, and the service guard stays the authority. |
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
| Keyboard-only edits | §6 | Matches for the shell and layout edits; domain edits follow their changes. |
| Long names and 200 % zoom | §2 | Matches: headings, IDs and tree rows wrap or break anywhere; side columns become drawers; status chips stay in the viewport. |
