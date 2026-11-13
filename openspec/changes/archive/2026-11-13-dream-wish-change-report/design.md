# Design: the dream panel shows what changed and edits requirement rows

## Context

- After `dream-wish-stage-panel`, `components/DreamPanel.vue` is the
  prototype port without the change report, without requirement editing and
  without the farewell. Its whole-wish view reads the computed `proposal`;
  its edit sheet lists requirement rows read-only; `directionPayload()` sends
  `proposal.requirements`.
- The prototype
  (`docs/design/dream-proposal-coediting/DreamWishPrototype.vue`) contains
  the reference implementation of everything added here. Review document for
  visual treatment and wording: Storybook `Design/DreamWish` (stories
  `ChangedWish`, `NothingChanged`, `WholeWish`, `OwnHand`) and the
  "Player-Facing Wording" table of
  `docs/superpowers/specs/2026-11-13-dream-proposal-coediting-design.md`.
- `state.changes` is `null` or
  `{"summary": null|"formed"|"changed", "lists": {themes|atmosphere|participants|emphasis|exclusions: {"added": [...], "removed": [...]}}, "requirements": {"added": [rows], "removed": [rows]}}`.
- The panel wire is schema 4 and still carries `direction_parts`,
  `draft_preferences`, `requirements`, `requirement_version`
  (`world/narrative/dream_surface.py::dream_state`,
  `protocol/panels/dream.js`). After `dream-wish-text-commands` and
  `dream-wish-stage-panel` no production code reads them.

## Goals / Non-Goals

**Goals:** the three requirements of the delta spec and the schema-5 cleanup.

**Non-Goals:** the farewell; any change to actions, the service, the stage
rules or the applier; per-row server error reporting (the server's refusal
stays one message for the whole form); text-client editing.

## Decisions

1. **Change report on the card.** Port from the prototype, unchanged except
   for the rename `penned` → `finalized`: `SHORT_LABELS`, `shown`, `inked`,
   `shownCompleted`, `settleShown`, the watcher over
   `[props.state.proposal, props.state.changes]`, the watcher over
   `moreToRead`, the `settleShown()` call and `inked.value = false` in
   `onMounted`, `strokes`, `strokeText`, the card's
   `<p class="dream-ink" data-testid="dream-ink">` element, the
   `dream-keepsake--inked` class with its `@animationend` handler.
   `cardSummary` becomes `finalized ? summary : shown.proposal.summary.trim()`.
   The announced text (`strokeText`) uses the wording table's words: a list
   part is `${label}` + `新添 ${added}` when added + `劃去 ${removed}` when
   removed; the summary part is `願望成形` or `願望更動`; parts are joined
   with `、` after `女神為你改了：` and end with `。`; the no-change text is
   `女神這次沒有更動願望。`.
   The rule that holds the card back: a publication whose `completed` is
   greater than the count already settled on the card does not settle; the
   card settles when `moreToRead` becomes false. Any other publication
   settles at once.

2. **Marks in the whole-wish view.** Port `touched`, `addedIn`, `removedIn`,
   `isAdded` and the view markup that uses them (`dream-scroll--touched`,
   the `<em>` marks, `dream-scroll__new` with `<b>新添</b>`, the
   `dream-scroll__gone` paragraphs with `<s>` items). The view reads
   `shown.proposal` and `shown.changes`, so it always agrees with the card.

3. **Editable requirement rows.** Port `REQUIREMENT_KINDS`,
   `MAX_REQUIREMENTS = 8`, `reqs`, `reqsSnapshot`, `synced.reqs`, `addReq`,
   `removeReq`, the rows part of the rehydration watcher, the rows term of
   `directionDirty`, and the editable `<section class="dream-requirements">`
   markup (count, one `<select>` and one text `<input maxlength="200">` per
   row, remove button, add control hidden at the limit). Differences from the
   prototype:
   - `directionPayload().requirements` is
     `reqs.value.map((row) => ({ kind: row.kind, text: row.text.trim() }))`
     (no silent filtering of blank rows).
   - New `const reqErrors = ref([])` (row indexes). `draft()` (finalized
     only) and `confirm()` first compute the indexes of rows whose trimmed
     text is empty; when any exist they set `reqErrors`, set `refusal` to
     `有一筆需求還沒有內容。填上內容，或把那一筆移除。`, open the sheet when
     closed, focus the first invalid row's text input and return without
     dispatching. Editing or removing a row clears `reqErrors`.
   - Each row's text input carries `:aria-invalid="reqErrors.includes(index)
     || undefined"`, and an invalid row renders
     `<small class="dream-requirements__error" role="alert">請填上內容</small>`
     inside its `<li>`.
   - A new row starts with kind `place` and empty text and takes focus.

4. **Schema 5.** Remove the four keys from
   `dream_surface.dream_state` (and the now-unused `draft_direction`,
   `draft_preferences` computation and `REQUIREMENT_FIELDS` import when
   nothing else uses them), set `DREAM_SCHEMA_VERSION = 5` and `dream: 5`,
   and in `protocol/panels/dream.js` remove the four keys from the exact
   field list together with their validation blocks and the constants only
   they used (`MAX_REQUIREMENT_VERSION`). Requirement-row validation stays
   for `proposal.requirements` and `changes.requirements`. Update the
   fixtures and the literal schema number in
   `web/static/webclient/js/tests/protocol_dream.test.js`,
   `web/webclient-app/tests/dream.test.js`,
   `stories/World/DreamPanel.stories.js` and the Python tests that read the
   removed keys (`world/narrative/tests/test_dream_surface.py`,
   `web/webclient/presentation/tests/test_dream_artwork.py`). Add one
   protocol test that a payload carrying a removed key is rejected.

5. **Stories.** In `stories/World/DreamPanel.stories.js` add `ChangedWish`
   (three scripted turns), `NothingChanged` (four turns) and make
   `WholeWish` and `OwnHand` show the marks and the editable rows; the story
   server already computes `changes` with `diffProposal`.

6. **Vitest and bridge.** Add one case per scenario of the delta spec to
   `tests/dream.test.js`. The reveal-timing cases advance the typewriter by
   activating the message band (as the existing live-reveal cases do); they
   use no timers or real time. Add three bridge methods (one per ADDED
   requirement) to `web/webclient/tests/test_vue_dream_stage_evidence.py`
   without `covers_requirement`.

## Risks / Trade-offs

- [Holding the card back hides a committed change for a moment] → it is
  presentation only; the form, the payloads and the server state are
  unaffected, and a mount or reconnect shows the committed report at once.
- [A blank row is refused instead of dropped, unlike the prototype] → the
  source design asks for errors on the offending row; dropping silently
  would hide a row the player started.
