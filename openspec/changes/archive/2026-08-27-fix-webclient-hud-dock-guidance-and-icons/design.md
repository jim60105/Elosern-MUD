## Context

`web/webclient-app/components/ActionDock.vue` and `DockTabBar.vue` were built across
`webclient-hud-03-action-dock` (H3) and never revisited since. Two small, independent presentation
defects survived every later wave (H4–H6) because neither is covered by an existing normative
requirement:

- `ActionDock.vue:133-135` renders `.action-dock__description` (a plain, visible `<div>`) and
  `DockTabBar.vue:143-145` renders `.dock-tab-bar__hint` (a `<span>` inside the tab bar) — both bound to
  the literal identical string. The Vitest suite (`web/webclient-app/tests/action/action_dock.test.js`)
  and the Playwright suite (`web/tests/browser/test_browser_shell.py:754-756`) both assert only against
  `[data-testid="action-dock-description"]`; neither ever noticed the second, class-only element carries
  the same text, because nothing asserts they must not both be visible.
- `dock-icons.js`'s `GLYPHS` table was authored independently of `docs/design/elosern-redesign/index.html`,
  even though the redesign is the binding visual reference (roadmap precedence item 3) and ships exact
  `d` path data for the same tab concepts.
- `ActionDock.vue`'s `.action-dock` background/shadow were authored as a generic `--panel-hi`/`--panel`
  card gradient instead of the redesign's specific `.dockwrap` values, even though `HudFrame.vue`'s
  `[data-anchor="dock"]` wrapper (the direct analogue of the draft's `.dockwrap`) applies no background
  of its own, so nothing else needs to change to fix this.

All three are pure presentation fixes inside already-`Done` components; no router, store, dispatch, or
DOM contract identifier is touched.

## Goals / Non-Goals

**Goals:**
- Exactly one visible instance of the dock's shortcut legend, with text that matches the client's real
  keyboard behaviour.
- Keep the `data-testid="action-dock-description"` Node-contract hook intact and readable (some other
  gate may still query its `textContent` even though it should no longer be the *visible* one) —
  visually hide it, don't remove it.
- Replace the tab/root glyph paths for every key the redesign itself draws an icon for, using the
  redesign's own path data unmodified (or trivially adapted, per Decision 3 below), with matching
  stroke-linecap/linejoin fidelity.
- Match `.action-dock`'s background gradient and box-shadow to the redesign's `.dockwrap` values.

**Non-Goals:**
- No change to which root items exist (`character`/`quests`/`inventory`/`wait` stay — they are H4's
  sanctioned drawer entry points, not part of this fix's scope; see the roadmap's §8 risk on drawers).
- No change to badge logic, router/keyboard behaviour, or any `data-testid`/DOM contract identifier.
- No icon for keys the redesign has no icon for (`character`, `quests`, `inventory`, `wait`, look-entity
  kinds, direction words, participant teams) — inventing a glyph the reference never drew would not be
  "matching the redesign," it would be new design work outside this fix's scope.
- No change to the quick-word chips (command line) — that is a separate, independently-sized change
  (`fix-webclient-hud-quick-word-chip-icons`).

## Decisions

**1. Hide `ActionDock.vue`'s description by authoring its own `.visually-hidden` rule in its own
`<style scoped>` block — matching the codebase's existing per-component duplication of that same rule,
not a cross-component reuse.**
Vue's `<style scoped>` compiles every selector with a per-component `data-v-xxxx` attribute, so a
`.visually-hidden` rule defined in `DockMenuItem.vue`'s scoped style **cannot** style an element rendered
by `ActionDock.vue` even though the class name matches — confirmed by `grep`: `.visually-hidden` is
already independently redefined in both `DockMenuItem.vue` and `DockMenu.vue` today, which is the
existing convention this change follows, not a new one. The implementation therefore adds a second,
textually-identical `.visually-hidden` rule (absolute-position, 1×1px, clipped, `clip: rect(0 0 0 0)`)
inside `ActionDock.vue`'s own `<style scoped>` block, and applies the class to `.action-dock__description`.
This means: (a) `test_browser_shell.py:754` keeps working verbatim (`inner_text()` on a clipped element
still returns its text in Playwright), (b) the Vitest assertions against
`[data-testid="action-dock-description"]` keep passing verbatim, (c) the one *visible* legend a player
sees is `DockTabBar.vue`'s trailing hint, matching the redesign's `.dock .hint` placement (§draft
`index.html:301-302`). The acceptance check for this decision (task 1.5) asserts the element's actual
rendered state (computed `clip`/size, or a Playwright `is_visible()` check) — not merely that the
`visually-hidden` class name is present on it, since a present-but-inert class name would let the test
suite go green while the element still renders visibly (the CSS-scoping gap above is exactly how that
would happen silently).
Alternative considered: delete `ActionDock.vue`'s description entirely and point the Node-contract gate
at `DockTabBar.vue`'s hint instead. Rejected — `DockTabBar` renders conditionally (`v-if="showChrome"`,
i.e. absent in creation mode), so the gate would lose its always-present hook exactly when creation mode
needs to assert its *absence* of chrome; `ActionDock`'s description has no such conditional and is the
correct permanent anchor for the Node-contract text check.

**2. Reword to `"方向鍵選擇・Enter 確認・Esc 返回・/ 聚焦指令列"` — the `/` clause changes from
"opens" to "focuses", the rest is untouched.**
Verified from `keyboard_router.js:272-275` (`/` emits `toggle-drawer`) and
`stores/elosern.js:577-582` (the handler bumps `drawerRequest`, which `AppShell.vue`'s watcher turns into
`shellRef.value?.focusCommandField()` — a focus call, not an open/close toggle; per
`webclient-contextual-hud`'s "permanently present bar" requirement the field has no open/closed state to
toggle in the first place). `方向鍵選擇・Enter 確認・Esc 返回` is unchanged because it is accurate:
`keyboard_router.js` moves focus on `ArrowUp/Down/Left/Right`, confirms on `Enter`, and pops/escapes on
`Escape` — confirmed against the live client with `agent-browser`.
Alternative considered: match the design draft's own hint text verbatim
(`數字鍵 1–4 · Enter 執行 · Esc 返回`, `index.html:762`). Rejected — the draft's static demo binds
digit keys 1–4; this client's `keyboard_router.js` binds arrow keys, never digits, for dock navigation.
Copying the draft's wording would make the hint describe a keyboard scheme the client does not
implement, which is exactly the failure this change fixes for `/ 開啟指令` — the fix must describe this
client's real behaviour, not the mockup's.

**3. Copy the redesign's glyph `d` data verbatim per key; compose `look`'s two-element icon
(eye outline + pupil circle) into one multi-subpath `d` string.**
`dock-icons.js`'s `glyphPath(key)` returns a single `d` string consumed by one `<path>` element
(`DockTabBar.vue:124-134` — no `<circle>` sibling). The redesign draws most icons as one `<path>` already
(`move`, `interact`, `suggestions`/`skills`, `attack`, `items`, `defend`, `flee`), so those copy over
unchanged. `look` is drawn in the redesign as a `<path>` (the eye outline) plus a separate `<circle
cx="12" cy="12" r="3">` (the pupil). SVG's `d` grammar supports multiple subpaths in one string (each new
`M` starts a fresh subpath), and a circle is representable with two arc (`A`) commands, so the pupil
folds into the same `d`:
`"M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7Z M9 12a3 3 0 1 0 6 0a3 3 0 1 0 -6 0"`.
Rendered with `fill="none" stroke="currentColor"` (the existing `DockTabBar.vue` SVG attributes), this
produces the identical two-outline look as the reference. `forfeit`'s reference path carries a
`transform="translate(0,-1)"` the current renderer has no attribute slot for (`glyphPath` returns a bare
`d` string); the translation is baked into the copied coordinates by hand (shifting both subpaths'
starting `y` by `-1`: `"M6 2h12l-5 8v6M9 2l1 7"`) rather than adding transform support to `DockTabBar.vue`
for one glyph.
Alternative considered: add a full icon-component library (e.g. render `<component>` per glyph with its
own viewBox/transform). Rejected as disproportionate — ten path strings is a data change, not an
architecture change, and `glyphPath`'s single-`d`-string contract already serves the other ~30 mapped
keys correctly.

The reference also sets `stroke-linecap="round"` and/or `stroke-linejoin="round"` on several of the
copied icons — selectively, not on every icon: `move` carries both cap and join, `interact` carries
join only, `attack` and `flee` carry cap only, while the star glyphs (`suggestions`/`skills`),
`items`, `defend`, `look`, and `forfeit` carry neither (the star's points would visibly soften under a
round join, which is why the reference omits the attributes there). This change therefore applies the
attributes **per key**, not unconditionally: `dock-icons.js` gains a `STROKE_ATTRS` map
(`move`: cap+join, `interact`: join, `attack`/`flee`: cap, all other keys: none) exposed through a
`glyphAttrs(key)` export, and `DockTabBar.vue`'s tab icon `<path>` binds them via
`v-bind="glyphAttrs(tab.key)"`. `glyphSvg`'s path child merges the same per-key attributes. This
keeps every rendered glyph visually identical to the reference — an unconditional attribute set would
have rounded the star tips and diverged from the binding visual reference. The tab icon's
`stroke-width` also moves from the client's `1.8` to the reference's `1.9` (every `.tab svg.ic` in
the reference carries `stroke-width="1.9"`), and `glyphSvg`'s path uses the same value; the helper's
outer decorative `<circle>` outline (a client-side addition with no reference counterpart) keeps its
existing width.

**4. The exact key → path mapping this change applies (all copied from
`docs/design/elosern-redesign/index.html`, byte-verified against the lines quoted):**

| Key | Redesign source line | New `d` |
|---|---|---|
| `move` | 758 | `M12 5v14M12 5 7 10M12 5l5 5` |
| `look` | 759 | `M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7Z M9 12a3 3 0 1 0 6 0a3 3 0 1 0 -6 0` |
| `interact` | 760 | `M4 5h16v11H8l-4 4V5Z` |
| `suggestions` | 761 | `M12 3l1.9 5.6L19.5 10l-5.6 1.9L12 17l-1.9-5.1L4.5 10l5.6-1.4L12 3Z` |
| `attack` | 831 | `M5 19 19 5M5 19h4M5 19v-4` |
| `skills` | 832 | `M12 3l1.9 5.6L19.5 10l-5.6 1.9L12 17l-1.9-5.1L4.5 10l5.6-1.4L12 3Z` (same glyph as `suggestions`) |
| `items` | 833 | `M4 8h16v11H4zM8 8V6a4 4 0 0 1 8 0v2` |
| `defend` | 834 | `M12 3 4 6v6c0 5 3.5 8 8 9 4.5-1 8-4 8-9V6l-8-3Z` |
| `flee` | 835 | `M13 5l7 7-7 7M4 12h16` |
| `forfeit` | 836 | `M6 2h12l-5 8v6M9 2l1 7` (y-shifted −1 per Decision 3) |

`character`, `quests`, `inventory`, `wait`, and every look-entity/direction/team key are unchanged (no
redesign counterpart — Non-Goals).

**5. Match `.action-dock`'s background and shadow to the redesign's `.dockwrap` values exactly, leave
everything else about the panel's chrome untouched.**
Replace `background: linear-gradient(180deg, var(--panel-hi), var(--panel))` with
`background: linear-gradient(0deg, #0c0a0e, #141019 70%, var(--panel))`, and
`box-shadow: 0 -12px 40px -20px rgba(0, 0, 0, 0.9)` with `box-shadow: 0 -14px 34px -24px #000` — both
copied verbatim from `docs/design/elosern-redesign/index.html:263-265`. `border-top: var(--line)` is
already identical to the reference and is untouched. `border-radius: 0 0 12px 12px` has no counterpart
in the reference's edge-to-edge `.dockwrap` (which spans `left:0;right:0` with no rounding at all) — but
`ActionDock.vue`'s own H3 comment documents the panel as a deliberately re-chromed, `max-width:1180px`
*centred floating card* (matching the HUD islands' anchored-card treatment elsewhere in this HUD, not the
draft's full-bleed band), so the rounding is an intentional architectural adaptation this change does not
touch — only the color values the panel's own comment already claims to replicate ("the draft's upward
gradient") but does not.
Alternative considered: also flatten the panel to the reference's edge-to-edge, unrounded `.dockwrap`
shape. Rejected — that is a structural layout change (removing the `max-width`/`margin:0 auto`/
`border-radius` centred-card treatment H1 established for every anchored HUD surface), well outside a
background-color fix, and not something this change's research found any defect in (no comparison
image or gap analysis flagged the panel's shape, only its color).

## Risks / Trade-offs

- **[Risk] The Playwright literal-keyword assertion at `test_browser_shell.py:755` checks for the
  substring `"/ 開啟指令"`, which this change removes.** → Update that assertion in the same change
  (task-tracked below); it is a same-file, same-line text update, not a contract redefinition.
- **[Risk] Some other, not-yet-found Playwright or Vitest spec may assert one of the ten replaced `d`
  strings verbatim (e.g. a snapshot test).** → `grep -rn` for each literal old path string across
  `web/webclient-app/tests/` and `web/tests/browser/` before landing; none were found during this
  change's research pass (`web/webclient-app/tests/` has no `dock-icons`-named test file at all — a
  pre-existing coverage gap this change also closes with a new fast unit test), but the grep is a task
  gate, not an assumption.
- **[Trade-off] `look`'s compound `d` string is harder to hand-edit than a single simple path.** →
  Accepted: it is generated once from the reference and covered by a Storybook visual story
  (`Action/DockTabBar`), so it is verified visually rather than by reading the path data.
- **[Risk] A `.visually-hidden` class added without its own scoped CSS rule in `ActionDock.vue` would be
  a silent no-op** (Vue scoped styles do not cross component boundaries) **— fixed by requiring the rule
  be authored in `ActionDock.vue`'s own `<style scoped>` block (Decision 1) and by requiring task 1.5's
  test to assert actual rendered invisibility, not class-name presence.**

## Migration Plan

Not applicable — no data migration, no feature flag, no phased rollout. This is a source-level content
edit to three files plus their two covering test files, landed and reviewed as one change.

## Open Questions

None — every decision above is settled by an existing pattern in this codebase (`.visually-hidden`), a
verified behavioural fact (the router's real key bindings), or the redesign's own committed source.
