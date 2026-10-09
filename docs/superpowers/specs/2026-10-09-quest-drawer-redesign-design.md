# Quest Drawer Redesign Design

**Date:** 2026-10-09
**Status:** Visual design approved through the Storybook prototype. Split into five OpenSpec changes (§9); implementation not started.
**Scope:** Replace the quest drawer's stacked 我的任務簿 and 公會櫃台 sections with one two-level tabbed master/detail surface, and give the `quest_log` and `services` guild-board payloads the structured fields that surface needs.

The current drawer stacks two text-heavy cards. In the live client every quest-book row repeats itself: `detail` is the multi-line `describe_quest_detail()` blob (name, state, stage, objective, progress, grade, rationale, flavor, reward), which the client renders as one run-on paragraph under fields that already show the same facts. `reward_line` already starts with 獎勵：, so the client prints 獎勵：獎勵：. The client renders the 0-based `stage_index` as 第 0 階段 while the blob says 階段：1. The board shows only a name, one objective line, and a reward string, so a player cannot judge an offer before accepting it.

The guild rank block (rank crest, merit meter, 預約升等考核) is approved as is and is carried over visually unchanged.

**Visual reference:** the approved Storybook prototype is committed at [`docs/design/quest-drawer-redesign/`](../../design/quest-drawer-redesign/). It contains `QuestDrawerPrototype.vue` (a self-contained component), `prototype-data.js` (mock data in the §4 payload shapes, using real catalog prose), and `QuestDrawerPrototype.stories.js`. Storybook loads it through the `../docs/design/**/*.stories.js` glob in `.storybook/main.js` under the title `Design/QuestDrawerRedesign`, with the stories `QuestBook`, `GuildBoard`, and `AwayFromCounter`; run `pnpm run serve-storybook` and open `?path=/story/design-questdrawerredesign--quest-book`. The prototype is the source of truth for colors, spacing, glyph shapes, and the gem material ladder, and implementation should match it. It is reference only: it reads no payload, sits outside the webclient component-coverage manifest, and is not imported by the app. Where this document and the prototype disagree on behavior, this document wins.

## 1. Authority and Constraints

- `web/webclient-app/AGENTS.md` governs: desktop 16:9 only, ship through OpenSpec, no standalone HTML prototypes, and grep `styles/app-shell.css` for `.elosern-root` duplicates of any restyled class.
- Server-authoritative honesty stays: the client renders only committed payload fields, never synthesizes an action descriptor, and never enables an action the server disabled.
- The style is the existing ink-night system in `styles/tokens.css`: ink grounds, paper text, seal-red for primary action, selection and status, and muted gold for emphasis and focus. Monster Hunter World's quest board was the layout reference only: list on the left, detail on the right, conditions and client set apart. No parchment and no book metaphor.
- Every size is written `calc(<n>px * var(--ui-scale))` or uses a type/spacing token. No text below `--text-xs`.

## 2. Selected Approach

The rejected alternatives were a single merged list with one detail pane (no good home for the rank block, long list), three columns (too narrow at the 1451px reference width), and collapsible state groups (the user wants no expand/collapse churn; a player never needs to see all three states at once).

Selected: **two-level icon tabs, then master/detail**.

```
┌─ (◎) 任務   [📜][🛡]  ←first-level tabs (icons only) ─────────────── [×] ┐
├────┬──────────────────────────┬──────────────────────────────────────────┤
│ ⌛3│ 進行中 ─────────────── 3 │ ▶討伐委託                          ◇F◇  │
│ ✓2 │▌⚔ 驅除東部平原穗鳴雀 ⚑ ◇F│ 驅除東部平原穗鳴雀                       │
│ ✕1 │  ━━━━━━──────── 1/2      │ 在東部大平原討伐 2 隻穗鳴雀              │
│    │ ⚔ 討伐西北高地…霧鬃山貓 ◇D│ 計數變體：領群型、啄穗型                 │
│    │  ──────────────── 0/1    │ 階段 1/1                         1 / 2   │
│    │                          │ ▰▰▱▱                                     │
│rail│        list column       │ 評價 ───────────  │ 期限 ───────────     │
│    │                          │ 低階群居鳥類…     │ ◷ 無期限             │
│    │                          │ ┃委託人 埃洛西恩冒險者公會 阿爾托利亞分會 │
│    │                          │ ┃收穫已近尾聲，東側田區…            (🛡)  │
│    │                          │ 報酬  [◎ 40 銅] [☆ 20 功績] [⚗ 治療藥水×2]│
│    │                          ├──────────────────────────────────────────┤
│    │                          │ 放棄委託                       [⚑ 追蹤中] │
└────┴──────────────────────────┴──────────────────────────────────────────┘
```

## 3. Surface Structure

### 3.1 Frame and header

`QuestDrawer.vue` replaces the inline `.quest-drawer` block in `AppClient.vue` and fills the existing `HudDrawer` workspace. The header row holds the drawer seal glyph, the title 任務, the first-level tabs, and the close button. Body grid: `rail (68px) | list (minmax(360px, 0.82fr)) | detail (minmax(0, 1.18fr))`, all scaled by `--ui-scale`. The list and the detail scroll independently. The detail's action bar is pinned to its bottom.

### 3.2 First-level tabs (top)

Two icon-only tabs: 任務簿 (scroll glyph) and 公會櫃檯 (guild-shield glyph). The active tab has a gold icon with a soft glow and a 2px seal-red underline that sits on the header rule. Each tab carries `role="tab"`, `aria-label`, and a tooltip shown on hover and on keyboard focus.

公會櫃檯 is disabled when the drawer has no usable guild section. It uses `aria-disabled="true"` rather than the native `disabled` attribute, so it stays focusable and keyboard users can read its tooltip. The tooltip then states the reason: the services panel's own `reason.message` when the panel is unavailable, otherwise 需在公會職員面前才能辦理. The drawer remembers the last first-level tab for the session. The first open, and any open where the remembered tab is now disabled, lands on 任務簿.

### 3.3 Second-level rail (left)

A vertical icon tablist (`aria-orientation="vertical"`). The active tab joins the list column (the list background, no right border, a 3px seal-red marker on its left edge). Each tab shows a count badge when its count is non-zero, and a tooltip on hover and focus.

- **任務簿 rail:** 進行中 (hourglass), 已完成 (circled check), 失敗 (circled cross). Badges are ink-and-gold. The 已完成 badge turns seal-red ("hot") only when at least one completed row has an enabled counter `turnin` descriptor, which marks it as the one actionable state. Default tab: 進行中.
- **公會櫃檯 rail:** one difficulty gem per key of the guild section's `rank_ladder` (today F E D C B A S), always in ladder order so positions never move. The client never hardcodes the ladder. A small gold dot marks the player's own rank. A grade with no listed offers is dimmed. Grades above the player's rank are shown locked (dimmed, lock treatment), because `list_guild_offers()` only lists offers at or below the actor's rank. Their empty state says the grade opens after promotion, a fact the server rule guarantees, so it is not an invention. Default tab: the highest grade at or below the player's rank that has offers, or else the player's own rank.

Unregistered holder: the counter tab renders no rail. The content area shows a centered registration card: 未加入公會, plus the `registration.register` descriptor's button, or its disabled reason when the descriptor is disabled.

### 3.4 Grade gem

`GradeGem.vue`: a rotated-square seal carrying the upright grade letter, in sizes `sm` (30px, list rows), the default (34px, rail), and `lg` (64px, detail). The material ladder runs iron (F) → bronze (E) → dark bronze (D) → silver (C) → gold (B) → bright gold (A) → seal-red with gold rim (S). The letter always carries the meaning; the material only reinforces it.

### 3.5 List column

A section heading (the tab's name in the gold display face, a fading rule, the row count), then the rows (`role="listbox"`, rows `role="option"`, arrow keys move the selection, Enter selects).

On the counter tab, the rank card (§3.7) sits above the heading.

Row layout: `category glyph | name + secondary line | grade gem`.
- The name renders in the serif face and is ellipsized when it overflows. Tracked rows end the name with a small seal-red flag.
- Secondary line: for an in-progress book row, a 4px gold progress bar plus `progress/target`. Every other row shows the issuer summary (公會委託, or the npc issuer's label) plus the deadline line when present.
- Selected row: a seal-red→gold-glow gradient, a seal-red border, and a 3px seal-red left marker. Dashed gold separators run between rows.
- No per-row state stamp: the tab already says the state.

The selection is remembered per tab key for the session. When the remembered row leaves the list, the selection falls back to the first row.

Empty list: a large faint glyph and one line: 這裡還沒有任務。 for the book, 目前沒有 X 級委託。 for an eligible grade, or X 級委託要等你的公會等級提升後才會開放。 for a locked grade.

### 3.6 Detail column

Top to bottom:

1. **Hero:** a seal-red notched ribbon with the category glyph and label (討伐委託, or e.g. 護衛 · 私人委託 for an npc issuer); the title in `--text-3xl` display face; `objective_line` in gold serif `--text-lg`; then `objective_note` (for example 計數變體：領群型、啄穗型) in small muted text. The `lg` grade gem sits top-right. Completed rows add a rotated double-ruled seal-red stamp 達成; failed rows add a grey 失敗 stamp.
2. **Progress** (in-progress book rows only): 階段 `stage_index + 1` / `stage_total` on the left and a large `stage_progress / objective_quantity` on the right. Targets of 12 or fewer render as slanted segment pips; larger targets render as a bar.
3. **Conditions pair** (two columns): 評價 (the `rationale` text; on board rows headed 接取條件 and led by 公會等級 X 級以上) and 期限 (the deadline line, or 無期限, plus one plain sentence). The 評價 cell is omitted when `rationale` is null on a book row.
4. **委託人 letter:** a gold left-ruled panel with the issuer label and the `flavor` prose in serif at line-height 1.9, over a faint guild-shield watermark. The fallback is 委託人沒有留下說明。 when `flavor` is null.
5. **報酬:** a row of item cells: coin glyph + copper, star glyph + merit (omitted when 0), and one cell per item (`display_name × quantity`). Under it, the settlement note: 回公會櫃檯領取 (counter) or 完成即結算 (auto). The whole section is omitted when `reward` is null (unresolvable issuance).

The detail fades in with a 6px slide on each selection change, using `--motion-reveal`. Reduced motion disables it.

### 3.7 Rank card

The current `GuildCounter.vue` rank block is extracted verbatim, markup, logic and styles, into `GuildRankCard.vue`, with its `exam_request` emit. Only its host changes: it now sits at the top of the counter list column. Its data-testids are kept. The extraction is verbatim with one exception: its two literal transition durations (`400ms` on the meter fill and `150ms` on the exam button) switch to `--motion-*` tokens. The existing `tests/motion_tokens.test.js` already rejects them on master.

### 3.8 Action bar

The bar is pinned to the bottom of the detail, with right-aligned buttons and a left-aligned reason line.

| Context | Content |
|---|---|
| Book, in progress | left: 放棄委託, a ghost button rendered only from a matched counter row whose `abandon` descriptor is enabled, with that descriptor's label. Right: a 追蹤／追蹤中 toggle (`aria-pressed`) from the row's `track` descriptor. |
| Abandon armed | the reason line in seal-red, 放棄後任務會判定失敗，且無法回復。, then 取消 and 確認放棄 (filled seal). Only 確認放棄 dispatches. |
| Book, completed, counter row with enabled `turnin` | primary seal-red button with the descriptor's label. |
| Book, completed, otherwise | reason line only: the matched descriptor's `disabled_reason.message`, else 報酬已領取 when `reward_claimed`, else 回到公會櫃檯即可交付並領取報酬 for counter settlement. |
| Book, failed | reason line 此委託已失敗，沒有報酬。 |
| Board | primary 接取委託 from the row's `accept` descriptor. When the descriptor is disabled, the button gets the dashed disabled shape and the reason line shows its `disabled_reason.message`. |

The merge rule stays the same as today's: counter actions come only from `services.guild.quests` rows matched by `quest_id`, mirrored exactly.

### 3.9 Glyphs

New 24×24 stroke glyphs are added to `components/dock-icons.js` beside the existing ones: `quest_book`, `guild_counter`, `quest_in_progress`, `quest_completed`, `quest_failed`, one per quest category (`cat_gather`, `cat_defeat`, `cat_escort`, `cat_explore`, `cat_emergency`), `track_flag`, `reward_copper`, `reward_merit`, `reward_item`, `deadline`, and `lock`. Each icon-only control carries a text `aria-label`. Each decorative glyph is `aria-hidden`.

## 4. Payload Changes

### 4.1 `quest_log` v1 → v2

Row fields removed: `detail` and `reward_line`. Row fields added:

| Field | Type | Source |
|---|---|---|
| `category` | `"gather" \| "defeat" \| "escort" \| "explore" \| "emergency"` | `definition.quest_type` (a stable wire key, never the zh label) |
| `grade` | rank key in `GUILD_RANK_REGISTRY` | `definition.rank` |
| `objective_note` | string or null, at most `MAX_OBJECTIVE_LINE_CODE_POINTS` | the variant clause of a species-hunt objective (see §4.3) |
| `rationale` | string or null | `definition.rating_rationale_zh`, verbatim |
| `flavor` | string or null | `definition.background_flavor_zh`, verbatim |
| `reward` | `{copper, merit, items: [{item_key, display_name, quantity}]}` or null | the resolved issuance's `QuestReward`; item names from `ITEM_REGISTRY` |
| `reward_claimed` | boolean | `quest_id in parse_reward_claims(owner)`; counter turn-in and auto settlement write the same ledger |

`objective_line` now excludes the variant clause. `settlement` and `reward` are null together or present together, the existing coherence rule moved from `reward_line` to `reward`. `stage_index` stays 0-based on the wire. The client renders `stage_index + 1`. The prose fields reuse the definition-registration bounds (`MAX_DEFINITION_PROSE_LENGTH`). The item list is capped at eight entries at the panel (`QUEST_LOG_MAX_REWARD_ITEMS`), guarded by a tagged data-contract test over every registered offer and issuance. The canonical-JSON envelope check is unchanged and must still pass at `QUEST_LOG_MAX_ROWS` rows with maximal prose; the presenter tests cover that case.

### 4.2 `services` v5 → v6 (guild board rows only)

Board row fields removed: `reward_summary`. Added: `category`, `objective_note`, `deadline_line` (string or null, from §4.3's offer-deadline seam), `rationale`, `flavor`, `reward` (the same object shape as §4.1, never null on a board row). The guild section gains `branch_label`, the local branch's `display_name_zh` and the issuer label of every board row, and `rank_ladder`, every guild rank key in ascending order, which the grade rail and the lock rule read. The board still never carries offers above the holder's rank. `objective_summary` keeps its name and drops the variant clause. The `quests` rows and the registration and rank objects are unchanged.

### 4.3 Describe seams (`world/quests/describe.py`)

- `describe_objective_parts(objective) -> tuple[str, str | None]` returns the line and the optional note. `describe_objective()` becomes `line + （note）`, so `guild show`, the objective tracker, and every other text consumer render byte-for-byte as today.
- `describe_offer_deadline(deadline_hours) -> str | None` returns 接取後 N 日 when the hours divide by 24, otherwise 接取後 N 小時, and None for no deadline.
- `describe_reward_parts(offer) -> dict` builds the structured reward. `describe_reward()` keeps its current string output for text consumers.
- `describe_quest_detail()` is unchanged, because `guild show` still uses it. Only the web payload stops carrying it.

### 4.4 Mirrors and contracts

The Python validators (`web/webclient/presentation/quest_log.py`, `services.py`), the JS mirrors (`web/static/webclient/js/elosern/protocol/panels/quest_log.js`, `services.js`), the constants (`QUEST_LOG_SCHEMA_VERSION`, the services schema version), the parity contracts (`tests/test_quest_log_parity_contract.py`, `tests/test_panel_schema_version_parity_contract.py`), the protocol fixtures (`web/static/webclient/js/tests/protocol_fixtures.js`), and the story fixtures (`stories/fixtures/quest_log_panels.js`, `services_panels.js`) move together in one change. Story fixtures must use realistic content: real catalog prose, the full guild branch name, item rewards, and a deadline. Fixtures shorter and cleaner than live data hid the current defects.

## 5. Components and Files

| Unit | Responsibility |
|---|---|
| `components/quest-drawer-model.js` | Pure functions: rows per state, counts, hot-badge flag, the board grouped by grade, the default grade, grade lock, the `quest_id` counter merge, and the normalized detail view model (book row and board row → one shape). Fully unit-tested. |
| `components/QuestDrawer.vue` | Frame, first-level tabs, tab memory, rail selection, and composition of the units below. Emits the existing intents (`quest_track`, `quest_abandon`, `quest_turnin`, `quest_register`, `quest_accept`, `exam_request`). |
| `components/IconTabs.vue` | Generic icon tablist, horizontal or vertical: roving tabindex, arrow keys, tooltip, badge, and locked/dim states. Used by the first-level tabs and both rails. |
| `components/QuestList.vue` | Heading plus listbox rows, and the empty states. |
| `components/QuestDetail.vue` | Hero, progress, conditions, letter, rewards, and the action bar (actions passed in as resolved descriptors). |
| `components/GradeGem.vue` | The grade seal (§3.4). |
| `components/GuildRankCard.vue` | The rank block, extracted unchanged (§3.7). |

`QuestLog.vue` and `GuildCounter.vue` are deleted, along with their stories. They are replaced by `stories/World/QuestDrawer.stories.js` (book per state, board, top rank, unregistered, counter unavailable, away from counter, abandon armed, empty grade, locked grade) and `stories/World/GuildRankCard.stories.js`, which carries over the existing rank-block variants. `component-manifest.json` and the showcase-coverage script are updated. The `.elosern-root .quest-log*` and `.guild-counter*` rules in `styles/app-shell.css` (lines 350–362) are removed.

## 6. Error and Absence Handling

- `quest_log` absent (not yet committed): the 任務簿 tab shows 尚未取得任務簿資料 in the list column, and the detail stays empty.
- `quest_log` unavailable: its `reason.message`, with `data-reason-code`.
- `services` unavailable, or no guild section: the counter tab is disabled with that reason (§3.2). The book still works, but no counter actions render.
- Null `reward` / `settlement`: the reward section is omitted, and no settlement note is invented.
- A remembered selection or tab that disappears after a panel update falls back as described in §3.2, §3.3, and §3.5. An armed abandon disarms when its row leaves or the selection changes.

## 7. Testing

- **Python:** presenter and validator tests for `quest_log` v2 and `services` v6 (field presence, null pairing, closed `category` and `grade` sets, prose bounds, envelope size at the row cap with maximal prose, `reward_claimed` for counter vs auto). `describe` tests prove that `describe_objective()` and `describe_reward()` output is byte-identical to before for every catalog definition.
- **JS protocol:** mirror tests for both validators, plus the parity contracts.
- **Vitest:** `quest-drawer-model.js` unit tests. Component tests for tab switching, keyboard navigation on both tablists and the listbox, the action-bar matrix in §3.8 (descriptor mirroring, no synthesized or enabled-when-disabled action, two-step abandon), the locked and empty grade states, and the unregistered card.
- **Visual:** Storybook stories in §5 at 1451×790 and 1920×1080, plus a live-client browser check with `agent-browser` against the running server (Storybook does not reproduce live data or every `.elosern-root` interaction). The check covers the four main screens, a long-prose row, tooltip placement, and the focus ring on every control.

## 8. Non-Goals

- No quest-location map in the detail (MHW's right-page map): no quest location payload exists yet.
- No monster portrait in the hero: monster art is not delivered to the client.
- No change to `guild show` text, the objective tracker, quest rules, rank eligibility, or the rank block's design.
- No grade-ladder page or per-rank thresholds beyond what the rank card already shows.
- No board category filter; category is shown per row only.

## 9. OpenSpec Changes and Batch Order

Implementation ships as five OpenSpec changes under `openspec/changes/`. Each one is sized for one engineer-day and keeps `master` deployable on its own. This document records the approved design; it changes no main capability spec by itself.

| # | Change | Delivers | Spec deltas | Size | Worker |
|---|---|---|---|---|---|
| 1 | `quest-log-structured-rows` | `quest_log` v2 (§4.1), the objective-parts and reward-parts seams (§4.3), the JS mirror and parity contracts, realistic quest-log fixtures, and an interim `QuestLog.vue` adaptation | MODIFIED/RENAMED `webclient-quest-log-panel`; MODIFIED `webclient-service-menus` | ~7h | Logic |
| 2 | `guild-board-structured-offers` | `services` v6 (§4.2) with `branch_label` and `rank_ladder`, the offer-deadline seam, the JS mirror, realistic services fixtures, and an interim `GuildCounter.vue` board adaptation | MODIFIED/ADDED `webclient-service-menus` | ~6h | Logic |
| 3 | `quest-drawer-ui-primitives` | `IconTabs`, `GradeGem`, the new glyphs (§3.9), and the `GuildRankCard` extraction (§3.7), each with Storybook stories and manifest entries | none (`skip_specs`) | ~6h | **Visual** |
| 4 | `quest-drawer-book-tab` | `QuestDrawer` shell, `quest-drawer-model.js`, `QuestList`, `QuestDetail`, the live quest book tab; deletes `QuestLog.vue`; the counter tab hosts the legacy counter | ADDED new capability `webclient-quest-drawer`; REMOVED four `webclient-service-menus` requirements | ~8h | **Visual** |
| 5 | `quest-drawer-guild-board-tab` | The grade-tabbed board, the rank card above the list, offer detail and accept, the registration card; deletes `GuildCounter.vue` and its skin rules | ADDED `webclient-quest-drawer`; REMOVED one `webclient-service-menus` requirement | ~7h | **Visual** |

**Worker:** *Logic* changes are payload, validator, and contract work with no visual judgment. *Visual* changes need a worker with visual ability that can read screenshots, drive `agent-browser`, and match the `Design/QuestDrawerRedesign` prototype pixel for pixel. Their tasks include side-by-side visual parity reviews.

### 9.1 Dependencies

- 2 depends on 1 (shared seams, reward shape, category keys).
- 4 depends on 1 and 3.
- 5 depends on 2, 3, and 4.
- 1 and 3 have no dependencies.

### 9.2 Apply batch order

```text
Batch 1 (parallel):  1 quest-log-structured-rows    3 quest-drawer-ui-primitives
Batch 2 (parallel):  2 guild-board-structured-offers 4 quest-drawer-book-tab
Batch 3:             5 quest-drawer-guild-board-tab
```

Start each batch only after every change in the previous batch has merged.

### 9.3 Archive order

Archive strictly 1 → 2 → 4 → 5. Change 3 has no deltas and can archive any time after it merges. Any other order fails `openspec archive`:

- Change 4 REMOVES a requirement that change 1 MODIFIES.
- Change 5 adds to the capability that change 4 creates.
- Change 5 REMOVES a requirement that change 2 adds.

### 9.4 Code conflicts

| Changes | Shared files | Handling |
|---|---|---|
| 1 ↔ 2 | `world/quests/describe.py`, protocol `constants.js`, protocol fixtures | Sequenced: 2 starts after 1 merges. |
| 2 ↔ 3 | `GuildCounter.vue` | Unordered within the plan. If 3 merges first, 2 edits only the board markup, because the rank block already lives in `GuildRankCard.vue`. |
| 2 ↔ 4 | `web/tests/browser/test_browser_services_quest_drawer.py` | Parallel. 2 bumps one injected services payload; 4 rewrites the journeys. Rebase whichever lands second. |
| 2 ↔ 5 | `test_browser_services_guild.py`, services browser seed, services story fixtures, `GuildCounter.vue` | Sequenced. |
| 3 ↔ 4 ↔ 5 | `component-manifest.json`, the showcase evidence key sets | Sequenced. Each change adds or removes its own titles following the `World/LettersPanel` precedent. |
| 4 ↔ 5 | `QuestDrawer.vue`, `quest-drawer-model.js`, drawer stories, `test_node_suite_evidence.py` | Sequenced. 5 extends what 4 builds. |

### 9.5 Notes

- Sizing risk: 4 is the tightest. Its visual parity review (task 5.2) is the only deferrable item, and any deferral is recorded in tasks.md.
- The prototype under `docs/design/quest-drawer-redesign/` stays as reference until 5 is archived. Whether to retire it, together with its Storybook glob, is left to the user.
