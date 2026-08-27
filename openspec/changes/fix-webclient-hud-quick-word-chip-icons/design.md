## Context

`QuickWordChips.vue` (`webclient-hud-05-overlays-and-command-line`, H5) renders its exploration and
combat verb chips as plain `<button>{{ verb }}</button>` elements — verified by reading the component's
full template (35 lines, no `<svg>` anywhere). `dock-icons.js` (H3) already maintains a `GLYPHS` table of
stable-keyed SVG path data consumed by the action dock's tab bar (`DockTabBar.vue`) and its pane rows
(`DockMenu.vue`). Cross-referencing each chip's verb against the reference's own command-line icons
(`index.html:868-873`) and against `GLYPHS`'s existing keys:

| Chip verb | Reference has an icon? | Matching `GLYPHS` key | Path identical to reference? |
|---|---|---|---|
| 看 (look) | yes (`index.html:868`) | `look` | yes, once the sibling icon-fix change lands (see Sequencing note) |
| 拿 (get) | yes (`index.html:870`) | none yet — added by this change | yes (copied verbatim) |
| 說 (say) | yes (`index.html:871`) | `interact` | yes — the reference itself reuses one message-bubble path for both 互動 and 說 |
| 交談 (talk) | no — this client's own D4 addition | `character` (reused, not an exact-concept match) | n/a — no reference icon exists for this verb |
| 等待 (wait) | no — this client's own D4 addition | `wait` | n/a — no reference icon exists for this verb |
| 施法 (cast) | yes (`index.html:873`) | `suggestions`/`skills` | yes, once the sibling icon-fix change lands (see Sequencing note) |

**Correction from this change's own rubber-duck review:** the table above originally marked
`suggestions`/`skills` as an unconditional path match. That is only true after the sibling
`fix-webclient-hud-dock-guidance-and-icons` change lands — the *current*, pre-that-change value of
`GLYPHS.suggestions` (`"M12 2l2.4 4.9 5.4.8-3.9 3.8.9 5.4L12 14.5 7.2 16.9l.9-5.4L4.2 7.7l5.4-.8L12 2z"`)
does not match the reference's star path. This row now carries the same "once the sibling change lands"
caveat already given to `look`/`interact`, rather than overstating an unconditional match.

## Goals / Non-Goals

**Goals:**
- Every quick-word chip carries a decorative icon beside its text label, closing the visual gap with the
  reference's `.verb` chips.
- Reuse the existing `dock-icons.js` glyph vocabulary rather than introducing a second, parallel icon
  source — one glyph table for the whole app.
- No behavior change: a chip still only prepares text and focuses the field; it never submits.

**Non-Goals:**
- No key-mnemonic badge — unchanged, already a deliberate, spec-mandated decision (`webclient-contextual-hud`:
  "Chips SHALL carry no key-mnemonic badge unless this client binds that key").
- No change to which verbs exist in each mode's chip set, or to the mode-gating CSS
  (`data-elosern-mode` `display:none` switching) — this change only adds a decorative icon to each
  already-existing chip.
- No invented icon for a concept the reference never drew (`交談`, `等待`) beyond reusing an existing,
  already-reviewed glyph from this client's own vocabulary — never a brand-new, unreviewed shape.

## Decisions

**1. Reuse `dock-icons.js`'s `glyphPath()` and existing keys wherever a chip's verb maps onto a concept
that table already covers; add exactly one new key (`get`) for the one verb with no existing match.**
`看`→`look`, `說`→`interact`, `等待`→`wait`, `施法`→`suggestions` all resolve to glyphs `dock-icons.js`
already carries — importing `glyphPath` into `QuickWordChips.vue` and calling
`glyphPath(GLYPH_KEY_FOR_VERB[verb])` needs zero new path data for four of six verbs. `拿` has no
existing key; its reference path (`index.html:870`,
`M6 11V7a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v4M4 11h16v9H4z`) is added to `GLYPHS` as a new `get` entry — this
is additive (a new object key), not an edit to any key the sibling icon-fix change also touches, so the
two changes can land in either order without a text-level merge conflict even though both edit
`dock-icons.js`.
Alternative considered: give `QuickWordChips.vue` its own local, standalone icon map (copy the four
reused paths inline instead of importing `dock-icons.js`). Rejected — that duplicates path data the app
already maintains once, and risks the two copies drifting apart on a future icon-language update (e.g.
if the reference's `look` icon changes again, only one of two places would get fixed).

**2. For `交談` (a verb this client added beyond the reference's own set, per the component's existing
D4 comment), reuse the `character` glyph rather than leaving it icon-less or inventing new iconography.**
The reference never drew a `交談` chip at all — there is nothing to copy. Leaving it icon-less would
single out one chip as visually inconsistent with its five siblings once they all carry icons, which
looks like an oversight rather than a deliberate choice. Inventing a brand-new, unreviewed glyph shape
would be new design work this change's scope (matching *existing* reviewed iconography) explicitly
excludes. `character` (a person silhouette) is already this client's own established shorthand for
"engage with a person" — the dock's `角色狀態` tab — and `交談` (converse with someone) is conceptually
the closest existing concept in the app's own vocabulary to reach for.
Alternative considered: reuse `interact`'s glyph (the same message-bubble `說` uses) for `交談` too, since
both are speech-adjacent. Rejected — `說` and `交談` sitting side-by-side with the identical icon would
look like a rendering bug (two chips, same icon, different text) rather than two distinct verbs; a
person-silhouette glyph keeps every visible chip icon distinct.

**3. Icon sizing and placement mirror the reference's `.verb` chip layout, scaled to this chip's existing
compact padding, with no other structural change to the chip.**
The reference's `.verb .ic{width:15px;height:15px}` sits before the label inside a
`padding:0 10px;height:34px` pill. `QuickWordChips.vue`'s existing `.qwc__chip{padding:4px 10px}` is
already a comparable compact pill, but — verified by reading its current CSS — `.qwc__chip` itself has
no `display: inline-flex`/`align-items` today (only its ancestors `.qwc`/`.qwc__group` are flex
containers), so adding an `<svg>` before the text as plain inline content would default to baseline
vertical alignment against the text, a visible misalignment. The fix therefore sets
`.qwc__chip { display: inline-flex; align-items: center; gap: 6px; }`, mirroring `DockTabBar.vue`'s own
established convention for an icon+label button (`.dock-tab-bar__tab { display: inline-flex;
align-items: center; gap: 8px; }`) rather than inventing a new layout pattern. The icon itself is a
leading `<svg>` (14px, `aria-hidden="true"`, `fill="none" stroke="currentColor"`, matching
`DockTabBar.vue`'s existing icon-rendering attributes for consistency).

Confirmed via the existing test suite (`web/webclient-app/tests/command_line.test.js`) that adding an
`aria-hidden` icon before the label carries no accessible-name regression risk: every existing test
selects a chip by its `data-testid="quick-word-chip-<verb>"`, never by `getByRole('button', {name})` or
any accessible-name computation, so this change's DOM structure edit is not observed by anything
sensitive to child-node order.

## Risks / Trade-offs

- **[Risk] `交談`/`character` and any future dock tab reusing the same glyph could visually imply an
  unintended equivalence between the two surfaces.** → Low — the codebase already reuses several glyphs
  across concepts (`suggestions`/`skills`/`施法` all share one star), and each reuse is always paired
  with a distinct, unambiguous text label, so the label — not the icon alone — carries the concept's
  identity. `dock-icons.js`'s own header comment states the same principle for its existing consumers:
  "Every glyph is `aria-hidden` beside the real text label"; the `webclient-contextual-hud` spec states
  the stronger, binding form of this for navigation rows ("Icons SHALL be decorative ... SHALL always
  accompany a real text label").
- **[Risk] Adding a `get` key to `GLYPHS` at the same time a sibling change edits several *existing*
  keys' values could still produce a merge conflict at the object-literal level (e.g. trailing-comma /
  adjacent-line collisions) even though the keys themselves don't overlap.** → Low-severity, ordinary git
  merge mechanics, not a logical conflict, for a human-reviewed line-level diff; whichever change lands
  second does a trivial rebase. This risk would sharpen only if either change were applied as a scripted
  whole-object rewrite of `GLYPHS` rather than a targeted patch — not the case here (both changes' tasks
  specify targeted, per-key edits). Noted as a task-tracked check, not left implicit.
- **[Trade-off] `交談` and `等待` carry icons with no reference precedent, so this change's icon choices
  for those two are this project's own judgment call, not a verified copy.** → Accepted and documented
  explicitly (Decision 2) rather than left to look like an unremarked copy; both reuse existing,
  already-reviewed glyphs rather than introducing new shapes.

## Migration Plan

Not applicable — no data migration, no feature flag. A template/style edit to one component plus one
additive entry in a shared glyph table, landed and reviewed as one change.

## Open Questions

None — every reused glyph is verified against `dock-icons.js`'s current keys, and every reference-drawn
icon's path is verified against `docs/design/elosern-redesign/index.html`'s cited line numbers.
