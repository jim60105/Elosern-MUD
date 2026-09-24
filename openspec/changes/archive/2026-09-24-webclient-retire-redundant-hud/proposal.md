## Why

The requester reviewed the live client at 1920×1080 (design `docs/superpowers/specs/2026-09-23-webclient-avg-stage-redesign-design.md` §1, §4, §5.2, §5.3) and found the left column full of surfaces that carry no meaning in the current context:

- HP / MP / stamina bars stay on screen while the player walks through a city at full health.
- The head card (`CharacterHead`: name, magic-power badge, guild rank, wallet) repeats the top bar's character switcher and the 角色 / 背包 drawers.
- An empty party still draws `同伴 0 / 4` and four `+ 邀請` cells.
- The `美術展示` strip (`ArtPanel`) shows an NPC face in the bottom-left corner.
- The command line carries quick-word chips (`QuickWordChips`) and single-letter key bindings (`l g s t w`, `c` in combat). Each one repeats an action-dock entry.

The design's rule is "show when meaningful, hide completely otherwise". This change applies that rule to the existing left column before the stage-shell rewrite (C4a `webclient-avg-stage-shell`, C4b `webclient-avg-place-card-top-bar`, C4c `webclient-avg-stage-hud-anchors`) moves surfaces into new anchors. The project is unreleased, so the retired components, their tests, stories, and spec requirements are deleted, not kept behind a flag.

## What Changes

- **BREAKING (internal)**: delete the head card.
  - Delete `web/webclient-app/components/CharacterHead.vue`, its story `stories/Data/CharacterHead.stories.js`, its Vitest `tests/data/character_head.test.js`, and its `.character-head` overrides in `styles/app-shell.css`.
  - `StatusPanel.vue` composes only `VitalsTrack` and `ConditionChips`, and drops its `character` prop.
  - Every head-card field stays reachable in a drawer. The full title, guild rank / merit, `magic_power`, and disguise are in the 角色 status drawer (`CharacterStatusDrawer`). The wallet is in the 背包 inventory drawer (header subtitle and `金錢` row). The name is in the top-bar switcher. `components/character-identity.js` stays, because `InventoryPanel`, `use-drawers.js`, and `party-helpers.js` import `formatCopper` / `portraitGlyph`; only its header comment changes.
- **BREAKING (internal)**: delete the left-column art strip.
  - Delete `components/ArtPanel.vue` (testid `art-panel`, title `美術展示`, per-portrait full view `art-panel__fullview`), its story `stories/World/ArtPanel.stories.js`, its Vitest `tests/world/art_panel.test.js`, its `z_index_scale.test.js` row, and the `.art-panel` rule in `styles/app-shell.css`.
  - The `art` panel's `portrait_catalog` is unchanged. It still feeds `PartyStrip`, `PartyDrawer`, `ParticipantFrame`, `DockMenu` target rows, the interact-target avatars in `AppClient.vue`, and the dialogue host avatar in `NarrativeFeed`.
  - The UMD art model `web/static/webclient/js/elosern/art_panel.js` and its Node test are untouched.
- **BREAKING (internal)**: delete the quick-word chips and their letter bindings.
  - Delete `components/QuickWordChips.vue`, `lib/quick_chips.js`, `stories/Core/QuickWordChips.stories.js`, and `tests/quick_word_chips.test.js`.
  - `CommandLine.vue` stops mounting the chips, and its Tab-completion candidate set drops the chip letters (`chipLetters`).
  - `AppShell.vue` deletes the bound-letter branch of `onWindowKeydown` (`boundLetters`). `/` keeps its default-suppression claim.
  - `lib/controls-reference.js` drops the `Quick-word chips` and `l g s t w / s c` rows, and its Tab row stops naming chip badge letters.
  - `commands/tests/test_localized/test_surface_and_quickbar.py` deletes `QuickbarLetterPinningTests`. The server's single-letter aliases stay installed as typed shortcuts; nothing else pins them.
- **Vitals auto-hide.**
  - The store's derived `view.vitals` slice gains `visible`, from a new pure `isVitalsVisible()` in `components/vitals.js`. It is true when the committed mode is `combat`, `lowHp` is true, any committed vital's `current` is below its `maximum`, or `status.conditions` carries a condition whose `severity` is `warning`, `harmful`, or `critical` (vocabulary: `world/rules/status_display.py` `_SEVERITIES`; the status presenter already ships `severity`). `beneficial` and `informational` conditions, including passive `skill_owned` combat-modifier rows, never force the island visible; the requester asked for vitals when "injured or in an abnormal state", not for passive buffs. While the island is visible, its condition chips render every condition, whatever its severity.
  - `StatusPanel` stays mounted and is hidden with `v-show` (`display:none`) while `visible` is false, so `VitalsTrack` keeps its trailing-bar memory for the first hit taken at full health.
  - `AppShell` gains a `vitalsVisible` prop. A pre-flush watcher moves focus to `#action-dock` through the existing `restoreDockFocus` path before the panel hides, following the `HIDDEN_BY_MODE` pattern.
  - `StatusPanel` now mounts on `status` availability alone.
- **Empty party renders nothing.** `PartyStrip.vue` renders no root element when the committed party has no slots. The 同伴 · 隊伍 drawer stays reachable at every party size through a new labelled `同伴 · 隊伍` control in the character status drawer (`data-testid="character-status-drawer__open-party"`), which follows the existing `open-skill` pattern.
- **Gallery opener re-homed.**
  - The left-column `gallery-opener` button moves into the command line's overlay utility cluster, beside 技能系譜 / 圖鑑 / 稱號冊 / 設定 / 說明.
  - It keeps `data-testid="gallery-opener"` and the label `角色肖像圖庫`, and is gated by a new `galleryAvailable` prop (AppClient → AppShell → CommandLine).
  - `openOverlayByName('gallery')` is unchanged.
- `TitleBallotMenu` is untouched. It lives in `#panel-right`, which this change does not edit.
- Manifest governance: `web/webclient-app/component-manifest.json` drops `Core/QuickWordChips`, `Data/CharacterHead`, and `World/ArtPanel`. The showcase spec names the AVG stage series as a governed redesign wave that may add and delete components in lockstep with the manifest and stories.
- Spec deltas across `webclient-contextual-hud`, `webclient-component-showcase`, `webclient-art-panel`, `webclient-input-narrative`, and `webclient-desktop-shell` (listed below).
- No OOB schema, presenter, server action, persistence, or anchor-geometry change.

Out of scope:
- The band and portrait anchors are owned by `webclient-avg-stage-shell` (C4a); the 48px top bar, removing the `探索` tab, and the `place` anchor by `webclient-avg-place-card-top-bar` (C4b); the `vitals` / `map` anchors and the compact party avatars by `webclient-avg-stage-hud-anchors` (C4c). The left column simply gets emptier here.
- Collapsing the command line (and deciding where its utility cluster, including the re-homed gallery opener, lives when collapsed) is owned by `webclient-collapsible-command-line` (C5).
- The vitals fade-in / fade-out transition is owned by `webclient-motion-layer` (C11). Here the island appears and disappears instantly.
- Minimap and full-log fixes are owned by C1 and C2. This change touches none of their files. It shares one requirement with C2 ("The map, settings, and help surfaces are reachable from the live client"), and its MODIFIED block is written on top of C2's text.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `webclient-contextual-hud`:
  - MODIFIED "Surface visibility is gated by the committed game mode": the matrix's island rows state their own data rules (vitals rule, non-empty party). Focus rescue also covers a data-driven hide.
  - MODIFIED "The HUD island stack renders as bounded floating islands, not column cards": the left anchor carries vitals, then conditions, then party. There is no head card.
  - ADDED "The vitals island is shown only in combat or while a vital or a condition needs attention".
  - REMOVED "The character head card renders only backed identity".
  - MODIFIED "The command line is a permanently present bar in the stage's command-line anchor": no chips, and the utility cluster includes the gallery opener.
  - REMOVED "Quick-word chips prepare a command without submitting it".
  - MODIFIED "The command line advertises only affordances this client implements": the Tab candidates lose the chip letters.
  - MODIFIED "The map, settings, and help surfaces are reachable from the live client": the help reference names no chips. The block is rebased on C2's version, so it keeps C2's fit / zoom / pan / 置中 / legend-popover map clause.
  - MODIFIED "The party quickbar island presents the committed party only": an empty party renders nothing, and the character-status drawer opens the party drawer.
  - REMOVED "Bound quickbar letters are pinned against the installed player cmdset".
- `webclient-component-showcase`:
  - MODIFIED "Every required UI component is a Vue SFC with a documented Storybook story"
  - MODIFIED "The status, character, and skill surfaces present truthful, non-color-only state"
  - MODIFIED "The map, art, and services surfaces render OOB-backed data truthfully"
  - MODIFIED "The frozen component set grows only through a governed redesign wave": the AVG stage series is a governed wave that may add and delete components.
- `webclient-art-panel`:
  - MODIFIED "Art panel browser acceptance is keyboard-first, accessible, and desktop-bounded": no per-portrait full-view control.
  - MODIFIED "The browser maps each framed portrait's carried face rectangle to a centered cover crop through one shared pure function": no 美術展示 browser.
- `webclient-input-narrative`: REMOVED "Every deliberate mutation echo appears exactly once at dispatch" and ADDED "A deliberate mutation echo appears exactly once at dispatch". The requirement is the same without the chip sentence and the chip scenario. `openspec validate` rejects a MODIFIED block that drops a scenario, so the requirement is re-titled.
- `webclient-desktop-shell`:
  - MODIFIED "Required desktop surfaces remain visible and usable": the island stack is present when its own rules render it.
  - MODIFIED "The command drawer preserves ordinary text control": the chip entrance path is removed.

## Impact

- Deleted:
  - `web/webclient-app/components/CharacterHead.vue`, `ArtPanel.vue`, `QuickWordChips.vue`
  - `web/webclient-app/lib/quick_chips.js`
  - Stories: `Data/CharacterHead`, `World/ArtPanel`, `Core/QuickWordChips`
  - Vitest: `tests/data/character_head.test.js`, `tests/world/art_panel.test.js`, `tests/quick_word_chips.test.js`
- Edited components and client code:
  - `web/webclient-app/AppClient.vue`
  - `components/AppShell.vue`, `CommandLine.vue`, `StatusPanel.vue`, `PartyStrip.vue`, `CharacterStatusDrawer.vue`, `HelpOverlay.vue` (comment), `vitals.js`, `character-identity.js` (comment)
  - `lib/controls-reference.js`, `stores/elosern/view.js`, `styles/app-shell.css`, `component-manifest.json`
- Edited stories: `Data/StatusPanel`, `Overlays/PartyStrip`, `Core/CommandLine`, `Data/CharacterStatusDrawer`
- Vitest:
  - edited: `tests/data/status_panel.test.js`, `tests/data/party_strip.test.js`, `tests/command_line.test.js`, `tests/app_client_drawers.test.js`, `tests/app_client_gallery.test.js`, `tests/z_index_scale.test.js`, `tests/overlays/deferred_surfaces_absent.test.js`, `tests/data/character_status_drawer.test.js`
  - new: `tests/data/vitals_visibility.test.js`
- Python evidence and lint lists:
  - `web/webclient/tests/test_vue_showcase_{action,data,world,overlays}_evidence.py`
  - `web/webclient/tests/test_node_suite_evidence.py`: a new vitals-visibility suite
  - `commands/tests/test_localized/test_surface_and_quickbar.py`
  - `tools/test_data_freeze.json`, `tools/test_data_lint_seed.json`
- Browser tests:
  - `web/tests/browser/test_browser_shell_surfaces.py`, `test_browser_input_narrative.py`, `test_vue_foundation.py`, `test_browser_art.py`, `test_browser_reconnect.py`, `test_browser_layout.py`, `test_browser_local_map_interaction.py`, `test_browser_inventory_actions.py` (annotation only), `seed/art_fixture.py` (comments)
  - `.github/browser-shards.json`
- Spec traceability:
  - three requirement IDs are removed, together with their annotations
  - `webclient-input-narrative::every-deliberate-mutation-echo-appears-exactly-once-at-dispatch` is re-anchored to `…::a-deliberate-mutation-echo-appears-exactly-once-at-dispatch` in four browser tests
  - one new ID (the vitals requirement) is covered by the new node-suite evidence test and a browser test
- Dependencies:
  - Archive order C1 → C2 → C3. No file overlaps with C1 / C2. The only requirement overlap is "The map, settings, and help surfaces are reachable from the live client", which C2 also modifies; this change's block builds on C2's text, so it must be archived after C2.
  - C4a (`webclient-avg-stage-shell`), then C4b and C4c, build on this change's `webclient-contextual-hud` and `webclient-desktop-shell` texts and must be archived after it. C5 builds on this change's command-line requirement texts.
