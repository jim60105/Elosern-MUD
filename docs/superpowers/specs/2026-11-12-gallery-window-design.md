# Gallery window design

**Date:** 2026-11-12
**Status:** approved in brainstorming; prototype at `docs/design/gallery-window/`
(Storybook `Design/GalleryWindow`)
**Origin:** `tmp/gallery-rail-species-budget-handoff.md` — the 24-row subject
rail reserves 23 rows for species, so no companion or NPC gallery can be opened
and 29 of 52 species are unreachable.

## Problem

The gallery panel lists every subject kind on one rail capped at 24 rows. Any
split of that budget starves one kind as the catalogs grow. The surface is also
a flat overlay that predates the book-style windows (quest handbook, codex,
party, shop), crops 9:16 portraits into square thumbnails, and cannot show
scene backgrounds at all.

## Goals

- Replace the single rail with categories that are each bounded on their own,
  so no kind can crowd out another.
- Rebuild the gallery as its own book-style window with a left category rail,
  after the codex tab.
- Show images at their true aspect ratio: portraits 9:16 (864×1536), scenes
  16:9 (1536×864).
- List only subjects the player has a reason to know.

## Non-goals

- No change to art generation, storage, the card model, bindings, face-rect or
  stage-transform rules, or official-art resolution.
- No search and no filter tabs (see D7).
- No redesign of the four editors (generate drawer, binding drawer, face-rect
  modal, stage-transform modal); they are reopened from the new action footer.

## Delivery

The work is four independent pieces, shipped in this order. Each gets its own
OpenSpec change.

0. **Remove the baseline art-only visual species** (see "Prerequisite").
   Small, and it removes a special case from everything after it.
1. **Gallery window and category-scoped panel** (D1–D9). Ships 我的角色,
   隊友 and 魔物. 人物 and 背景 are present on the rail but disabled with a
   reason. Resolves the handoff.
2. **People category and the met-person record** ("Specification 2").
3. **Scene category and the scene gallery** ("Specification 3").

The window, the wall, the page and the panel shape are designed for all five
categories now, so specifications 2 and 3 add data and enable a tab without
reshaping the wire or the layout.

## Prerequisite: remove the baseline art-only visual species

The visual registry merges 40 combat species with twelve authored "baseline"
rows (`slime`, `goblin`, `giant_rat`, `wolf_beast`, `ogre`, `earth_dragon`,
`two_headed_dragon`, `magical_creature`, `troll`, `ancient_dragon`,
`demon_god`, `calamity_beast`). They were meant for tier-built monsters that
have no combat species, reached through `Monster.art_species_key`. No
non-test code writes that attribute, so no monster in the game uses them; the
startup sync still generates and stores art for all twelve, and several take
rows on today's rail.

The change removes:

- `BASELINE_VISUAL_ROWS` and `MonsterVisualDeclaration.is_baseline_art_only`
  (`world/lore/monster_visuals.py`); the registry becomes the projection of
  the combat species registry alone.
- `Monster.art_species_key` (`typeclasses/monsters.py`) and the fallback that
  reads it (`world/art/presenter.py`, `ART_SPECIES_PROVENANCE_ATTRIBUTE` in
  `world/art/official_refs.py`).
- The baseline requirements and scenarios of `monster-visual-identity` and the
  tier-built scenario of `species-portrait-identity`.
- Stored gallery records, queue records and image files of the twelve keys,
  through the existing unregistered-key handling or an explicit cleanup step;
  the change decides which and proves no orphan remains.

Tests that borrow `BASELINE_VISUAL_ROWS[0]` as a sample key switch to a
synthetic registry. The tier registry's example labels (史萊姆, 哥布林, …) are
plain strings with no link to these rows and stay.

## Decisions

### D1. Five categories on a vertical rail

| Key | Label | Contents | Bound |
| --- | --- | --- | --- |
| `mine` | 我的角色 | Every character of the account that owns the rendered puppet (the `roster` panel's set), the live one first and marked 操作中 | `MAX_NR_CHARACTERS` (≤ 10) |
| `party` | 隊友 | The live character's active party companions (`live_companions`), party order | party capacity |
| `people` | 人物 | Named NPCs the live character has interacted with, grouped by place (specification 2) | one place per panel |
| `monster` | 魔物 | Visual species the player has sighted, grouped by threat tier | visual registry size (authored) |
| `scene` | 背景 | Scene archetypes the live character has entered (specification 3) | archetype registry size (authored) |

The category set and order are closed and client-labelled. `mine` follows the
account, not the puppet: while the player possesses a companion, `mine` still
lists the account's characters and `party` still lists the owning character's
party.

### D2. Group headings only where grouping exists

A category's subjects arrive in ordered groups. A group with a label draws a
heading; a group without one draws none. `mine` and `party` have one unlabeled
group, so the wall starts with tiles and never repeats the tab's name.
`monster` has one group per threat tier.

### D3. Monsters are grouped by threat tier and gated by sighting

- Tier of a species is the tier of its default variant, in
  `MONSTER_TIER_REGISTRY` order — the codex's rule, so the two surfaces agree.
- A species is listed only when the holder's lore record holds
  `monster:<key>` (the record the codex reads). The holder is the same one the
  `lore_codex` panel uses.
- Every tier that has at least one registered species draws its heading with
  `seen / total`. Unseen species get no tile and no placeholder: the gallery
  manages images, the codex owns collection progress.
- After the prerequisite change every visual species is a codex species, so
  the sighting gate needs no exception.

### D4. The wall with an inline image tray

The wall is a grid of aspect-true subject tiles (name caption; image count for
subjects that may hold several images; 操作中 ribbon on the live character).

- Selecting a subject whose kind allows more than one card opens a **tray**
  directly under that subject's row, spanning the row. The tray lists that
  subject's cards as tiles of the same size, then a 生成新圖 tile, then a
  second run labelled 官方圖片 (唯讀) for its official entries.
- A subject whose kind caps cards at one (monsters; scenes later) opens no
  tray. Selecting it selects its only image, or the empty page when it has
  none.
- The tray is tied to its owner by a seal-coloured wash, a border and a notch
  under the owner tile. Card tiles carry state by shape and text, not colour
  alone: a crown and 預設 on the default, a spinner and 生成中, a warning
  triangle and 生成失敗; official tiles have a double border.
- One tray is open at a time. Opening it scrolls it into view.

### D5. The page shows one image

The right page belongs to the selected image.

- **Portrait:** the art fills the page height at 9:16; ribbon, subject name,
  image facts (label, default mark, relative and exact date, chips), binding
  conditions sit beside it.
- **Landscape (scenes):** the art spans the page width at 16:9; the facts sit
  under it.
- The ribbon reads `<category>` or `<category>・<group>`.
- The footer is a `DetailFooter` whose buttons depend on the selection:

| Selection | Buttons |
| --- | --- |
| Character card | 刪除 · 臉框 · 舞台位置 · 綁定裝備 · 設為預設 (disabled as 目前預設 on the default) |
| Monster card | 臉框 · 舞台位置 · 重新生成 |
| Scene card (spec 3) | 重新生成 |
| Official entry | 清除個人調整 · 臉框 · 舞台位置 · 設為預設 |
| Pending card | none; the page says it is generating |
| Failed card | 刪除 · 重新生成 |
| Subject without images | 生成新圖 |

Buttons stay capability-driven: the table is what the declared kind
capabilities produce, not a kind comparison in the client. 刪除 keeps its
confirmation step.

### D6. The panel carries one category at a time

`gallery` becomes schema version 4:

```
{
  schema_version: 4, available: true, kind: "gallery",
  categories: [{ key, count, enabled, reason }],   // all five, fixed order
  category: "<key>",                               // the selected one
  groups: [{ key, label, seen, total,              // label/seen/total nullable
             expanded, count,                      // see "Group expansion"
             subjects: [{ subject_key, kind, display_name,
                          is_current, card_count, artwork }] }],
  selected: "<subject_key>" | null,
  cards, official_entries, equipment_summary,
  capabilities, binding_warnings, error_state      // of `selected`, as today
}
```

- `subjects` and `GALLERY_MAX_SUBJECTS` are removed. There is no cross-kind
  budget.
- `groups` holds only the selected category. Switching category is a server
  round trip, exactly as switching subject already is:
  `gallery.category.select {category}`. The rail marks the pressed tab
  immediately and the wall follows the next committed panel.
- `gallery.subject.select {subject_key}` must name a subject of the selected
  category.
- Each subject tile carries the artwork descriptor of that subject's resolved
  default image (or null), so the wall needs no per-subject request.
- `selected` is null only for a category with no subject; then the card fields
  are empty and `capabilities` is null.
- Each category is bounded by its own source: the account's character limit,
  the party capacity, the authored registry. None grows without an author.
  There is no truncation rule and no "incomplete list" state: a list that
  silently drops subjects is the defect this design removes.
- The validators keep one hard ceiling on subjects per panel, set far above
  any authored content. It is a guard against a programming error, not a
  content rule: a panel past it is not rendered in part — the gallery takes
  the common unavailable form and the error is logged.
- A category that can grow without an author (people) must page, delivering
  complete content in parts. That is designed in specification 2.
- Both validator mirrors (Python and JS) enforce the shape, fail closed.

**Group expansion.** Every group carries `expanded` and `count`. A group with
`expanded: false` carries its `count` and no `subjects`. In specification 1
every group is expanded, so the fields are constant; they exist so the people
category can page by group without reshaping the panel.

**Stored selection.** The session remembers one category and one subject per
category. Opening the gallery restores them. A remembered subject that is gone
falls back to the category default (the live character in `mine`, else the
first subject, else null); a remembered category that is disabled falls back to
`mine`. A fresh session opens on `mine` with the live character selected.

**Authority.** Every mutating gallery action re-derives whether its subject is
admitted for the actor — a member of any enabled category — before writing.
Being absent from the currently listed category is not a rejection; being in
no category is.

### D7. Removed from the current surface

- The subject rail, the truncation scenario and `GALLERY_MAX_SUBJECTS`.
- The filter tabs (全部／預設／已綁定／生成中／失敗) and the grid/list
  toggle. One subject's images fit a tray; tile marks carry the states.
- `GalleryPanel.vue` and `GalleryDetailRail.vue`. No second surface remains.
- The tool entry is renamed from 角色肖像圖庫 to 圖庫.

### D8. The window

The gallery is its own window, mounted like the party and shop windows rather
than inside `OverlayHost`, on the shared drawer chrome (seal `gallery`, title
圖庫, close, focus trap, Escape, motion). Its body is the book grid of the
codex tab: rail, wall, page. The rail is wider than the codex rail because
我的角色 is four characters.

Scrolling regions (the wall, the page facts) reserve a stable scrollbar gutter,
so a list that grows past one page never reflows its tiles.

### D9. Keyboard and focus

- Rail: the existing `IconTabs` roving tablist; disabled tabs stay focusable
  and announce their reason.
- Wall: one listbox with one tab stop; arrows, Home and End move focus in
  reading order across groups; Enter, Space and click select. The owner tile
  exposes `aria-expanded`.
- Tray: a second listbox with its own tab stop, directly after the wall in tab
  order, labelled `<subject>的圖片`. Escape inside the tray returns focus to
  the owner tile; a second Escape closes the window.
- A commit that removes the focused tile returns focus to the rail's selected
  tab, as the codex tab does.
- All sizes use `--ui-scale` or tokens, no text below `--text-xs`, durations
  use `--motion-*`, and reduced motion disables the tray and page animations.

## Components

| Unit | Responsibility |
| --- | --- |
| `web/webclient/presentation/gallery.py` | Build the v4 panel: categories, the selected category's groups, the selected subject's cards. Read-only. |
| `web/webclient/presentation/gallery_categories.py` (new) | One function per category returning ordered groups of subjects; the admission check used by actions. |
| `gallery_selection.py` | Stored category and per-category subject, with the fallbacks of D6. |
| `protocol/panels/gallery.js` and the Python validator | Mirrored v4 validation. |
| `GalleryWindow.vue` | Window frame, rail, wiring of wall, page and the four editors. |
| `GalleryWall.vue` | Grouped aspect-true tiles, the tray, roving focus (D9). |
| `GalleryImagePage.vue` | Art, facts and the footer for one selection. |
| `gallery-window-model.js` | Pure view-model functions: tabs, groups, footer descriptor. |

The wall extends the `TileWall` interaction contract but cannot reuse the
component as is: tiles are not square and a tray interrupts the grid.

## Testing

- Presenter tests use synthetic registries, parties and rosters. They assert
  the rules (ordering, grouping, sighting gate, fallbacks, the ceiling's
  unavailable form), never shipped counts.
- The registry patch in `test_art_push.py` is removed; its character
  assertions hold against the shipped registry because characters no longer
  share a budget with species.
- Mirrored validator tests reject malformed v4 payloads on both sides.
- Component tests cover the tray placement, the one-card rule, footer
  descriptors per selection, focus rescue and the keyboard contract.
- Storybook stories replace the `GalleryPanel` and `GalleryDetailRail` stories;
  `component-manifest.json` follows.
- `test_browser_gallery_image_contract.py` is rewritten for the window: open
  the 魔物 category, select a sighted species, assert its image. The fixture
  must record a sighting first.
- Gates: `tools.spec_traceability`, `tools.contract_gate`, `pnpm test`,
  `pnpm run build-storybook`, `pnpm run showcase-coverage`, and a rebuilt dist
  before the browser run.

## Specification 2: people

### Who is listed

A subject appears under 人物 when all of these hold:

- it is an NPC with a named portrait policy (`portrait_policy.mode ==
  "named"`); NPCs on the generic built-in fallback have no gallery and are
  never listed;
- the live character has interacted with it (below);
- it exists in the world now;
- it is not in the live character's party (those are under 隊友).

Other players' characters are never listed. A player manages their own
characters under 我的角色 and nobody else's.

### The met-person record

- Owned by the character, like the lore record and the party. Switching
  character switches the list.
- One entry per named NPC, keyed by its portrait stable key: the place and the
  time of the last interaction.
- Written by exactly four player-initiated interactions that name the NPC as
  their target: talk, look, using one of its services, and inviting it to the
  party. Being attacked or addressed by the NPC writes nothing.
- While the player possesses a companion, the interaction is recorded for the
  character that owns that companion.
- Every interaction updates the time. The place is rewritten only when it
  differs from the stored one.
- **Place** is the settlement the interaction happened in, or the wilderness
  region when outside any settlement. Districts are not used: an NPC that
  walks between home and shop would otherwise jump between groups.
- One writer module. The presenter stays read-only. A read skips entries whose
  NPC no longer exists; the writer drops such entries when it next writes, so
  no cleanup job is needed.

### Grouping and paging

- One group per place. Groups are ordered by the most recent interaction in
  them; subjects inside a group by most recent interaction.
- Exactly one group is expanded. The panel carries every group's label and
  `count`, and the subjects of the expanded group only.
- `gallery.group.select {group}` expands another group and collapses the
  current one — one server round trip, like a category switch. Group headings
  in this category are buttons with `aria-expanded`; tier headings under 魔物
  stay plain headings.
- The session remembers the expanded place and the selected person per
  character. A remembered place that is gone falls back to the most recent
  one.
- This is the only category that grows without an author, and place paging is
  what keeps its content complete without a truncation rule.

### Out of scope, recorded for later

The project intends to stop reclaiming scene NPCs, so that they live on
somewhere in the world. Nothing here depends on that: "exists in the world
now" lists whoever exists. Once NPCs persist, this list only grows, which
place paging already carries.

## Specification 3: scenes

### Current state

- A scene subject is a scene archetype (`scene:<archetype>`), not a room;
  rooms of one archetype share one image.
- A room's background resolves in this order: the room's own official image,
  the archetype's generated image, an operator's archetype image, the bundled
  archetype image, a terminal image. A generated image therefore overrides the
  bundled one.
- Generated scene images are classic asset records with no gallery. Only the
  staff command `@art requeue` regenerates them, and `art-staff-commands`
  states that no player-triggered regeneration surface exists.

### The scene kind becomes gallery-bearing

- The capability record of the scene kind changes to: has a gallery, one card,
  no bindings, no age precondition, no prompt field selection, no free text —
  the monster kind's set, plus two new declared facts shared by every kind:
  whether a card may carry a face rectangle and whether it may carry a stage
  transform. Scenes declare neither; characters and monsters declare both. The
  footer of D5 reads these instead of comparing kinds.
- Existing scene asset records and image files migrate to gallery records. The
  migration is idempotent and leaves no orphan file or record.
- The generated step of the background chain reads the scene gallery's default
  card. The order of the chain does not change; every scenario of
  `scene-artwork-presentation` is re-verified against the new source.
- Generation, pending and failed states, deletion and pushes go through the
  gallery path the other kinds use. `@art requeue` and `@art retry` follow the
  kind's new declaration.
- `art-staff-commands` drops the statement that players cannot regenerate, for
  the kinds the gallery window serves.

### The category

- Lists the archetypes the live character has entered. The fact is recorded at
  the existing room-entry seam that ensures the scene asset, per character.
- One unlabeled group; no tray, since the kind holds one card.
- The page shows the image in effect for the archetype and says which it is:
  生成圖 or 官方內建圖 (no generated card yet).
- Footer: 刪除 and 重新生成 on a generated image; 生成新圖 on the bundled
  one. Deleting returns the archetype to its bundled image. No face rectangle,
  no stage transform, no bindings, no custom prompt.
- Tiles are 16:9; the page puts the art above the facts.
- Not listed: a room's own official image (authored, fixed, never generated)
  and the dream throne scene (not an archetype).
- Scene images are world assets, like NPC and monster images: a regeneration
  changes the background for every player.

## Prototype

`docs/design/gallery-window/` — `GalleryWindowPrototype.vue`, `GalleryWall.vue`,
`prototype-data.js`, `GalleryWindow.stories.js`. Reference only, synthetic
fixtures, not imported by the app. Stories: MyCharacters, FirstRelease, Party,
OfficialImage, NoImages, Monsters, People (place groups, one expanded), Scenes
(a generated image), SceneBundled (the bundled image), and three at
1920×1080. The
prototype's tiles are plain buttons; the keyboard contract of D9 is specified
here, not prototyped.
