## Why

This is change **H2** of the WebClient Contextual HUD Redesign, governed by
`docs/superpowers/specs/2026-08-25-webclient-hud-redesign-roadmap-design.md` (depends on: **H1**,
`webclient-hud-01-shell-and-scene`, which is landed and archived).

H1 replaced the three-column grid with the cinematic stage and its named anchors, and it re-homed the
existing panels into those anchors **with their own chrome untouched** — so today the `hud-left`
anchor holds a boxed `<aside class="status-panel">`, a boxed `<aside class="local-map">` and a boxed
`<aside class="art-panel">` stacked like column cards on a stage that was built for floating islands.
H1 also shipped the low-HP machinery it deliberately could not drive: `HudFrame.vue` declares a
`lowhp` prop defaulting to `false`, its `[data-lowhp="true"]` selector swaps `--vignette` for
`--vignette-lowhp` on the stage vignette, and `tokens.css` carries the `elosern-hp-pulse` keyframe
bound to nothing at all. `AppShell.vue` does not yet forward the prop, because the low-HP state is
derived from the `status` payload and H1 carried no `status` dependency (H1 D7).

H2 supplies that chrome and that state. It is the wave that turns the draft's left HUD island stack
into real components — the character head card, the vitals with their trailing damage bar, the
condition chips — and re-chromes the minimap as the right-anchor island under the top-meta pill. It
runs parallel to H3 (roadmap §6: `H2 ∥ H3`, disjoint component sets).

It is also the wave that confronts the draft's two unbacked HUD claims head-on. The draft's character
card prints 種族(亞種) / 職業 / 拾荒者同盟, and its minimap prints a bearing line 「北 324° · 西 262°」.
Neither has a read model: the `character` payload carries `traits`, `actives`, `passives`,
`equipment`, `disguise`, `guild`, `wallet`, `persona.background` and nothing else
(`web/webclient/presentation/character.py:229-321`), and `local_map` node `x`/`y` are declared
*renderer-local presentation geometry, not canonical world coordinates*
(`openspec/specs/webclient-local-map/spec.md:17`). Both are dropped rather than mocked, per roadmap
§2.4 and §5's truthful-data rule.

## What Changes

- **The left anchor becomes a stack of floating islands.** `StatusPanel.vue` is re-chromed from one
  boxed column card into the island-stack root — translucent `--panel` fill, `backdrop-filter:
  blur(9px)`, `--line` hairline, `--radius`, `--shadow`, bounded width — composing three new
  components: `CharacterHead.vue`, `VitalsTrack.vue` and `ConditionChips.vue`. It keeps
  `data-testid="status-panel"` and the three `status-panel__gauge-value--{hp,mp,sp}` hooks so the
  combat and transport-mount browser journeys need no edit.
- **The character head card renders only backed identity.** A glyph portrait tile (the actor is never
  a focusable subject of their own exploration catalog — `world/rules/art_view.py:176` — so there is
  no image to render and none is invented), a numeric badge from `character.traits.magic_level`, the
  display name from `status.actor.name`, the derived magic-rank title, the guild rank and merit from
  `character.guild`, the wallet from `character.wallet`, and the `status.disguise_active` marker as
  explicit text. **No race, subrace, class, or faction line is rendered at all.**
- **Vitals gain icons, numerals and a trailing "ghost" bar.** Each of hp/mp/sp renders an icon, its
  Traditional Chinese label and `current / maximum` numerals above a `.track` holding a trailing bar
  (delayed behind the fill, so damage taken is visible as the gap) and the fill. SP's fill carries a
  diagonal stripe texture instead of the highlight sheen, so it is distinguishable from HP and MP
  without colour. A vital at or below the display threshold takes the `.vital.low` recolour **and** an
  explicit 「危險」 text marker.
- **The low-HP state is supplied to H1's hooks.** A new `view.vitals` store slice derives the low-HP
  boolean from the committed `status.resources.hp` ratio against one display-only threshold and feeds
  `HudFrame`'s existing `lowhp` prop through `AppShell`, lighting the red stage vignette; the same
  boolean reaches `VitalsTrack`, which finally binds the orphaned `elosern-hp-pulse` keyframe to the
  HP fill. No server field is read or invented; the numerals and the text marker carry the
  information, the colour and the motion only reinforce it.
- **Conditions become icon chips.** One chip per `status.conditions[]` entry, each pairing a
  per-severity shape glyph (`▲` beneficial, `◆` informational, `▽` warning, `▼` harmful, `✕` critical)
  with an accessible name carrying the label, the remaining duration and every derived modifier, plus
  a duration badge rendered **only** when the payload supplies `remaining_seconds` and never counted
  down client-side between revisions. Chips past the visible cap collapse into a `+N` chip that
  discloses the remainder inside the island.
- **The minimap moves to the right anchor and becomes an island.** `LocalMap.vue` is re-chromed in
  place — no new component — beneath H1's top-meta pill, with the draft's island top-meta line
  carrying the map title and a **renderer-axis orientation legend** (`北↑`) on the coordinate-bearing
  `grid` / `wilderness` layers only. No bearing, no distance, no compass degrees. The combat hide is
  already specified by H1's mode × surface matrix and already implemented against the literal
  `.local-map` root class (in `HudFrame.vue`'s CSS and `AppShell.vue`'s `HIDDEN_BY_MODE` focus-rescue
  map), so H2 keeps that class as the island's root and only satisfies the rule — it re-specifies
  nothing.
- **The HUD becomes the single persistent wallet surface.** Today the wallet is printed five times
  (`StatusPanel`, `CharacterPanel`, `ShopPanel`, `LoreDrawer`, `InventoryPanel`). H2 retires the
  `StatusPanel` copy into the head card; the four drawer-bound copies are an explicit H4 hand-off.
- **BREAKING (test-facing only):** the status and local-map class selectors move. The
  `status-panel__gauge-value--*` testids and every `local-map` `data-testid` hook are preserved
  byte-identical; the class-literal selectors are re-mapped to `data-testid` in this change.

## Capabilities

### New Capabilities

None. H2 introduces no new capability: its behaviour belongs to `webclient-contextual-hud`, the
capability H1 created and archived, and is delivered as `## ADDED Requirements` against that existing
capability. None of H1's five landed requirements is modified — in particular H2 does **not** restate
the mode × surface matrix that already specifies the combat minimap hide, nor the drawer/overlay stage
recession; it satisfies both.

### Modified Capabilities

- `webclient-contextual-hud` (**ADDED**, not modified): the left island stack and its chrome; the
  backed-identity-only character head card; the vitals track with its trailing damage bar and
  never-colour-only low state; the low-HP stage state; the condition chips with their severity glyph,
  duration badge and bounded overflow disclosure; the minimap island and its truthful orientation
  legend.
- `webclient-local-map`: the browser-minimap requirement currently pins the renderer to a **pane that
  scrolls** (`spec.md:122`) and forbids map content overlapping "other pane content". An island is
  bounded and scrolls no column, so the requirement is re-expressed for the island — still
  non-overlapping, still not colour-only, still lattice-based, but bounded to the island and with the
  canvas scaling down rather than the island scrolling a required surface out of view. The orientation
  legend's truthfulness rule is added to the same requirement.
- `webclient-component-showcase`: the status/character surface requirement is re-expressed for the
  island form — gauges pair an icon, a label and numerals; conditions pair a shape glyph with an
  accessible name carrying label, duration and modifiers plus a bounded overflow disclosure; the head
  card renders only backed identity with no race/class/faction line; the wallet has one persistent
  surface. The **frozen-set growth rule H1 added is not re-added**; H2 extends the manifest under it.
  The component-enumeration requirement is left untouched: `StatusPanel` keeps its listed role as
  "the status panel with its gauges, counters, and conditions", now as the island-stack root.
- `webclient-status-presentation`: **no delta.** It is a pure server-side data/derivation contract —
  payload shape, canonical-true resources, matched-modifier conditions, mode derivation, no-mutation
  discipline — with no DOM pin and no presentation geometry anywhere in its text. H2 changes only how
  the browser draws that payload, so nothing in it becomes false. It is named here explicitly so the
  omission reads as a decision rather than an oversight.

## Impact

- **New:** `web/webclient-app/components/CharacterHead.vue`, `VitalsTrack.vue`, `ConditionChips.vue`;
  the pure derivation modules `components/vitals.js` (ratio, low predicate, trailing-bar tracking) and
  `components/character-identity.js` (the five display rank bands, copper grouping, portrait glyph);
  their Storybook stories and Vitest suites; three `component-manifest.json` entries
  (`Data/CharacterHead`, `Data/VitalsTrack`, `Data/ConditionChips`), taking the frozen set from H1's
  29 to 32, with the matching `webclient-component-showcase` extension.
- **Modified:** `components/StatusPanel.vue` (boxed card → island-stack root), `components/LocalMap.vue`
  (boxed card → right-anchor island + orientation legend, keeping its `.local-map` root class),
  `stores/elosern.js` (add the derived `view.vitals` slice), `AppClient.vue` (move the `LocalMap` slot
  from `#panel-left` to `#panel-right`, pass the low-HP state), and two one-line additions to
  `components/AppShell.vue` (a `lowHp` prop forwarded onto `HudFrame`'s existing `lowhp` prop — see
  design D5).
- **Re-mapped browser assertions:** `web/tests/browser/test_browser_shell.py`
  (`.status-gauge__value`, `.status-gauge__bar`, `.local-map`), `test_browser_local_map.py`
  (`.local-map__lattice`, `.local-map__node`, `.local-map__marker--current`, `.local-map__actionable`,
  `.status-panel`, and `test_minimap_content_stays_inside_its_pane` → the island assertion),
  `test_browser_combat.py` (the `status-panel__conditions` `inner_text` modifier assertion → the
  chip's accessible name), and `test_browser_layout.py`'s `COMPONENT_SELECTORS["local-map"]`, which H1
  re-mapped only as far as the literal `.local-map` class. `test_vue_transport_mount.py` needs **no**
  edit — its `status-panel__gauge-value--*` hooks are preserved.
- **Preserved / untouched:** the server, all eight presenters, the action allowlist, the OOB envelope,
  `transport.js`, `bridge.js`, the preserved `js/elosern/*` logic (including the `local_map` render
  model and its Node gate), the keyboard router contract, `explore.move` submission through a node's
  own `exit_ref`, the dependency-free text fallback, and — as a hard constraint, not a courtesy — the
  `.local-map` root class that H1's combat-hide CSS and focus-rescue map both select on.
- **Deliberately not moved:** `CharacterPanel.vue`, `ShopPanel.vue`, `QuestBoard.vue`,
  `LoreDrawer.vue`, `InventoryPanel.vue` stay where H1 put them — they are H4's drawer content
  (roadmap §7), and H2 only stops competing with them for the wallet. `ArtPanel.vue`, which H1 reduced
  to the portrait catalog and left in `hud-left`, is likewise untouched: H1's `webclient-art-panel`
  delta assigns its presentation to H3's participant frame. Both are accounted for in the left stack's
  height budget rather than edited (design D12).
- **Not built (no backing read model, roadmap §2.4):** the companion strip the draft draws inside this
  very island stack, the race/subrace/class/faction line on the head card, and any bearing or distance
  on the minimap. `tests/overlays/deferred_surfaces_absent.test.js` is extended to name each of them
  and its frozen-count assertion moves from 29 to 32.
