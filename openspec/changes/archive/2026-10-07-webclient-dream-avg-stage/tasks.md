## 1. Design pass and storyboard

- [x] 1.1 Capture the current surface with the real cloud-throne artwork (Storybook `World/DreamPanel` Storyboard/Pending/AtCap at 1600×900), run a game-UI heuristic critique, and produce the redesign brief: state machine, 1920×1080 layout, eight-frame ASCII storyboard, keyboard/ARIA map, zh-TW copy table, edge cases. Verify by recording the ranked critique and the chosen layout in `design.md` (Context, D1–D11).

## 2. Stage layout and visual tracks

- [x] 2.1 Rewrite `web/webclient-app/components/DreamPanel.vue` as a full-stage `role="dialog"` named by its 雲上王座之夢 crest. It contains the artwork, a pale pearl fallback with an ordinal-driven rose aura, the keepsake card in the sky, the reply bar docked above a 2/3-width band, and the band itself (name plate, beat page, control strip). It uses ink-lacquer glass with pale halos, gold corner brackets and no `<details>`. Verify with the Vitest "stages the dream…" and "scene artwork…" cases and Storybook screenshots at 1280×720 and 1920×1080.
- [x] 2.2 Render the exchange budget as six pips plus `尚餘 n`, with spent pips hollow and the next pip pulsing while composing or pending. Render the excitement track as a five-segment gauge plus the level label on the name plate. Expose both as `role="meter"` with the value texts `尚可交談 n 次，共 6 次` and `女神的興奮：{level}`. Verify with the Vitest structure and live-reveal cases.
- [x] 2.3 Add a CSS default for the inline-bound `--dream-ordinal` custom property. Verify that the Node UI contract "every custom property consumed without a fallback is defined" passes (481/481).

## 3. Beat pacing and the reply bar

- [x] 3.1 Implement the beat controller over the shared `useTypewriter` and `effectiveCps`:
  - arrival types the opening;
  - a live `completed` increase reveals the scene, then the line;
  - a mount or reconnect shows the latest beat in full;
  - a same-count republish replays nothing;
  - 重讀 steps back;
  - a synchronous beat watcher completes echo and notice beats at once;
  - one polite live region announces each event.

  Verify with the Vitest "types the opening…" and "reveals a response only on a live exchange increase" cases and the motion-token duration guard.
- [x] 3.2 Implement the reply bar:
  - Enter sends `dream.say` split at 2000 code points; Shift+Enter and IME composition do not send;
  - the field is disabled while pending or locked, with an echo `你：「…」` and the breathing name plate;
  - on failure the sent words refill the field and the button reads 再說一次;
  - at the cap an end bar replaces the form;
  - converging and disconnected captions.

  Verify with the Vitest Enter/IME/retry/cap cases.

## 4. Keepsake card, 念頭 sheet and exits

- [x] 4.1 Build the keepsake card: the summary or an empty-state invitation, the provenance label (取自你剛才的話 / 已記下 / 已改寫・未記下), the 歸屬 line, and four rows (① edit, ② confirm, ③ draft, ✕ awaken) with arrow-key movement and digit shortcuts 1–3 outside text fields. The single primary action is 訴說 until the cap and the confirm row at the cap. Verify with the Vitest structure, provenance/digit and "usable at cap, during generation and after failure" cases.
- [x] 4.2 Build the flat modal 念頭 sheet with its own focus trap, an inert stage and an ink scrim. It contains the summary with a code-point counter and a revert control, thread radios with a filter above eight threads and an orphaned-saved-thread option, five chip lists (Enter adds a de-duplicated chip, Backspace removes the last), and the draft/confirm footer. Draft closes the sheet and shows a toast; Escape keeps the edits. Verify with the Vitest chips/draft, latest-revision and thread-list cases.
- [x] 4.3 Validate locally:
  - an empty confirm opens the sheet with the 念頭還是空的 alert and focuses the summary;
  - the confirm row carries `aria-disabled` plus the reason 尚無念頭;
  - an over-2000 summary is shown in full, counted as over, and blocks draft and confirm.

  Verify with the Vitest "empty carry-out" and "over-length" cases.
- [x] 4.4 Escape never dispatches. In order, it closes the confirm dialog, closes the sheet, blurs a text field, or focuses the ✕ row. 醒來 dispatches at once when nothing local would be lost; otherwise it opens the 就此醒來？ `alertdialog` with focus on 回到夢中. Verify with the Vitest "never awakens on Escape…" case.
- [x] 4.5 Keep the same-session rehydration rule for summary, thread and chips (unedited fields follow the server; edited fields and unsent reply text are kept). Verify with the Vitest "rehydrates…" and "keeps an unsent direction edit…" cases.

## 5. Storybook storyboard and tests

- [x] 5.1 Update `web/webclient-app/stories/World/DreamPanel.stories.js`:
  - the fixture starts from a true arrival state;
  - the view model provides `motionLevel`/`textSpeed`;
  - the synthetic publisher advances canonical track labels;
  - add the state stories Conversing, Converging, Pending, Failed, Drafted, AtCap, ManyThreads, Disconnected and NoArt, keeping the `World/DreamPanel` title.

  Verify `pnpm run build-storybook` and `pnpm run showcase-coverage` (64/64), and capture the ten-frame after-storyboard at 1920×1080.
- [x] 5.2 Rewrite `web/webclient-app/tests/dream.test.js` for the new structure (18 cases) while keeping the strict panel-schema and command-echo checks. Verify that `npx vitest run web/webclient-app/tests/dream.test.js` passes (28/28 after the review round).
- [x] 5.3 Add the evidence bridge `web/webclient/tests/test_vue_dream_stage_evidence.py`, with one Python test per `webclient-dream-stage` requirement. Each runs its exact Vitest case names and requires exactly that many to pass, so a renamed or deleted case fails the bridge. The module is owned by the existing `web.webclient.tests` label in `.github/evennia-shards.json`, so no manifest edit is needed. Verify that the bridge and `tests.test_evennia_test_optimization_contract` pass (18 tests OK).

## 6. Verification

- [x] 6.1 Run `npx vitest run` (137 files / 1598 tests pass), the Node gate `node --test web/static/webclient/js/tests/*.test.js` (481/481 pass), and `pnpm run build` (OK).
- [x] 6.2 Run `uv run --locked python -m tools.contract_gate` (passed: traceability 1927/1927 covered, observability 0 violations, test-data 0 violations, manifests, contracts 18 OK) and the showcase evidence modules `web.webclient.tests.test_vue_showcase_world_evidence web.webclient.tests.test_vue_showcase_evidence web.webclient.tests.test_vue_dream_stage_evidence` (22 tests OK).

## 7. Review round (independent critique)

- [x] 7.1 Fix mount-time rehydration of saved preference chips: the snapshot now starts from empty lists, so a saved draft loads as 已記下, confirm keeps its themes, and 醒來 does not falsely warn. Verify with the Vitest "loads saved draft preferences on mount as already saved" case.
- [x] 7.2 Lock every control while the store would refuse the dispatch (disconnected, `mutationsLocked`, inactive phase, in-flight, `beatLocked`). Show the draft toast only once a newer state carries the saved draft. Make digit shortcuts ignore Ctrl/Meta/Alt. Keep focus on the page after 重讀. Guard the layer-open tick. Compare trimmed summaries when rehydrating. Verify with the Vitest locked-transport, draft-toast and digit cases.
- [x] 7.3 Add Vitest cases for every claim the review found unasserted: full-motion typing, gauge and next-pip state, live-region announcements, the lock, converging captions and sixth-exchange focus, the dialog name, the empty invitation and row order, Escape from a text field, summary focus and inertness, unsaved-edit protection, over-length draft refusal, and edited thread/chips plus new reply text surviving republish or failure. Verify 28/28 pass.
- [x] 7.4 Amend the spec with observable wording for the reconnect count increase, typing by motion level, the lock and disconnected caption, converging captions, modifier-free digits with sixth-exchange focus, the committed-draft toast, and saved preferences on mount. Record the dispositions in `design.md` (D5, D8b, D9, D9b and "Review dispositions"). Verify `openspec validate webclient-dream-avg-stage --strict`.
- [x] 7.5 Update the browser dream paragraph of `docs/game/command-reference.md`, which still said Esc awakens, to the new key map. Verify `tests.test_command_docs` passes (29 tests OK).

> Archive note (not an apply task): `webclient-dream-stage` is a new capability, so its canonical requirement IDs exist only after the archive's delta sync. At that point, list them with `uv run --locked python -m tools.spec_traceability list` and attach `covers_requirement` to the nine bridge methods (each method's comment names its ID), then re-run `tools.contract_gate`. This follows the established pattern for new main IDs. The live-client geometry check at 1280×720, 1920×1080 and 2560×1440 after the next image rebuild remains a follow-up (design Risks).
