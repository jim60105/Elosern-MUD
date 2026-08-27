## Why

`QuickWordChips.vue`'s persistent command-line chips (看/拿/說/交談/等待 in exploration, 說/施法 in
combat) render as bare text buttons — no icon — while `docs/design/elosern-redesign/index.html`'s
`.verb` chips (the same command-line surface) pair a small icon with the label for every verb
(`index.html:868-873`, e.g. `看`'s chip carries the eye glyph, `說`'s carries the message-bubble glyph).
The component's own code comment already documents *why* the letter-key badge was dropped ("No mnemonic
key badge: the draft's letter badges are dropped because the client binds no key to them") but never
addresses the icon — the icon was simply never added, not deliberately omitted; nothing in
`webclient-hud-05-overlays-and-command-line`'s design record calls out an intentional icon-drop the way
it does for the key badge.

This client already maintains exactly the icon language the reference draws for four of these six verbs,
in `dock-icons.js`'s `GLYPHS` table (used by the action dock's tab bar): `看`/look shares the dock's
`look` glyph, `說`/say shares the dock's `interact` glyph (the reference itself draws identical
message-bubble icons for both concepts — `index.html:760,871`), `等待`/wait shares the dock's `wait`
glyph, and `施法`/cast shares the dock's `suggestions`/`skills` star glyph (again, the reference reuses
one glyph for both). Only two verbs need something new: `拿`/get (the reference's own get-icon path,
`index.html:870`, not currently in `GLYPHS`) and `交談`/talk (a verb this client added beyond the
reference's own set — see below — with no reference icon to copy).

**Sequencing note (not a hard dependency):** `看`'s reused `look` glyph and `說`'s reused `interact`
glyph are most visually faithful once the sibling change `fix-webclient-hud-dock-guidance-and-icons`
also lands (it corrects those same two `GLYPHS` entries to match the reference exactly). This change
functions correctly and adds real value on its own regardless of landing order — `glyphPath()` simply
returns whatever `look`/`interact` path is current at the time — but landing after that sibling change
gives both chips their intended final shape immediately rather than in two visible steps.

## What Changes

- Add SVG icons to every `QuickWordChips.vue` chip, reusing `dock-icons.js`'s existing `glyphPath()`
  function and `GLYPHS` table rather than maintaining a second, parallel icon map: `看` → `look`, `說` →
  `interact`, `等待` → `wait`, `施法` → `suggestions`.
- Add one new `GLYPHS` entry, `get`, with the reference's own get-icon path
  (`M6 11V7a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v4M4 11h16v9H4z`, `index.html:870`), used by `拿`.
- For `交談` (a verb the reference does not draw — this client's own D4 addition, the talk alias with no
  reference counterpart), reuse the existing `character` glyph (a person silhouette) rather than
  inventing new, unreviewed iconography: `交談` means "converse with someone," and the dock already uses
  that same glyph for its person-centric `角色狀態` tab, so the association reads consistently within
  this client's own icon vocabulary even though the reference itself never drew this verb.
- Style each chip's icon at 14px (matching the reference's `.verb .ic{width:15px;height:15px}` sizing in
  spirit, scaled to this chip's slightly more compact padding), decorative and `aria-hidden`, always
  paired with the existing visible text label — no icon ever stands alone.
- No key-mnemonic badge is added (unchanged, deliberate per the existing D5 decision and the
  `webclient-contextual-hud` "Quick-word chips" requirement, which already forbids a chip advertising a
  key mnemonic this client does not bind).
- **BREAKING**: none. No prop, event, DOM id, `data-testid`, dispatch, or protocol contract changes; the
  chip's clickable target, inserted text, and mode-gating are unchanged — only a decorative icon is
  added beside each existing label.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `webclient-contextual-hud`: the "Quick-word chips prepare a command without submitting it" requirement
  gains a clause that each chip carries a decorative icon, drawn from the same stable glyph vocabulary
  the action dock uses, alongside its existing text label.

## Impact

- **Code**: `web/webclient-app/components/QuickWordChips.vue` (per-chip icon markup + styling),
  `web/webclient-app/components/dock-icons.js` (one new `get` glyph entry).
- **Tests**: extend `web/webclient-app/stories/Core/QuickWordChips.stories.js`'s existing exploration/
  combat/creation stories (already offline-deterministic) to visually confirm the icons; a Vitest
  assertion that every rendered chip carries an `aria-hidden` icon element alongside its text label, and
  that `glyphPath("get")` returns the new path.
- **Docs**: none.
- **No protocol, read-model, dispatch, or component-inventory changes.** `component-manifest.json` stays
  frozen; no new component is added.
