## 1. Freeze what this change may not move

- [ ] 1.1 Record the identifiers H2 preserves byte-identical: the `.local-map` root class (H1's combat-hide CSS in `HudFrame.vue` and `AppShell.vue`'s `HIDDEN_BY_MODE` focus-rescue map both select it literally), `data-testid="status-panel"`, `data-testid="status-panel__gauge-value--{hp,mp,sp}"`, `data-testid="local-map"`, `local-map__title`, `local-map__legend`, `local-map-detail`, `local-map-remembered`, and the per-node `local-map__node--<id>` / `data-node-id` hooks
- [ ] 1.2 Add a Vitest asserting each preserved identifier is still present after the re-chrome, so a regression fails at the unit gate rather than by silently un-hiding the minimap in combat
- [ ] 1.3 Grep `web/tests/browser/` for the class-literal selectors this change relocates (`.status-gauge__value`, `.status-gauge__bar`, `.status-panel`, `.local-map`, `.local-map__lattice`, `.local-map__node`, `.local-map__marker--current`, `.local-map__actionable`) and record the file/line list; they are re-mapped in group 9
- [ ] 1.4 Confirm H1's landed hooks before consuming them: `HudFrame`'s `lowhp` prop, the `[data-lowhp="true"]` vignette swap, the unreferenced `elosern-hp-pulse` keyframe, and the `feed` anchor's `calc(90vw - 524px)` reservation for `hud-right`

## 2. Island chrome and the left stack root

- [ ] 2.1 Add the shared HUD island chrome (`var(--panel)` fill, `backdrop-filter: blur(9px)`, `var(--line)`, `var(--radius)`, `var(--shadow)`) as a class the island components share, consuming existing tokens only — no token addition, so `styles/tokens.css` stays H1's file untouched
- [ ] 2.2 Rewrite `components/StatusPanel.vue` as the `hud-left` island-stack root: it keeps `data-testid="status-panel"`, drops the boxed `<aside>` chrome, and composes `CharacterHead`, `VitalsTrack` ×3 and `ConditionChips` as separate islands with the anchor's 9px gap
- [ ] 2.3 Redistribute every row the old panel owned so none loses its only home: `magic_level` + `guild_merit` → the head card's rank line; the wallet → the head card; `disguise_active` → the head card marker; the combat session line → the vitals island header; the `無條件` empty state → the conditions island; `atk_phys`/`agility`/`defense` are already rendered in full by the still-mounted `CharacterPanel`
- [ ] 2.4 Vitest: the stack renders three sibling islands, the preserved testids survive, and no row present in the pre-change `StatusPanel` is absent from the client as a whole

## 3. Character head card

- [ ] 3.1 Add `components/character-identity.js`: the five display rank bands (學徒 0–15 / 術師 16–30 / 大師 31–70 / 賢者 71–90 / 主宰 90+) scanned in order, thousands-grouped copper formatting, and the portrait glyph derived as the first Unicode grapheme of `status.actor.name`
- [ ] 3.2 Add `components/CharacterHead.vue`: the glyph portrait tile with the `magic_level` numeric badge, the display name from `status.actor.name`, the rank line (`魔階·<title>` plus `公會 <rank> · 功績 <merit>` from `character.guild`), the wallet line from `character.wallet`, and the `目前有偽裝` marker when `status.disguise_active` is true
- [ ] 3.3 Render no race, subrace, class, or faction line and no `<img>` in the portrait tile; an empty actor name renders an empty tile rather than a substitute character
- [ ] 3.4 Vitest: all five rank-band boundaries plus the two edge cases (level 0 → 學徒, level 90 → 賢者, matching `world/rules/progression.py::MAGIC_RANK_BANDS`'s documented overlap resolution)
- [ ] 3.5 Vitest: an active disguise whose `displayed` rows carry `magic_level` leaves the head card's badge and rank line on the **true** trait value
- [ ] 3.6 Storybook story with deterministic offline args: each rank band, guild joined vs. `未加入公會`, disguise on/off, a zero wallet, and a long name that must ellipsize

## 4. Vitals with the trailing damage bar

- [ ] 4.1 Add `components/vitals.js`: the per-gauge ratio, the low predicate at the pinned 25% display threshold, and the trailing-bar tracking rule (hold the previous committed ratio of the same gauge; reset to current on an epoch change)
- [ ] 4.2 Add `components/VitalsTrack.vue`: one row per gauge with an inline SVG icon, its Traditional Chinese label (生命 / 魔力 / 耐力), the `current / maximum` numerals carrying the preserved `status-panel__gauge-value--<key>` testid, and a `.track` holding the trailing bar and the fill
- [ ] 4.3 Give the trailing bar the draft's delayed transition so it lags the fill on damage and is overtaken on heal; mark it `aria-hidden` with no accessible name
- [ ] 4.4 Give the SP fill the diagonal stripe texture instead of the highlight sheen so it is distinguishable from HP and MP without colour
- [ ] 4.5 Render the low state as the `.vital.low` recolour **plus** an explicit `危險` text marker, and bind `elosern-hp-pulse` to the HP fill on the low row — the keyframe H1 shipped unreferenced
- [ ] 4.6 Vitest: a damaging revision leaves the trailing bar behind the fill and a healing revision does not; the trailing bar only ever holds a previously committed ratio of its own gauge; an epoch change resets it
- [ ] 4.7 Vitest: the numerals render at every value so nothing is colour-only, and the low marker is text rather than colour
- [ ] 4.8 Storybook story: full / damaged / low / empty, each of hp/mp/sp, and a reduced-motion variant

## 5. The low-HP state reaches H1's stage hook

- [ ] 5.1 Add the derived `view.vitals` slice to `stores/elosern.js` (the three ratios plus `lowHp`), computed from the committed `status.resources` alone with no new payload field and no server call
- [ ] 5.2 Pass `lowHp` from `AppClient.vue` to `AppShell.vue`, and forward it from `AppShell.vue` onto `HudFrame`'s already-declared `lowhp` prop — one prop declaration and one attribute binding, no structural edit to the frame
- [ ] 5.3 Vitest: crossing the threshold downward sets the stage's `data-lowhp`, crossing upward clears it, and an unavailable `status` panel leaves it false rather than true-by-default
- [ ] 5.4 Vitest: `store.view.vitals` is derived only from `status.resources`, and building it mutates no other slice

## 6. Condition chips

- [ ] 6.1 Add `components/ConditionChips.vue`: one chip per `status.conditions[]` entry pairing a per-severity shape glyph (`▲` beneficial, `◆` informational, `▽` warning, `▼` harmful, `✕` critical) with an accessible name carrying the label, the remaining duration and every derived modifier
- [ ] 6.2 Render the duration badge only when the payload supplies `remaining_seconds`, show that integer verbatim, and add no client-side countdown timer of any kind
- [ ] 6.3 Add the focus/hover detail line inside the island so a sighted pointer user reads the label, duration and modifier text that the icon-only chip moves into the accessible name
- [ ] 6.4 Cap visible chips at 6 and render the remainder behind a `+N` chip that discloses them in a bounded, scrollable region inside the island, collapsing on re-activation or Escape; record in the change that H4 re-points this control at the character-status drawer
- [ ] 6.5 Keep the `無條件` empty state as explicit text
- [ ] 6.6 Vitest: `warning` and `harmful` are distinguishable with colour removed; a condition without `remaining_seconds` renders no badge; the badge value does not change between revisions without a new payload; the overflow disclosure reveals every remaining condition
- [ ] 6.7 Storybook story: none / one / six / thirty-two conditions, each severity, with and without durations and modifiers

## 7. The minimap island

- [ ] 7.1 Re-chrome `components/LocalMap.vue` as an island — the shared island chrome, the draft's top-meta line carrying the payload `title`, and the bounded canvas — **keeping the `.local-map` root class** that H1's combat-hide CSS and focus-rescue map select on
- [ ] 7.2 Add the renderer-axis orientation legend (`北↑`) on the `grid` and `wilderness` layers only, and omit it entirely on the coordinate-free `instance` and `interior` layers; render no bearing, no degrees and no distance
- [ ] 7.3 Size the canvas so it fits inside the island rather than scrolling the island, keeping the legend, the remembered list and the detail line non-overlapping below it
- [ ] 7.4 Move the `LocalMap` mount in `AppClient.vue` from the `#panel-left` slot to `#panel-right`, beneath H1's top-meta pill, leaving the `@move` wiring and `explore.move` submission untouched
- [ ] 7.5 Ship no full-map control on the island: `MapOverlay` is unmounted until H5, and a control that opens nothing is worse than an absent one
- [ ] 7.6 Vitest: the rendered root still carries `.local-map`; the orientation legend appears for `grid`/`wilderness` and is absent for `instance`/`interior`; no rendered text contains a degree sign or a distance
- [ ] 7.7 Update `stories/World/LocalMap.stories.js` for the island chrome across all four layers

## 8. Manifest, showcase gate, and deferred surfaces

- [ ] 8.1 Add `Data/CharacterHead`, `Data/VitalsTrack`, `Data/ConditionChips` to `component-manifest.json`, taking H1's frozen 29 to 32; do not re-add H1's frozen-set growth requirement, which already governs this
- [ ] 8.2 Update `tests/overlays/deferred_surfaces_absent.test.js`: the frozen count moves 29 → 32, and the assertion is extended to name the companion strip the draft draws inside this island stack, the race/subrace/class/faction head-card line, and any minimap bearing or distance
- [ ] 8.3 Run `npm run build-storybook` and `npm run showcase-coverage`; both must pass with the extended set

## 9. Browser acceptance and re-map

- [ ] 9.1 Re-map `test_browser_shell.py` off `.status-gauge__value` / `.status-gauge__bar` / `.local-map` onto the island `data-testid` hooks, keeping the numeric current/maximum assertion exactly as it stands
- [ ] 9.2 Re-map `test_browser_local_map.py` off `.local-map__lattice`, `.local-map__node`, `.local-map__marker--current`, `.local-map__actionable` and `.status-panel` onto `data-testid` hooks, and rewrite `test_minimap_content_stays_inside_its_pane` as the island assertion: the canvas, the legend, the remembered list and the detail line stay inside the island and do not overprint each other at both viewports
- [ ] 9.3 Re-map `test_browser_combat.py`'s `status-panel__conditions` `inner_text` assertion onto the chip's accessible name / detail line, so the seeded poisoned buff's `agility` and `-10%` stay proven present
- [ ] 9.4 Re-map `test_browser_layout.py`'s `COMPONENT_SELECTORS["local-map"]` off the literal `.local-map` class onto the island's `data-testid`
- [ ] 9.5 Add a browser assertion that the left island stack, the minimap island, the narrative caption and the dock do not intersect at **both** 1440x900 and 1280x720, with the condition overflow disclosed and `ArtPanel` present
- [ ] 9.6 Re-run the existing combat assertion that the minimap is absent in combat and present in exploration — unchanged, as the end-to-end proof that the re-chrome kept H1's matrix intact
- [ ] 9.7 Confirm `test_vue_transport_mount.py` needs no edit: its `status-panel__gauge-value--*` hooks are preserved

## 10. Gates and handoff

- [ ] 10.1 `npm test`, `npm run build`, `npm run build-storybook`, `npm run showcase-coverage` green
- [ ] 10.2 `node --test web/static/webclient/js/tests/*.test.js` green (the preserved `local_map` render model and its dependency-free gate are asserted not broken)
- [ ] 10.3 `uv run --locked python -m tools.spec_traceability check` green; new requirements carry `@covers_requirement` annotations
- [ ] 10.4 `openspec validate webclient-hud-02-status-islands --strict` passes
- [ ] 10.5 Rebuild `web/static/webclient/app/dist` and verify the running client at both supported viewports
- [ ] 10.6 Flip the roadmap's H2 Status cell to `Done`
- [ ] 10.7 Record the H4 hand-offs in the change: the `+N` chip's target becomes the character-status drawer, and the four remaining wallet copies (`CharacterPanel`, `ShopPanel`, `LoreDrawer`, `InventoryPanel`) are removed when those surfaces move into drawers
