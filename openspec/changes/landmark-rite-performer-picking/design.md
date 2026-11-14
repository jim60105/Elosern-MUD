# Design

## Context

Approved interface: design §12.2 "Rite panel" and the prototype `docs/design/landmark-rites/LandmarkRitesPrototype.vue` (`targeting`, `onTargetPointer`, `stepPerformer`) and `RitePanel.vue` (`canSwitch`, the hint, the capture-phase arrow handler). Port that behaviour.

Existing code, read on 2026-11-14:

- `CompanionLineup.vue` accepts `targeting`: `null`, or `{lit, selectable, selected}`, three `Set`s of `String(identity)`. It emits `target-pointer(identity, "hover" | "activate")`. A slot's `identity` is the member's dbid; the controlled figure's slot has `isControlled`.
- `AppClient.vue`: `controlledFigureId` (the controlled slot's identity), `renderedLineup`, and the line-up bindings `:targeting="targeting"` and `@target-pointer="onTargetFigure"` used by the combat stage target step. Combat and the rite stage are mutually exclusive (the rite stage exists only in exploration mode).
- `stores/elosern/rite.js` and `composables/use-rite-stage.js` (`landmark-rite-stage`): `performRite(optionKey, memberId)`, `view.rite`, `performer` (always the first row).
- `components/rite/rite-model.js`: `ritePerformers(rite)` -> rows `{id, memberId, name, self}` with `id` `"self"` for the first row, else `String(member_id)`.

## Goals / Non-Goals

**Goals**

- Performer picking by pointer and by keyboard, with one source of truth in the store.

**Non-Goals**

- No server, panel or content change. No edit of `CompanionLineup.vue`, `ChoiceCard.vue` or the combat target step.
- No picking of a body the panel does not list. The action still re-validates.
- No persistence of the pick across stage entries.

## Decisions

### D1. Store (`stores/elosern/rite.js`)

Add `performerId` (default `"self"`) to the group's state and to `view.rite`, and:

- `canSwitchRite()` (also published as `view.rite.canSwitch`): `panel.performers.length > 1 && panel.options.some((o) => o.companion)`.
- `pickRitePerformer(id)`: allowed only when `phase === "stage"`, `canSwitch`, not `pending`, not `playing`, and `id` is the `id` of a row of `ritePerformers(panel)`; sets `performerId`.
- `stepRitePerformer(delta)`: same guards; moves to the next or previous row, wrapping.
- `approachRite()` additionally sets `performerId = "self"`.
- On every committed state: if `performerId` is not a row of the current panel, or `canSwitch` is false, set `performerId = "self"`.
- `performRite(optionKey)` now takes no member argument: it sends `member_id` of the picked row (`null` for the first row), and refuses (returns false, sends nothing) when the picked row's `self` flag is false and the option's `companion` is false. The `self` flag is the panel row's `owner` flag (`ritePerformers`), not "is the first row": a possessed companion in the first row is not `self`.

### D2. Composable (`composables/use-rite-stage.js`)

- `performer`: the row of `ritePerformers(rite)` whose `id` is `view.rite.performerId` (fallback: the first row).
- `canSwitch`: `view.rite.canSwitch && panelShown`.
- `hovered`: a local ref of a line-up identity or `null`; cleared on activation, on pointer leave and whenever `panelShown` becomes false.
- `targeting({controlledId})`: a function returning the line-up input. Map a performer row to a line-up identity with `figureId(row) = row.self ? String(controlledId) : row.id`.
  - playing or pending: `{lit: Set([figureId(performer)]), selectable: Set(), selected: Set()}`;
  - `canSwitch`: `{lit: Set([figureId(performer), hovered?]), selectable: Set(all rows' figureId), selected: Set([figureId(performer)])}`;
  - otherwise `null`.
- `onFigure(identity, action, {controlledId})`: ignore an identity that is not a row's `figureId`; `"hover"` sets `hovered`; `"activate"` calls `store.pickRitePerformer(rowId)` and clears `hovered`.
- `step(delta)` calls `store.stepRitePerformer(delta)`; `perform(key)` calls `store.performRite(key)`.

### D3. `AppClient.vue`

- Line-up `:targeting`: `riteStage.onStage.value ? riteStage.targeting({controlledId: controlledFigureId.value}) : targeting`.
- Line-up `@target-pointer`: on the rite stage call `riteStage.onFigure(identity, action, {controlledId: controlledFigureId.value})`, else `onTargetFigure(identity, action)`.
- Add `@pointerleave` on the line-up's wrapper in the `#actor-left` slot (a native listener on the component root) that clears the rite hover.
- `RitePanel`: pass `:can-switch="riteStage.canSwitch.value"` and `@step-performer="riteStage.step"`.

### D4. `RitePanel.vue`

Add prop `canSwitch` (boolean, default false) and emit `step-performer(delta)`.

- Header: when `canSwitch`, append the hint `點立繪或 <kbd>←</kbd><kbd>→</kbd> 換人` with the prototype's `.rite-panel__performer-hint` styles.
- A capture-phase `keydown` listener on the panel's root (the prototype's `onKeydownCapture`): when `canSwitch` and no Ctrl, Alt or Meta is held, ArrowLeft emits `step-performer(-1)` and ArrowRight emits `step-performer(1)`, each with `preventDefault()` and `stopPropagation()`. Without `canSwitch` the keys pass through untouched.
- The card's `view-key` already depends on the performer, so the rows re-render when the performer changes; the card keeps focus.

### D5. Stories

Add to `stories/World/LandmarkRite.stories.js`: `PanelSwitchable` (two performers, the hint shown) and update `PanelCompanion` to pass `canSwitch`.

### D6. Tests

- `tests/rite/store.test.js`: `canSwitch` true only with two performers and a companion option; `pickRitePerformer` and `stepRitePerformer` (wrapping in both directions) and their refusals outside the stage, while pending and for an unlisted id; `approachRite` resets the pick; a snapshot that drops the picked performer resets the pick; `performRite` sends the picked `member_id`; a companion pick with a solo-only option sends nothing.
- `tests/rite/surfaces.test.js`: with `canSwitch` the hint renders and ArrowLeft / ArrowRight emit `step-performer` with -1 / 1 and do not reach the card (the active row does not change); without it no hint renders and the arrows emit nothing.
- `tests/app_client_rite.test.js` with a synthetic panel of two performers and one companion option: on the stage the two figures are selectable and the controlled one is selected; activating the companion's figure changes the header name, disables the solo-only row and moves the selection; ArrowRight from the panel steps to the next performer and wraps; picking the companion option sends `member_id` equal to the companion's id; during playback only that figure is lit and no figure is selectable; re-entering the stage shows the controlled character again; with one performer, or with no companion option, no figure is selectable and no hint is shown.

### D7. Agent guide

Add two sentences to the rite paragraph of `web/webclient-app/AGENTS.md`: performer picking reuses the line-up's targeting input, and when it is offered.

## Risks / Trade-offs

- The line-up's targeting input now has two owners, selected by stage. They cannot be active together; the app-level test asserts the rite targeting is `null` outside the rite stage by checking a combat stage target test still passes.
