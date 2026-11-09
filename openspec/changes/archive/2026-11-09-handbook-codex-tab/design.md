# Design: handbook-codex-tab

## Context

Source of truth: `docs/superpowers/specs/2026-11-09-handbook-codex-titles-design.md` §5 and §7, D1–D4, D6, D7 and D10. Visual reference: `docs/design/handbook-codex-titles/CodexTabProto.vue`, `TileWall.vue`, `CodexEmblem.vue` and `prototype-data.js`, including the legend fix in commit `08406a57` (legend marks have a fixed `calc(12px * var(--ui-scale))` size, and the legend is `position: sticky` at the wall's bottom edge). The prototype is reference only. Never import it from the app.

State after the two prerequisites (verify before starting):

- From `handbook-primitives` and `handbook-titles-tab`: `components/handbook/handbook-tabs.js` (`HANDBOOK_TAB_META`, `handbookTabs({combat})`), `TileWall.vue`, `CodexMedalGrid.vue`, `CodexDetail.vue` (props `detail`, `footer`), `CodexEmblem.vue` (paths in `dock-icons.js` as `emblem_<name>`), `DetailFooter.vue`, `TitleCodexTab.vue`, `QuestDrawer.vue` as tab dispatcher with `combat`, `titleCodex` and `closeGuard`, `ctx.openHandbook(tab)` in `stores/elosern/hud.js`, the `handbook` route slot, and `nav-tools.js` `codex` with `handbook: "titles"`.
- From `lore-codex-schema-v2`: `lore_codex` v2 (`categories[].{key,label,discovered,total,groups[].{key,label,slots[]}}`, slot `{placeholder:true}` or `{key,title,stage,art,card,locked_fields}`), validated client-side by `protocol/panels/exotic.js`. `LoreCodexDrawer.vue` reads v2 discovered slots.
- Still present and removed here: `components/LoreCodexDrawer.vue`, `lib/codex_field_label.js`, `stories/World/LoreCodexDrawer.stories.js`, `stories/fixtures/lore_codex_panels.js` (kept, see D8), `tests/world/lore_codex_drawer.test.js`, the `lore` entry in `HUD_DRAWER_NAMES` / `DRAWER_TITLES` / `DRAWER_ICONS`, `nav-tools.js` `{ key: "lore", drawer: "lore" }`, and the AppClient `LoreCodexDrawer` branch.
- Art rendering: `composables/useArtwork.js` `useArtwork(artwork, availability, options)` returns `{attempt, phase, onImageLoad, onImageError, dispose, …}`. `lib/artwork.js` `artworkAvailability({panel, required, hasReference, artwork})` builds the availability. `ReferenceArtwork.vue` is the canonical consumer to copy from.

## Goals / Non-Goals

**Goals:** the codex tab and its removals as specified in this change's deltas.

**Non-Goals:**

- No server or protocol change. No re-push of `lore_codex` when a portrait completes.
- No search, filter, sort or aggregate "全部" control. The old drawer's aggregate is dropped with the drawer.
- No counts per monster, no per-variant tiles.
- No change to the titles tab beyond its shared components gaining optional props.

## Decisions

### D1. Tabs and route

- `handbook-tabs.js`: `HANDBOOK_TAB_META.codex = { label: "圖鑑", glyph: "lore" }`. `handbookTabs({combat})` returns `["codex", "titles"]` in combat and `["book", "counter", "codex", "titles"]` outside.
- `QuestDrawer.vue`: new prop `loreCodex: { type: Object, default: null }` and a `<LoreCodexTab v-else-if="top === 'codex'" …/>` branch. The effective-`top` rule from `handbook-titles-tab` D3 is extended: `codex` is selected when present and not disabled. In combat a remembered `book` or `counter` resolves to the first combat tab (`codex`). The codex tab is disabled with the panel's reason when the panel is unavailable.
- `nav-tools.js`: the `lore` record becomes `{ key: "lore", label: "圖鑑", testid: "nav-tool-lore", handbook: "codex" }`, with no `drawer`. `openHandbook("codex")` already works through D1 of `handbook-titles-tab`.
- `stores/elosern/hud.js`: remove `lore` from `HUD_DRAWER_NAMES` and from the header comment. `composables/use-drawers.js`: remove the `lore` title and icon entries and update the comment. `AppClient.vue`: delete the `LoreCodexDrawer` import and branch, and pass `:lore-codex="panel('lore_codex')"` to `QuestDrawer`.

### D2. Session memory

`quest-drawer-memory.js` gains `codexCategory: null` (reset in `clear()`). Codex selection reuses `selectedByTab` under the key `codex:<category key>`. The effective category is `memory.codexCategory` when it is present in the panel, else the first category with `discovered > 0`, else the first category. The computed never overwrites the remembered key.

### D3. Pure model `components/handbook/lore-codex-model.js`

| Export | Contract |
| --- | --- |
| `loreCodexStatus(panel)` | `"absent"` / `"unavailable"` / `"available"`, as `titleCodexStatus` |
| `codexRail(panel)` | `categories.map(c => ({ key: c.key, label: c.label, count: c.discovered }))` |
| `defaultCodexCategory(panel)` | as D2 |
| `codexGroups(panel, categoryKey)` | `[{ key, label, items: [...] }]` in slot order. A placeholder item is `{ id: "p:<group key>:<index in group>", selectable: false, label: "未記錄", placeholder: true }`. An entry item is `{ id: slot.key, selectable: true, label, placeholder: false, stage: slot.stage, art: slot.art, title: slot.title }`, with `label` = `title` plus `，已擊敗` / `，已目擊` for a monster stage |
| `firstEntryKey(panel, categoryKey)` | the first entry slot's key, or `null` |
| `codexDetail(panel, categoryKey, key)` | `{ kind: "codex", id, category, name: title, ribbon: category label, emblem: category key, stage, art, stamp, fields: [{ name, label: codexFieldLabel(name), value }], locked: [{ name, label: codexFieldLabel(name) }], track }` or `null`. `stamp` is `{ kind: stage, label: stage === "defeated" ? "已擊敗" : "目擊" }` for a monster and `null` otherwise. `track` is `null` for non-monster entries, else `[{ key: "sighted", label: "目擊", unlocks: null, reached: true }, { key: "defeated", label: "擊敗", unlocks, reached: stage === "defeated" }]`. For a sighted entry, `unlocks` is the readable labels of `slot.locked_fields` joined with `・`. For a defeated entry it is `null`. No field list is hard-coded on the client. The `display_name_zh` field is excluded from `fields`, because it is the title |
| `CODEX_FIELD_LABELS`, `codexFieldLabel(name)` | the v1 map from `lib/codex_field_label.js` plus `published_appearance_zh: "外觀"`, `threat_tier: "威脅"`, `published_description_zh: "描述"`, `published_ecology_zh: "生態"`, `habitat_tags: "棲地"`, `variants: "變種"`. Unknown names map to `資料` |

### D4. Components

- `CodexTileGrid.vue`: `TileWall variant="tile"` over `codexGroups`. The tile slot draws one of three faces. An entry face is a `CodexArt` thumbnail with `class="is-sighted"` (CSS `filter: grayscale(1) brightness(.8)`) when sighted, plus a stage mark `<span class="codex-tile__stage" :data-stage="stage">` with a filled diamond for defeated and a hollow diamond for sighted (SVG `M6 1 11 6 6 11 1 6Z`, `fill` vs `fill="none"`). Its caption is the title. A placeholder face is a hatched dashed tile with `？` and `data-stage="unknown"`. Each cell has `data-testid="handbook__tile--<id>"`. For the monster category only, `<p class="codex-wall__legend" data-testid="handbook__codex-legend">` follows the wall with the three marks. Its CSS is `position: sticky; bottom: 0`, and the mark SVGs are `width: calc(12px * var(--ui-scale)); height: calc(12px * var(--ui-scale)); flex: none`. Copy the rules from `CodexTabProto.vue` `.hb-wall__legend` and `.hb-legend` as of `08406a57`. The wall scroller is the element that owns `overflow-y: auto`, and the legend is its last child.
- `CodexArt.vue`: props `art`, `panel`, `emblem` and `variant` (`tile` | `hero`). It calls `useArtwork(() => props.art, computed(() => artworkAvailability({ panel: props.panel, required: true, hasReference: !!props.art, artwork: props.art })))`. It renders `<img :src="attempt.url" @load="onImageLoad" @error="onImageError">` while `attempt` exists and `phase` is `loading` or `success`. Otherwise (null art, exhausted attempts, failure) it renders `<CodexEmblem :name="emblem">` with `data-testid="handbook__art-emblem"`. It calls `dispose` in `onBeforeUnmount`, following `ReferenceArtwork.vue`. A terminal alpha mask counts as a loaded image (the monster silhouette fallback).
- `CodexDetail.vue` (extended, backward compatible with the title view model): when `detail.kind === "codex"`, the hero band renders `CodexArt variant="hero"` with the rotated stamp over it (`data-testid="handbook__stamp"`, `data-stage`). For monsters, an `<ol data-testid="handbook__research-track">` follows with two `<li :data-reached>` items. Then `fields` render as labelled sections (`data-field="<name>"`), and each `locked` item as a dashed box `data-testid="handbook__locked-field"` with `data-field`, its label and the text `擊敗後解鎖`, and no value. A codex detail passes `footer = null`, so no footer renders, because the codex has no action. The empty detail for "nothing discovered" is `EmptyState` (glyph `lore`, headline `尚無記錄`, guidance `旅途中遭遇的事物會記錄於此`).
- `LoreCodexTab.vue`: rail `IconTabs` (vertical, `show-labels`, `aria-label="圖鑑分類"`, `#icon` = `CodexEmblem :name="tab.key"`, `data-testid="handbook__codex-rail"`), `CodexTileGrid` and `CodexDetail`, in the same grid template as `TitleCodexTab`. The root is `data-testid="handbook__codex"`. Props are `codex`, `memoryScope` and `combat`. Selection is local and dispatches nothing. A vanished selection falls back to `firstEntryKey`.
- `CodexEmblem.vue` / `dock-icons.js`: add `emblem_<key>` paths for `monster`, `race`, `nation`, `region`, `anchor`, `element`, `magic` and `guild` from the prototype's `EMBLEMS`. The title-category `guild` path already exists from change 1 and is shared with the codex `guild`.

### D5. Focus rescue

When a commit removes the focused tile or entry, `QuestDrawer`'s existing `focusSource` rescue must cover the codex tab. Add the codex selection key to `focusSource` and the `codex` rail testid to the rail choice (`handbook__codex-rail`), following the existing pattern.

### D6. Docs

In `docs/game/commands.md` line 24 (the top-bar paragraph), state that 圖鑑 and 稱號冊 open the 手帳 on its 圖鑑 / 稱號 tab and stay available in combat. No command changes, so `docs/game/command-reference.md` is unchanged.

### D7. Removals

Delete `components/LoreCodexDrawer.vue`, `lib/codex_field_label.js`, `stories/World/LoreCodexDrawer.stories.js` and `tests/world/lore_codex_drawer.test.js`. In `component-manifest.json` and `web/webclient/tests/test_vue_showcase_{action,data,overlays,world}_evidence.py`, replace `World/LoreCodexDrawer` (and its story IDs `world-lorecodexdrawer--*`) with `World/LoreCodexTab` and its story IDs. In `docs/development/webclient-vue-frozen-contract-audit.md` §2.3, remove the `lore-codex-drawer` family, extend the `handbook__` family with the testids from D4, and add a dated `handbook-codex-tab` section. Update `tests/test_data_independence_js_webclient.py` paths. Update or replace the browser tests that targeted `lore-codex-drawer` (`web/tests/browser/test_browser_contextual_hud_drawers.py`, `test_browser_drawer_content.py`, `test_browser_contextual_hud_combat.py`, `test_browser_contextual_hud_dock.py` and `test_browser_contextual_hud_stage.py`; find them with `git grep -n "lore-codex-drawer\|nav-tool-lore" web/tests/browser`). Vitest files that open the `lore` drawer directly also need updating, including `tests/dialogue_store.test.js` (`openHudDrawer("lore")`), `tests/app_client_frameless_shop.test.js` and `tests/reference_surface_frame.test.js`. Task 3.2's grep finds them all. The live `webclient-desktop-shell` offline-overlay scenario lists `lore` among reference drawers next to already-retired names (`skill`, `inventory`, `status`). It is a descriptive list that this change leaves as is. They now open `[data-testid="nav-tool-lore"]` and assert `handbook__codex`. Keep every existing `covers_requirement` that still names a live requirement, and move the ones that named the three REMOVED drawer requirements to the new codex-tab requirements at archive (Workflow follow-up).

### D8. Stories

`stories/World/LoreCodexTab.stories.js` (title `World/LoreCodexTab`) uses synthetic v2 fixtures in `stories/fixtures/lore_codex_panels.js` (converted to v2 by `lore-codex-schema-v2`, extended here). It covers these states: monster wall with mixed stages and the legend, sighted detail with locked fields, defeated detail, region with scene art, element without art (emblem), nothing discovered, absent, unavailable, and in combat. `stories/World/QuestDrawer.stories.js` gains a `Codex tab` story.

## Risks / Trade-offs

- [Many `useArtwork` instances on a large wall] → Each is the same composable the stage uses. Placeholders carry no art. No wall-clock assertion is added (CI runners are slow).
- [`.elosern-root` duplicates overriding component styles, which Storybook does not show] → Grep `styles/app-shell.css` for `codex-tile`, `codex-wall`, `codex-art`, `lore-codex-tab` and `codex-detail` and expect no match. Geometry and the sticky legend are asserted on the live client at both reference viewports.
- [Removing the `lore` drawer breaks tests that opened it directly] → D7 enumerates them by grep, and the evidence bridge plus browser tests are rerun.
- [The scene descriptor of a region could fail on the live server's art store] → `CodexArt` falls back to the emblem, which the spec pins.

## Review document (human-reviewed)

This section is the named review document. A human reviews it and no requirement or test pins it:

1. Visual fidelity against Storybook `Design/Handbook` codex states at 1451×790 and 2560×1440: tile size and gap, the hatched placeholder, the desaturated sighted art, the diamond marks, the rotated stamp, the research track and the dashed locked boxes.
2. The copy: 圖鑑, 未記錄, ？, 已擊敗, 僅目擊 (legend), 目擊 (stamp), 擊敗後解鎖, the track labels in D3, the field labels in D3, and the empty-detail text in D4.
3. The monster tile art crops for portrait descriptors, and the scene crops for regions.

The apply worker attaches live-client screenshots at both viewports to the handoff.
