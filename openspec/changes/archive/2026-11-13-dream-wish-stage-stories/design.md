# Design: the dream stories and documents follow the wish stages

## Context

After `dream-wish-stage-panel`:

- `components/DreamPanel.vue` is the port of
  `docs/design/dream-proposal-coediting/DreamWishPrototype.vue` without the
  change report, without requirement editing and without the farewell. It
  reads `props.state.stage`, the schema-4 proposal and the stage flags.
- `tests/dream.test.js` is rewritten for the schema-4 contract, and the
  evidence bridge follows the surviving and new requirements.
- `stories/World/DreamPanel.stories.js` is still the old story: the wire
  change only replaced its fixture with a valid schema-4 state, so it plays
  the old flow (direction drafts, confirm without finalize).
- `stories/fixtures/` has no dream fixtures file; `stories/fixtures.js`
  holds the small shared samples.
- `docs/game/command-reference.md` and `docs/game/commands.md` still
  describe the 念頭 sheet; `dream-wish-text-commands` already adjusted the
  text-client sections only.

## Goals / Non-Goals

**Goals:** the Storybook review surface for both stages, the opening
sentence, and the two documents.

**Non-Goals:** the component, its tests, the evidence bridge, the wire, the
actions or any server rule; the change line, changed-field marks, editable
requirement rows and the farewell (their own stages).

## Decisions

1. **Fixtures file.** Create `stories/fixtures/dream_wish.js` by copying
   `THREADS`, `OPENING` and `SCRIPT` from
   `docs/design/dream-proposal-coediting/prototype-data.js` (drop `sample`
   from each turn and drop `FAREWELLS`). Later stages extend the same file.

2. **Story file.** Rewrite `stories/World/DreamPanel.stories.js` on the
   prototype story's pattern: copy `fieldText`, `storeField`, `applyEdits`,
   `diffProposal`, `track`, `fixture` and the `render` server (stage values
   `conversing` / `finalized`; no `sample`, `farewell`, `outcome`,
   `leaveWith`; `dream.confirm` and `dream.awaken` just set `open: false`).
   The fixture must be a valid schema-4 state, so it also carries the four
   schema-3 keys with the values the server would send (`direction_parts`
   from the summary, `requirements` from the proposal,
   `draft_preferences: null`, `requirement_version: null`).
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

3. **Server copy.** In `world/narrative/dream_surface.py::OPENING` replace
   the last sentence `你可以在這裡商談故事方向，也可以隨時醒來。` with
   `你可以在這裡向她訴說願望，也可以隨時醒來。`. Nothing else in the string
   changes; the existing surface tests that pin the opening as a non-empty
   string stay green.

4. **Documents.** In `docs/game/command-reference.md` rewrite the paragraph
   that starts `網頁客戶端的等待畫面` from `夢境佔滿舞台` onward to describe:
   the wish card with its four rows, the stage indicator, the read-only view
   while speaking, the finalize confirmation, the thread choice above the
   reply bar, editing only after finalize. In `docs/game/commands.md` replace
   the remaining web statements that mention 念頭 or 記下念頭 with the same
   facts. Leave the text-client syntax rows to `dream-wish-text-commands`.

## Risks / Trade-offs

- [A story fixture drifts from the schema-4 validator] → `pnpm run
  build-storybook` plus the component's own fixture assertions fail, and
  `showcase-coverage` fails on a missing export.
- [The documents describe a panel whose marks and farewell arrive later] →
  the paragraphs are written for the staged panel only; the later stages add
  their own sentences.
