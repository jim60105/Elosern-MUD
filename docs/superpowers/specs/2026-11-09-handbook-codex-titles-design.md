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

## 3. Delivery: OpenSpec changes, in dependency order

The work is proposed as five OpenSpec changes under `openspec/changes/`. The
original first change (titles tab) was split in two after review because it
exceeded one workday.

| # | Change | Scope | Depends on |
| --- | --- | --- | --- |
| 1 | `handbook-primitives` | Client. Extracts the quest detail's action footer into a shared `DetailFooter.vue` (same test ids); adds the handbook `TileWall`, `CodexEmblem` and `CodexDetail` with stories and a vitest evidence bridge. | — |
| 2 | `handbook-titles-tab` | Client. Renames the quest window to 手帳; adds the `titles` tab (medal wall, epithet and ballot rows, equip, two-step removal cancelled through `closeGuard`, ballot answers); adds the handbook route request (`slot: "handbook"`, each request applied once); the 稱號冊 shortcut opens the tab; combat shows only the handbook tabs. Removes `TitleCodexPanel.vue` and the `codex` overlay branch. `title_codex` is unchanged. | 1 |
| 3 | `lore-species-research` | Server. Re-points the monster category to `MONSTER_SPECIES_REGISTRY`; adds `lore_species_defeated`, `record_species_sighting`, `record_species_defeat`, `list_species_defeated` and post-commit push scheduling. The sighting hook is called when a hostile combat session is created and credits every player character in the session; the defeat hook is in `_record_round_defeats`. Removes the tier reveal on defeat. | — |
| 4 | `lore-codex-schema-v2` | Server and protocol. `lore_codex` v2 (totals, identity-free ordinal placeholders, tier groups, stage-filtered species cards with `locked_fields`, art descriptors with per-slot failure isolation), bounds, envelope trimming, JS validator parity; an interim v2 read in `LoreCodexDrawer`. | 3 |
| 5 | `handbook-codex-tab` | Client. The `codex` tab (rail, grouped tile wall, stage marks drawn as different shapes, sticky legend, hero art with emblem fallback, stamp, research track derived from `locked_fields`, locked boxes); the 圖鑑 shortcut opens the tab. Removes `LoreCodexDrawer.vue`, `lib/codex_field_label.js` and the `lore` drawer branch. | 2, 4 |

The client chain (1 → 2) and the server chain (3 → 4) are independent until
change 5. Change 5 depends on 2 for sequencing only: it extends the handbook
shell and modifies the same quest-drawer and desktop-shell requirements.

Known limits recorded in the proposals:

- Kills recorded outside `_record_round_defeats` do not count as defeats.
- A portrait that finishes generating reaches the codex on its next push; no
  new push path is added.

## 4. Server design

### 4.1 Research records (change 3)

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
  - Sighting: a helper in `world/rules/combat_initiation.py`, called when a
    hostile session is created, once per hostile individual's species, for
    every player character in the session.
  - Defeat: `world/rules/combat_session/rounds.py` `_record_round_defeats`,
    the same source the quest kill counters read.
  - A participant without a resolvable species records nothing.
- Stale `monster:<tier>` records are omitted by the existing tolerant read.
  No migration (no released users).

### 4.2 `lore_codex` schema v2 (change 4)

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
  `discovered` equals the category's entry-slot count; the slot count is at
  most `total`.
- Envelope trimming: if the canonical payload exceeds the OOB envelope,
  trailing placeholders drop first (last category first), then art
  descriptors; if it still does not fit, the panel fails closed. Entries are
  never trimmed, and `total` still describes the untrimmed view.

### 4.3 `title_codex`

Unchanged. The medal face is drawn client-side from `category`; guild-category
medals use the existing `GradeGem`.

## 5. Client design

### 5.1 Structure

New components under `web/webclient-app/components/handbook/`:

- `LoreCodexTab.vue` — rail (`IconTabs` with `showLabels`, 8 categories,
  discovered count badge), `CodexTileGrid`, `CodexDetail`.
- `TitleCodexTab.vue` — rail (`IconTabs` with `showLabels`: six categories
  (風流韻事 drawn as 韻事), divider, 異名, 提名 with the hot badge, present only
  while a ballot is pending), `CodexMedalGrid` for fixed titles,
  `QuestList`-style rows for epithets and ballot entries, `CodexDetail`.
- `CodexTileGrid.vue` / `CodexMedalGrid.vue` — group headings and tiles;
  roving focus with arrow keys, selection on Enter, Space or click.
  Placeholders are focusable, named 未記錄, and not selectable.
- `CodexDetail.vue` — hero band (art or emblem; medal plus full-title
  nameplate for titles), the quest detail's ribbon, title, subtitle and
  sections, and the quest detail's pinned action footer
  (`QuestDetail` `.quest-detail__actions` / `__why` / `__btn`), extracted into
  a shared component rather than copied; `ActionBar` is not used because the
  quest window does not use it.
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
- Equip: select an unlocked medal or an epithet; the footer's 裝備 emits
  `title.equip` (`kind: fixed | epithet`). The equipped entry shows 已裝備
  disabled with ★ 目前裝備中 in the footer's reason slot; a locked medal stays
  selectable (its detail shows 取得條件) with 裝備 disabled and
  尚未取得，無法裝備.
- Remove: only where the row says `can_remove`. 移除… arms a confirm state
  (確認移除・此操作不可恢復); any close attempt (Escape, ✕, scrim) cancels
  it through `closeGuard`, as 放棄任務 does, and focus moves to 取消 when
  armed. Confirm emits `title.remove`.
- Ballot: select a nominee; the footer offers 放棄提名 (`title.decline`) and
  接受此異名 (`title.accept`).
- Tile stage marks differ by shape: defeated is a filled gold diamond,
  sighted a hollow one (sighted art is also desaturated); placeholders are a
  hatched dashed tile with ？. A legend under the monster wall names all three.
- The monster detail shows a two-pip research track (目擊｜擊敗, each naming
  what it unlocks) and a rotated stage stamp over the hero (已擊敗 / 目擊).
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

## 6. Prototype

`docs/design/handbook-codex-titles/` (Storybook `Design/Handbook`) is the
approved visual reference: real `HudDrawer`, `IconTabs`, `GradeGem`,
`EmptyState` and `QuestDrawer`, prototype `TileWall`, `CodexEmblem`, codex
and titles tabs, synthetic v2 fixtures. Monster tiles show the pipeline's
offline fallback (`monster_anon`).

## 7. Error and empty states

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

## 8. Testing

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
