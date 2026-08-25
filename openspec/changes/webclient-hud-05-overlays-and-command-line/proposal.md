## Why

This is change **H5** of the WebClient Contextual HUD Redesign, governed by
`docs/superpowers/specs/2026-08-25-webclient-hud-redesign-roadmap-design.md` (depends on: **H1**, which
landed and archived the stage, its named anchors and the mode matrix; **H3**, which owns the dock's
frames, badges and keyboard geometry; and — see below — **H2**, which deferred the minimap's full-map
control to this wave).

The roadmap's gap table (§2.2) names two rows H5 owns, and they are the last two surfaces still shaped
by `2026-08-02-webclient-ui-design.md` §5.1 rather than by the design draft:

- **Command line.** The draft's is an always-visible 46px bar: a `›` prompt, the field, quick-word
  chips, and the history hints. The shipped client has a collapsed `指令輸入（/）` entry button, and the
  input field *does not exist in the DOM* until the player opens it. H1 re-homed that button into the
  stage's `command-line` anchor unchanged and recorded (task 2.7) that H5 upgrades the chrome.
- **Overlays.** `MapOverlay.vue`, `SettingsOverlay.vue` and `HelpOverlay.vue` are complete, unit-tested,
  Storybook-covered and listed in `component-manifest.json` — **and imported by nothing**. `grep -rn
  "MapOverlay\|SettingsOverlay\|HelpOverlay" web/webclient-app/*.vue` returns no hit; `AppClient.vue`
  mounts `CreationOverlay` (mode-driven) and H1's `FullLogOverlay` and nothing else. Three built
  surfaces have shipped to production behind zero triggers for four waves. The `--prose-scale`
  A−/A/A+ control the roadmap lists as an H5 deliverable is inside the second of them, which is why it
  has never run: `--prose-scale` is not even defined in `styles/tokens.css` today.

Wiring the settings overlay is also the moment a latent contract violation would fire.
`SettingsOverlay.vue:74` emits `options.type_scale`; `web/webclient/actions/registry.py:350` shows
`options.dismiss` is the **only** allowlisted `options.*` action. That dispatch would be rejected by
the allowlist the first time the overlay is mounted. It has never fired only because the overlay has
never been mounted. Widening the allowlist is a server change the roadmap forbids to every wave
(§3 Non-Goals), so H5 resolves it the other way: those settings are client-local presentation state,
and the spec clause that promises otherwise is corrected in the same change.

**Dependency amendment.** H2's `webclient-local-map` delta deliberately withholds the minimap's
full-map affordance — *"a full-map affordance SHALL exist only once the full-map surface it opens is
reachable"* — because H2 could not mount the surface. H5 mounts it and adds that control, which means
H5 edits `LocalMap.vue`, a file roadmap §7 assigns to H2. Per roadmap §9 that is a **forced serialize,
not a merge**: H5 amends the roadmap's H5 "Depends on" cell to `H1, H2, H3` rather than diverging from
the ownership table silently.

## What Changes

- **The command drawer becomes a persistent command line.** `CommandDrawer.vue` is rewritten as
  `CommandLine.vue`: a bar filling H1's `command-line` anchor with a `›` prompt chevron, the
  permanently visible field, a hint cluster, and up/down history controls. The entry button, its
  `aria-expanded` state and the whole open/closed concept are **removed**. `#inputfield` does not move.
- **`/` focuses instead of toggling.** With no closed state there is nothing to toggle: `/` pressed
  outside an editable moves focus into the field and does not insert a literal `/`; `/` pressed inside
  any editable — the command field included — stays ordinary text, so `whisper /ooc` is still typeable.
  Escape from the focused field returns focus to `#action-dock` without sending, exactly as before.
- **Mode-contextual quick-word chips** sit to the left of the field: buttons that write a verb into the
  field and focus it, never submitting. Their labels are the literal commands they insert, drawn from
  the **installed command set** — the draft's `go` and `ask` chips are dropped because this game has no
  such commands (movement is by exit name through the dock's 移動 frame; NPC keywords are `交談`).
- **One shared full-overlay surface.** A new `OverlayHost.vue` generalises the focus-trap / Escape /
  focus-restore pattern H1 hard-coded in `FullLogOverlay.vue` and H4 extracted into
  `components/focus-trap.js`, and adds the contract the wave needs: **at most one overlay open at a
  time**, registration into H1's existing open-surface set so the stage recession applies without a
  second mechanism, and focus returned to the trigger on every close path.
- **The three dead overlays get real triggers.** The minimap island gains its full-map control (H2's
  precondition now satisfied); the command line's utility strip carries 設定 and 說明 controls. The map
  overlay re-renders its available/unavailable branch on every `local_map` replacement — a requirement
  `webclient-component-showcase` has carried since B5 and that becomes observable for the first time
  here.
- **The settings surface tells the truth.** Prose scale becomes the draft's A−/A/A+ segmented control at
  `[0.92, 1, 1.12]`, replacing the inert 90/100/110/125% select; the invented font-family select is
  removed; nothing dispatches a `ui_action`; every setting is applied to the document immediately and
  persisted through the versioned presentation-only browser store's harmless-display-preference lane —
  `fontScale` and `text2html` already exist there and have been written by nothing since D1.
- **`--prose-scale` is added to `styles/tokens.css`** and applied **only** to narrative and dialogue
  prose sizes, never to general UI text.
- **BREAKING (test-facing only):** `data-testid="command-drawer"` and its `-entry` / `-input` /
  `-prompt` / `-send` children retire to `command-line`-prefixed hooks, and the entry-button and
  `aria-expanded` assertions are deleted. `#inputfield`, `#action-dock`, `#elosern-action-live`,
  `#elosern-offline-overlay`, `#narrative-unread`, the `action-*` / `target-*` item keys and the
  persisted layout component id `command-drawer` are all unchanged. This change re-maps every
  assertion it breaks.

## Capabilities

### New Capabilities

None. H1 created and archived `webclient-contextual-hud`; H5 adds requirements to it.

### Modified Capabilities

- `webclient-contextual-hud` (**ADDED** requirements only; none of H1's five landed requirements and
  none of H2's, H3's or H4's not-yet-archived ADDED requirements is modified): the persistent command
  line and its anchor; the mode-contextual quick-word chips; the shared single-open full-overlay
  contract; the map/settings/help triggers and their mode gating; and the client-local narrative prose
  scale. H1's mode matrix already places the command line (visible in exploration and combat, hidden in
  creation) and H1's stage-recession requirement already covers the dim behind an open overlay — H5
  **satisfies** both and restates neither.
- `webclient-desktop-shell`: three `MODIFIED` requirements.
  - *The command drawer preserves ordinary text control* — untouched by H1–H4, so copied from the main
    spec and re-expressed for a permanently present field. Every behaviour that is not chrome is
    preserved: `#inputfield`, the single send implementation, Enter sends exactly one command,
    Shift+Enter newlines, the field clears and keeps focus after an ordinary send, ArrowUp/ArrowDown
    walk the history with the draft preserved, a rejected borrowed send keeps the typed speech while
    mutations are locked, Escape and a completed borrowed send both return focus to `#action-dock`, and
    the borrowed-dialogue release rules.
  - *Keyboard routing is menu-first and submission-safe* — **H3 also modifies this requirement and lands
    before H5, so H5's copy is based on H3's edited version**
    (`openspec/changes/webclient-hud-03-action-dock/specs/webclient-desktop-shell/spec.md`), not on the
    main spec. Only the `/` clause and its scenario change.
  - *Required desktop surfaces remain visible and usable* — **H3 and H4 both modify this requirement and
    both land before H5, so H5's copy is based on H4's version**
    (`openspec/changes/webclient-hud-04-reference-drawers/specs/webclient-desktop-shell/spec.md`, which
    was itself based on H3's). Only the command-drawer clauses become command-line clauses.
- `webclient-component-showcase`: one `MODIFIED` requirement — *The full overlays are complete, the
  deferred surfaces are absent, and the manifest is frozen*. **H4 also modifies this requirement and
  lands before H5, so H5's copy is based on H4's version** (which dropped the inventory-bag deferral).
  The `SHALL emit options.*` clause becomes client-local presentation state with the allowlist fact
  stated; the overlays must be reachable from the live client, not only from the showcase. H1's
  frozen-set growth rule is obeyed, not duplicated.
- `webclient-input-narrative`: one `MODIFIED` requirement — *Every deliberate mutation echo appears
  exactly once at dispatch*. Its borrowed-dialogue clauses pin the drawer's open/closed state ("the
  drawer closes", "the drawer SHALL stay open"); they are re-expressed as focus outcomes. The echo
  contract itself — exactly one line, at dispatch, never on retry or replay, never entering the markup
  pipeline — is unchanged.
- `webclient-pointer-activation`: one `MODIFIED` requirement — *Keyboard input is dispatched through the
  WebClient plugin contract*. "claimed … when the open command drawer owns the key" becomes "when the
  focused command field owns the key". Untouched by H1–H4 (H3 modifies the other two requirements in
  this capability), so copied from the main spec.
- `webclient-browser-verification`: one `MODIFIED` requirement — *Browser acceptance covers foundation
  recovery and layout behavior*. "drawer open, send, and cancel behavior" becomes the command line's
  focus/send/cancel behaviour, and the full-overlay journey is added to the enumerated coverage.
  Untouched by H1–H4, so copied from the main spec.
- `webclient-local-map`: **no delta.** H2's requirement is conditional — the full-map affordance exists
  *once the surface it opens is reachable* — and H5 satisfies that precondition rather than contradicting
  it. The positive obligation (the island's control opens the map overlay) is added under
  `webclient-contextual-hud`.
- `webclient-options-surface`: **no delta.** It owns the dock's *suggestions* section and `options.dismiss`
  — H3 already re-expressed it for router rows. H5's settings surface is a different surface that
  dispatches nothing, so nothing in that capability changes.
- `webclient-character-creation-ui`: **no delta.** `CreationOverlay` is mode-driven, not user-opened, and
  is deliberately outside the single-open overlay stack (design D7), so its mount, its adult gate and
  its `creation.*` dispatches are untouched.

## Impact

- **New:** `web/webclient-app/components/CommandLine.vue` (replacing `CommandDrawer.vue`),
  `QuickWordChips.vue`, `OverlayHost.vue`, `lib/controls-reference.js` (the client's own key/命令
  reference, the single source for the help overlay's control section), their Storybook stories with
  deterministic offline args and their Vitest suites. `component-manifest.json` gains `Core/QuickWordChips`
  and `Overlays/OverlayHost` and renames `Core/CommandDrawer` → `Core/CommandLine`; the frozen count in
  `tests/overlays/deferred_surfaces_absent.test.js` is raised by exactly two from whatever count H2/H3/H4
  leave — never a hard-coded number.
- **Modified:** `components/AppShell.vue` (the `/` key claim, the Escape ladder, the drawer open/close
  API becomes a focus API), `AppClient.vue` (mount the three overlays through `OverlayHost`, register
  them into the open-surface set, wire the triggers), `components/LocalMap.vue` (the full-map control —
  **the forced serialize behind H2**), `components/SettingsOverlay.vue` (A−/A/A+ prose scale, font-family
  select removed, no `ui_action` dispatch, persistence through the layout store),
  `components/HelpOverlay.vue` (the control-reference section), `components/MapOverlay.vue` (hosted in
  `OverlayHost`; no zoom/pan hint), `stores/elosern.js` (the `hudOverlay` slice beside H4's `hudDrawer`,
  and the presentation-preference slice), `styles/tokens.css` (adds `--prose-scale`),
  `web/static/webclient/js/elosern/layout_store.js` (**additive only**: `reducedMotion` and `colorblind`
  join the existing `PREFERENCE_TYPES`; no layout-version bump, because an existing v1 wrapper without
  the keys already normalizes cleanly).
- **Re-mapped browser assertions** (`grep -rn '#inputfield\|command-drawer\|drawer-entry\|aria-expanded'
  web/tests/browser/`): `test_browser_shell.py` (12 `command-drawer`, 5 `.drawer-entry`, 1
  `aria-expanded`, 12 `#inputfield`), `test_browser_input_narrative.py` (18, 3, 2, 10),
  `test_browser_exploration.py` (2 `command-drawer`, 6 `#inputfield`), `test_vue_foundation.py` (5
  `command-drawer` plus the `-entry` / `-input` hooks and the required-testid list at :68-69),
  `test_browser_actions.py` (3 `#inputfield`), `test_browser_wait_helper.py` (3 `command-drawer` in the
  bounded-wait fixtures), `test_browser_layout.py` (the required-surface name at :34 and its selector at
  :268), `browser_helpers.py` (the required-selector list at :35), and `test_browser_art.py` (a docstring
  at :386). `#inputfield` is asserted **unchanged** in all of them.
- **Re-mapped unit assertions:** `tests/command_drawer.test.js` → `tests/command_line.test.js`,
  `tests/preserved_contract.test.js`, `tests/app.test.js`, `tests/bridge/app_shell_bridge.test.js`,
  `tests/bridge/bridge.test.js`, `tests/overlays/settings_overlay.test.js` (the `options.*` emit cases
  become persistence + token-application cases), `tests/overlays/{map,help}_overlay.test.js`,
  `stories/Core/CommandDrawer.stories.js` → `CommandLine.stories.js`, `stories/Core/AppShell.stories.js`.
- **Preserved / untouched:** the server, all eight presenters, the action allowlist (`options.dismiss`
  stays the sole `options.*` action), the OOB envelope, `transport.js`, `bridge.js`, the KeyboardRouter's
  frame/geometry semantics, `narrative_markup.js`'s allowlist grammar, `#inputfield`, `#action-dock`,
  `#elosern-action-live`, `#elosern-offline-overlay`, `#narrative-unread`, the `action-*` / `target-*`
  item keys, the persisted layout component id `command-drawer`, and the dependency-free text fallback.
- **Wave boundaries:** H5 does not edit `ActionDock.vue`, `DockMenu.vue`, `DockMenuItem.vue`,
  `DockTabBar.vue` or `DockBreadcrumb.vue` (H3), the drawer chrome or `focus-trap.js`'s trap semantics
  (H4 — H5 consumes it), `StatusPanel.vue` or the island components (H2), or `HudFrame.vue`'s anchor
  geometry (H1, archived; the `command-line` anchor is already 46px). The single cross-wave edit is
  `LocalMap.vue`, declared above.
- **Not built (no backing read model, roadmap §2.4):** the draft's 分類 → 條目 → 子主題 game-help browser
  (the `help` command's output reaches the client only as narrative text; no OOB panel carries it — the
  help overlay therefore renders the client's own control reference and the game's help stays reachable
  by typing `help` into the field), the draft's audio-volume rows (no audio subsystem exists), the
  draft's `HUD 縮放` slider and 重映射 control, and map zoom/pan. Each is named in the extended
  `tests/overlays/deferred_surfaces_absent.test.js` with what it waits on.
