# Handbook: Codex and Titles in the Quest Book — Design

Date: 2026-11-09
Status: Approved (brainstorming)

## 1. Goal

Fold the world codex (圖鑑) and the title book (稱號冊) into the existing quest
window, which already reads like a Monster Hunter World quest book (top
icon tabs, a vertical rail, a list column, a detail column with a red ribbon,
gold subtitle, grade gem and a pinned action bar). The codex gains the MHW
hunter's-notes feel: a tile wall with silhouette placeholders for unrecorded
entries, a hero image per entry, and a two-stage monster research state.

The window is renamed 手帳 (Handbook). Its top tabs become:

| Key | Label | Content |
| --- | --- | --- |
| `book` | 任務簿 | unchanged |
| `counter` | 公會櫃檯 | unchanged |
| `codex` | 圖鑑 | new (replaces `LoreCodexDrawer`) |
| `titles` | 稱號 | new (replaces `TitleCodexPanel` overlay) |

Visual language: the game's existing tokens only (`--ink-*`, `--paper-*`,
`--gold-*`, `--seal-*`, `--f-serif`, `--f-sans`, `--line`, `--radius*`,
`--sp-*`, `--text-*`, `--motion-*`, every size in
`calc(<n>px * var(--ui-scale))`). No new palette.

## 2. Decisions

- D1 Integrate into the quest window rather than a new overlay; rename the
  window and its primary navigation entry to 手帳, hotkey J unchanged.
- D2 The 工具 group keeps its 圖鑑 and 稱號 shortcuts; each opens the handbook
  on its own tab through the existing `routeRequest` mechanism.
- D3 The codex middle column is an MHW tile wall (grouped tiles), not list rows.
- D4 Unrecorded codex entries render as silhouette placeholders, and each
  category discloses its total. This amends the lore-codex non-disclosure
  requirement from "discloses no existence" to "discloses only count and
  ordinal position".
- D5 The codex 魔物 category is re-pointed from threat tiers
  (`MONSTER_TIER_REGISTRY`) to species (`MONSTER_SPECIES_REGISTRY`); the
  tier becomes a grouping and a label.
- D6 Monster research has two stages: sighted and defeated. No counts.
- D7 Hero art reuses existing pipelines only. Monsters use the existing
  `portrait:monster:<visual key>` generation and fallback; regions and
  anchors use their declared `scene:<archetype>`; every other category draws
  a client SVG emblem. No new art subject kind, generator or queue.
- D8 The titles rail is the six fixed-title categories, then a divider, then
  異名 and 提名. Fixed titles render as a medal wall; epithets and ballot
  entries render as list rows.
- D9 Locked fixed titles keep showing their name and hint (current server
  behaviour); only the medal face becomes a dashed silhouette.
- D10 In combat the handbook is reachable only through the tool shortcuts and
  shows only the 圖鑑 and 稱號 tabs.

## 3. Delivery: four changes, in dependency order

1. **Titles tab (client only).** Handbook rename, `titles` tab, medal wall,
   detail, equip/remove/ballot through `ActionBar`. `title_codex` payload is
   unchanged. Removes `TitleCodexPanel.vue` and the `codex` overlay branch;
   the 稱號 tool shortcut opens the tab.
2. **Monster species codex and research state (server).** Re-point the
   monster category; add sighting/defeat recording and the combat hooks.
3. **`lore_codex` schema v2 (server and protocol).** Placeholders, totals,
   groups, stage-filtered fields, art descriptors, raised bounds.
4. **Codex tab (client).** Tile wall, detail with hero art, research state.
   Removes `LoreCodexDrawer.vue` and the `lore` drawer branch; the 圖鑑 tool
   shortcut opens the tab.

Change 1 has no dependency. Change 3 depends on 2. Change 4 depends on 3.

## 4. Server design

### 4.1 Research records (changes 2)

`world/rules/lore_knowledge.py` stays the sole writer.

- The existing `lore_discovered` set is unchanged. A `monster:<species_key>`
  member means *sighted*.
- New append-only attribute `lore_species_defeated`: a set of species keys.
- New writers:
  - `record_species_sighting(player, species_key)` — adds
    `monster:<species_key>` to `lore_discovered`.
  - `record_species_defeat(player, species_key)` — adds the key to
    `lore_species_defeated` and also records the sighting.
  - Both are idempotent, reject an unknown species with the named
    `LoreKeyError`, and schedule the `lore_codex` push after commit through
    the existing `_schedule_lore_codex_push`.
- `CODE_CATEGORIES["monster"]` resolves against `MONSTER_SPECIES_REGISTRY`.
- Hooks:
  - Sighting: `world/rules/combat_initiation.py`, once per hostile
    individual's species when a session is created.
  - Defeat: `world/rules/combat_session/rounds.py` `_record_round_defeats`,
    the same source the quest kill counters read.
  - A participant without a resolvable species records nothing.
- Stale `monster:<tier>` records are omitted by the existing tolerant read.
  No migration (no released users).

### 4.2 `lore_codex` schema v2 (change 3)

```
{
  schema_version: 2,
  available: true,
  discovered_total, total,
  categories: [
    { key, label, discovered, total,
      groups: [ { key, label | null, slots: [Slot, ...] } ] }
  ]
}

Slot = { placeholder: true }
     | { key, title, stage, art, card: [{name, value}], locked_fields: [name] }
```

- Categories keep `CODE_CATEGORIES` order. Slots keep registry order.
- Groups: the monster category groups by the species' default variant
  `threat_tier` (group `key` = tier key, `label` = tier display name), in
  `MONSTER_TIER_REGISTRY` order. Every other category has exactly one group
  with `label: null`.
- A placeholder carries no key, title, art, or any field that could identify
  the entry. Only its ordinal position and group are disclosed.
- `stage`: `"sighted"` or `"defeated"` for monsters; `null` elsewhere.
- Monster card fields by stage:
  - sighted: `display_name_zh`, `published_appearance_zh`, `threat_tier`
    (display name).
  - defeated adds: `published_description_zh`, `published_ecology_zh`,
    `habitat_tags`, `variants` (each `display_name_zh` and `danger_grade`,
    ordinary variants only).
  - `locked_fields` names the defeated-stage fields while only sighted; the
    client sees names, never values.
  - `author_hidden_truth_zh`, `author_explanation_zh` and
    `author_conjecture_zh` are never serialized at any stage.
- Other categories keep their existing declared card fields.
- `art`: an existing art descriptor or `null`.
  - monster: the species' visual key projected by `world.lore.monster_visuals`,
    resolved through the existing monster portrait presenter, including its
    `gallery_fallback` result.
  - region / anchor: the entry's declared `scene_archetype` through the
    existing scene descriptor.
  - others: `null`.
- Bounds (shared by the Python and JS validators, pinned by the existing
  dual-direction parity test): slots per category ≤ 128, total slots ≤ 512,
  card fields ≤ 8, field value ≤ 1024 code points, variants ≤ 8.
  `discovered` and `total` must equal the counted slots.
- Envelope trimming: if the canonical payload exceeds the OOB envelope,
  trailing placeholders drop first (last category first); `total` and
  `discovered` still describe the untrimmed view.

### 4.3 `title_codex`

Unchanged. The medal face is drawn client-side from `category`; guild-category
medals use the existing `GradeGem`.

## 5. Client design

### 5.1 Structure

New components under `web/webclient-app/components/handbook/`:

- `LoreCodexTab.vue` — rail (`IconTabs`, 8 categories, discovered count
  badge), `CodexTileGrid`, `CodexDetail`.
- `TitleCodexTab.vue` — rail (six categories, divider, 異名, 提名 with the
  hot badge while a ballot is pending), `CodexMedalGrid` for fixed titles,
  `QuestList`-style rows for epithets and ballot entries, `CodexDetail`.
- `CodexTileGrid.vue` / `CodexMedalGrid.vue` — group headings and tiles;
  roving focus with arrow keys, selection on Enter, Space or click.
  Placeholders are focusable, named 未記錄, and not selectable.
- `CodexDetail.vue` — hero band (art or emblem; medal plus full-title
  nameplate for titles), the quest detail's ribbon, title, subtitle and
  sections, and a pinned `ActionBar`.
- `CodexEmblem.vue` — one SVG emblem per codex category and per title
  category, in the `dock-icons.js` stroke style. Used for tiles, medal faces
  and the art fallback.
- Pure models: `lore-codex-model.js`, `title-codex-model.js` (payload →
  groups/tiles/detail view). Field labels move to a v2 label map.
- `QuestDrawer.vue` becomes the tab dispatcher only (the book and counter
  bodies stay as they are; no further growth of the 513-line file).
- `quest-drawer-memory.js` gains the codex category, the titles rail key,
  and per-category selection, under the same session scope.

### 5.2 Behaviour

- Full title: shown at the right end of the top tab row on the 稱號 tab
  only, verbatim from `full_title`.
- Equip: select an unlocked medal or an epithet; `ActionBar` 裝備 emits
  `title.equip` (`kind: fixed | epithet`). The equipped entry shows 已裝備
  disabled.
- Remove: only where the row says `can_remove`. 移除… arms a confirm state
  (確認移除・此操作不可恢復); any close attempt (Escape, ✕, scrim) cancels
  it through `closeGuard`, as 放棄任務 does. Confirm emits `title.remove`.
- Ballot: 接受 per row (`title.accept`), 放棄提名 in the action bar
  (`title.decline`).
- Codex detail for a sighted monster shows each `locked_fields` entry as a
  dashed 擊敗後解鎖 box.
- Shortcuts: the 圖鑑 / 稱號 tools call `openHudDrawer("quest")` with a route
  request naming the tab.
- Combat: tools still open the handbook; only `codex` and `titles` tabs are
  rendered.

### 5.3 Removed

`LoreCodexDrawer.vue`, `TitleCodexPanel.vue`, the `lore` HudDrawer branch,
the `codex` OverlayHost branch, `lib/codex_field_label.js`, their stories,
and any `.elosern-root` duplicates in `styles/app-shell.css`.

## 6. Error and empty states

- Panel not yet committed: the tab is enabled and shows `EmptyState`.
- Panel unavailable: the tab is disabled but focusable with the registry
  reason, as the counter tab does.
- Nothing discovered: the full placeholder wall renders; the detail shows
  旅途中遭遇的事物會記錄於此.
- Art pending or failed: the hero falls back to `CodexEmblem`; never an empty
  frame.
- Selected entry gone after a commit: select the category's first discovered
  entry, else show the empty detail. Focus rescue follows `QuestDrawer`'s
  `focusSource` pattern.

## 7. Testing

Specs and tests define logic only, never game data; no wall-clock assertions.

- Server: sighting/defeat writers (idempotent, append-only, defeat implies
  sighting, unknown species rejected); combat hooks with fixture species; v2
  presenter (placeholders carry no identity, stage filtering, `author_*`
  never serialized, `locked_fields`, trimming order); Python/JS validator
  parity.
- Client (vitest): both models; grid roving focus and placeholder
  non-selection; equip; two-step removal and `closeGuard` cancellation;
  shortcut route requests; combat tab set; art fallback to emblem.
- Browser geometry on the live client at 1451×790 and 2560×1440: three
  columns without overflow, no horizontal scroll in grids, no text below
  `--text-xs`.
- Storybook stories for every handbook codex/titles state; update the
  component manifest and showcase coverage.
