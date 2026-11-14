# Design

## Context

Approved interface: `docs/superpowers/specs/2026-11-14-landmark-rites-design.md` §12.2 and the prototype files `docs/design/landmark-rites/RiteArrivalCard.vue`, `RitePanel.vue`, `LandmarkRitesPrototype.vue` (its `.rite-proto__art` and `.rite-proto__place` styles are the backdrop), `LandmarkRites.stories.js`. Port their markup and styles; change only what this design names.

Existing code, read on 2026-11-14:

- `web/webclient-app/components/ChoiceCard.vue`: props `rows`, `viewKey`, `trailingIndex`, `digitRows`, `trapFocus`, `autofocus`, `entrance`, `caption`, `ariaLabel`, `testId`; emits `pick(key)` and `back`. A row is `{key, label, badge, enabled, reason, back, icon, kind, unread, ...}`. The template renders `<div v-if="caption" :class="cls('__caption')" aria-hidden="true">` directly before the rows container.
- `web/webclient-app/components/travel/LandmarkCard.vue`: the existing arrival card. It renders art through `ArtworkPreview` (`:artwork`, `:panel`) and collapses to a quiet ink header when there is no descriptor. The rite arrival card follows the same art handling.
- The `rite` panel shape (`landmark-rite-panel` design D1): `{district: {key, name, landmark, lit}, guardian: {name, form}, art, options: [{key, label, companion}], performers: [{member_id, name, owner}], delivery, seen}`.
- Stories live under `web/webclient-app/stories/<Group>/`; `web/webclient-app/component-manifest.json` lists the required story titles and is checked by `pnpm run showcase-coverage` after `pnpm run build-storybook`.

## Goals / Non-Goals

**Goals**

- Three passive components and one slot, each tested alone with synthetic panel data.

**Non-Goals**

- No store, composable, `AppClient.vue` or `AppShell.vue` edit; nothing mounts the components (`landmark-rite-stage`).
- No performer switching: `RitePanel` shows the performer it is given and emits nothing about switching (`landmark-rite-performer-picking`). The prototype's `canSwitch` prop, switching hint and `step-performer` emit are not ported in this change.
- No scene playback, no return entry.
- No new control style, colour token or font size. Use the tokens the prototype uses.

## Decisions

### D1. `ChoiceCard` header slot

In `ChoiceCard.vue`, directly after the caption element and before the rows container, add:

```html
<div v-if="$slots.header" :class="cls('__header')"><slot name="header" /></div>
```

Style `.choice-card__header` in the component's existing style block: a block row with the card's horizontal padding, a bottom hairline `1px solid rgba(185, 154, 96, 0.18)`, and bottom padding `calc(6px * var(--ui-scale))`. The slot is not `aria-hidden`. A card with no header slot renders exactly as before (no element, no class). Add a `WithHeader` story to `stories/Core/ChoiceCard.stories.js` and one test to `tests/components/choice_card.test.js`: with the slot the header element precedes the rows and the keyboard composite is unchanged (ArrowDown still moves the active row); without it no header element exists.

### D2. Pure model (`components/rite/rite-model.js`)

```js
// The performer rows of a rite panel: {id, memberId, name, self}. id is "self" for the first row (the controlled
// character, member_id null), else String(member_id). self is the row's `owner` flag: only the record owner's own
// body performs in the first person, so a possessed companion in the first row has self false.
export function ritePerformers(rite) { ... }
// The rite panel's ChoiceCard rows for one performer.
export function riteRows(rite, performer) { ... }
export const SOLO_ONLY_REASON = "這個儀式只能親自進行";
export const UNSEEN_LABEL = "尚未體驗";
```

`riteRows` returns, for each option in order, `{key, badge: String(index + 1), label, enabled: !blocked, reason: blocked ? SOLO_ONLY_REASON : null, unread: !blocked && !rite.seen.includes(key)}` with `blocked = !performer.self && !option.companion`, followed by `{key: "leave", label: "退開", icon: "close", kind: "leave", back: true}`.

### D3. `RiteArrivalCard.vue`

Props: `rite` (required object, the panel), `artPanel` (object, default null), `revisit` (boolean, default false), `entrance` (boolean, default true). Emits: `approach`, `leave`.

Port the prototype's template, keyboard handling (Enter approaches, Escape leaves, Tab toggles between the two buttons, a held repeat does nothing, every other key except Space is stopped from bubbling) and styles, with these changes:

- Root keeps `class="choice-card rite-arrival"`, `role="dialog"`, `aria-modal="true"`, `:aria-label="rite.district.landmark"`, and adds `data-testid="rite-arrival-card"`.
- Art: replace the `<img>` with `ArtworkPreview` given `:artwork="rite.art"` and `:panel="artPanel"`, inside the 16:5 band, exactly as `LandmarkCard.vue` mounts it in its own frame. `rite.art` null: the collapsed quiet ink band of the prototype's `is-empty` state and no `ArtworkPreview`.
- Kicker: `地標儀式` when `revisit`, else `抵達地標`; the element carries `data-revisit="true"` or `"false"`.
- District line: `◆ <name>已探明` when `rite.district.lit`, else `◇ <name>尚未探明`, with `data-lit`.
- Experienced line: `已體驗 <rite.seen.length> / <rite.options.length>`, with `data-testid="rite-arrival-seen"`, `data-seen` and `data-total`.
- Buttons: 退開 with `data-testid="rite-arrival-leave"`, 走近 with `data-testid="rite-arrival-approach"`; 走近 takes focus on mount (`preventScroll`).
- `entrance` false adds the class `choice-card--still` to the root so the card shows at rest.

### D4. `RitePanel.vue`

Props: `rite` (required), `performer` (required, a row of `ritePerformers`), `entrance` (boolean, default true). Emits: `perform(optionKey)`, `leave`.

Template: one `ChoiceCard` with `:rows="riteRows(rite, performer)"`, `:view-key="'rite-' + performer.id"`, `:trailing-index="rite.options.length"`, `:digit-rows="rite.options.length"`, `aria-label="儀式"`, `test-id="rite-panel"`, `trap-focus`, `autofocus`, `:entrance`, `@pick` -> `leave` for the key `leave` else `perform(key)`, `@back` -> `leave`. In its `header` slot:

```html
<p class="rite-panel__performer" aria-live="polite">
  <span class="rite-panel__performer-label">執行者</span>
  <span class="rite-panel__performer-name">{{ performer.name }}</span>
</p>
```

Use the prototype's `.rite-panel__performer-label` and `.rite-panel__performer-name` styles. Drop the prototype's absolute positioning and its `padding-top` override on `.choice-card`: the header slot of D1 places the line. Keep the root `.rite-panel` wrapper only if the width rule (`min(100%, calc(560px * var(--ui-scale)))`) needs it.

The not-yet-experienced mark is `ChoiceCard`'s existing `unread` row pip. Its accessible text must say `尚未體驗`: if `ChoiceCard` hard-codes the unread text, add an optional `unreadLabel` string prop to `ChoiceCard` whose default is the current text, and pass `UNSEEN_LABEL`; change nothing else about unread rows.

### D5. `RiteBackdrop.vue`

Props: `rite` (required), `artPanel` (object, default null). No emits, no interaction (`aria-hidden="true"` on the art; the plate is text).

Template: a full-bleed container (the prototype's `.rite-proto__art`, renamed `.rite-backdrop`) holding `ArtworkPreview` (`:artwork="rite.art"`, `:panel="artPanel"`) sized to cover when `rite.art` is not null, the ink wash overlay, and the plate `.rite-backdrop__plate` with the text `<landmark>・<guardian name>` preceded by a decorative `◆` (`aria-hidden`). `rite.art` null: the class `is-empty`, the quiet ink gradient and no `ArtworkPreview`. `data-testid="rite-backdrop"`.

### D6. Stories and fixtures

`stories/fixtures/rite.js`: `ritePanel(overrides)` returning a valid synthetic panel (synthetic names; two options, the first with `companion: true`, the second `false`; `seen: []`; `art: null`; one performer), plus `ritePanelWithArt()` using an artwork descriptor built with the helpers of `stories/fixtures/art_panels.js` over a bundled scene image, as `stories/World/WildernessTravel.stories.js` builds its landmark artwork.

`stories/World/LandmarkRite.stories.js`, title `World/LandmarkRite`: `ArrivalCard`, `ArrivalCardLit`, `ArrivalCardNoArt`, `ArrivalCardRevisit`, `Panel`, `PanelExperienced` (first option in `seen`), `PanelCompanion` (a companion performer: the solo-only row disabled with its reason), `PanelThreeOptions`, `Backdrop`, `BackdropNoArt`. Each renders the component alone in a frame sized like the `choices` anchor (cards) or the stage (backdrop). Add `"World/LandmarkRite"` to `component-manifest.json`.

### D7. Tests (`tests/rite/surfaces.test.js`, Vitest, `@vue/test-utils` `mount`)

- `rite-model`: `ritePerformers` ids and the `self` flag (true for an `owner` row, false for a first row whose `owner` is false); `riteRows` for the controlled character (both enabled, unread only for unseen keys) and for a companion (the `companion: false` row disabled with `SOLO_ONLY_REASON` and not unread).
- `RiteArrivalCard`: the lit and unlit district line and `data-lit`; both kickers; the experienced count from `seen` and `options`; Enter emits `approach` once and a repeated Enter emits nothing; Escape emits `leave`; clicking each button emits its event; Tab moves focus between the two buttons and never leaves the card; 走近 is focused after mount; no artwork descriptor renders no `ArtworkPreview` and the `is-empty` band; the card contains no text of `delivery` lines when the panel carries a delivery.
- `RitePanel`: one row per option plus 退開; digit `1` emits `perform` with the first key; Enter on the active row emits `perform`; Escape and the 退開 row emit `leave`; a disabled row emits nothing on its digit, Enter and click; the header names the performer; the unseen row carries the unseen accessible text and the seen row does not.
- `RiteBackdrop`: the plate text; with and without art.

Synthetic text only. Assert structure, state attributes, `data-testid`s and emitted events; where a test must tell two states apart (lit and unlit, arrival and revisit, seen and unseen) assert that the rendered text differs and that the synthetic names appear, never the literal interface wording.

### D8. Agent guide

Add one paragraph to `web/webclient-app/AGENTS.md` beside the landmark card paragraph: the three rite components, that they read the `rite` panel, and that the card and panel send nothing themselves.

## Risks / Trade-offs

- The components are verified in isolation only. Layout inside the real stage at 1451x790 and 2560x1440 is verified by `landmark-rite-stage`.
