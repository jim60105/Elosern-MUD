# Design: the dream panel follows the wish stages

## Context

- `web/webclient-app/components/DreamPanel.vue` (971 lines) is the live
  panel, mounted by `AppClient.vue` while `panel('dream').state.open`.
- `docs/design/dream-proposal-coediting/DreamWishPrototype.vue` is a modified
  copy of that file and the approved reference for this surface. Its story
  `DreamWishPrototype.stories.js` plays the server; `prototype-data.js` holds
  synthetic fixtures. Review document for everything a test cannot judge
  (layout, polish, wording): the Storybook story `Design/DreamWish` together
  with the "Player-Facing Wording" table of
  `docs/superpowers/specs/2026-11-13-dream-proposal-coediting-design.md`.
- The panel state (schema 4, `dream-wish-stages`) carries `stage`
  (`"conversing"` | `"finalized"`), `proposal`, `changes`, `thread_id`,
  `thread_choices`, `can_choose_thread`, `can_input`, `can_finalize`,
  `can_edit`, `can_confirm`, `can_draft`, `drafted`, plus the schema-3 keys
  `direction_parts`, `draft_preferences`, `requirements`,
  `requirement_version`, which the new panel must not read.
- Server actions: `dream.say`, `dream.choose_thread {thread_id}`,
  `dream.finalize`, `dream.draft [direction]`, `dream.confirm {direction}`,
  `dream.awaken`, each with `session_id` and `revision`.
- `web/webclient/tests/test_vue_dream_stage_evidence.py` runs named Vitest
  cases of `tests/dream.test.js` per `webclient-dream-stage` requirement.
- The prototype differs from this change's contract in three ways: it names
  the stages `wishing` / `penned`; it implements the change line, the
  changed-field marks and editable requirement rows
  (`dream-wish-change-report`); and it implements the farewell
  (`dream-farewell-beat`).

## Goals / Non-Goals

**Goals:** the stage-aware panel described by the delta spec, its tests,
stories and documents.

**Non-Goals:** the change line and changed-field marks; editable requirement
rows; the farewell; any wire, validator, action or server-rule change;
`AppClient.vue`; removing the prototype directory.

## Decisions

1. **Port method.** Replace the `<script setup>`, `<template>` and
   `<style scoped>` of `components/DreamPanel.vue` with the prototype's, then
   apply decisions 2–6. Keep the file header comment accurate (stages, no
   provenance of "last words").

2. **Mechanical corrections.**
   - Imports use the panel's own relative paths (`../lib/...`,
     `../composables/...`, `./focus-trap.js`) exactly as the current file.
   - Remove the prop `initialLayer` and its three lines in `onMounted`.
   - Remove `state.sample`: the reply placeholder is
     `state.pending ? '女神正在聆聽……' : '向女神說出你的願望……'`.
   - Rename the computed `penned` to `finalized`, defined as
     `props.state.stage === "finalized"`, at every use. CSS class names from
     the prototype are kept unchanged.

3. **Leave out the change report** (owned by `dream-wish-change-report`).
   Do not port: `shown`, `inked`, `shownCompleted`, `settleShown`, the two
   watchers that call it, `strokes`, `strokeText`, `touched`, `addedIn`,
   `removedIn`, `isAdded`, `SHORT_LABELS`. In the template: drop the
   `<p v-if="!penned && strokes" class="dream-ink" data-testid="dream-ink">`
   element (the provenance paragraph that followed it becomes
   `v-if="provenance"`), the `dream-keepsake--inked` class and the
   `@animationend` handler on the card; in the whole-wish view drop every
   `touched(...)` class and `<em>` marker, every `isAdded(...)` class and
   `<b>新添</b>`, and every `劃去` paragraph, and read `proposal` (the computed
   over `props.state.proposal`) where the prototype reads `shown.proposal`.
   `cardSummary` is `finalized ? summary : proposal.summary.trim()`.

4. **Leave out requirement editing** (owned by `dream-wish-change-report`).
   Do not port `reqs`, `reqsSnapshot`, `synced.reqs`, `addReq`, `removeReq`,
   `MAX_REQUIREMENTS`, `REQUIREMENT_KINDS` (keep a `REQUIREMENT_LABELS`
   object with the three labels). The edit sheet's requirement section is a
   read-only list rendered only when rows exist: heading `這個願望需要`, one
   `<li>` per row with the kind label and the text, `data-testid=
   "dream-requirements"`. `directionPayload().requirements` is
   `proposal.requirements.map((row) => ({ kind: row.kind, text: row.text }))`.
   `directionDirty` compares summary, thread and lists only.

5. **Leave out the farewell** (owned by `dream-farewell-beat`). Do not port
   `leaving`, `departed`, `depart`, `defineEmits`, the watcher on
   `props.state.open`, the classes `dream-scene--leaving` /
   `dream-scene--departed`, `data-leaving`, the `dream-scene__wishlight` and
   `dream-scene__waking` elements, `:inert="!!leaving || undefined"`, the
   `v-if="!leaving"` on the reply zone, the `leaving` branches of the key
   hint, marker and toast, `if (leaving.value) return;` in the Escape branch
   and `!leaving.value &&` in the digit branch. `data-state` keeps the five
   values `pending`, `failure`, `cap`, `arrival`, `turn`; add
   `:data-stage="state.stage"`.

6. **Behaviour kept from the prototype (the contract of this change).**
   Rows: `data-row="main"`, `data-row="take"` (conversing) or
   `data-row="confirm"` (finalized), `data-row="draft"`, `data-row="awaken"`.
   Layers and test ids: whole-wish view `data-testid="dream-view"`, finalize
   confirmation `data-testid="dream-take"`, edit sheet
   `data-testid="dream-sheet"`, awaken check `data-testid="dream-confirm"`,
   thread choice `data-testid="dream-belong"`. Functions `openMain`,
   `requestTake`, `take`, `chooseThread`, `draft`, `confirm`,
   `requestAwaken`, the rehydration watcher over
   `[session_id, proposal, thread_id]`, the watcher that opens the sheet when
   `finalized` becomes true before the cap, the draft toast gated on
   `state.drafted`, and all labels are taken as written in the prototype.
   `draft()` dispatches `dream.draft` with no `direction` key while
   conversing and with `directionPayload()` when finalized.
   `directionPayload()` carries no `requirement_version`.

7. **Server copy.** In `world/narrative/dream_surface.py::OPENING` replace
   the last sentence `你可以在這裡商談故事方向，也可以隨時醒來。` with
   `你可以在這裡向她訴說願望，也可以隨時醒來。`. Nothing else in the string
   changes.

8. **Stories.** Create `stories/fixtures/dream_wish.js` by copying
   `THREADS`, `OPENING` and `SCRIPT` from
   `docs/design/dream-proposal-coediting/prototype-data.js` (drop `sample`
   from each turn and drop `FAREWELLS`). Rewrite
   `stories/World/DreamPanel.stories.js` on the prototype story's pattern:
   copy `fieldText`, `storeField`, `applyEdits`, `diffProposal`, `track`,
   `fixture` and the `render` server (stage values `conversing` /
   `finalized`; no `sample`, `farewell`, `outcome`, `leaveWith`; `dream.confirm`
   and `dream.awaken` just set `open: false`). The fixture must be a valid
   schema-4 state, so it also carries the four schema-3 keys with the values
   the server would send (`direction_parts` from the summary, `requirements`
   from the proposal, `draft_preferences: null`, `requirement_version: null`).
   Keep every existing export name of this story file (`Storyboard`,
   `Conversing`, `Converging`, `Pending`, `Failed`, `Drafted`,
   `RequirementsProposed`, `RequirementsShown`, `AtCap`, `ManyThreads`,
   `Disconnected`, `BundledDream`, `PreferredRefused`, `MissingArt`) with
   states that mean the same under the new model, and add `Arrival`,
   `ArrivalNoThreads`, `FirstWish`, `WholeWish`, `StopSpeaking`, `OwnHand`.
   A story that must show an open layer clicks the row from its wrapper's
   `onMounted` (`document.querySelector("[data-row='main']")?.click()` after
   `nextTick`); no prop is added to the component for it. The title stays
   `World/DreamPanel`, so `component-manifest.json` needs no edit; verify
   with `showcase-coverage`.

9. **Vitest.** Rewrite `tests/dream.test.js`: the `state()` fixture is a
   valid schema-4 state (conversing, empty proposal by default, with helper
   overrides for finalized). Keep the cases that do not concern the reworked
   regions (artwork, beats, budget and gauge, reply bar, protocol mirror)
   with their names unchanged where their behaviour is unchanged. Add or
   rewrite one case per scenario of the delta spec. Assertions select by
   `data-row`, `data-testid`, roles and dispatched payloads; they do not
   assert shipped wording except where the spec names a literal (`你：`, the
   dialog title). Reduced-motion and typing cases are untouched.

10. **Evidence bridge.** In
    `web/webclient/tests/test_vue_dream_stage_evidence.py`: update the
    Vitest case names of every method whose requirement survives; delete the
    two methods annotated with the removed requirements (keepsake 念頭, 念頭
    sheet); add one method per ADDED requirement listing its Vitest cases,
    without `covers_requirement` (the IDs do not exist before archive).

11. **Documents.** In `docs/game/command-reference.md` rewrite the paragraph
    that starts `網頁客戶端的等待畫面` from `夢境佔滿舞台` onward to describe:
    the wish card with its four rows, the stage indicator, the read-only
    view while speaking, the finalize confirmation, the thread choice above
    the reply bar, editing only after finalize. In `docs/game/commands.md`
    replace the remaining web statements that mention 念頭 or 記下念頭 with
    the same facts.

## Risks / Trade-offs

- [Subtracting three feature groups from the prototype can leave dangling
  references] → decisions 3–5 list every symbol; `pnpm run build` and the
  Vitest suite fail on a dangling reference.
- [The panel ignores keys the wire still carries] → removed by
  `dream-wish-change-report`.
- [Requirement rows cannot be edited in this stage] → interim of one change;
  the form still submits the rows it shows.
