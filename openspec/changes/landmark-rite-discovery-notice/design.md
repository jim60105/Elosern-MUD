# Design

## Context

Design document: `docs/superpowers/specs/2026-11-14-landmark-rites-design.md` §12.2 ("Playback and return") and §12.3. Existing code after the earlier changes:

- `world/rules/landmark_rites.py` `perform_rite`: returns `RiteResult` with `first_completion` and `plan.site` (`district_key`, `district_name`); its `transaction.on_commit` callback stores the receipt and logs `landmark_rite_committed`.
- `web/webclient/actions/rite_actions.py`: `rite_completion_line(result)` builds the one completion line both the browser adapter and the text command send; the adapter's result data carries `first_completion`.
- `web/webclient-app/stores/elosern/rite.js` adopts the action result (`data.delivery`); `composables/use-rite-stage.js` builds `lines` (the guardian's form) for the stage's message window.
- The event name `map_district_discovered` (context `char`, `district`) existed on the movement path until `landmark-rite-lighting` removed it there; the observability catalog already lists it.

## Goals / Non-Goals

**Goals**

- One notice per first completion, on both clients.

**Non-Goals**

- No change to lighting, the record, the panel or the world map component.
- No toast, sound or new component.
- No notice for a repeat, a refusal or a rolled-back rite.

## Decisions

### D1. Server

- `rite_completion_line(result)`: when `result.first_completion`, append a second line `已探明：<district_name>` (joined with `\n`).
- `perform_rite`: in the existing `on_commit` callback, when `first_completion`, also `log_info("map_district_discovered", context={"char": owner.pk, "district": site.district_key})`.

### D2. Browser

- `stores/elosern/rite.js`: add `newlyLit` (boolean) to `view.rite`. On an adopted success result set it to `result.data.first_completion === true`. Clear it in `approachRite`, `leaveRite`, at the start of `performRite`, and in every reset.
- `composables/use-rite-stage.js` `lines`: when `view.rite.newlyLit` and no scene is playing, append `{kind: "out", text: "◆ " + rite.district.name + "的地圖亮了起來。", seq: 2}` after the guardian's form.

### D3. Documentation

- `docs/game/command-reference.md`: the `rite` entry gains one sentence: the first rite completed at a landmark explores its district on the map.
- `docs/development/map-panel-protocol.md`: state that the exploration announcement follows the first completed rite.

### D4. Tests

Assert structure, never the literal wording:

- `web/webclient/actions/tests/test_rite_actions.py` and `commands/tests/test_rite_command.py`: the first completion's message has exactly one more line than a repeat's, and that extra line contains the synthetic district name; a repeat's message does not contain the district name.
- `world/rules/tests/test_landmark_rites.py`: one `map_district_discovered` event with the owner and district on a first committed rite; none on a repeat, a refusal or a rolled-back rite.
- `web/webclient-app/tests/rite/store.test.js`: `newlyLit` true after a success result with `first_completion` true, false with `false`, and cleared by leave, approach and a new perform.
- `web/webclient-app/tests/app_client_rite.test.js`: after the first completion's scene finishes, the message window shows two lines and the second contains the synthetic district name; during playback it is not shown; after leaving and re-entering only the guardian's form is shown.

## Risks / Trade-offs

- The browser line is local state: a reconnect right after the scene loses it. The district is lit regardless and the world map shows it.
