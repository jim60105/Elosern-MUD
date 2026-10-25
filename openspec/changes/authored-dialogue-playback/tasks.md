# Tasks

Read design.md and the named dependency shared contracts first. All boxes are future implementation tasks; this proposal implements nothing. Each unit includes its own tests/documentation and is bounded to 45-120 minutes.

## 1. Reusable playback state

- [ ] 1.1 Implement the composable over MessageWindow page events, including explicit final activation and no timer auto-advance; add synthetic Vitest state/page tests with same-speaker and narration transitions and docstrings describing event ownership.

## 2. Stage and focus integration

- [ ] 2.1 Bind line/name/actor-host portrait emphasis synchronously through AppClient/view.js and retire old in-flight speaker heuristic for authored scenes. Extend focus/choices tests for selection and keyboard repeat guards; document scene versus combat mode in existing component comments.

## 3. Recovery transcript and preferences

- [ ] 3.1 Key local playback by delivery/context, replay line one on mount, retain local cursor on same delivery refresh and retire on invalidation. Add transcript dedup, speed/reduced-motion and reconnect tests without persistent local storage.

## 4. Real browser acceptance

- [ ] 4.1 Extend web/tests/browser/test_browser_exploration_dialogue.py with one focused multi-line portrait/paging/focus method; register it in .github/browser-shards.json and update relevant Storybook scene fixture/showcase inventory. Verify focused Vitest, existing combat MessageWindow regression and browser method, then contract_gate.

