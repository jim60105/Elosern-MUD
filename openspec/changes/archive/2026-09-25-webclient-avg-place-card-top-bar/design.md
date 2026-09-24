## Context

See proposal.md (Why). The current state was checked in code. C1, C2, C3, and C4a (`webclient-avg-stage-shell`) are assumed archived first.

- `styles/tokens.css` sets `--header-h: 80px`. `styles/app-shell.css` sets it to `72px` under `(max-width: 1350px)`.
- Consumers of `--header-h`:
  - `app-shell.css`: the header strip `::before`, `.topbar-brand`, `.topbar-right`, the scene backdrop's `top`, `.scene-heading`, the island anchors
  - `DesktopNavigation.vue`: `top: 0; height: var(--header-h)`
  - `OverlayHost.vue`: overlay inset
  - `ToastQueue.vue`: top offset
  - `stories/Core/DesktopNavigation.stories.js`
- `TopBar.vue` renders:
  - the brand (`topbar-title`): the `ELOSERN` wordmark and the tagline `伊洛瑟恩 · 文字構築的另一個世界`, stacked in a column
  - the right cluster: the possession banner, `CharacterSwitcher`, and the meta pill `topbar` with `meta-loc` (`topbar-location`, placeholder `位置：--`), `meta-clock` (`topbar-clock`, placeholder `時間：--`), and `meta-conn` (`connection-state`)

  `AppShell` passes it `locationLabel` / `timeLabel` from `AppClient`'s `store.view.statusSlice`. The store already resolves the location (local_map current-node label, else the status label).
- `DesktopNavigation.vue`'s first button emits `home`. Its label is `探索` or, in combat, `戰鬥`, and it carries `aria-current="page"` while no drawer is open. `AppClient` binds it to `use-dock.js` `onNavigateHome`, which closes any drawer, calls `store.resetFramesToRoot()`, and restores dock focus. Nothing else calls `onNavigateHome`, and no test targets the home button.
- `AppClient.vue`'s `#backdrop` renders `.scene-heading` (eyebrow `探索伊洛瑟恩` / `戰鬥`, `h1` location, `p` time), `v-if` not creation. No test and no spec names it.
- The login-gate requirement "The WebClient uses the real game name in its brand surfaces" requires the top-bar title to show 「伊洛瑟恩」.

## Goals / Non-Goals

**Goals:**
- A 48px top band that carries no location, no time, and no home entry.
- One place card that states location and time, in a fixed-size `place` anchor.
- The 65% stage rule measured and asserted at 1920x1080.

**Non-Goals:**
- The `hud-left` / `hud-right` island contents (C4c). `hud-left` only moves below the place card.
- Changing how the location is resolved. The store's `statusSlice.locationLabel` is unchanged, and only the surface that renders it moves.
- The map overlay's own location title (`OverlayHost`'s `location-label` prop): unchanged.

## Decisions

### D1. Header height is one token at 48px
`--header-h: 48px` in `tokens.css`, and the 1350px media block stops overriding it.

The brand becomes one row: `.topbar-brand { flex-direction: row; align-items: baseline; gap: 10px }`, with the wordmark at 20px and a `span.topbar-tagline` that now reads only `伊洛瑟恩` at 12px serif. The game name stays in the title (login-gate), and the slogan tail is dropped because it cannot fit a 48px row at `--left-column` 216px.

`DesktopNavigation` buttons use `flex-direction: row; gap: 7px; padding: 0 14px; width: auto` with an 18px icon, so they fit 48px.

At `(max-width: 1350px)`, where `--left-column` is 216px, the wordmark drops to 16px with `.2em` tracking and the brand padding to 16px, so the row fits the column without reaching the navigation.

The top-meta pill holds only the connection state, so its two-row grid becomes a plain flex row.

*Alternative:* keep the stacked brand at a smaller font. Rejected: 9px text is below the redesign's smallest chrome step.

### D2. The home entry is deleted, not hidden in exploration only
The design (§4) removes the `探索` tab because it names the screen the player is already on. The combat variant `戰鬥` names the current screen just as much, so the whole button goes.
- Its function (close the drawer, reset the router to the root, focus the dock) is already reachable: Escape closes an open drawer and pops router levels, and the breadcrumb's back control pops one level.
- `onNavigateHome` has no other caller, so it is deleted rather than left unused.
- Drawer nav entries keep `aria-current="page"` for the open drawer.

### D3. The place card is its own component in its own anchor
`PlaceCard.vue` takes props `locationLabel` and `timeLabel` (strings or null) and renders:

```
<section class="place-card hud" data-testid="place-card" aria-label="目前位置">
  <h1 class="place-card__location" data-testid="place-card__location" :title="location">…</h1>
  <p class="place-card__time" data-testid="place-card__time">…</p>
</section>
```

- The placeholders `位置：--` / `時間：--` are unchanged from `TopBar`, so the fallback wording does not change.
- The `h1` moves from the retired `.scene-heading`, so the stage keeps exactly one top-level heading naming the place.
- Truncation uses `white-space: nowrap; overflow: hidden; text-overflow: ellipsis`, and the `h1` text node keeps the full label for assistive technology.
- The card is `height: 100%` of the `place` anchor. `--place-h: 68px` (new token) holds a 20px serif heading and a 12px time line with the island padding.

`AppShell` owns the mount, the same way it owns `NarrativeFeed`, because it already receives `locationLabel` / `timeLabel`. No new AppClient prop is needed, and `TopBar` loses both props.

*Why a new component, not a reshaped `TopBar` fragment:* the card lives in a stage anchor with its own visibility and island chrome, and it has a story of its own. The series' governance rule (C3) lets the AVG wave add it with its manifest title, story, and spec entry in lockstep.

### D4. Anchor geometry
`[data-anchor="place"] { top: calc(var(--header-h) + 16px); left: 16px; width: calc(var(--left-column) - 32px); height: var(--place-h); z-index: 4 }`. It is hidden in creation. `hud-left` gets `top: calc(var(--header-h) + 16px + var(--place-h) + 12px)` and `max-height: calc(100% - var(--header-h) - var(--band-h) - var(--place-h) - 44px)`.

At 1280x720 that leaves `720 − 48 − 16 − 68 − 12 − 260 − 16` = 300px for the island stack. That is 56px less than after C4a, and C4c's compact avatars pay it back (see Risks). `HIDDEN_BY_MODE.creation` gains `[data-anchor='place']` for consistency. The card has no tab stop, so no rescue is ever triggered.

### D5. `.scene-heading` is retired
The place card states location and time. The eyebrow (`探索伊洛瑟恩` / `戰鬥`) is a mode label, which the desktop-shell requirement already forbids in place of location, and the dock and the caption head (`敘述` / `戰鬥日誌`) already identify the mode. All `.scene-heading` markup and CSS is deleted.

### D6. The 65% rule
At 1920x1080: `1080 − 48 − 300.24` = 731.76px (67.8%) ≥ 702px. At 1440x900 the stage box is 592px (65.8%). At 1280x720 it is 412px (57%), below the design goal but not asserted there: the design sets the goal at the 1920x1080 reference and scopes out sub-1600px layouts, and the coordinator kept 1280x720 only as an acceptance viewport for usability and non-overlap. The stage requirement therefore states the rule at 1920x1080 only.

### D7. Spec strategy and archive order
- The stage requirement and the visibility matrix are MODIFIED on C4a's text.
- The desktop-shell requirement is MODIFIED on C4a's text, which itself builds on C3.
- Its scenario titles "The top-meta location names the region, not the raw room key" and "The location falls back when the map panel cannot supply a name" are kept, as `openspec validate` requires, and their bodies now assert the place card.
- The location-resolution rule moves into the new place-card requirement, and the desktop-shell text points to it instead of restating it.
- The showcase enumeration is MODIFIED on C3's text.

**Archive order: C1 → C2 → C3 → C4a (`webclient-avg-stage-shell`) → C4b (this change) → C4c (`webclient-avg-stage-hud-anchors`).** C4c writes its stage and visibility blocks on top of this change's text.

## Risks / Trade-offs

- [The `hud-left` island stack loses 68 + 12px to the place card, while the top bar gives 32px back] At 1280x720 the stack keeps 300px, and C3's populated-stack test (vitals, a harmful condition, two party cells) may not fit until C4c's compact avatars land. → Task 5.2 runs the test. If it fails, the C4a fallback (8px stack gap, compact party cells) applies. C4c then restates the island requirement for the `vitals` anchor with compact avatars.
- [Dropping the slogan changes the brand text] → The login-gate contract only names 「伊洛瑟恩」, which stays. `top_bar.test.js` asserts the title text contains it.
- [Browser tests clicking `.desktop-navigation button` by text] They target 角色狀態 / 任務 / 背包, not the home entry. → Unchanged. Task 4.3 adds a Vitest case that no 探索 / 戰鬥 button exists.

## Migration Plan

None. The client is unreleased.
