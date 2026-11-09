# Design: handbook-primitives

## Context

Source of truth: `docs/superpowers/specs/2026-11-09-handbook-codex-titles-design.md` §5.1. Visual reference: `docs/design/handbook-codex-titles/TileWall.vue`, `CodexEmblem.vue`, `TitlesTabProto.vue` (the `.hb-detail` block) and `HandbookPrototype.vue`. Never import the prototype from the app.

Observed:

- `components/QuestDetail.vue` owns the pinned footer: `.quest-detail__actions`, `__why`, `__why--danger`, `__btn` with `--primary`, `--ghost` and `--danger`, `__spacer`, a reduced-motion block, and the abandon arm/disarm focus logic. Its testids are `quest-drawer__actions`, `__abandon`, `__abandon-confirm`, `__abandon-confirm-no`, `__abandon-confirm-yes`, `__track`, `__turnin`, `__accept` and `__action-reason`. The track toggle uses native `disabled`. The accept button uses `aria-disabled` with `aria-describedby` pointing at the reason.
- `tests/world/quest_detail.test.js:221` asserts the class `quest-detail__btn--primary`.
- `components/dock-icons.js` is the stroke glyph registry (`glyphPath`, `glyphAttrs`).
- `styles/app-shell.css` has no `.elosern-root` rule for these classes. That must stay true for every new class.
- JS tests reach traceability only through a Python evidence bridge that runs vitest (pattern: `web/webclient/tests/test_vue_hud_drawer_evidence.py`).

## Goals / Non-Goals

**Goals:** the four shared components, with `QuestDetail` switched to `DetailFooter` and its behavior unchanged.

**Non-Goals:** mounting any new component in the app; the titles or codex tab; codex category emblems (added by `handbook-codex-tab`); medal grids or tile faces (they are slot content, supplied by later changes); `ActionBar`.

## Decisions

### D1. DetailFooter (verbatim contract)

New `web/webclient-app/components/DetailFooter.vue`:

```js
props: {
  reason: { type: String, default: null },
  reasonTone: { type: String, default: "plain" },        // "plain" | "danger"
  reasonRole: { type: String, default: null },           // "alert" while a confirmation is armed
  reasonTestid: { type: String, default: null },
  buttons: { type: Array, default: () => [] },
  // [{ key, label, tone: "plain"|"primary"|"ghost"|"danger", enabled = true,
  //    pressed = null, glyph = null, testid, describedByReason = false, spacerBefore = false }]
  testid: { type: String, default: null },
}
emits: ["press"]          // press(key); never emitted for enabled === false
expose: { focus(key) }    // focuses the rendered button with that key
```

- A disabled button renders `aria-disabled="true"` and stays focusable, with `aria-describedby` pointing at the reason line when `describedByReason`.
- A button with `pressed !== null` is a toggle. It renders `aria-pressed`, uses native `disabled`, and gets class `is-on` when pressed.
- `glyph` draws `glyphPath(glyph)` before the label.
- `spacerBefore` inserts `<span class="detail-footer__spacer">`.
- Move the footer CSS listed above, including the reduced-motion block, into this component with the prefix `detail-footer` (`detail-footer__why`, `detail-footer__why--danger`, `detail-footer__btn`, `detail-footer__btn--primary|--ghost|--danger`, `detail-footer__spacer`). The declarations stay unchanged.
- `QuestDetail.vue` builds its button list from its current `actions` and armed state:
  - Armed: reason `ABANDON_WARNING(detail.name)` with tone `danger` and role `alert`, then buttons `cancel` (`quest-drawer__abandon-confirm-no`) and `confirm` (tone danger, `__abandon-confirm-yes`).
  - Otherwise: reason `actions.reason` (`__action-reason`), then `abandon` (ghost), `track` (toggle, glyph `track_flag`, `spacerBefore` when abandon or track exists), `turnin` (primary) and `accept` (primary, `describedByReason`).
  - The root carries `quest-drawer__actions`. The armed reason uses `__abandon-confirm`.
  - Its existing `arm`, `disarm`, `confirmAbandon`, `accept` and `toggleTrack` functions stay, called from one `press` handler, and focus goes through `footerRef.value.focus(key)`.
- Update the single class assertion in `tests/world/quest_detail.test.js` to `detail-footer__btn--primary`.

### D2. TileWall

Port `docs/design/handbook-codex-titles/TileWall.vue` to `components/handbook/TileWall.vue` with unchanged behavior and markup:

- Props: `groups` (`[{key, label|null, items:[{id, selectable, label}]}]`), `selectedId`, `ariaLabel` and `variant` (`tile` | `medal`).
- Emits `select(id)`. The scoped slot is `tile` (`{item, selected}`).
- Up and Down step by the measured grid column count (`getComputedStyle(grid).gridTemplateColumns`). The vitest config loads SFC styles, so jsdom returns the unresolved `repeat(auto-fill, ...)` string; the row-step test stubs the measurement with a fixed column count.
- Add `data-testid="tile-wall"` on the root and `data-tile="<id>"` on each cell (already in the prototype).

### D3. CodexEmblem

Add to `components/dock-icons.js` the prototype's path strings as `emblem_combat`, `emblem_spell`, `emblem_explore`, `emblem_guild`, `emblem_clergy`, `emblem_romance`, `emblem_epithet`, `emblem_ballot` and `emblem_unknown`. `components/handbook/CodexEmblem.vue` takes props `name` and `strokeWidth` (default 1.6) and renders one `aria-hidden` SVG of `glyphPath("emblem_" + name)`. A name without a path falls back to `emblem_unknown`.

### D4. CodexDetail

`components/handbook/CodexDetail.vue`, after the prototype's `.hb-detail`:

- Props: `detail` (`{id, name, ribbon, emblem, grade, locked, stamp: {kind,label}|null, subtitle, sections: [{label,text}], nameplate}` or `null`) and `footer` (`{reason, reasonTone, reasonRole, buttons}` or `null`). There is also a named slot `hero` that replaces the default hero face, which `handbook-codex-tab` uses for art.
- The default hero face is a round medal holding `GradeGem :grade` when `grade` is set, else `CodexEmblem :name="emblem"`. A dashed silhouette ring is drawn when `locked`. The optional `nameplate` text sits beside it.
- Then the ribbon, the title (`h3`), the gold subtitle, the sections, and `<DetailFooter v-if="footer">` pinned at the bottom.
- Emits `press(key)`, exposes `focus(key)`.
- `detail === null` renders `<div class="codex-detail codex-detail--empty" data-testid="handbook__detail-empty">`.
- Classes use the prefix `codex-detail__*`. Copy the hero, ribbon and title declarations from `QuestDetail.vue`.
- Testids: `handbook__detail`, `handbook__ribbon`, `handbook__stamp` (with `data-stamp="<kind>"`) and `handbook__section`.

### D5. Stories and evidence

- Stories:
  - `stories/World/DetailFooter.stories.js`: quest buttons, an armed danger reason, a disabled aria button.
  - `stories/World/TileWall.stories.js`: two groups, with a non-selectable item.
  - `stories/World/CodexDetail.stories.js`: emblem hero, grade hero, locked with sections, empty.
  - Every fixture is synthetic.
- Add `World/DetailFooter`, `World/TileWall` and `World/CodexDetail` to `component-manifest.json` and to the lists in `web/webclient/tests/test_vue_showcase_{action,data,overlays,world}_evidence.py` wherever those files list every manifest entry.
- Create `web/webclient/tests/test_vue_handbook_evidence.py`, modelled on `test_vue_hud_drawer_evidence.py`, with a class `VueHandbookEvidenceTest`.
  - One method runs `tests/handbook/tile_wall.test.js`.
  - One runs `tests/components/detail_footer.test.js` and `tests/world/quest_detail.test.js`.
  - Register the module in exactly one shard of `.github/evennia-shards.json`.

## Risks / Trade-offs

- [The extraction shifts the quest footer's pixels] → Declarations move unchanged, and the existing `quest_detail` vitest suite and quest-drawer browser tests still pass with identical testids.
- [Components land with no app consumer] → Storybook and vitest exercise them, and the next change mounts them.
