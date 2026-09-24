## Context

See proposal.md (Why). The current state, verified in code:

- `AppClient.vue` `#panel-left` renders, in order:
  - `StatusPanel`, when `panelAvailable('status') || panelAvailable('character')`. It composes `CharacterHead`, `VitalsTrack`, and `ConditionChips` under root `data-testid="status-panel"`.
  - `PartyStrip`, when `store.partyAvailable && mode !== 'creation'`.
  - `ArtPanel`, when `panelAvailable('art') && mode !== 'combat'`.
  - A `button.gallery-opener` (`data-testid="gallery-opener"`, `角色肖像圖庫`), when `panelAvailable('gallery')`, calling `openOverlayByName('gallery')`.
- `#panel-right` holds `LocalMap`, `ParticipantFrame`, and `TitleBallotMenu`. This change does not touch it.
- `CharacterHead` is the only consumer of `status.actor.full_title` / `status.actor.name` for display, and the only place in the HUD with a wallet.
  - `CharacterStatusDrawer` already shows `character.full_title`, the `magic_power` attribute (`use-status-drawer-character.js` `ATTRIBUTE_KEYS`), guild rank / merit, and disguise.
  - The inventory drawer shows the wallet in its subtitle (`use-drawers.js` `inventoryWalletSubtitle`) and its `金錢` row.
  - `character-identity.js` stays: `formatCopper` is imported by `InventoryPanel.vue`, `use-drawers.js`, and a story, and `portraitGlyph` is re-exported by `party-helpers.js`.
- `ArtPanel` is imported only by `AppClient.vue`, its story, and `tests/world/art_panel.test.js` (plus a `z_index_scale.test.js` row). The `art` panel's `portrait_catalog` is consumed independently by `PartyStrip`, `PartyDrawer`, `ParticipantFrame`, `DockMenu`, the interact-target avatars in `AppClient.vue`, and `NarrativeFeed`'s dialogue host avatar (all through `party-helpers.js` `portraitFor` or direct lookup).
- The quick-word chips have three consumers of `lib/quick_chips.js`:
  - `QuickWordChips.vue` (rendered by `CommandLine.vue`)
  - `CommandLine.vue` (`chipLetters(mode)` in the Tab candidate set)
  - `AppShell.vue` (`boundLetters(mode)` in `onWindowKeydown`)

  `lib/controls-reference.js` names both in the help overlay. The server pin is `commands/tests/test_localized/test_surface_and_quickbar.py::QuickbarLetterPinningTests`.
- `stores/elosern/view.js` derives `view.vitals = { hp, mp, sp, lowHp }` from the committed `status` panel through `components/vitals.js` (`gaugeRatio`, `isLowHp`).
- `AppShell.vue` keeps `HIDDEN_BY_MODE` and a `watch(() => props.mode)` that, in Vue's default pre-flush, calls `restoreDockFocus()` when `document.activeElement` is inside a surface the next mode hides.
- `VitalsTrack` keeps its trailing-bar ("ghost") memory in component state (`lastSeen`, `ghostInstant`), keyed on the committed revision and epoch. `ConditionChips` renders `<button>` chips (focusable) and nothing when the list is empty.
- `PartyStrip` always renders its island when mounted. With zero slots it draws `0 / 4` and four `party-strip__empty-slot` cells. Nothing else opens the party drawer: `store.openHudDrawer('party')` is called only from the strip's `@open-drawer`.
- The command line's utility cluster (`span.cmdutil` in `CommandLine.vue`) carries 技能系譜 (`command-line-lineage`), 圖鑑 (`command-line-lore`), 稱號冊 (`command-line-codex`), 設定, and 說明. Each emits `open-overlay` or `open-drawer` up through `AppShell` to `AppClient`'s `onOpenOverlay` / `onOpenDrawer`, which capture the opener element.

## Goals / Non-Goals

**Goals:**
- Delete `CharacterHead`, `ArtPanel`, and `QuickWordChips` (with `lib/quick_chips.js` and the bound-letter keydown branch), and remove every test, story, manifest entry, spec requirement, and help-text line that names them.
- Hide the vitals island at full health outside combat, following the §5.3 formula exactly.
- Render nothing for an empty party while keeping the party drawer reachable.
- Keep the gallery overlay reachable from a labelled control.

**Non-Goals:**
- Anchor geometry and the band/portrait anchors (C4a), the top bar and place card (C4b), the vitals/map anchors and the compact party avatars (C4c). The left anchor keeps its current CSS. It is simply emptier, and it may be completely empty at full health with no party.
- The vitals fade transition (C11). This change toggles `display` instantly.
- The server's single-letter aliases (`g`, `s`, `t`, `w`, `c`). They stay installed as typed shortcuts, and no command set changes.
- `TitleBallotMenu`, `ParticipantFrame`, `LocalMap`: untouched.
- The UMD art model and its "Contextual portrait focus" requirement, which the Node gate still exercises: untouched.

## Decisions

### D1. Vitals hide with `v-show` (display:none), not `v-if`
`StatusPanel` stays mounted while the `status` panel is available. `visible` toggles its root with `v-show`.

Reason: `VitalsTrack` draws the damage trail from the previously committed ratio held in component state. The common case of the new rule is "full health, then the first hit". With `v-if`, the island would mount on that hit with `lastSeen` empty, and the trailing bar would start at the new ratio. The first hit would show no damage gap, which breaks the existing "Damage leaves a visible trailing bar" contract. `v-show` keeps the state and still removes the island from rendering, the accessibility tree, and the tab order. That is the design's §4 rule ("hidden surfaces use `display:none`").

*Alternative:* a stage-root attribute (`data-elosern-vitals`) gated in `HudFrame` CSS, mirroring `data-elosern-mode`. Rejected: this rule is data-driven and belongs to one island, not to a stage mode. C4c moves the island into its own `vitals` anchor anyway, and the `v-show` binding moves with it unchanged.

### D2. The rule is a pure function in `components/vitals.js`, committed on the store's vitals slice
Add `isVitalsVisible({ mode, resources, conditions, lowHp })` next to `isLowHp`. It returns true when:
- `mode === "combat"`, or
- `lowHp`, or
- any of `hp` / `mp` / `sp` has a numeric `current` below a numeric `maximum`, or
- `Array.isArray(conditions)` and some entry's `severity` is `"warning"`, `"harmful"`, or `"critical"`.

A missing gauge or a non-numeric field never counts. A condition whose `severity` is `beneficial` or `informational`, or is missing or unknown, never counts. The vocabulary is `world/rules/status_display.py` `_SEVERITIES` (`beneficial`, `informational`, `warning`, `harmful`, `critical`), and `web/webclient/presentation/status.py` already ships `severity` on every `status.conditions` entry (`ConditionChips` reads it for its glyph), so no server change is needed. The severity filter only decides visibility: while the island is visible, `ConditionChips` renders every committed condition, whatever its severity.

Why severity, not "any condition": the requester asked for vitals when the character is "injured or in an abnormal state", not for passive buffs. `combat-modifier-table` surfaces `skill_owned` modifier rows as `status.conditions` entries (e.g. `defense_instinct_defense_bonus`, `severity: beneficial` in `world/rules/rulebook/status_display.yaml`), so a character with such a skill always carries a condition. Under an "any condition" rule the island would never hide for that character, which defeats §5.3. The coordinator recorded the severity rule in the series brief, and it is binding here. `rulebook/status_display.yaml` currently has 55 `beneficial`, 6 `warning`, 46 `harmful`, and 15 `critical` rows, and no `informational` row.

`view.js` adds `visible` to the available branch of the `vitals` slice and `visible: false` to the unavailable branch. `AppClient` passes `store.view.vitals.visible` to `StatusPanel` (`:visible`) and to `AppShell` (`:vitals-visible`). Dialogue follows exploration because only `combat` forces visibility. In creation mode the `hud-left` anchor is already hidden by `HIDDEN_BY_MODE` and the CSS matrix.

`StatusPanel` now mounts on `panelAvailable('status')` alone. Its only remaining children read `status`, and the `character` prop is deleted.

### D3. Focus rescue reuses the `HIDDEN_BY_MODE` path
`AppShell` gains a `vitalsVisible` prop and a second watcher with the same default pre-flush timing as the mode watcher. On a true-to-false edge, if `document.activeElement?.closest('[data-testid="status-panel"]')`, it calls `restoreDockFocus()`.

The only focusable elements inside the island are condition chips and the overflow control. Outside combat at full vitals, the island hides when the last `warning` / `harmful` / `critical` condition clears, even if `beneficial` chips remain, so a focused chip can be removed from the tab order. Without the rescue, that clear already drops focus onto `<body>` today. This change fixes that as a side effect.

### D4. Empty party: the component renders nothing, and the status drawer gains the only extra opener
`PartyStrip.vue` wraps its root in `v-if="safeSlots.length > 0"`, so the component itself honours "renders nothing" in stories and tests. The `AppClient` mount condition is unchanged. The strip keeps its `+ 邀請` padding for a party of one to three. Compact avatars are C4c's work.

Without the strip, an empty party would leave the 同伴 · 隊伍 drawer unreachable: its 空位 row, its invite control, and its follow rules. `CharacterStatusDrawer.vue` gains a `同伴 · 隊伍` button (`data-testid="character-status-drawer__open-party"`) beside the existing `技能書` (`open-skill`) button:
- it emits `open-party`
- `AppClient` maps that to `store.openHudDrawer('party')`
- it renders only when a new `partyAvailable` prop is true

That is the same one-labelled-control pattern the drawer already uses, and it keeps the party drawer within two actions of the top bar's 角色 entry.

*Alternative:* a top-navigation entry. Rejected: `NAVIGATION_ITEM_KEYS` is server-menu-driven (`character`, `quests`, `inventory`, `bag`), and the top bar is C4b's scope.

### D5. The gallery opener joins the command line's utility cluster
The cluster is already the home of every other overlay opener (lineage, codex, settings, help). The design's top bar (§5.4) is fixed at 角色 / 任務 / 背包 / 地圖 / 設定. The 角色 drawer was the other candidate, and it would have meant an overlay opened from inside a drawer: `openOverlay` closes the drawer first, which detaches the opener and sends the focus-trap restore to its fallback. The move:
- `CommandLine.vue` gains a `galleryAvailable` prop and a `button.cmdutil__btn` with `aria-label="角色肖像圖庫"` and `data-testid="gallery-opener"` (kept, so `tests/app_client_gallery.test.js` keeps its selector), emitting `onOpenOverlay('gallery')`.
- `AppShell` forwards the prop.
- `AppClient` binds `panelAvailable('gallery')`.
- The `.gallery-opener` CSS block in `AppClient.vue` is deleted.

C5 decides where the whole utility cluster lives once the line collapses. The gallery button moves with the rest of the cluster.

### D6. Quick-chip removal keeps the `/` claim and the Tab contract
In `AppShell.onWindowKeydown`, only the bound-letter tail goes: the `event.repeat` / `isEditable` guard, the letter normalisation, and `boundLetters`. The `/` default-suppression stays.

`CommandLine`:
- drops the `QuickWordChips` mount, `onChipInsert`, and `insertText` (its only callers are the chip click and `AppShell`'s letter branch; `defineExpose` keeps `focusField` only)
- drops `chipLetters` from the candidate list
- drops the `mode` prop: its only readers are the chip mount and `chipLetters(props.mode)`. The candidate-reset watch still keys on `candidateList`, so a mode switch that changes the exploration candidates still resets the cycle. `AppShell` drops `:mode` on `<CommandLine>`.
- deletes any CSS rule and comment that targets the chip cluster (`.qwc`, and the "chip cluster scrolls" constrained-width comment near the `.cmdline .hint` rule)

`controls-reference.js` loses its two chip rows, and its Tab row says "history and the room's exits and targets".

### D7. Spec strategy
Every changed requirement keeps its title, except in `webclient-input-narrative`. There, the echo requirement must drop the scenario "Preparing a command from a chip echoes nothing". `openspec validate` rejects a MODIFIED block that omits an existing scenario, so the requirement is REMOVED and re-ADDED as "A deliberate mutation echo appears exactly once at dispatch". The chip scenario is replaced by "Preparing a command in the field echoes nothing". The stale "quantity-form Enter" surface, already deleted by `retire-service-keyboard-frames`, is dropped at the same time. The four browser annotations re-anchor to the new ID.

In `webclient-contextual-hud`, "The map, settings, and help surfaces are reachable from the live client" is also MODIFIED by C2 (`webclient-full-map-fit-view`), whose map clause describes the fitted open, wheel / `+` / `-` zoom, 放大 / 縮小, drag-pan, 置中, and the 圖例 legend popover. This change's MODIFIED block is written on top of C2's text: it carries C2's map clause and C2's scenario bodies verbatim, and changes only the help paragraph (the quick-word-chip clause is removed and "It SHALL name no key binding or control the client does not implement" is added). Every scenario title is kept.

Archive order: C1 (`webclient-minimap-and-log-quick-fixes`) → C2 (`webclient-full-map-fit-view`) → C3 (this change). This change must be archived after C2, or archiving C2 second would overwrite the help edit with C2's chip wording. No other requirement this change touches is modified by C1 or C2: they otherwise modify only "The minimap island states only its own drawing convention", "A full-screen overlay is one focus-trapped surface…", "The full-log surface opens at its latest line", and `webclient-local-map` requirements, none of which this change edits. C4a/C4b/C4c and C5 must write their MODIFIED blocks on top of this change's texts for "Surface visibility…", "The HUD island stack…", "The command line is a permanently present bar…", "The party quickbar island…", and the two `webclient-desktop-shell` requirements, and must be archived after this change.

### D8. Traceability
Removed IDs and their annotations:
- `webclient-contextual-hud::the-character-head-card-renders-only-backed-identity` (`test_browser_shell_surfaces.py::test_character_head_card_renders_only_backed_identity`, deleted)
- `…::quick-word-chips-prepare-a-command-without-submitting-it` (two tests in `test_browser_input_narrative.py`, deleted)
- `…::bound-quickbar-letters-are-pinned-against-the-installed-player-cmdset` (`QuickbarLetterPinningTests`, deleted)

The new vitals ID is covered by:
- a new `test_node_suite_evidence.py` case running `tests/data/vitals_visibility.test.js`
- a new browser test in `test_browser_shell_surfaces.py`: full-health snapshot, then the island is hidden; below-max snapshot, then it is visible

## Risks / Trade-offs

- [Only `warning` / `harmful` / `critical` conditions force the island visible] This narrows the design doc's §5.3 wording ("any condition is active"). The requester asked for vitals when "injured or in an abnormal state", not for passive buffs, and a literal "any condition" rule would keep the island on permanently for any character with a passive `skill_owned` combat-modifier row (all `beneficial`). The coordinator's decision in the series brief makes the severity filter binding (see D2). → A `beneficial` or `informational` condition at full vitals outside combat is not shown until something else makes the island visible; its chip then renders with the rest. A condition code added later with a mislabelled severity would hide wrongly, but `status_display.py` fails closed on any severity outside `_SEVERITIES`, and the chip glyph already depends on the same field.
- [Browser tests that assert `status-panel` is visible] The seeded browser characters are at full health, so after this change `[data-testid="status-panel"]` exists but is `display:none` in exploration.
  - `test_browser_local_map_interaction.py::test_minimap_visible_and_keyboard_usable_at_both_viewports` asserts `is_visible()`.
  - `test_browser_shell_surfaces.py::test_populated_island_stack_fits_its_anchor_at_both_viewports` measures it.
  - → Both inject a below-max `status` (the helper `valid_status_panel` plus a lowered `hp.current`) before measuring. Tests that only read gauge text (`inner_text` works on a `display:none` node in Playwright) or wait for DOM presence (`test_browser_layout.py`) are unaffected. Task 6.x greps every `status-panel` browser selector and classifies it.
- [Shared requirement with C2] "The map, settings, and help surfaces are reachable from the live client" is modified by both C2 and this change. → This change's block is rebased on C2's text (D7), so archiving in the order C1 → C2 → C3 yields both edits. If C2's map clause changes before archive, this block must be re-synced to it.
- [Empty left anchor] At full health with no party, `hud-left` renders nothing. → Intended by the design. The anchor has no chrome of its own, and the browser anchor-intersection tests treat a missing box as non-intersecting (`intersect()` returns false when an element is absent or has no box). Task 6.x re-runs them.
- [Deleting `ArtPanel` removes the only NPC portrait full view] → Accepted. The design (§4) removes the strip outright. The art-panel acceptance requirement is restated without a per-portrait full-view control, and C10's `StageActor` shows the dialogue host at stage size.
