# Proposal: Align shell, theme, and navigation specs with the shipped gold redesign

## Why

The `feat/webclient-obsidian-gold` branch shipped three shell-level behavior
changes that the master main specs never recorded, and one of them is a live
code defect:

1. **Gold accent wave.** The action dock's open-tab fill, the focused-row fill,
   and the whole navigation accent moved from seal-red to the muted-gold ramp.
   `webclient-desktop-shell` still pins "the open entry marked by a seal-red
   fill", "a seal-red fill plus a leading glyph", and a palette sentence with
   "a deep seal-red accent"; `webclient-vue-application` still pins "its single
   seal-red accent". Seal-red remains real in the shipped client, but only in
   its semantic roles (decisive/danger buttons, selection, the narrative `sys`
   marker and error lines, the offline title, the map here-marker). The specs
   describe a one-accent palette the client no longer has.
2. **Top navigation bar.** The branch added `Core/DesktopNavigation` (a new
   manifest component with a Storybook story) as a persistent header bar that
   carries 探索/戰鬥、角色狀態、任務、背包、地圖、設定. The keyboard root's
   `character`/`quests`/`inventory` items are filtered out of the dock's root
   projection so they are not invisible duplicate stops. No main spec describes
   the bar; `webclient-contextual-hud` still says the reference surfaces are
   "reached from the dock" and `webclient-desktop-shell` still enumerates the
   unfiltered G2 keyboard root.
3. **Undefined token (code defect).** `--gold-600` is consumed by
   `CharacterSwitcher.vue` (with no fallback — the button background is
   silently dead today), `RestForm.vue`, and `app-shell.css`, but
   `styles/tokens.css` only defines `--gold-400`/`--gold-500`/`--gold-glow`.
   This change defines the token.

All behavior is already shipped and green; this change aligns the specs and
fixes the token. The exploration-menu and waiting/practice alignment lives in
`align-webclient-waiting-practice-specs`, which this change **stacks on** for
the shared `The exploration dock is keyboard-first and re-homes the service
submenus` requirement: archive that change first and rebase this delta on the
synced result.

## What changes

- `webclient-desktop-shell`:
  - MODIFIED `Required desktop surfaces remain visible and usable` — gold fill
    wording, the top navigation bar joins the required-surface list, reference
    reachability counts from the bar or the dock, one added scenario.
  - MODIFIED `Theme and controls remain accessible` — the palette sentence
    names the gold navigation/focus accent and the semantic seal-red roles; the
    seal-red-only meaning-alone scenario covers both accents.
  - MODIFIED `Keyboard routing is menu-first and submission-safe` — the G2
    keyboard root drops the navigation-projected entries (`character`,
    `quests`, `inventory`, `bag`) and keeps the parent root's column count.
- `webclient-vue-application`: MODIFIED `The design system carries over from
  the design draft and stays offline` — "single seal-red accent" becomes the
  two-family accent statement (sync additionally refreshes the capability
  purpose sentence).
- `webclient-contextual-hud`: RENAMED + MODIFIED
  `The reference surfaces have no permanently visible home and are reached from
  the dock` → `... and are reached from the top navigation or the dock`; the
  opener sentence and the reachability scenario follow the shipped openers.
- `webclient-exploration-menu`: MODIFIED `The exploration dock is
  keyboard-first and re-homes the service submenus` (stacked on change 1) —
  the tab/keyboard root projection omits the navigation-presented entries.
- Code fix: define `--gold-600` in `styles/tokens.css` and correct the stale
  "single seal-red accent" comments in `tokens.css`.

## Out of scope

- Dock pane geometry (height clamps, interaction/dialogue/suggestions panes) —
  `align-webclient-dock-workspace-specs`.
- Gallery face-rect consumption, ReferenceArtwork lockstep —
  `align-gallery-art-consumption-specs`.
- Waiting/practice behavior — already shipped, spec'd in change 1.
- The seal-red contrast contract test (`ui_contract.test.js`) keeps its rule;
  the deep seal text allowlist is unchanged.
