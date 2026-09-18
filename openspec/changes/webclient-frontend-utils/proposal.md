## Why

The Vue app duplicates two presentation rules verbatim, and the central store duplicates its
defensive-panel-read boilerplate:

- `ConditionChips.vue:50 chipName` and `CharacterStatusDrawer.vue:147 conditionName` are
  byte-identical (incl. the zh-TW strings `剩 … 秒` and the `，` join): the condition label an
  accessible chip name and the drawer roster render MUST agree, yet two copies guarantee they
  drift — an a11y-name/prose divergence with no test that catches the first half changing.
- `FullLogOverlay.vue:88 lineNodes` and `NarrativeFeed.vue:146 lineNodes` are ~identical
  line-to-vnode renderers (divider + literal `.inp` line for player input, markup-pipeline
  line otherwise, `BOX_DRAWING` monospace class) — the "one renderer, no second markup path"
  design note in both files is enforced by copy-paste.
- `stores/elosern.js::buildView` repeats the same defensive read shape ~5 times
  (`(rs.panels && rs.panels.X) || null` + `available === true` / `Array.isArray(field)`
  guards) for party/objectives/roster/exploration.

## What Changes

- New `web/webclient-app/lib/condition_label.js` exporting `conditionLabel(condition)` — the
  single copy of the label rule; both components import it (each keeps its local `chipName` /
  `conditionName` as one-line delegates so template usage and any test introspection stay
  unchanged).
- New `web/webclient-app/lib/narrative_line_nodes.js` exporting `lineText(line)` and
  `narrativeLineNodes(line, index)` (imports `h` from vue, `NarrativeMarkup` from
  `./narrative_markup.js`, `renderNarrativeTokens` from `../components/narrative-renderer.js`
  — the same pipeline both components already import); both components delete their local
  copies. The two `BOX_DRAWING` literals (`/[\u2500-\u257f]/` and its literal-glyph spelling
  `/[─-╿]/`) denote the identical code-point range; one copy remains, written as the escaped
  form.
- New `readPanel(rs, key)` helper (module-level in `stores/elosern.js`, not exported) replacing
  the `(rs.panels && rs.panels.X) || null` lines; per-field `available`/type guards stay at
  each read because the predicates genuinely differ (`available === true` for
  party/objectives/roster vs `available !== false` for vitals/exploration — see design).
- Zero visual/behavior change; `pnpm test` suite stays green untouched.

## Capabilities

### New Capabilities
None.

### Modified Capabilities
None — `skip_specs: true`. Governed behaviors (`webclient-contextual-hud` condition chips,
`webclient-input-narrative` line rendering, `webclient-party-panel`/`webclient-objectives-panel`/
`webclient-character-roster`/`webclient-exploration-menu` store views) are unchanged
requirements; no command surface, no Python, no protocol touched.

## Impact

`web/webclient-app/components/{ConditionChips,CharacterStatusDrawer,FullLogOverlay,NarrativeFeed}.vue`,
`web/webclient-app/stores/elosern.js`; new `lib/condition_label.js`,
`lib/narrative_line_nodes.js`, plus two small Vitest files. The Vitest suite and the Vite
build inputs change; `pnpm run build` and the showcase fingerprint inputs follow
automatically (CI-owned builds). `.github/evennia-shards.json` untouched.

## Batch

- depends-on: (none)
- Independent of every other change in the program: touches only `web/webclient-app/**`,
  disjoint from `webclient-presentation-push-factory`'s `web/webclient/**` Python.
- No overlap with `martial-arts-catalog` / `elementless-damage-effect` /
  `divine-mystery-catalog` (Python/data files only).

## Non-goals

- Do NOT split the rest of `buildView` — the remaining logic is heterogeneous (drawer,
  prefs, toast queue, TDZ-ordered refs) and forcing a split would obscure more than it saves.
- `VitalsTrack`'s `isLowHp` / gauge helpers already live in `lib/` — untouched.
