## Context

`docs/design/elosern-redesign/index.html`'s internal `<style>` block gives exact rules for every
element this change adds (confirmed by direct read of the draft's stylesheet, not inferred from the
rendered screenshot):

```
details>summary{...padding:11px 14px;font-size:13.5px;color:var(--paper-100);display:flex;align-items:center;gap:9px}
details>summary .tw{margin-left:auto;color:var(--paper-500);transition:transform .2s}
details[open]>summary .tw{transform:rotate(90deg)}
details.cat>summary .cnt{margin-left:auto;font-family:var(--f-mono);font-size:11px;color:var(--paper-500)}
details.cat>summary .lab{color:var(--gold-400);font-weight:600}
.grp{font-size:10.5px;letter-spacing:.08em;color:var(--paper-500);margin:11px 2px 3px;display:flex;align-items:center;gap:7px}
.grp .dot{width:7px;height:7px;border-radius:2px}
.grp .line{color:var(--seal-400)}
.srow .cost{margin-left:auto;font-family:var(--f-mono);font-size:11px;color:var(--vit-mp)}
.srow .cost.sp{color:var(--vit-sp)} .srow .cost.free{color:var(--paper-500)}
.srow .ooc{font-size:9px;letter-spacing:.04em;color:var(--ok);border:1px solid rgba(112,150,122,.5);border-radius:4px;padding:0 4px;margin-left:8px}
.srow .prf{font-family:var(--f-mono);font-size:10px;color:var(--paper-700);margin-left:8px}
```

`tokens.css` already defines every custom property these rules reference:
`--paper-100/500/700`, `--gold-400`, `--seal-400/500`, `--vit-mp` (`#5c86dd`), `--vit-sp` (`#d8a83e`),
`--ok` (`#70967a`, `#4d9e6a` under the `:root[data-colorblind="on"]` override — this codebase has no
separate dark-mode block, only the colourblind one). The draft's three sampled element dots
(`style="background:#cf4444"` fire, `#5c86dd` water, `#c79a4a` wind — read directly from
`index.html:894/898/901`) are byte-exact matches of the default-palette `--seal-500` (`#cf4444`),
`--vit-mp` (`#5c86dd`), and `--warn` (`#c79a4a`) respectively — confirming the draft itself reuses the
existing token set for element dots rather than a dedicated palette, and giving this change existing
tokens to reuse for exactly the three elements it has evidence for. Using the token names (not the
draft's literal hex) is deliberate: `tokens.css:139-148`'s colourblind override redefines `--vit-mp` to
`#3a6fc4` and `--warn` to `#e2a03c` (`--seal-500` is not overridden), so referencing the tokens lets the
existing colourblind accessibility path apply to these dots too, at the cost of the hex match being
exact only in the default palette — the correct trade-off, not a discrepancy to fix.

`world/lore/elements.py`'s `ELEMENT_REGISTRY` defines eight elements (`fire`, `water`, `wind`, `earth`,
`lightning`, `ice`, `light`, `dark`); the design draft's `#dr-skill` markup only ever instantiates
`fire`/`water`/`wind` rows. The other five have no colour evidence anywhere in the draft or its
companion `REDESIGN.md`.

## Goals / Non-Goals

**Goals:**
- Match the draft's row/category visual language (chevron rotation, dot, cost colour-coding, OOC pill
  styling, passive badge, legend) using only tokens `tokens.css` already defines. The category count is
  a flattened total of the category's own skill rows, not a byte-exact reproduction of the draft's
  per-category qualifier text (`8 元素 · 87`, `7 線 · 已解鎖 21`) — the draft's "已解鎖" unlock-progress
  figures have no backing field in the character payload, so this change renders the plain count it can
  honestly compute and leaves the richer qualifier text out rather than inventing it.
- Keep every visual addition non-color-only: the count is a digit (not a colour cue), the chevron is a
  shape (rotation, not a colour swap), the cost colour pairs with the resource unit already in the cost
  text (`mp`/`sp`/`免費`), the OOC pill and the passive badge each carry their own text.

**Non-Goals:**
- No dot colour for `earth`/`lightning`/`ice`/`light`/`dark` groups. Inventing five colours the design
  never specified would be exactly the kind of fabrication the `webclient-component-showcase` spec's
  truthful-data-scope rule forbids applied to *presentation* choices, not just data — a colour with no
  design source is as invented as a field with no payload source. These groups render their label with
  no dot, which is a strictly additive future change (seed the map further) whenever a source for those
  colours exists, not a regression from today (today no group has a dot at all).
- No change to `SkillBook.vue`'s data flow, props, or the fields it consumes — this change is styling
  and small template additions over data `fix-webclient-skillbook-descriptor-data` already serializes
  and `SkillBook.vue` already receives.
- No change to the drawer chrome around `SkillBook.vue` (title, subtitle, tabs, search icon, footer) —
  that is `fix-webclient-skillbook-drawer-chrome`'s scope, a different set of files
  (`HudDrawer.vue`/`AppClient.vue`) with no overlap here.
- No freeform-scale ("威力") row styling changes. The draft's `#dr-skill` example rows never show a
  freeform-scale cell inline (only the combat detail pane does, per `SkillDetailPane.vue`'s own D14
  scope note), so there is no design evidence to style against; `SkillBook.vue`'s existing `castText()`
  rendering is left exactly as-is.

## Decisions

- **The element-dot colour map lives as a small local object in `SkillBook.vue`
  (`{ fire: "var(--seal-500)", water: "var(--vit-mp)", wind: "var(--warn)" }`), not in `tokens.css` as
  new named tokens.** The three colours are already named tokens; adding second names
  (e.g. `--element-fire`) for values that already have a name would be indirection with no benefit, and
  keeping the map local and visibly three-entries-long makes the "only what the draft samples" scope
  decision legible in the code, not just in this doc.
- **`sexual_act` gets a uniform dot (`var(--seal-500)`), keyed off `category`, not `group`.** The draft's
  `#dr-skill` sexual-act section shows the same `--seal-500` dot in front of every one of its line
  groups (獨處/關係/戰鬥) — a category-level rule, not a per-group lookup like the elemental map.
- **The chevron uses the native `<details>`/`<summary>` `open` attribute plus a CSS transform, not a
  Vue-tracked open/closed ref.** `SkillBook.vue` already renders each category as a plain
  `<details>`/`<summary>` pair with no JS-tracked open state (`:open="index === 0"` sets only the
  initial state); the draft's own `details[open]>summary .tw{transform:rotate(90deg)}` rule is a pure
  CSS selector against the native attribute, so no new reactive state is needed — the browser already
  toggles `open` on click/Enter/Space, and CSS reacts to it.
- **The cost colour is chosen by resource key present, matching `.cost.sp`'s override precedence.** The
  draft's CSS cascade means a row with both `mp` and `sp` gets the `.sp` (later, more specific)
  colour — this proposal's `costColorClass(row)` helper mirrors that: `sp` in cost → `--vit-sp`; else
  `mp` in cost → `--vit-mp`; else (empty cost) → `--paper-500`.

## Risks / Trade-offs

- **A future content addition to `earth`/`lightning`/`ice`/`light`/`dark` groups will render with no dot
  while `fire`/`water`/`wind` groups have one, reading as visually inconsistent.** → Accepted: an
  inconsistent-but-honest render is preferable to an invented colour; the map is a three-line object,
  trivially extended the moment a real source (an updated design draft, or an explicit product decision)
  supplies the other five colours.
- **The legend's copy is authored UI text living in the component, not sourced from any payload or i18n
  table this codebase has today.** → This matches how every other static client-local UI string in
  `SkillBook.vue` already works (tab labels, search placeholder, the "沒有符合的技能" empty state) —
  no new pattern, no new maintenance burden beyond what already exists.

## Migration Plan

Not applicable — 0 released users, purely a view-layer styling change with no persisted state or OOB
schema involved.

## Open Questions

None outstanding.
