## Why

A visual comparison of the shipped WebClient against `docs/design/elosern-redesign/index.html` (the
binding visual reference per `docs/superpowers/specs/2026-08-25-webclient-hud-redesign-roadmap-design.md`
§4) found two concrete defects in the action dock, confirmed both by reading the source and by driving
the live client (`podman compose`, `http://localhost:4001/webclient/`) with a browser:

1. **The dock's shortcut legend renders twice, and the shared copy is stale.** `ActionDock.vue`'s
   `.action-dock__description` (`data-testid="action-dock-description"`) and `DockTabBar.vue`'s
   `.dock-tab-bar__hint` both hardcode the exact same literal string —
   `"方向鍵選擇・Enter 確認・Esc 返回・/ 開啟指令"` — so the phrase is visibly printed twice: once on
   its own line above the tab row, once again pinned to the tab row's trailing edge. A DOM query against
   the running client confirms both elements return that identical string. The two elements' own code
   comments show this was never the intent: `DockTabBar.vue:140-142` says *"The `action-dock-description`
   hook is carried by ActionDock ... so the hint keeps the class only (no duplicate testid)"* — i.e. one
   element was meant to carry the visible legend and the other only the Node-contract test hook, but no
   visually-hidden styling was ever applied to the latter, so both render visibly.

   The shared text is also stale: `/ 開啟指令` ("press `/` to open the command line") describes the
   pre-H5 collapsed command drawer. Since `webclient-hud-05-overlays-and-command-line` landed, the
   command line is a permanently present, always-focusable bar with no open/closed state at all
   (`webclient-contextual-hud`'s "The command line is a permanently present bar" requirement); `/` now
   only moves focus into it (`web/webclient-app/stores/elosern.js:577-582`,
   `web/static/webclient/js/elosern/keyboard_router.js:272-275`). The capability's own sibling
   requirement, "The command line advertises only affordances this client implements," already forbids
   exactly this failure mode for the command line's own hint cluster; the dock's shortcut legend has no
   equivalent guarantee today, which is how the stale phrase survived six HUD-redesign waves.

2. **The dock's tab and pane glyphs are ad hoc shapes that do not read as their concept.** `dock-icons.js`
   assembles a full custom `GLYPHS` path table (`move`, `look`, `interact`, `suggestions`, `attack`,
   `skills`, `items`, `defend`, `flee`, `forfeit`, ...) that was never checked against the redesign's own
   icon language, even though `docs/design/elosern-redesign/index.html` ships the exact, already-approved
   `d` path data for every one of those same concepts (e.g. `move` is a clean upward arrow
   `M12 5v14M12 5 7 10M12 5l5 5`; the current `move` glyph is an unrelated flag/pennant shape
   `M12 2 7 9h4v6h-6v-6h4l-3-7z`). The mismatch is visible in the live client: the redesign's UI 設計稿
   uses recognisable pictograms per tab, while the shipped tab bar's icons do not visually communicate
   their tab's action. `webclient-contextual-hud`'s "The dock's root frame renders as an icon tab bar"
   requirement already mandates "a decorative glyph" per tab; it does not currently pin the glyph shapes
   to the approved reference, which is why an unrelated shape set could ship without violating any
   requirement.

3. **The dock panel's background does not match the redesign's gradient.** `ActionDock.vue`'s
   `.action-dock` renders `background: linear-gradient(180deg, var(--panel-hi), var(--panel))` — a
   lighter, violet-tinted `--panel-hi` at the top fading to the slightly darker `--panel` at the bottom —
   with `box-shadow: 0 -12px 40px -20px rgba(0, 0, 0, 0.9)`. The redesign's `.dockwrap` (the element that
   owns the dock's visible background in `index.html`) instead renders
   `background: linear-gradient(0deg, #0c0a0e, #141019 70%, var(--panel))` with
   `box-shadow: 0 -14px 34px -24px #000` — near-black at the bottom, rising only as far as the translucent
   `--panel` tone by the top, reading as the dock sinking into shadow beneath the scene rather than a lit
   violet-glass card. Confirmed via `docs/design/elosern-redesign/index.html:263-265` and by inspecting
   the shipped `.action-dock` computed style; `HudFrame.vue`'s `[data-anchor="dock"]` wrapper (the
   direct analogue of the draft's `.dockwrap`) applies no background of its own, so the mismatch is fully
   contained inside `ActionDock.vue`'s own `<style scoped>` block.

Every defect above is a pure presentation/content fix inside components already built and wired by the
completed `webclient-hud-01` through `webclient-hud-06` waves — no protocol, dispatch, router, or DOM
contract change is needed. This matches the precedent set by
`openspec/changes/archive/2026-08-26-fix-webclient-hud-integration-gaps`, a small finalize-class fix
against the same roadmap.

## What Changes

- Make `ActionDock.vue`'s `.action-dock__description` visually hidden (the standard `sr-only` clip
  pattern already used elsewhere in this codebase) while keeping its `data-testid` and text content
  intact, so the Node-contract gate that reads this hook keeps passing unchanged, but the legend text
  renders exactly once for a sighted or screen-reader-only-off player: as the visible trailing hint on
  `DockTabBar.vue`'s tab row.
- Reword the shared legend string from `"方向鍵選擇・Enter 確認・Esc 返回・/ 開啟指令"` to
  `"方向鍵選擇・Enter 確認・Esc 返回・/ 聚焦指令列"` in both files (they must stay byte-identical to
  each other, since the hidden copy exists only to satisfy the same contract-gate assertion as the
  visible one) — replacing the false "opens" claim with the real "focuses" behaviour, without touching
  the accurate `方向鍵選擇・Enter 確認・Esc 返回` clause.
- Replace the dock's tab and combat-root glyph paths in `dock-icons.js`'s `GLYPHS` table with the exact
  `d` path data the redesign already ships for the same concept: `move`, `look`, `interact`,
  `suggestions` (exploration root) and `attack`, `skills`, `items`, `defend`, `flee`, `forfeit` (combat
  root), copied verbatim from `docs/design/elosern-redesign/index.html`, including that reference's
  `stroke-linecap`/`stroke-linejoin="round"` attributes on the tab-bar's icon `<svg>` so multi-subpath
  glyphs (`move`, `attack`, `flee`) and the compound `look` glyph render with the same rounded joins and
  caps as the reference. Keys with no redesign counterpart (`character`, `quests`, `inventory`, `wait`,
  look-entity kinds, direction words, team glyphs) are unchanged — this change only touches concepts the
  redesign itself draws an icon for. (`suggestions` and `skills` intentionally resolve to the identical
  star path — the reference itself reuses one glyph for both concepts.)
- Replace `.action-dock`'s `background` and `box-shadow` with the redesign's exact `.dockwrap` values
  (Decision 5 below), so the floating dock panel reads as sinking into shadow rather than as a lit
  violet-glass card. The panel's existing `border-radius: 0 0 12px 12px` and `border-top: var(--line)`
  are unchanged — they are a deliberate H1 "floating anchored card" adaptation, not part of this defect.
- Update the one Node-contract test that asserts the legend's literal text
  (`web/static/webclient/js/tests/*.test.js`, the `action-dock-description` hook check) to the reworded
  string, and add a fast component-level assertion that `.action-dock__description` and
  `.dock-tab-bar__hint` are never both visible at once.
- **BREAKING**: none. No prop, event, DOM id, `data-testid`, dispatch, or protocol contract changes; the
  visible legend text and the tab icons are the only observable differences, and both are presentation
  content already scoped as "not story content."

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `webclient-contextual-hud`: the "dock's root frame renders as an icon tab bar" requirement gains an
  explicit clause that the tab glyphs match the redesign's reference icon for tabs the redesign draws an
  icon for, and a new requirement establishes that the dock's shortcut-legend text names only real
  keyboard behaviour and renders as exactly one visible instance (mirroring the command line's existing
  "advertises only affordances this client implements" requirement). The "action dock renders as a
  floating panel" requirement gains an explicit clause that the panel's background and shadow match the
  redesign's reference values.

## Impact

- **Code**: `web/webclient-app/components/ActionDock.vue` (its own `.visually-hidden` rule on the
  description div; the panel's `background`/`box-shadow`), `web/webclient-app/components/DockTabBar.vue`
  (reworded hint string; `stroke-linecap`/`stroke-linejoin` on the tab icon), `web/webclient-app/components/dock-icons.js`
  (glyph path table for the redesign-matched keys).
- **Tests**: `web/static/webclient/js/tests/*.test.js` (update the literal legend-text assertion),
  a new Vitest/component check that the two legend elements are never both visible, and a Storybook
  visual diff (`Action/ActionDock`, `Action/DockTabBar` stories) confirming the new icon shapes render.
- **Docs**: none — no capability-spec precedence or roadmap document changes; this is a same-tier fix
  against already-`Done` HUD-redesign waves, matching the `fix-webclient-hud-integration-gaps` precedent.
- **No protocol, read-model, dispatch, or component-inventory changes.** `component-manifest.json` stays
  frozen; no new component is added.
